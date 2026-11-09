import {
  ApiError,
  type DrugPrice,
  type MemberAnswer,
  type MemberProfile,
  type MemberRecord,
  type MemberTopic,
  type SearchResult,
  type Session,
  type SessionMode,
  type UnitRef,
  type UnitView,
  type VisitCost,
} from "@/api/types";

/**
 * Client for the prototype API described in api/README.md on web/api.
 * Paths below are the contract this UI calls. If the README uses different
 * paths, change them here only. See WEB_BUILD_LOG.md, API gaps.
 */

const root = "";

const EXPLORE_CLOSED = "Open an Explore role before";
const ROLE_NOT_OPEN = "Open that role first";
let reopening: Promise<void> | null = null;

/** The Explore role on screen. The server holds the session role, so the client opens it on every role switch. */
let exploreRole = "Member";

export function setExploreRole(role: string) {
  exploreRole = role;
}

export function openExploreRole(role: string) {
  exploreRole = role;
  return rawRequest<unknown>("/api/explore/open", { method: "POST", body: JSON.stringify({ role }) });
}

/**
 * Explore sandboxes live on the server's disk, which a deploy or restart clears while the browser
 * still believes the sandbox is open. When the server says so, open a fresh sandbox and retry once.
 */
export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await rawRequest<T>(path, init);
  } catch (error) {
    const closed = error instanceof ApiError && error.status === 400 && error.message.startsWith(EXPLORE_CLOSED);
    const otherRole = error instanceof ApiError && error.status === 403 && error.message.startsWith(ROLE_NOT_OPEN);
    if (!(closed || otherRole) || path === "/api/explore/open") {
      throw error;
    }
    reopening ??= rawRequest<unknown>("/api/explore/open", { method: "POST", body: JSON.stringify({ role: exploreRole }) })
      .then(() => undefined)
      .finally(() => {
        reopening = null;
      });
    await reopening;
    return rawRequest<T>(path, init);
  }
}

async function rawRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${root}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(0, "The knowledge service did not respond. Check that the API is running, then try again.");
  }
  if (!response.ok) {
    let detail = "";
    try {
      const body = (await response.json()) as { detail?: string; message?: string; error?: string };
      detail = body.error || body.detail || body.message || "";
    } catch {
      detail = "";
    }
    const message =
      response.status === 404
        ? detail || "That request is not available on the API yet."
        : detail || "The knowledge service could not complete that request.";
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  // The source files carry a line naming the interviewer's company. It stays in the data, because saved model
  // answers are keyed to each document's exact text, and is removed wherever the app displays it (D69).
  const body = (await response.text()).replaceAll(" Not a Humana document.", "");
  return JSON.parse(body) as T;
}

type MemberTopicRow = { index: number; label: string; question: string };

let topicCache: Promise<MemberTopicRow[]> | null = null;

function topicRows(): Promise<MemberTopicRow[]> {
  if (!topicCache) {
    topicCache = apiRequest<{ topics: MemberTopicRow[] }>("/api/explore/member/topics")
      .then((body) => body.topics)
      .catch((error) => {
        topicCache = null;
        throw error;
      });
  }
  return topicCache;
}

/**
 * The API keys sessions by an HttpOnly cookie, so there is no id to carry.
 * The id returned here only tells the UI which world is ready.
 * Explore: open the sandbox once. Demo: reset the guided database to the mode.
 */
export async function createSession(mode: SessionMode): Promise<Session> {
  if (mode === "explore") {
    await apiRequest("/api/explore/open", { method: "POST", body: JSON.stringify({ role: exploreRole }) });
    topicCache = null;
  } else {
    // A new tab joins a demo already in progress in this browser instead of wiping it. Reset stays an explicit button.
    const state = await apiRequest<{ mode?: string; step?: number; steps?: Array<{ done: boolean }> }>("/api/demo?world=guided").catch(() => null);
    // A fresh short demo starts with one step already done; a fresh full demo with none.
    const freshDone = mode === "short" ? 1 : 0;
    const done = (state?.steps ?? []).filter((item) => item.done).length;
    const inProgress = Boolean(state && state.mode === mode && ((state.step ?? 0) > 0 || done > freshDone));
    if (!inProgress) await apiRequest("/api/session/reset", { method: "POST", body: JSON.stringify({ mode }) });
  }
  return { session_id: `${mode}-${Date.now()}`, mode };
}

type MemberReply = {
  kind: string;
  reply?: string;
  chips?: string[];
  units?: UnitRef[];
  price?: DrugPrice;
  visit_cost?: VisitCost;
  abstained: boolean;
  member_text?: string;
  citation?: string;
  title?: string;
  version?: number | null;
  unit_id?: string;
  ai_source?: string;
  effective_date?: string;
  suggestions?: Array<{ label: string } | string>;
};

/** Topic questions use the topic route, which answers without recording a clarification. */
export async function memberAnswer(
  _sessionId: string,
  question: string,
  options: { channel?: "voice_bot"; memberId?: string; callId?: string } = {},
): Promise<MemberAnswer> {
  const topics = await topicRows().catch(() => [] as MemberTopicRow[]);
  const match = topics.find((topic) => topic.question.toLowerCase() === question.trim().toLowerCase());
  const extra = { member_id: options.memberId || MEMBER, ...(options.channel ? { channel: options.channel, call_id: options.callId || "" } : {}) };
  const body = match ? { topic: match.index, ...extra } : { question, ...extra };
  const reply = await apiRequest<MemberReply>("/api/explore/member", { method: "POST", body: JSON.stringify(body) });
  return {
    abstained: reply.abstained || !reply.member_text,
    member_text: reply.member_text || "",
    title: reply.title || "",
    version: reply.version ?? null,
    unit_id: reply.unit_id || "",
    citation: reply.citation || "",
    ai_source: reply.ai_source || "",
    query: question,
    effective_date: reply.effective_date,
    suggestions: (reply.suggestions || []).map((item) => (typeof item === "string" ? item : item.label)),
    kind: reply.kind,
    reply: reply.reply || "",
    chips: reply.chips || [],
    units: reply.units || [],
    price: reply.price,
    visit_cost: reply.visit_cost,
  };
}

const MEMBER = "HBR-20418";

/** An approved phone-line prompt, returned with the member topics. */
export type IvrPrompt = { unit_id: string; version: number; title: string; text: string; citation: string };

let ivrCache: Promise<Record<string, IvrPrompt>> | null = null;

/** Approved phone-line prompts: authenticate, before_amount, advocate, add_caller. */
export function ivrPrompts(): Promise<Record<string, IvrPrompt>> {
  if (!ivrCache) {
    ivrCache = apiRequest<{ ivr_prompts?: Record<string, IvrPrompt> }>("/api/explore/member/topics")
      .then((body) => body.ivr_prompts ?? {})
      .catch(() => {
        ivrCache = null;
        return {};
      });
  }
  return ivrCache;
}

/** The advocate confirms two identifiers; the server records it for this session. The client never claims it. */
export function verifyCaller(memberId: string, dateOfBirth: string) {
  return apiRequest<{ ok?: boolean; verified?: boolean }>("/api/explore/verify", {
    method: "POST",
    body: JSON.stringify({ member_id: memberId, date_of_birth: dateOfBirth }),
  });
}

/** The automated line checks the caller before any member-specific figure. */
export function phoneAuthenticate(memberId: string, dateOfBirth: string, callId = "") {
  return apiRequest<{ ok?: boolean }>("/api/explore/phone/authenticate", {
    method: "POST",
    body: JSON.stringify({ member_id: memberId, date_of_birth: dateOfBirth, call_id: callId }),
  });
}

/** A member's request to add someone who can call for them. The server records it as pending. */
export function requestAuthorizedCaller(callerName: string, relationship: string, memberId = MEMBER) {
  return apiRequest<{ confirmation?: string; status?: string; units?: UnitRef[]; message?: string }>("/api/explore/member/authorized-caller", {
    method: "POST",
    body: JSON.stringify({ member_id: memberId, caller_name: callerName, relationship }),
  });
}

/** Approved plain-language definitions (tier, coverage stage, deductible, preferred retail, mail order, out-of-pocket maximum). */
export function memberGlossary() {
  return apiRequest<{ entries?: Array<{ key: string; unit_id: string; version: number; title?: string; text: string }> }>("/api/explore/member/glossary");
}

/** One approved unit, by reference, in the wording for a channel. Used where a page shows a figure or a plan rule. */
export async function approvedUnit(unitId: string, channel = "website"): Promise<UnitRef | null> {
  const body = await apiRequest<{ unit?: { unit_id: string; version: number; title?: string; member_text?: string; text?: string; status?: string } }>(
    `/api/portal/units/${encodeURIComponent(unitId)}?world=explore&channel=${encodeURIComponent(channel)}`,
  ).catch(() => null);
  const unit = body?.unit;
  if (!unit || unit.status !== "approved") return null;
  return { unit_id: unit.unit_id, version: unit.version, title: unit.title || "", text: unit.member_text || unit.text || "", citation: "" } as UnitRef;
}

export function memberProfile(memberId = MEMBER) {
  return apiRequest<MemberProfile>(`/api/explore/member/profile?member_id=${encodeURIComponent(memberId)}`);
}

export function drugPrice(drugId: string, pharmacy: string, days: number, memberId = MEMBER) {
  const query = new URLSearchParams({ member_id: memberId, drug_id: drugId, pharmacy, days: String(days) });
  return apiRequest<DrugPrice>(`/api/explore/member/drug-price?${query}`);
}

export function visitCost(visit: string, network: string, memberId = MEMBER) {
  const query = new URLSearchParams({ member_id: memberId, visit, network });
  return apiRequest<VisitCost>(`/api/explore/member/visit-cost?${query}`);
}

export function memberRecord(memberId: string, role: string, verified: boolean) {
  const query = new URLSearchParams({ member_id: memberId, role, verified: String(verified) });
  return apiRequest<MemberRecord>(`/api/explore/member-record?${query}`);
}

type ApiUnit = Omit<UnitView, "kb_scope" | "audience" | "channels" | "verbatim"> & {
  kb_scope: string[] | string;
  audience: string[] | string;
  channels: string[] | string;
};

function joined(value: string[] | string | undefined) {
  return Array.isArray(value) ? value.join(", ") : value || "";
}

export async function searchAnswers(
  _sessionId: string,
  role: string,
  question: string,
  caller?: { memberId: string; verified: boolean },
): Promise<SearchResult> {
  type AskBody = {
    result?: Omit<SearchResult, "unit"> & { unit: ApiUnit | null };
    kind?: string;
    price?: SearchResult["price"];
    visit_cost?: SearchResult["visit_cost"];
    price_options?: SearchResult["price_options"];
    units?: UnitRef[];
    text?: string;
    message?: string;
  };
  const body = await apiRequest<AskBody>("/api/explore/ask", {
    method: "POST",
    body: JSON.stringify({ role, query: question, ...(caller ? { member_id: caller.memberId, verified: caller.verified } : {}) }),
  });
  // An unverified caller gets only the approved rule, with no search result: show the rule as the answer.
  if (!body.result) {
    const rule = body.units?.[0];
    // The rule arrives as a reference; load its record so the citation names the approver and date.
    const record = rule
      ? await apiRequest<{ unit?: ApiUnit } & Partial<ApiUnit>>(`/api/units/${encodeURIComponent(rule.unit_id)}?world=explore`).catch(() => null)
      : null;
    const full = (record && ("unit" in record && record.unit ? record.unit : record)) as Partial<ApiUnit> | null;
    return {
      verify_first: true,
      abstained: !rule,
      query: question,
      role,
      ai_source: "",
      note: "",
      searched: [],
      unit: rule
        ? {
            unit_id: rule.unit_id,
            version: rule.version,
            title: rule.title,
            text: rule.text,
            type: full?.type || "policy",
            approved_by: full?.approved_by,
            approved_on: full?.approved_on,
            effective_date: full?.effective_date,
            kb_scope: "",
            audience: "",
            channels: "",
            verbatim: false,
          } as unknown as UnitView
        : null,
    };
  }
  // Plan-data answers (price, visit cost, options) come back beside the search result.
  const { unit, ...searched } = body.result;
  const rest = {
    ...searched,
    ...(body.kind ? { kind: body.kind } : {}),
    ...(body.price ? { price: body.price } : {}),
    ...(body.visit_cost ? { visit_cost: body.visit_cost } : {}),
    ...(body.price_options ? { price_options: body.price_options } : {}),
    ...(body.units ? { units: body.units } : {}),
  };
  return {
    ...rest,
    unit: unit
      ? {
          ...unit,
          kb_scope: joined(unit.kb_scope),
          audience: joined(unit.audience),
          channels: joined(unit.channels),
          verbatim: unit.type === "verbatim",
        }
      : null,
  };
}

export function memberTopics(_sessionId: string): Promise<MemberTopic[]> {
  return topicRows().then((rows) => rows.map((row) => ({ label: row.label, question: row.question })));
}

export type FeedbackBody = {
  source: "advocate" | "channel" | "member";
  role: string;
  kind: string;
  question: string;
  unit_id: string;
  note: string;
};

export function sendFeedback(_sessionId: string, body: FeedbackBody) {
  const source = body.source === "member" ? "channel" : body.source;
  return apiRequest<{ ok: boolean }>("/api/feedback", {
    method: "POST",
    body: JSON.stringify({ ...body, source, world: "explore" }),
  });
}

export function flagAnswer(
  sessionId: string,
  body: { role: string; kind: string; question: string; unit_id: string; note: string },
) {
  return sendFeedback(sessionId, { source: "advocate", ...body });
}
