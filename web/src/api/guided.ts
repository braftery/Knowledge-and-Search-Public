import { apiRequest } from "@/api/client";

/** Guided and Explore reads described in api/README.md. The demo uses world "guided". */

export type World = "guided" | "explore";

export type ApiDiff = { kind: "equal" | "remove" | "add"; text: string };

export type UndoState = {
  available: boolean;
  label: string;
  world: string;
  screen?: number;
  restore_screen?: number;
};

export type Mutation = {
  ok: boolean;
  message: string;
  undo?: UndoState;
  demo?: { mode?: string; step?: number; short_path?: boolean };
};

export type IfYouApprove = {
  searchable_by?: string[];
  appears_in?: string[];
  replaces?: string;
  approved_by?: string;
  applies_to?: string;
};

export type Unit = {
  /** "Knowledge Ops author" when a person added the unit from the source; otherwise the AI extracted it. */
  drafted_by?: string;
  domain?: string;
  /** The exact passage of the source document this unit came from. */
  source_span?: string;
  /** Set when the AI thinks this repeats an approved unit. */
  duplicate_of?: string;
  /** Set when a person edited this unit's tags before the bulk confirm. */
  tags_edited_by?: string;
  unit_id: string;
  version: number;
  title: string;
  type: string;
  text: string;
  member_text?: string;
  tags?: string[];
  audience?: string[];
  channels?: string[];
  kb_scope?: string[];
  status?: string;
  source_quote?: string;
  source_doc?: string;
  document_name?: string;
  approved_by?: string;
  approved_on?: string;
  effective_date?: string;
  review_by?: string;
  applicability?: string;
  notes?: string;
  number?: number;
  stale?: boolean;
  proposed_text?: string;
  requires_legal?: boolean;
  source_mismatch?: boolean;
  verbatim_altered?: boolean;
  search_visible?: boolean;
  if_you_approve?: IfYouApprove;
  routing_reason?: string;
};

export type TodayView = {
  ran: boolean;
  query: string;
  message: string;
  cards: Array<{ title: string; signed: string; text: string; diff: ApiDiff[] }>;
};

export type ExtractionView = {
  extracted: boolean;
  tags_confirmed: boolean;
  document: { doc_id: string; title: string; body: string };
  units: Unit[];
  unit_count: number;
  verbatim_matching_source: number;
  verbatim_total: number;
  audience_corrections: Array<{
    unit_id: string;
    title: string;
    ai_audience: string;
    audience: string;
    applied: boolean;
  }>;
  message: string;
};

export type Pair = {
  a_id: string;
  b_id: string;
  a_title: string;
  b_title: string;
  a_text: string;
  b_text: string;
  a_doc: string;
  b_doc: string;
  a_status: string;
  b_status: string;
  relation: string;
  confidence: number | string | null;
  reason: string;
  differing_phrases: Array<{ a: string; b: string }>;
  diff: ApiDiff[];
  human_line: string;
};

export type CopiesView = {
  ready: boolean;
  message: string;
  pairs: Pair[];
  counts: { near_duplicate: number; exact: number; conflict: number; all: number };
  canonical?: boolean;
  escalated?: boolean;
  can_keep_canonical?: boolean;
  can_escalate?: boolean;
  website_merge?: {
    into_unit_id: string;
    member_text: string;
    units: Array<{ unit_id: string; text: string; status: string }>;
    merged: boolean;
  } | null;
};

export type LegalQueue = {
  ready: boolean;
  count: number;
  waiting: Unit[];
  can_approve_all: boolean;
  held: Array<{ unit_id: string; title: string; notes: string }>;
  approved_count: number;
  message: string;
};

export type AuthorQueue = {
  count: number;
  waiting: Unit[];
  can_approve_all: boolean;
  message: string;
};

export type ConflictPlan = {
  id: string;
  label: string;
  open: boolean;
  resolve_in_demo: boolean;
  chosen_unit_id: string;
  chosen_title: string;
  chosen_text: string;
  chosen_doc: string;
  retire_unit_ids: string[];
  reason_suggestion: string;
  recorded_reason: string;
  comparisons: Array<{ unit_id: string; title: string; doc: string; text: string; diff: ApiDiff[] }>;
};

export type ConflictsView = { count_open: number; plans: ConflictPlan[]; message: string };

export type InboxItem = {
  kind: "approval" | "conflict";
  id: string;
  title: string;
  routing_reason?: string;
  unit?: Unit;
  conflict?: ConflictPlan;
};

export type Inbox = { count: number; items: InboxItem[]; message: string };

export type SearchHit = {
  abstained: boolean;
  unit: Unit | null;
  searched: string[];
  note?: string;
  ai_source?: string;
  query?: string;
  role?: string;
};

export type SearchPrompts = {
  cost: string;
  abstain: string;
  misspell: string;
  pharmacy_only: string;
  roles: string[];
};

export type ChannelsView = {
  ready: boolean;
  revised?: boolean;
  live: Unit | null;
  previous: Unit | null;
  advocate_diff?: ApiDiff[];
  member_diff?: ApiDiff[];
  revision_ready?: boolean;
  revision_preview?: {
    find: string;
    replace: string;
    advocate_text: string;
    advocate_diff: ApiDiff[];
    member_text: string;
    member_diff: ApiDiff[];
    next_version: number;
  };
  message: string;
};

export type Gap = {
  id: string;
  cluster: string;
  query_example: string;
  search_count: number;
  roles: string[];
  draft_title: string;
  draft_text: string;
  suggested_kb: string;
  unit_id?: string;
  findability?: boolean;
  status: string;
  placeholders: string[];
  checklist: string[];
  queries: string[];
  invented_figures: string[];
  reason: string;
};

export type GapsView = { count: number; gaps: Gap[]; message: string };

export type DriftView = {
  unit_id?: string;
  live_text?: string;
  live_version?: number;
  member_text?: string;
  stale?: boolean;
  proposed_text?: string;
  material?: boolean;
  cosmetic?: boolean;
  sent?: boolean;
  summary?: string;
  cosmetic_summary?: string;
  /** A cosmetic edit inside a verbatim span, sent to Legal. */
  verbatim_to_legal?: boolean;
  change?: string;
  material_line?: string;
  cosmetic_line?: string;
  events?: Array<{ ts?: string; kind?: string; flagged?: boolean; status?: string; summary?: string }>;
  prepared?: {
    cosmetic?: { old_span: string; new_span: string; diff: ApiDiff[] };
    material?: { old_span: string; new_span: string; diff: ApiDiff[] };
  };
  ready: boolean;
  message: string;
};

export type QualityRow = Record<string, string>;

export type QualityView = {
  scored: boolean;
  message: string;
  held_out_pass?: number;
  held_out_total?: number;
  open_conflicts?: Array<{ id: string; label: string }>;
  tiles?: Array<{ key: string; label: string; display: string; detail: string; note?: string }>;
  verbatim_source?: { label?: string; ok?: number; total?: number; display?: string; note?: string };
  golden_table?: { columns: string[]; rows: QualityRow[]; held_out: QualityRow[] };
  dedup_table?: { columns: string[]; rows: QualityRow[] };
  misses?: Array<{ miss: string; next_step: string }>;
  scored_questions?: number;
  held_out_questions?: number;
};

export type MyWorkItem = {
  group: string;
  id: string;
  title: string;
  kind: string;
  unit?: Unit | null;
  feedback?: {
    id: number;
    kind: string;
    kind_label?: string;
    question?: string;
    note?: string;
    status?: string;
    resolution?: string;
    unit_id?: string;
  };
  gap?: Gap;
  document?: AuthorDocument;
};

export type MyWork = {
  count: number;
  items: MyWorkItem[];
  groups: Array<{ group: string; count: number; items: MyWorkItem[] }>;
  empty_groups: string[];
  waiting_on_legal: Array<{ id: string; label: string }>;
  message: string;
};

export type Insights = {
  open_gaps: number;
  drift_waiting: number;
  expired_count: number;
  tiles: Array<{ key: string; label: string; display: string; detail: string }>;
  held_out: { pass: number; total: number };
  top_gaps: Gap[];
  /** Questions an expert said the company has no answer for. No unit can be written until the business decides. */
  process_gaps?: Array<{ id: string; cluster: string; reason?: string; search_count?: number }>;
  drift: { material: boolean; sent: boolean; waiting: boolean; summary: string };
  expired_units: Unit[];
  feedback: { week_start?: string; by_kind?: Array<{ kind: string; count: number; label: string }> };
  wrapups?: WrapupSummary;
  acknowledgements?: Array<{ unit_id: string; title: string; version: number; acknowledged_by: string[]; pending: string[] }>;
  message: string;
};

export type PortalQuickStart = {
  base: string;
  sample_request: string;
  sample_unit: Record<string, unknown> | null;
  sample_event: Record<string, unknown> | null;
  endpoints: Array<{ method: string; path: string; what: string }>;
};

function worldQuery(path: string, world: World) {
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}world=${world}`;
}

function post<T>(path: string, body: Record<string, unknown> = {}, world: World = "guided") {
  return apiRequest<T>(path, { method: "POST", body: JSON.stringify({ world, ...body }) });
}

export function getToday(world: World = "guided") {
  return apiRequest<TodayView>(worldQuery("/api/demo/today", world));
}

export function runToday(world: World = "guided") {
  return post<Mutation & { today: TodayView }>("/api/demo/today", {}, world);
}

export function getExtraction(world: World = "guided") {
  return apiRequest<ExtractionView>(worldQuery("/api/demo/extraction", world));
}

export function extractUnits(world: World = "guided") {
  return post<Mutation & { extraction: ExtractionView }>("/api/demo/extract", {}, world);
}

export function confirmTags(world: World = "guided") {
  return post<Mutation & { extraction: ExtractionView }>("/api/demo/confirm-tags", {}, world);
}

export function getCopies(world: World = "guided") {
  return apiRequest<CopiesView>(worldQuery("/api/demo/copies", world));
}

export function keepCanonical(world: World = "guided") {
  return post<Mutation>("/api/demo/keep-canonical", {}, world);
}

export function escalateConflicts(world: World = "guided") {
  return post<Mutation>("/api/demo/escalate", {}, world);
}

export function getLegalQueue(world: World = "guided") {
  return apiRequest<LegalQueue>(worldQuery("/api/legal/queue", world));
}

export function getAuthorQueue(world: World = "guided") {
  return apiRequest<AuthorQueue>(worldQuery("/api/author/queue", world));
}

export function getConflicts(world: World = "guided") {
  return apiRequest<ConflictsView>(worldQuery("/api/conflicts", world));
}

export function getInbox(world: World = "explore") {
  return apiRequest<Inbox>(worldQuery("/api/legal/inbox", world));
}

export function approveLegal(unitId?: string, world: World = "guided") {
  return post<Mutation>("/api/legal/approve", unitId ? { unit_id: unitId } : {}, world);
}

export function approveLegalAll(world: World = "guided") {
  return post<Mutation>("/api/legal/approve-all", {}, world);
}

export function approveAuthor(unitId: string, world: World = "guided") {
  return post<Mutation>("/api/author/approve", { unit_id: unitId }, world);
}

export function approveAuthorAll(world: World = "guided") {
  return post<Mutation>("/api/author/approve-all", {}, world);
}

export function declineLegal(unitId: string, reason: string, world: World = "guided") {
  return post<Mutation>("/api/legal/decline", { unit_id: unitId, reason }, world);
}

export function resolveConflict(reason: string, conflictId?: string, world: World = "guided") {
  return post<Mutation>("/api/conflicts/resolve", conflictId ? { conflict_id: conflictId, reason } : { reason }, world);
}

export function getSearchPrompts() {
  return apiRequest<SearchPrompts>("/api/search/prompts");
}

export function searchRole(role: string, query: string, record = true, world: World = "guided") {
  return post<Mutation & { result: SearchHit }>("/api/search", { role, query, record }, world);
}

export function searchBoth(query: string, record = true, world: World = "guided") {
  return post<Mutation & { query: string; results: SearchHit[] }>("/api/search/both", { query, record }, world);
}

export function getChannels(world: World = "guided") {
  return apiRequest<ChannelsView>(worldQuery("/api/channels", world));
}

/** Publish the prepared revision, or wording Legal typed (text for advocates, member_text for members). */
export function publishChannels(world: World = "guided", wording?: { text?: string; member_text?: string }) {
  return post<Mutation & { channels: ChannelsView; saved_answers?: string }>("/api/channels/publish", { ...(wording ?? {}) }, world);
}

/** Record a person's tag, audience and domain decision for one extracted unit. */
export function setUnitTags(unitId: string, body: { audience: string; domain: string; tags: string[] }, world: World = "guided") {
  return post<Mutation>(`/api/demo/units/${encodeURIComponent(unitId)}/tags`, body, world);
}

export type Workload = {
  by_type: Record<string, number>;
  by_risk_tier: Record<string, number>;
  minutes_per_tier: Record<string, number>;
  estimated_minutes: number;
  total_hours: number;
  queue_count: number;
  assumptions: string;
  proposed_tiering: { legal: string; knowledge_ops_batch: string };
  note?: string;
};

export function getWorkload(world: World = "explore") {
  return apiRequest<Workload>(worldQuery("/api/legal/workload", world));
}

export function extendReview(unitId: string, reason: string, reviewBy: string, world: World = "explore") {
  return post<Mutation>("/api/legal/review/extend", { unit_id: unitId, reason, review_by: reviewBy }, world);
}

export function retireReviewUnit(unitId: string, reason: string, world: World = "explore") {
  return post<Mutation>("/api/legal/review/retire", { unit_id: unitId, reason }, world);
}

export function acceptLinkReview(unitId: string, world: World = "explore") {
  return post<Mutation>("/api/legal/link-review/accept", { unit_id: unitId }, world);
}

export function getExpiredUnits(world: World = "explore") {
  return apiRequest<{ count: number; units: Unit[] }>(worldQuery("/api/units/expired", world));
}

export function getVersions(unitId: string, world: World = "guided") {
  return apiRequest<{ unit_id: string; versions: Unit[]; moments: string[] }>(
    worldQuery(`/api/units/${encodeURIComponent(unitId)}/versions`, world),
  );
}

export function getUnits(query: string, world: World = "guided") {
  return apiRequest<{ count: number; units: Unit[] }>(worldQuery(`/api/units${query ? `?${query}` : ""}`, world));
}

export function getUnit(unitId: string, world: World = "guided") {
  return apiRequest<{ unit: Unit; versions: Array<{ version: number; status: string; approved_by?: string; effective_date?: string }>; copies: Unit[] }>(
    worldQuery(`/api/units/${encodeURIComponent(unitId)}`, world),
  );
}

export function getGaps(world: World = "guided") {
  return apiRequest<GapsView>(worldQuery("/api/gaps", world));
}

export function actOnGap(gapId: string, action: "write" | "fix_process" | "dismiss", reason: string, world: World = "guided") {
  return post<Mutation & { gaps: GapsView }>(`/api/gaps/${encodeURIComponent(gapId)}`, { action, reason }, world);
}

export function getDrift(world: World = "guided") {
  return apiRequest<DriftView>(worldQuery("/api/drift", world));
}

export function applyDrift(kind: "cosmetic" | "material", world: World = "guided") {
  return post<Mutation & { drift: DriftView }>("/api/drift", { kind }, world);
}

export function sendDrift(world: World = "guided") {
  return post<Mutation & { drift: DriftView }>("/api/drift/send", {}, world);
}

export function getQuality(world: World = "guided") {
  return apiRequest<QualityView>(worldQuery("/api/quality", world));
}

export function scoreQuality(world: World = "guided") {
  return post<Mutation & { quality: QualityView }>("/api/quality/score", {}, world);
}

export function getUndo(world: World = "guided") {
  return apiRequest<UndoState>(worldQuery("/api/undo", world));
}

export function undoWorld(world: World = "guided") {
  return post<Mutation>("/api/undo", {}, world);
}

export function setDemoStep(step: number) {
  return post<Mutation>("/api/demo/step", { step });
}

export function resetGuided(mode: "start" | "short" | "jump") {
  return post<Mutation>("/api/session/reset", { mode });
}

export function getMyWork() {
  return apiRequest<MyWork>("/api/explore/my-work");
}

export function getInsights() {
  return apiRequest<Insights>("/api/explore/insights");
}

export function getFeedbackOpen(route: "author" | "product", world: World) {
  return apiRequest<{ count: number; items: Array<Record<string, unknown>> }>(
    worldQuery(`/api/feedback/open?route=${route}`, world),
  );
}

export function resolveFeedback(id: number, resolution: string, world: World) {
  return post<Mutation>(`/api/feedback/${id}/resolve`, { resolution }, world);
}

export function getFeedbackProduct(world: World) {
  return apiRequest<{ total: number; groups: Array<{ kind: string; count: number; examples: string[] }>; message: string }>(
    worldQuery("/api/feedback/product", world),
  );
}

export function getFeedbackSummary(world: World) {
  return apiRequest<{ week_start: string; by_kind: Array<{ kind: string; count: number; label: string }> }>(
    worldQuery("/api/feedback/summary", world),
  );
}

export function getPortalQuickStart(world: World = "explore") {
  return apiRequest<PortalQuickStart>(worldQuery("/api/portal/quick-start", world));
}

export function getPortalUnits(world: World = "explore") {
  return apiRequest<{ count: number; units: Array<Record<string, unknown>> }>(worldQuery("/api/portal/units", world));
}

export function getPortalEvents(world: World = "explore") {
  return apiRequest<{ events: Array<Record<string, unknown>>; message: string }>(worldQuery("/api/portal/events", world));
}

export function getPortalAnswers(question: string, role: string, world: World = "explore") {
  const params = new URLSearchParams({ question, role, world });
  return apiRequest<Record<string, unknown>>(`/api/portal/answers?${params.toString()}`);
}

export function getExpired(world: World = "guided") {
  return apiRequest<{ count: number; units: Unit[]; message: string }>(worldQuery("/api/units/expired", world));
}

export function getDocuments(world: World = "guided") {
  return apiRequest<{ documents: Array<{ doc_id: string; title: string; name: string; legal_signed: string; kb: string; unit_count: number }> }>(
    worldQuery("/api/documents", world),
  );
}

/** One source document with its full text and the units extracted from it. */
export function getDocument(docId: string, world: World = "guided") {
  return apiRequest<{ doc_id: string; title: string; name: string; legal_signed: string; body: string; units: Unit[] }>(
    worldQuery(`/api/documents/${encodeURIComponent(docId)}`, world),
  );
}

export type AuthorDraft = {
  id: string;
  cluster: string;
  status: string;
  draft_title?: string;
  draft_text: string;
  draft_member_text: string;
  draft_type: string;
  unit_id: string;
  placeholders: string[];
  open_placeholders: string[];
  invented_figures: string[];
  has_invented_figures: boolean;
  live: boolean;
  can_send: boolean;
  placeholder_sources?: PlaceholderSource[];
  search_count?: number;
  roles?: string[] | string;
  /** What the AI found when it searched every Harbor document for this question. */
  candidate?: GapCandidate | null;
};

export type GapCandidate = {
  kind: "" | "document" | "unit";
  ref: string;
  quote: string;
  fill: string;
  trust: "review_backlog" | "unreviewed" | "approved" | "none";
  trust_label: string;
  note: string;
  owner_role: string;
  source_name: string;
  source_status: string;
};

export type AuthorReturned = {
  unit_id: string;
  title: string;
  text: string;
  member_text: string;
  placeholders: string[];
  can_send: boolean;
  reason?: string;
  /** Legal's send-back reason is stored here. */
  notes?: string;
  type?: string;
};

/** A placeholder in a gap draft and where its fact comes from. */
export type PlaceholderSource = {
  index: number;
  token: string;
  kind: "" | "unit" | "document" | "request";
  ref: string;
  quote: string;
  request_id: string;
  filled_text: string;
  sourced: boolean;
  filled: boolean;
};

export type ReviewAction = "approve" | "send_to_legal" | "edit" | "reject";

/** Knowledge Ops decides on one extracted unit. */
export function reviewUnit(
  unitId: string,
  action: ReviewAction,
  body: { reason?: string; text?: string; member_text?: string; type?: string; tags?: string[]; audience?: string[] } = {},
) {
  return post<Mutation & { status?: string }>(`/api/author/units/${encodeURIComponent(unitId)}/review`, { action, ...body }, "explore");
}

export type AuthorDocument = {
  doc_id: string;
  title: string;
  name: string;
  kb: string;
  waiting_for_ko: number;
  with_legal: number;
  sent_back: number;
  approved: number;
  rejected: number;
  blocked: number;
};

/** Knowledge Ops turns a passage the AI missed into a unit. The passage must be word for word in the document. */
export function addUnitFromSpan(
  docId: string,
  body: { span: string; title: string; type: string; audience: string[]; tags: string[] },
) {
  return post<Mutation & { unit_id: string; routing_reason?: string; requires_legal?: boolean }>(
    `/api/author/documents/${encodeURIComponent(docId)}/units`,
    body,
    "explore",
  );
}

export function getAuthorDocuments(all = false) {
  return apiRequest<{ count: number; documents: AuthorDocument[] }>(`/api/author/documents?world=explore${all ? "&all=true" : ""}`);
}

export function groundPlaceholder(
  gapId: string,
  index: number,
  body: { kind: "unit" | "document" | "request"; ref?: string; quote?: string; owner_role?: string; question?: string },
) {
  return post<Mutation & { placeholders?: PlaceholderSource[] }>(
    `/api/author/gaps/${encodeURIComponent(gapId)}/placeholders/${index}/source`,
    body,
    "explore",
  );
}

export function fillPlaceholder(gapId: string, index: number, text: string) {
  return post<Mutation>(`/api/author/gaps/${encodeURIComponent(gapId)}/placeholders/${index}/fill`, { text }, "explore");
}

export type SourceRequest = {
  id: string;
  gap_id: string;
  placeholder_index: number;
  owner_role: string;
  question: string;
  status: string;
  statement: string;
  signer: string;
  doc_id: string;
  mark: string;
  answered_at: string;
  outcome?: string;
};

export function getSourceRequests() {
  return apiRequest<{ count: number; requests: SourceRequest[] }>("/api/explore/source-requests?world=explore");
}

export function answerSourceRequest(id: string, statement: string, signer: string, noPolicy = false) {
  return post<Mutation>(`/api/explore/source-requests/${encodeURIComponent(id)}/answer`, { statement, signer, no_policy: noPolicy }, "explore");
}

export function dismissGap(gapId: string, kind: "already_answered" | "out_of_scope", reason: string, unitId = "") {
  return post<Mutation>(`/api/author/gaps/${encodeURIComponent(gapId)}/dismiss`, { kind, reason, unit_id: unitId }, "explore");
}

export function markNoSource(gapId: string, reason: string) {
  return post<Mutation>(`/api/author/gaps/${encodeURIComponent(gapId)}/no-source`, { reason }, "explore");
}

export type AuthorDrift = {
  id: number;
  unit_id: string;
  /** material, uncertain (the AI is not sure it matters), removed (the source passage was deleted), cosmetic_verbatim. */
  kind?: string;
  kind_label?: string;
  title?: string;
  type?: string;
  doc_id?: string;
  legacy?: boolean;
  version?: number;
  old_wording: string;
  new_wording: string;
  source_before?: string;
  source_after?: string;
  summary?: string;
  queue: string;
  status: string;
};

export type LegalDrift = {
  id: number;
  unit_id: string;
  version?: number;
  old_wording: string;
  new_wording: string;
  source_before?: string;
  source_after?: string;
  summary?: string;
  member_text?: string;
};

/** Material source changes on Legal wording, waiting for the Legal approver. */
export function getLegalDrift(world: World = "explore") {
  return apiRequest<{ count: number; items: LegalDrift[]; message: string }>(worldQuery("/api/legal/drift", world));
}

export function approveLegalDrift(world: World = "explore") {
  return post<Mutation>("/api/legal/drift/approve", {}, world);
}

export function returnLegalDrift(reason: string, world: World = "explore") {
  return post<Mutation>("/api/legal/drift/return", { reason }, world);
}

export function getAuthorDrift() {
  return apiRequest<{ items: AuthorDrift[]; automatic: Array<{ id: number; unit_id: string; summary: string; actor: string }> }>(
    "/api/author/drift?world=explore",
  );
}

export type DriftAction = "accept_fix" | "edit_and_accept" | "keep_current" | "confirm_cosmetic" | "retire";

export function actOnAuthorDrift(id: number, action: DriftAction, body: { reason?: string; text?: string } = {}) {
  return post<Mutation>(`/api/author/drift/${id}`, { action, ...body }, "explore");
}

/** Every source change waiting for Legal, in the same shape as Knowledge Ops' list. */
export function getLegalSourceChanges() {
  return apiRequest<{ count: number; items: AuthorDrift[] }>("/api/legal/source-changes?world=explore");
}

export function actOnLegalSourceChange(id: number, action: DriftAction, body: { reason?: string; text?: string } = {}) {
  return post<Mutation>(`/api/legal/source-changes/${id}`, { action, ...body }, "explore");
}

export type AuthorEdits = { count: number; gaps: AuthorDraft[]; returned: AuthorReturned[]; message: string };

export function getAuthorEdits(world: World = "explore") {
  return apiRequest<AuthorEdits>(worldQuery("/api/author/edits", world));
}

export function editGapDraft(gapId: string, text: string, memberText: string, world: World = "explore") {
  return post<Mutation>(`/api/author/gaps/${encodeURIComponent(gapId)}`, { text, member_text: memberText }, world);
}

export function sendGapDraft(gapId: string, world: World = "explore") {
  return post<Mutation & { unit_id?: string; queue?: string; routing_reason?: string }>(`/api/author/gaps/${encodeURIComponent(gapId)}/send`, {}, world);
}

export function editReturnedUnit(unitId: string, text: string, memberText: string, world: World = "explore") {
  return post<Mutation>(`/api/author/units/${encodeURIComponent(unitId)}`, { text, member_text: memberText }, world);
}

export function sendReturnedUnit(unitId: string, world: World = "explore") {
  return post<Mutation & { queue?: string; routing_reason?: string }>(`/api/author/units/${encodeURIComponent(unitId)}/send`, {}, world);
}

// Call wrap-up and change acknowledgements (Explore). Contract: docs/cursor-prompts/wrapup-and-acknowledgements.md

export type WrapupOutcome = "resolved" | "follow_up" | "transferred";

export type WrapupSummary = { count: number; verbatim_required: number; verbatim_confirmed: number; follow_ups: number };

export type Wrapup = {
  id: string;
  role: string;
  call_id: string;
  call_reason: string;
  unit_ids: string[];
  displayed_units?: Array<{ unit_id: string; version: number; text_hash?: string; superseded_read?: boolean }>;
  read_verbatim: boolean | null;
  outcome: WrapupOutcome;
  note: string;
  created_at: string;
};

export function saveWrapup(body: {
  role: string;
  call_id: string;
  call_reason: string;
  unit_ids: string[];
  displayed_units?: Array<{ unit_id: string; version: number; text: string }>;
  read_verbatim: boolean | null;
  outcome: WrapupOutcome;
  note: string;
}) {
  return post<Mutation & { wrapup: Wrapup; summary: WrapupSummary }>("/api/explore/wrapup", body, "explore");
}

export function getWrapups() {
  return apiRequest<{ summary: WrapupSummary; items: Wrapup[] }>(worldQuery("/api/explore/wrapups", "explore"));
}

export type UnitChange = {
  unit_id: string;
  title: string;
  type: string;
  version: number;
  previous_version: number;
  approved_on: string;
  approved_by: string;
  text: string;
  previous_text: string;
  diff: ApiDiff[];
  acknowledged: boolean;
};

export type ChangesView = { role: string; pending: number; changes: UnitChange[] };

export function getChanges(role: string) {
  return apiRequest<ChangesView>(`${worldQuery("/api/explore/changes", "explore")}&role=${encodeURIComponent(role)}`);
}

export function acknowledgeChange(role: string, unitId: string, version: number) {
  return post<Mutation & { changes: ChangesView }>("/api/explore/changes/acknowledge", { role, unit_id: unitId, version }, "explore");
}

export type DemoState = {
  mode: string;
  step: number;
  steps: Array<{ number: number; name: string; title: string; done: boolean; on_short_path: boolean }>;
};

export function getDemoState() {
  return apiRequest<DemoState>(worldQuery("/api/demo", "guided"));
}

export type AsOf = {
  unit_id: string;
  version: number;
  text: string;
  member_text?: string;
  effective_date?: string;
  approver?: string;
  note?: string;
  /** Every version live at some point on that calendar day, with start and end ("" while still live). */
  versions_that_day?: Array<{ version: number; start: string; end: string }>;
};

/** The version of a unit that was live at a moment in time, for audits ("what did we say on this date?"). */
export function getAsOf(unitId: string, timestamp: string, world: World = "explore") {
  return apiRequest<AsOf>(`${worldQuery(`/api/units/${encodeURIComponent(unitId)}/as-of`, world)}&timestamp=${encodeURIComponent(timestamp)}`);
}
