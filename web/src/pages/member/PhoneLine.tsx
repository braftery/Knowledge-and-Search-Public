import { useMemo } from "react";
import { useMemberTextSize } from "@/pages/member/text-size";
import { Bot, Phone, User } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { ivrPrompts, memberAnswer, memberTopics, phoneAuthenticate, type IvrPrompt } from "@/api/client";
import type { MemberAnswer } from "@/api/types";
import { useQuery } from "@/api/use-query";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";

export function PhoneLine({
  sessionId,
  sessionError,
  onRetry,
}: {
  sessionId: string | null;
  sessionError?: string | null;
  onRetry?: () => void;
}) {
  useMemberTextSize();
  const [params, setParams] = useSearchParams();
  const topics = useQuery(`phone-topics:${sessionId ?? "none"}`, () => memberTopics(sessionId as string), Boolean(sessionId));
  const prompts = [...(topics.data ?? []).map((topic) => topic.question), ...EXTRA_PROMPTS.filter((extra) => !topics.data?.some((topic) => topic.question === extra))];
  const selected = params.get("prompt") || prompts[0] || "";
  const ivr = useQuery(`phone-ivr:${sessionId ?? "none"}`, () => ivrPrompts(), Boolean(sessionId));
  // Each caller question is a new call, so the line checks the caller again on every call.
  const callId = useMemo(() => `call-${Date.now()}`, [selected]); // eslint-disable-line react-hooks/exhaustive-deps
  const answer = useQuery(
    `phone:${sessionId ?? "none"}:${callId}:${selected}`,
    () => askLine(sessionId as string, selected, callId),
    Boolean(sessionId && selected),
  );
  // A clarifying question becomes a spoken exchange: the line asks, and the caller says one of the options.
  const choices = answer.data?.kind === "clarify" ? answer.data.chips ?? [] : [];
  const picked = params.get("answer") || "";
  const followUp = choices.length ? (choices.includes(picked) ? picked : choices[0]) : "";
  const second = useQuery(
    `phone2:${sessionId ?? "none"}:${callId}:${followUp}`,
    () => askLine(sessionId as string, followUp, callId),
    Boolean(sessionId && followUp),
  );
  const loading = answer.showSkeleton || answer.loading || (followUp && (second.loading || second.showSkeleton));
  const failed = !sessionId || topics.error || answer.error || second.error;
  const turns = buildTurns(answer.data, followUp, second.data, ivr.data ?? {});

  return (
    <main data-theme="member" className="hh-m member-phone">
      <div className="member-phone__wrap">
        <header className="call-head">
          <span className="call-head__icon" aria-hidden="true">
            <Phone />
          </span>
          <div>
            <h1 className="member-h3 call-head__title">Harbor Health automated line</h1>
            <p className="member-meta call-head__meta">1-800-555-0148 · Call transcript · Fictional caller</p>
          </div>
          <span className="call-head__status">Answered by the automated line</span>
        </header>
        {topics.showSkeleton ? <Skeleton width="480px" height="48px" label="Loading caller prompts" /> : null}
        {topics.data && topics.data.length > 0 ? (
          <div className="call-scenario">
            <label className="hh-label" htmlFor="caller-says">
              What the caller asks
            </label>
            <select
              id="caller-says"
              className="hh-input member-phone__select"
              value={selected}
              onChange={(event) => {
                const next = new URLSearchParams(params);
                next.set("prompt", event.target.value);
                next.delete("answer");
                setParams(next, { replace: true });
              }}
            >
              {prompts.map((prompt) => (
                <option key={prompt} value={prompt}>
                  {prompt}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        {choices.length ? (
          <div className="call-scenario">
            <label className="hh-label" htmlFor="caller-answers">
              What the caller says next
            </label>
            <select
              id="caller-answers"
              className="hh-input member-phone__select"
              value={followUp}
              onChange={(event) => {
                const next = new URLSearchParams(params);
                next.set("answer", event.target.value);
                setParams(next, { replace: true });
              }}
            >
              {choices.map((choice) => (
                <option key={choice} value={choice}>
                  {choice}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        {sessionError ? <ServiceError message={sessionError} onRetry={onRetry} /> : null}
        {topics.error ? <ServiceError message={topics.error} onRetry={topics.reload} /> : null}
        {!sessionId && !sessionError ? <ServiceError message="The phone line reads approved wording from the API." /> : null}
        {topics.data && topics.data.length === 0 ? <ServiceError message="The knowledge service did not return any caller prompts." /> : null}
        <ol className="call-transcript" aria-label="Transcript">
          <Turn
            who="ivr"
            time="0:02"
            text={ivr.data?.greeting?.text || "Thank you for calling Harbor Health. In a few words, tell me what you are calling about."}
            approved={Boolean(ivr.data?.greeting)}
          />
          <Turn who="caller" time="0:08" text={selected || "Waiting for a prompt from the knowledge service."} />
          {failed ? <Turn who="ivr" time="0:14" text="I cannot look that up right now." /> : null}
          {!failed && loading ? <Turn who="ivr" time="0:14" text="Looking that up…" /> : null}
          {!failed && !loading
            ? turns.map((turn, index) => <Turn key={index} who={turn.who} time={clock(14 + index * 8)} text={turn.text} approved={turn.approved} />)
            : null}
          <Turn who="ivr" time={clock(14 + Math.max(1, turns.length) * 8)} text={ivr.data?.anything_else?.text || "Is there anything else? Press 0 to talk to a member advocate."} approved={Boolean(ivr.data?.anything_else)} />
        </ol>
        <p className="member-meta member-phone__label">The line reads the same approved member wording as the website and the app.</p>
      </div>
    </main>
  );
}

function Turn({ who, time, text, approved = false }: { who: "ivr" | "caller"; time: string; text: string; approved?: boolean }) {
  return (
    <li className={`call-turn call-turn--${who}`}>
      <span className="call-turn__time">{time}</span>
      <span className="call-turn__who" aria-hidden="true">
        {who === "ivr" ? <Bot /> : <User />}
      </span>
      <div className="call-turn__body">
        <span className="call-turn__name">{who === "ivr" ? "Automated line" : "Caller"}</span>
        <p className="member-body">{text}</p>
        {approved ? <span className="member-meta call-turn__src">Approved wording, read word for word</span> : null}
      </div>
    </li>
  );
}

/** "0:14", "1:06": elapsed call time for a transcript turn. */
function clock(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/** Calls an older member makes that the topic list does not cover. */
const EXTRA_PROMPTS = ["What will a specialist visit cost?", "What is my out-of-pocket maximum?", "I was charged too much at the pharmacy", "I am having chest pain"];

/** The fictional caller's identifiers on the plan file (made up). */
const CALLER = { memberId: "HBR-20418", dateOfBirth: "1951-03-14", spoken: "H B R 2 0 4 1 8. March 14, 1951." };

type LineAnswer = MemberAnswer & { authPrompt?: string };

/**
 * Ask on the phone channel. When the line needs the caller's identifiers before a member-specific figure,
 * the caller gives them, the server checks them, and the question is asked again.
 */
async function askLine(sessionId: string, question: string, callId: string): Promise<LineAnswer> {
  const first = await memberAnswer(sessionId, question, { channel: "voice_bot", memberId: CALLER.memberId, callId });
  if (first.kind !== "authenticate") return first;
  await phoneAuthenticate(CALLER.memberId, CALLER.dateOfBirth, callId);
  const again = await memberAnswer(sessionId, question, { channel: "voice_bot", memberId: CALLER.memberId, callId });
  return { ...again, authPrompt: first.reply || first.units?.[0]?.text || "" };
}

const MEMBER_FIGURE = new Set(["price", "visit_cost", "plan_figure"]);

type SpokenTurn = { who: "ivr" | "caller"; text: string; approved?: boolean };

function spokenOptions(chips: string[]) {
  const names = chips.map((chip) =>
    chip
      .replace(/^How much is (a .*? of )?/i, "")
      .replace(/^What will (a|an) (.*?) visit cost\?$/i, "$2")
      .replace(/\?$/, ""),
  );
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")}, or ${names[names.length - 1]}`;
}

/** What the line says: the approved wording read word for word before any dollar amount, then the plan numbers. */
function speak(answer: LineAnswer | null | undefined, ivr: Record<string, IvrPrompt>): SpokenTurn[] {
  if (!answer) return [];
  const say = (key: string, fallback: string) => ({ who: "ivr" as const, text: ivr[key]?.text || fallback, approved: Boolean(ivr[key]) });
  if (answer.kind === "safety") {
    return [{ who: "ivr", text: answer.member_text || answer.reply || "", approved: true }];
  }
  if (MEMBER_FIGURE.has(answer.kind || "") && answer.reply) {
    const units = answer.units ?? [];
    return [
      ...(answer.authPrompt
        ? [
            { who: "ivr" as const, text: answer.authPrompt, approved: true },
            { who: "caller" as const, text: CALLER.spoken },
            ...(ivr.verified ? [{ who: "ivr" as const, text: ivr.verified.text, approved: true }] : []),
          ]
        : []),
      ...(units.length ? [say("before_amount", "Before I give you that amount, here is some important information.")] : []),
      ...units.map((unit) => ({ who: "ivr" as const, text: unit.text, approved: true })),
      { who: "ivr", text: answer.reply },
    ];
  }
  if (!answer.abstained && answer.member_text) {
    const turns: SpokenTurn[] = [{ who: "ivr", text: answer.member_text, approved: true }];
    // The caregiver rule states a requirement; tell the caller how to meet it.
    if (answer.unit_id === "U-RX-EDU-001-05") {
      turns.push(say("add_caller", "To add someone to your account, press 0 and a member advocate will help you set it up."));
    }
    return turns;
  }
  if ((answer.kind === "handoff_offer" || answer.kind === "handoff") && answer.reply) {
    return [{ who: "ivr", text: answer.reply, approved: Boolean(answer.units?.length) }, say("advocate", "Press 0 to talk to a member advocate.")];
  }
  return [say("no_answer", "I don't have an approved answer for that yet."), say("advocate", "Press 0 to talk to a member advocate.")];
}

function buildTurns(
  first: LineAnswer | null | undefined,
  followUp: string,
  second: LineAnswer | null | undefined,
  ivr: Record<string, IvrPrompt>,
): SpokenTurn[] {
  if (!first) return [];
  if (followUp && first.chips?.length) {
    return [
      { who: "ivr", text: `${(first.reply || "Which one?").replace(" Here are the ones on your list.", "")} You can say ${spokenOptions(first.chips)}.` },
      { who: "caller", text: followUp },
      ...speak(second, ivr),
    ];
  }
  return speak(first, ivr);
}
