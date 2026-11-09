import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { memberRecord, searchAnswers, sendFeedback, verifyCaller } from "@/api/client";
import type { SearchResult } from "@/api/types";
import { useQuery } from "@/api/use-query";
import { AnswerCard, FLAG_REASONS, type FlagPayload } from "@/components/answer-card";
import { Button } from "@/components/button";
import { EmptyState } from "@/components/empty-state";
import { ServiceError } from "@/components/service-state";
import { AnswerSkeleton } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { showUndoToast } from "@/components/toast";
import { AnsweredNotice, ChangeBanner, WrapUp, type ShownUnit } from "@/pages/advocate/desk-extras";
import { ClaimsTab, PlanFacts, PrescriptionsTab, ProfileTab } from "@/pages/advocate/member-tabs";
import { citeUnit } from "@/components/quote-card";
import { PHARMACY_LABELS, priceHeadline, visitHeadline } from "@/lib/plan-labels";
import { plainTitle } from "@/lib/labels";
import { ADVOCATE_ROLES, type AdvocateId, type CallScenario } from "@/pages/advocate/scenarios";
import { SlowNote } from "@/components/slow-note";

const NO_ANSWER =
  "No approved answer for this question. Tell the member you will follow up, and use Flag this answer if you think one should exist. The question was logged for the knowledge team.";

type DesktopProps = {
  advocateId: AdvocateId;
  sessionId: string | null;
  sessionError?: string | null;
  onRetry?: () => void;
};

export function AgentDesktop({ advocateId, sessionId, sessionError, onRetry }: DesktopProps) {
  const desk = ADVOCATE_ROLES[advocateId];
  const [params, setParams] = useSearchParams();
  const call: CallScenario = desk.calls.find((item) => item.id === params.get("call")) ?? desk.calls[0];
  const query = params.get("q") || "";
  const [draft, setDraft] = useState(query);
  const [notes, setNotes] = useState("");
  const [held, setHeld] = useState(false);
  const [ended, setEnded] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const searches = useRef(0);
  const sent = useRef(new Set<string>());
  const [shown, setShown] = useState<ShownUnit[]>([]);
  const [wrapped, setWrapped] = useState(false);
  const [tab, setTab] = useState<"interaction" | "profile" | "claims" | "rx">("interaction");
  // The member's questions, played one at a time. Each records the call time it was asked.
  const [heard, setHeard] = useState<Array<{ said: string; query: string; at: number }>>([]);
  const [focus, setFocus] = useState(0);
  // The advocate can verify an unverified caller during the call; the answer is then shown.
  const [verifiedNow, setVerifiedNow] = useState(false);
  const verified = call.verified || verifiedNow;
  // The server holds verification. A verified call records the two identifiers first; an unverified call never does.
  const record = useQuery(`record:${call.memberId}:${desk.role}:${call.verified}`, async () => {
    if (call.verified) await verifyCaller(call.memberId, call.dateOfBirth);
    return memberRecord(call.memberId, desk.role, call.verified);
  });

  const noteShown = useCallback((unit: ShownUnit) => {
    setShown((list) => (list.some((item) => item.unit_id === unit.unit_id) ? list : [...list, unit]));
  }, []);

  useEffect(() => {
    setDraft(query);
  }, [query]);

  useEffect(() => {
    searches.current = 0;
    setHeld(false);
    setEnded(false);
    setSeconds(0);
    setShown([]);
    setWrapped(false);
    setTab("interaction");
    setNotes("");
    setHeard([]);
    setFocus(0);
    setVerifiedNow(false);
  }, [call.id]);

  useEffect(() => {
    if (held || ended) return;
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [held, ended, call.id]);

  function setCall(next: CallScenario) {
    const search = new URLSearchParams(params);
    if (next.id === desk.calls[0].id) search.delete("call");
    else search.set("call", next.id);
    search.delete("q");
    setParams(search);
  }

  function setQuery(next: string) {
    const search = new URLSearchParams(params);
    if (next) search.set("q", next);
    else search.delete("q");
    setParams(search);
  }

  async function once(key: string, body: Parameters<typeof sendFeedback>[1]) {
    if (!sessionId || sent.current.has(key)) return;
    sent.current.add(key);
    try {
      await sendFeedback(sessionId, body);
    } catch {
      sent.current.delete(key);
    }
  }

  function onSearch(event: FormEvent) {
    event.preventDefault();
    const next = draft.trim();
    if (!next) return;
    setQuery(next);
    searches.current += 1;
    if (searches.current >= 3) {
      void once(`hard:${desk.role}:${call.id}`, {
        source: "advocate",
        role: desk.role,
        kind: "hard_to_find",
        question: next,
        unit_id: "",
        note: "Captured automatically: three or more searches in one call.",
      });
    }
  }

  return (
    <div className="desk" data-theme="tools">
      <header className="desk-top">
        <h1 className="desk-top__brand">
          Harbor Health <span>Contact Center</span>
        </h1>
        <span className="desk-top__queue">{desk.queue}</span>
        <span className="desk-top__user">
          <span className="avatar" aria-hidden="true">
            {desk.advocate
              .split(" ")
              .map((part) => part[0])
              .join("")}
          </span>
          {desk.advocate}
        </span>
      </header>
      <div className="desk-call">
        <div>
          <p className="desk-call__name">{call.member}</p>
          <p className="desk-call__meta">
            {call.memberId} · {call.plan} · Fictional caller
          </p>
        </div>
        <StatusBadge variant={verified ? "approved" : "review"}>{verified ? "Verified" : "Not verified"}</StatusBadge>
        <p className="desk-timer" aria-live="polite">
          {formatTime(seconds)}
          {held ? " · On hold" : ""}
          {ended ? (wrapped ? " · Wrapped up" : " · Ended, wrap-up open") : ""}
        </p>
        <Button variant="secondary" compact aria-pressed={held} onClick={() => setHeld((value) => !value)} disabled={ended}>
          {held ? "Resume" : "Hold"}
        </Button>
        <Button
          variant="secondary"
          compact
          onClick={() => {
            setEnded(true);
            setHeld(false);
            showUndoToast({ message: "Call ended. Wrap it up on the left.", onUndo: () => setEnded(false) });
          }}
          disabled={ended}
        >
          End call
        </Button>
      </div>
      <ChangeBanner role={desk.role} refreshKey={0} />
      <div className="desk-body">
        <section className="desk-main" aria-label="Call">
          <div className="desk-tabs" role="tablist" aria-label="Member">
            {(
              [
                ["interaction", "Interaction"],
                ["profile", "Member profile"],
                ["claims", "Claims"],
                ["rx", "Prescriptions"],
              ] as const
            ).map(([id, label]) => (
              <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}>
                {label}
              </button>
            ))}
          </div>
          {tab !== "interaction" ? (
            <div className="desk-cards">
              {record.loading && !record.data ? <AnswerSkeleton /> : null}
              {record.error ? <ServiceError message={record.error} onRetry={record.reload} /> : null}
              {record.data && tab === "profile" ? <ProfileTab record={record.data} /> : null}
              {record.data && tab === "claims" ? <ClaimsTab record={record.data} /> : null}
              {record.data && tab === "rx" ? <PrescriptionsTab record={record.data} /> : null}
            </div>
          ) : null}
          <div className="desk-cards" hidden={tab !== "interaction"}>
            {ended ? (
              <WrapUp
                key={call.id}
                role={desk.role}
                callId={call.id}
                callReason={call.reason}
                shown={shown}
                initialNote={notes}
                onSaved={() => setWrapped(true)}
                onNextCall={() => {
                  const index = desk.calls.findIndex((item) => item.id === call.id);
                  setCall(desk.calls[(index + 1) % desk.calls.length]);
                }}
              />
            ) : null}
            <LiveQuestion
              key={call.id}
              call={call}
              heard={heard}
              focus={focus}
              ended={ended}
              verified={verified}
              onVerify={() => {
                setVerifiedNow(true);
                showUndoToast({ message: `${call.member} confirmed the member ID and date of birth. Verified.` });
              }}
              onFocus={setFocus}
              onNext={() => {
                const line = call.script[heard.length];
                if (!line) return;
                setHeard((list) => [...list, { ...line, at: seconds }]);
                setFocus(heard.length);
                setTab("interaction");
              }}
              onTransfer={() => {
                setEnded(true);
                setHeld(false);
                showUndoToast({ message: `Transferred to the ${call.transferTo} queue with your notes.`, onUndo: () => setEnded(false) });
              }}
              answer={(line) =>
                sessionId ? (
                  <AnswerSlot
                    key={`${line.query}:${verified}`}
                    sessionId={sessionId}
                    role={desk.role}
                    question={line.query}
                    caller={{ memberId: call.memberId, verified, dateOfBirth: call.dateOfBirth }}
                    onShown={noteShown}
                    onMiss={(question) =>
                      void once(`no:${desk.role}:${question}`, {
                        source: "advocate",
                        role: desk.role,
                        kind: "no_answer",
                        question,
                        unit_id: "",
                        note: "No approved answer for a question asked on a call.",
                      })
                    }
                    onFlag={(question, unitId, payload) =>
                      void sendFeedback(sessionId, {
                        source: "advocate",
                        role: desk.role,
                        kind: payload.kind,
                        question,
                        unit_id: unitId,
                        note: payload.note,
                      })
                    }
                  />
                ) : (
                  <ServiceError message="The panel needs a session before it can show approved answers." />
                )
              }
            />
            <article className="desk-card">
              <h2 className="desk-card__title">Caller</h2>
              <dl className="desk-profile">
                <div>
                  <dt>Member</dt>
                  <dd>{call.member}</dd>
                </div>
                <div>
                  <dt>Member ID</dt>
                  <dd className="hh-id">{call.memberId}</dd>
                </div>
                <div>
                  <dt>Plan</dt>
                  <dd>{call.plan}</dd>
                </div>
                <div>
                  <dt>Identity</dt>
                  <dd>{call.verified ? "Verified with member ID and date of birth" : "Not verified yet"}</dd>
                </div>
              </dl>
            </article>
            <article className="desk-card">
              <h2 className="desk-card__title">This call</h2>
              <label className="hh-label" htmlFor="call-reason">
                Call reason
              </label>
              <select
                id="call-reason"
                className="hh-input"
                value={call.id}
                onChange={(event) => {
                  const next = desk.calls.find((item) => item.id === event.target.value);
                  if (next) setCall(next);
                }}
              >
                {desk.calls.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.reason}
                  </option>
                ))}
              </select>
              <p className="desk-card__said">
                <span className="hh-meta">Member said</span>
                <span>{call.detail}</span>
              </p>
            </article>
            <article className="desk-card desk-card--wide">
              <h2 className="desk-card__title">Recent contacts</h2>
              {!call.verified ? <p className="hh-meta">Hidden until the caller is verified.</p> : null}
              <ul className="desk-history">
                {(call.verified ? record.data?.recent_contacts ?? [] : []).map((contact, index) => (
                  <li key={index}>
                    <span className="desk-history__when">{shortDate(contact.date)}</span>
                    <span>{contact.channel}</span>
                    <span>{contact.summary}</span>
                  </li>
                ))}
              </ul>
              {call.verified && record.data && !record.data.recent_contacts.length ? <p className="hh-meta">No earlier contacts.</p> : null}
            </article>
            <article className="desk-card desk-card--wide">
              <label className="desk-card__title" htmlFor="call-notes">
                Interaction notes
              </label>
              <textarea
                id="call-notes"
                className="hh-input hh-textarea"
                placeholder="Notes for this call…"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
            </article>
          </div>
        </section>
        <aside className="desk-panel" aria-label="Knowledge">
          <form className="desk-search" onSubmit={onSearch}>
            <label className="sr-only" htmlFor="knowledge-search">
              Search approved answers
            </label>
            <input
              id="knowledge-search"
              className="hh-input"
              value={draft}
              placeholder="Search approved answers"
              onChange={(event) => setDraft(event.target.value)}
            />
          </form>
          {sessionError ? <ServiceError message={sessionError} onRetry={onRetry} /> : null}
          {!sessionId && !sessionError ? <ServiceError message="The panel needs a session before it can show approved answers." /> : null}
          {query ? (
            <>
              <p className="tools-label">Results for: {query}</p>
              {sessionId ? (
                <AnswerSlot
                  sessionId={sessionId}
                  role={desk.role}
                  question={query}
                  caller={{ memberId: call.memberId, verified: call.verified, dateOfBirth: call.dateOfBirth }}
                  onShown={noteShown}
                  onMiss={(question) =>
                    void once(`no:${desk.role}:${question}`, {
                      source: "advocate",
                      role: desk.role,
                      kind: "no_answer",
                      question,
                      unit_id: "",
                      note: "No approved answer for this question.",
                    })
                  }
                  onFlag={(question, unitId, payload) =>
                    void sendFeedback(sessionId, {
                      source: "advocate",
                      role: desk.role,
                      kind: payload.kind,
                      question,
                      unit_id: unitId,
                      note: payload.note,
                    })
                  }
                />
              ) : null}
              <Button variant="tertiary" compact onClick={() => setQuery("")}>
                Back to suggestions
              </Button>
            </>
          ) : (
            <>
              <AnsweredNotice role={desk.role} onShow={(question) => setQuery(question)} />
              {call.planFacts && verified && record.data ? <PlanFacts record={record.data} kind={call.planFacts} /> : null}
              <p className="hh-meta desk-panel__note">
                Answers to the member's questions appear in the middle of the screen as the call goes. Use search here for anything else.
              </p>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}

/**
 * The most important thing on the desktop: the question the member just asked, and the approved answer to it, front
 * and center. The sandbox has no live audio, so the advocate plays the member's scripted questions one at a time.
 */
function LiveQuestion({
  call,
  heard,
  focus,
  ended,
  verified,
  onVerify,
  onFocus,
  onNext,
  onTransfer,
  answer,
}: {
  call: CallScenario;
  heard: Array<{ said: string; query: string; at: number }>;
  focus: number;
  ended: boolean;
  verified: boolean;
  onVerify: () => void;
  onFocus: (index: number) => void;
  onNext: () => void;
  onTransfer: () => void;
  answer: (line: { said: string; query: string }) => React.ReactNode;
}) {
  const current = heard[focus];
  const remaining = call.script.length - heard.length;
  return (
    <section className="live-q" aria-labelledby="live-q-h">
      <div className="live-q__bar">
        <h2 className="live-q__title" id="live-q-h">
          <span className="live-q__dot" aria-hidden="true" />
          Live call
        </h2>
        {remaining > 0 ? (
          <Button variant={heard.length ? "secondary" : "primary"} compact disabled={ended} onClick={onNext}>
            {heard.length ? "Member asks the next question" : "Member asks a question"}
          </Button>
        ) : (
          <span className="hh-meta">No more scripted questions on this call. End the call to wrap it up.</span>
        )}
      </div>
      {heard.length ? (
        <ol className="live-q__transcript" aria-label="What the member has asked">
          {heard.map((line, index) => (
            <li key={index}>
              <button type="button" className="live-q__line" aria-current={index === focus ? "true" : undefined} onClick={() => onFocus(index)}>
                <span className="live-q__time">{formatTime(line.at)}</span>
                <span className="live-q__who">{call.member}</span>
                <span>{line.said}</span>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="hh-meta live-q__empty">
          When the member asks something, the question and its approved answer appear here. In production the question comes from the call audio; in the
          sandbox, press "Member asks a question".
        </p>
      )}
      {current ? (
        <div className="live-q__card" aria-live="polite">
          <p className="live-q__label">{call.member} asked</p>
          <p className="live-q__asked">&ldquo;{current.said}&rdquo;</p>
          <p className="hh-meta">Searched approved answers for your role: {current.query}</p>
          <p className="live-q__label">What to say or do</p>
          {call.transferTo ? (
            <div className="desk-none">
              <EmptyState
                heading={`This question belongs to the ${call.transferTo} queue`}
                reason={`Your role cannot read ${call.transferTo.toLowerCase()} knowledge, so there is no answer to give. Tell the member you are connecting them to the right team, and transfer with your notes.`}
              />
              <Button variant="primary" compact disabled={ended} onClick={onTransfer}>
                Transfer to the {call.transferTo} queue
              </Button>
            </div>
          ) : (
            <>
              <div key={`${call.id}:${focus}:${verified}`}>{answer(current)}</div>
              {!verified ? (
                <div className="live-q__verify">
                  <p className="tools-body">
                    Ask for two of these: member ID, date of birth, or the address on file. When they match the plan record, the caller is verified and the
                    answer appears here.
                  </p>
                  <Button variant="primary" compact disabled={ended} onClick={onVerify}>
                    {call.member} confirmed the member ID and date of birth
                  </Button>
                </div>
              ) : null}
            </>
          )}
        </div>
      ) : null}
    </section>
  );
}

function AnswerSlot({
  sessionId,
  role,
  question,
  caller,
  onMiss,
  onFlag,
  onShown,
}: {
  sessionId: string;
  role: string;
  question: string;
  caller?: { memberId: string; verified: boolean; dateOfBirth?: string };
  onShown: (unit: ShownUnit) => void;
  onMiss: (question: string) => void;
  onFlag: (question: string, unitId: string, payload: FlagPayload) => void;
}) {
  const result = useQuery(`search:${sessionId}:${role}:${question}:${caller?.memberId ?? ""}`, async () => {
    if (caller?.verified && caller.dateOfBirth) await verifyCaller(caller.memberId, caller.dateOfBirth);
    return searchAnswers(sessionId, role, question, caller);
  });
  useEffect(() => {
    if (result.data && (result.data.abstained || !result.data.unit)) onMiss(question);
  }, [result.data, onMiss, question]);
  useEffect(() => {
    const unit = result.data?.unit;
    if (result.data && !result.data.abstained && unit) {
      onShown({
        unit_id: unit.unit_id,
        title: plainTitle(unit.title),
        verbatim: Boolean(unit.verbatim || unit.type === "verbatim"),
        version: unit.version,
        text: unit.text,
      });
    }
  }, [result.data, onShown]);

  if (result.showSkeleton)
    return (
      <>
        <AnswerSkeleton />
        <SlowNote active />
      </>
    );
  if (result.error) return <ServiceError message={result.error} onRetry={result.reload} />;
  if (!result.data) return null;
  return <ResultView result={result.data} role={role} onFlag={onFlag} />;
}

function ResultView({
  result,
  role,
  onFlag,
}: {
  result: SearchResult;
  role: string;
  onFlag: (question: string, unitId: string, payload: FlagPayload) => void;
}) {
  const unit = result.unit;
  if (result.verify_first) {
    return (
      <div className="desk-none desk-verify">
        <EmptyState heading="Verify the caller before you answer" reason="This caller is not verified yet, so no price, tier or coverage detail can be given." />
        {unit ? (
          <div className="desk-rule">
            <p className="hh-label">The rule, for you. Do not read it to the member.</p>
            <p className="tools-body">{unit.text}</p>
            <p className="hh-meta">
              Approved {plainTitle(unit.title)}, version {unit.version}
            </p>
          </div>
        ) : null}
      </div>
    );
  }
  if ((result.kind === "price" && result.price) || (result.kind === "visit_cost" && result.visit_cost)) {
    const amount = result.price ? (result.price.available ? result.price.price_display : "") : result.visit_cost?.available ? result.visit_cost.cost_display : "";
    // The approved wording comes first: the advocate reads it before giving any amount.
    return (
      <div className="desk-quote">
        {(result.units ?? []).map((item) => (
          <div key={item.unit_id} className="desk-quote__unit">
            <p className="hh-label">{item.type === "verbatim" ? "Read word for word first" : "Also applies before you quote"}</p>
            <p className="tools-body">{item.text}</p>
            <p className="hh-meta">{citeUnit(item)}</p>
          </div>
        ))}
        {result.price_options?.length && result.price ? (
          <p className="tools-label">
            {result.price.drug.name} {result.price.drug.strength}: prices by pharmacy and supply
          </p>
        ) : (
          <>
            <p className="desk-quote__amount">{amount || "Not available"}</p>
            <p className="tools-label">{result.price ? priceHeadline(result.price) : result.visit_cost ? visitHeadline(result.visit_cost) : ""}</p>
          </>
        )}
        {result.price_options?.length ? (
          <dl className="desk-facts__list">
            {result.price_options.filter((option) => option.available).map((option) => (
              <div key={`${option.pharmacy}-${option.days}`}>
                <dt>
                  {option.days}-day, {PHARMACY_LABELS[option.pharmacy] || option.pharmacy}
                </dt>
                <dd>{option.available ? option.price_display : "Not available"}</dd>
              </div>
            ))}
          </dl>
        ) : null}
        <p className="hh-meta">Illustrative prices from made-up plan data.</p>
      </div>
    );
  }
  if (result.status === "blocked_conflict") {
    return (
      <div className="desk-none">
        <EmptyState heading="Under Legal review" reason={result.blocked_note || "Two versions of this rule disagree. Legal is deciding which one stays."} />
        <p className="hh-meta">Both versions stay out of search until Legal records a decision. Tell the member you will confirm, or transfer to a lead.</p>
      </div>
    );
  }
  if (result.transfer && (result.abstained || !unit)) {
    return (
      <div className="desk-none">
        <EmptyState heading={`This question belongs to the ${result.transfer.queue}`} reason={result.transfer.reason} />
        <p className="hh-meta">Transfer the caller with your notes, so they do not have to repeat themselves.</p>
      </div>
    );
  }
  if ((result.abstained || !unit) && result.ai_source === "expired") {
    return (
      <div className="desk-none">
        <EmptyState
          heading="The approved answer is past its review date"
          reason={`${result.note || "This answer is waiting for Legal to review it again."} Do not read the old wording. Tell the member you will confirm and call them back.`}
        />
        <FlagBox onSend={(payload) => onFlag(result.query, "", payload)} />
      </div>
    );
  }
  if (result.abstained || !unit) {
    return (
      <div className="desk-none">
        <EmptyState heading="No approved answer" reason={NO_ANSWER} />
        <FlagBox onSend={(payload) => onFlag(result.query, "", payload)} />
      </div>
    );
  }
  return (
    <AnswerCard
      fit
      question={unit.title.replace(/\s*\((Legal|Legal verbatim)\)\s*$/, "")}
      wording={unit.text}
      verbatim={unit.verbatim || unit.type === "verbatim"}
      citation={{
        title: plainTitle(unit.title),
        version: unit.version,
        approver: unit.approved_by || "not recorded",
        date: (unit.approved_on || unit.effective_date || "").slice(0, 10) || "date not recorded",
      }}
      approval={{
        role: unit.approved_by || "Legal approver",
        timestamp: unit.approved_on,
        version: unit.version,
      }}
      readerRole={unit.verbatim || unit.type === "verbatim" ? role : undefined}
      onFlag={(payload) => onFlag(result.query, unit.unit_id, payload)}
    />
  );
}

function FlagBox({ onSend }: { onSend: (payload: FlagPayload) => void }) {
  const [kind, setKind] = useState<FlagPayload["kind"]>("couldnt_find");
  const [note, setNote] = useState("");
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <Button variant="tertiary" compact onClick={() => setOpen(true)}>
        Flag this answer
      </Button>
    );
  }
  return (
    <form
      className="desk-flag"
      onSubmit={(event) => {
        event.preventDefault();
        onSend({ kind, note: note.trim() });
        setOpen(false);
        setNote("");
        showUndoToast({ message: "Flag sent. Member details are removed before it is stored." });
      }}
    >
      <fieldset>
        <legend className="hh-label">What went wrong?</legend>
        {FLAG_REASONS.map((reason) => (
          <label key={reason.id}>
            <input type="radio" name="flag-kind" value={reason.id} checked={kind === reason.id} onChange={() => setKind(reason.id)} />
            {reason.label}
          </label>
        ))}
      </fieldset>
      <label className="hh-label" htmlFor="flag-note">
        Note <span className="hh-opt">(optional)</span>
      </label>
      <input id="flag-note" className="hh-input" value={note} onChange={(event) => setNote(event.target.value)} />
      <Button variant="primary" compact type="submit">
        Send to the knowledge team
      </Button>
    </form>
  );
}

function formatTime(total: number) {
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

/** "2026-10-28" reads as "Oct 28"; anything else is shown as given. */
function shortDate(value: string) {
  const date = new Date(`${value.slice(0, 10)}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
