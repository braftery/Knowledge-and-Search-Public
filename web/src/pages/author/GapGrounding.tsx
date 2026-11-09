import { useMemo, useState } from "react";
import {
  answerSourceRequest,
  approveAuthor,
  dismissGap,
  fillPlaceholder,
  getAuthorDocuments,
  getDocument,
  getSourceRequests,
  groundPlaceholder,
  sendGapDraft,
  type AuthorDraft,
  type GapCandidate,
  type PlaceholderSource,
} from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { DecisionMarker } from "@/components/decision-marker";
import { Field } from "@/components/field";
import { StatusBadge } from "@/components/status-badge";
import { SourceDocument } from "@/pages/legal/SourceDocument";

type Mutation = { message: string; routing_reason?: string; undo?: { available?: boolean } };
type Run = (label: string, action: () => Promise<Mutation>, sentTitle?: string) => Promise<boolean>;
type Path = "" | "use" | "ask" | "cite" | "dismiss";

const MIN_WORDS = 4;
const words = (text: string) => text.trim().split(/\s+/).filter(Boolean).length;

const TRUST: Record<string, { label: string; variant: "approved" | "review" | "blocked" | "neutral" }> = {
  approved: { label: "Approved source", variant: "approved" },
  review_backlog: { label: "Harbor document, not reviewed yet", variant: "review" },
  unreviewed: { label: "Unreviewed text", variant: "blocked" },
  none: { label: "No source found", variant: "neutral" },
};

/** Split a document into sentences that are exact substrings of its body, so a pick can be cited as written. */
export function sentences(body: string) {
  const out: string[] = [];
  for (const raw of body.split("\n")) {
    const line = raw.replace(/^\s*(#+|[-*]|\d+\.)\s+/, "").replace(/^\*\*|\*\*$/g, "").trim();
    if (!line || line.startsWith("|") || /^illustrative/i.test(line)) continue;
    for (const part of line.split(/(?<=[.!?])\s+/)) {
      const sentence = part.trim();
      if (sentence.length > 12 && body.includes(sentence)) out.push(sentence);
    }
  }
  return out;
}

/**
 * An unanswered question: advocates or members asked it and no approved unit answers it. The AI searched every Harbor
 * document and shows what it found and how far to trust it. Knowledge Ops then uses that source, asks the subject
 * expert who owns the fact, or dismisses the question with a reason. No source, no unit.
 */
export function GapGrounding({ draft, askedAs, busy, problem, run }: { draft: AuthorDraft; askedAs: string[]; busy: string | null; problem: string | null; run: Run }) {
  const sources = draft.placeholder_sources ?? [];
  const candidate = draft.candidate ?? null;
  const open = sources.find((source) => !source.sourced) ?? null;
  const pending = sources.find((source) => source.kind === "request" && !source.quote) ?? null;
  const unfilled = sources.find((source) => source.sourced && !(source.kind === "request" && !source.quote) && !source.filled) ?? null;
  const [path, setPath] = useState<Path>("");
  const preview = sources.reduce((text, source) => (source.filled ? text.replace(source.token, source.filled_text) : text), draft.draft_text);
  const roles = (Array.isArray(draft.roles) ? draft.roles : draft.roles ? [draft.roles] : []).map((role) => `${role}s`).join(" and ");

  return (
    <article className="work-card gap-ground">
      <div className="item-head">
        <div className="item-head__text">
          <p className="tools-overline">Unanswered question</p>
          <h2 className="tools-title">{draft.draft_title || draft.cluster}</h2>
          <p className="item-head__meta">
            {draft.search_count ? `Asked ${draft.search_count} ${draft.search_count === 1 ? "time" : "times"}` : "Asked"}
            {roles ? ` by ${roles}` : ""} with no approved answer · illustrative counts
          </p>
        </div>
        <div className="item-head__badges">
          <StatusBadge variant={draft.can_send ? "approved" : "review"}>{draft.can_send ? "Ready to send" : pending ? "Waiting for the expert" : "Needs a source"}</StatusBadge>
        </div>
      </div>
      {askedAs.length > 1 ? (
        <p className="hh-meta">
          Also asked as: {askedAs
            .slice(1, 4)
            .map((question) => `"${question}"`)
            .join(", ")}
        </p>
      ) : null}

      <section className="gap-step" aria-labelledby={`found-${draft.id}`}>
        <h3 className="tools-label" id={`found-${draft.id}`}>
          1. What the AI found
        </h3>
        <FoundCard candidate={candidate} />
      </section>

      <section className="gap-step" aria-labelledby={`draft-${draft.id}`}>
        <h3 className="tools-label" id={`draft-${draft.id}`}>
          2. The AI's draft answer
        </h3>
        <p className="work-text">{preview}</p>
        <DecisionMarker kind="ai" detail="Drafted by the model. A bracketed placeholder is a fact the model may not invent; it is filled only from a source." />
      </section>

      <section className="gap-step" aria-labelledby={`decide-${draft.id}`}>
        <h3 className="tools-label" id={`decide-${draft.id}`}>
          3. Your decision
        </h3>
        {open && !pending ? (
          <>
            <div className="gap-ground__choices" role="group" aria-label="Choose what to do">
              {candidate?.ref ? (
                <Button variant={path === "use" ? "primary" : "secondary"} aria-pressed={path === "use"} onClick={() => setPath("use")}>
                  Use this source
                </Button>
              ) : null}
              <Button variant={path === "ask" ? "primary" : "secondary"} aria-pressed={path === "ask"} onClick={() => setPath("ask")}>
                {candidate?.ref ? "Ask an expert to confirm" : "Ask the expert who owns this"}
              </Button>
              <Button variant={path === "cite" ? "primary" : "secondary"} aria-pressed={path === "cite"} onClick={() => setPath("cite")}>
                Cite a different passage
              </Button>
              <Button variant={path === "dismiss" ? "primary" : "tertiary"} aria-pressed={path === "dismiss"} onClick={() => setPath("dismiss")}>
                Dismiss
              </Button>
            </div>
            <PathHelp path={path} candidate={candidate} />
            {path === "use" && candidate ? <UseSource draft={draft} slot={open} candidate={candidate} busy={busy} run={run} /> : null}
            {path === "ask" ? <AskExpert draft={draft} slot={open} candidate={candidate} busy={busy} run={run} /> : null}
            {path === "cite" ? (
              <CitePassage
                id={`cite-${draft.id}`}
                busy={busy}
                onCite={(ref, quote) => run("Citing…", () => groundPlaceholder(draft.id, open.index, { kind: "document", ref, quote }))}
              />
            ) : null}
            {path === "dismiss" ? <DismissForm draft={draft} busy={busy} run={run} /> : null}
          </>
        ) : null}
        {pending ? <ExpertReply id={`reply-${draft.id}`} requestId={pending.request_id} busy={busy} run={run} /> : null}
        {unfilled ? <FillStep gapId={draft.id} slot={unfilled} suggestion={candidate?.ref === unfilled.ref ? candidate.fill : ""} busy={busy} run={run} /> : null}
        {sources
          .filter((source) => source.filled)
          .map((source) => (
            <div key={source.index} className="gap-ground__done">
              <DecisionMarker kind="human" role="Knowledge Ops author" decision={`Filled ${source.token} with "${source.filled_text}".`} />
              <p className="hh-meta">
                Source: <span className="hh-id">{source.ref}</span>
                {source.kind === "request" ? " (statement from the subject expert, simulated)" : ""}
              </p>
              <blockquote className="source-quote">{source.quote}</blockquote>
            </div>
          ))}
        {draft.can_send ? (
          <div className="work-actions">
            <DecisionMarker kind="pending" role="Knowledge Ops author" />
            <Button
              busy={busy === "Finishing…"}
              busyLabel="Finishing…"
              disabled={Boolean(busy)}
              onClick={() =>
                void run(
                  "Finishing…",
                  async () => {
                    const sent = (await sendGapDraft(draft.id)) as Mutation & { queue?: string; unit_id?: string };
                    // A unit Knowledge Ops owns is approved here, by the same person, as with any procedure or FAQ.
                    if (sent.queue && sent.queue !== "Legal" && sent.unit_id) {
                      const approved = await approveAuthor(sent.unit_id, "explore");
                      return { ...approved, message: `${approved.message} Search can use it now.`, published: true };
                    }
                    return sent;
                  },
                  draft.draft_title || draft.cluster,
                )
              }
            >
              Approve, or send to Legal
            </Button>
            <span className="hh-meta">
              The routing rule decides: an FAQ or procedure you own is approved now and search can use it; cost, clinical and word-for-word wording goes to
              Legal. The unit carries its source either way.
            </span>
          </div>
        ) : null}
      </section>
      {problem ? (
        <p className="hh-error" role="alert">
          {problem}
        </p>
      ) : null}
    </article>
  );
}

function FoundCard({ candidate }: { candidate: GapCandidate | null }) {
  if (!candidate) return <p className="hh-meta">The AI did not search for a source on this older draft.</p>;
  const trust = TRUST[candidate.trust] ?? TRUST.none;
  return (
    <div className={`found-card found-card--${candidate.trust}`}>
      <div className="found-card__head">
        <StatusBadge variant={trust.variant}>{trust.label}</StatusBadge>
        {candidate.source_name ? <strong>{candidate.source_name}</strong> : null}
        {candidate.ref ? <span className="hh-id">{candidate.ref}</span> : null}
      </div>
      <p className="tools-body">{candidate.note}</p>
      {candidate.ref && candidate.quote ? (
        <SourceDocument
          docId={candidate.ref}
          quote={candidate.quote}
          world="explore"
          caption="The highlighted passage is the text the AI found. Read it in context before you trust it."
        />
      ) : null}
      <p className="hh-meta">
        {candidate.trust === "none" ? "" : `${candidate.trust_label}. `}Likely owner of this fact: {candidate.owner_role}.
      </p>
      <DecisionMarker kind="ai" detail="Searched every Harbor document, website page and approved unit." />
    </div>
  );
}

function PathHelp({ path, candidate }: { path: Path; candidate: GapCandidate | null }) {
  const text: Record<Path, string> = {
    "": candidate?.ref
      ? "Use the source if you trust it. If you are not sure it is current or complete, ask the expert who owns the fact to confirm first."
      : "Nothing in the company states this. Only the expert who owns the fact can answer it, or say that no policy exists.",
    use:
      candidate?.trust === "unreviewed"
        ? "This text was never reviewed. Using it puts unreviewed wording behind an approved answer. Ask an expert to confirm unless you are certain it is right."
        : "The answer is filled only from the words in this passage, and the unit records it as its source.",
    ask: "The expert's dated, signed reply becomes the source. If they say the company has no policy, no unit is written and the question goes to the Knowledge owner.",
    cite: "Pick any Harbor document and the exact sentence that states the fact.",
    dismiss: "No unit is written. Use this when an approved unit already answers the question, or when it is outside what Harbor does.",
  };
  return <p className="hh-meta gap-ground__help">{text[path]}</p>;
}

function UseSource({ draft, slot, candidate, busy, run }: { draft: AuthorDraft; slot: PlaceholderSource; candidate: GapCandidate; busy: string | null; run: Run }) {
  return (
    <div className="gap-ground__form">
      <Button
        busy={busy === "Using the source…"}
        busyLabel="Using the source…"
        disabled={Boolean(busy)}
        onClick={() =>
          void run("Using the source…", async () => {
            const grounded = await groundPlaceholder(draft.id, slot.index, { kind: "document", ref: candidate.ref, quote: candidate.quote });
            if (!candidate.fill) return grounded;
            return fillPlaceholder(draft.id, slot.index, candidate.fill);
          })
        }
      >
        {candidate.fill ? `Use it: fill "${candidate.fill}" from ${candidate.source_name}` : `Cite ${candidate.source_name}`}
      </Button>
    </div>
  );
}

function AskExpert({ draft, slot, candidate, busy, run }: { draft: AuthorDraft; slot: PlaceholderSource; candidate: GapCandidate | null; busy: string | null; run: Run }) {
  const question = draft.draft_title || draft.cluster;
  const [owner, setOwner] = useState(candidate?.owner_role || "");
  const [text, setText] = useState(
    candidate?.quote
      ? `${candidate.source_name} says: "${candidate.quote}" Is this correct and current? ${question}`
      : `${question} Does Harbor have a policy on this?`,
  );
  return (
    <form
      className="gap-ground__form"
      onSubmit={(event) => {
        event.preventDefault();
        void run("Asking…", () => groundPlaceholder(draft.id, slot.index, { kind: "request", owner_role: owner.trim(), question: text.trim() }));
      }}
    >
      <Field id={`owner-${draft.id}`} label="Subject expert team that owns the fact" value={owner} onChange={(event) => setOwner(event.target.value)} />
      <label className="hh-label" htmlFor={`question-${draft.id}`}>
        Question to the expert
      </label>
      <textarea id={`question-${draft.id}`} className="hh-input" rows={3} value={text} onChange={(event) => setText(event.target.value)} />
      <div>
        <Button type="submit" disabled={!owner.trim() || !text.trim()} busy={busy === "Asking…"} busyLabel="Asking…">
          Send the question
        </Button>
      </div>
    </form>
  );
}

function ExpertReply({ id, requestId, busy, run }: { id: string; requestId: string; busy: string | null; run: Run }) {
  const requests = useQuery(`source-req:${requestId}`, () => getSourceRequests());
  const request = requests.data?.requests.find((item) => item.id === requestId);
  const [mode, setMode] = useState<"confirm" | "none">("confirm");
  const [statement, setStatement] = useState("");
  const [signer, setSigner] = useState("");
  return (
    <div className="gap-ground__form expert-reply">
      <p className="tools-body">
        Sent to <strong>{request?.owner_role || "the expert"}</strong> as request <span className="hh-id">{requestId}</span>: "{request?.question || "…"}"
      </p>
      <DecisionMarker kind="pending" role={request?.owner_role || "Subject expert"} />
      <p className="hh-meta">
        In production the expert answers from their own inbox. In the sandbox you play the expert. The reply is saved with a signer and a date, and marked
        "Simulated owner reply".
      </p>
      <div className="gap-ground__choices" role="group" aria-label="The expert's reply">
        <Button variant={mode === "confirm" ? "primary" : "secondary"} aria-pressed={mode === "confirm"} onClick={() => setMode("confirm")}>
          The expert gives the answer
        </Button>
        <Button variant={mode === "none" ? "primary" : "secondary"} aria-pressed={mode === "none"} onClick={() => setMode("none")}>
          The expert says no policy exists
        </Button>
      </div>
      <form
        className="gap-ground__form"
        onSubmit={(event) => {
          event.preventDefault();
          void run("Recording…", () => answerSourceRequest(requestId, statement.trim(), signer.trim(), mode === "none"));
        }}
      >
        <Field
          id={`${id}-statement`}
          label={mode === "none" ? "What the expert said" : "The expert's statement"}
          hint={
            mode === "none"
              ? "For example: Harbor has no transportation benefit or policy on this plan today."
              : "For example: A 90-day insulin supply by mail is available after two retail fills. This figure is illustrative."
          }
          value={statement}
          onChange={(event) => setStatement(event.target.value)}
        />
        <Field id={`${id}-signer`} label="Signed by" hint="A made-up name." value={signer} onChange={(event) => setSigner(event.target.value)} />
        {mode === "none" ? (
          <p className="hh-meta">No unit is written. The question goes to the Knowledge owner labelled "The business has no answer yet", and advocates keep the no-answer.</p>
        ) : null}
        <div>
          <Button type="submit" variant="secondary" disabled={!statement.trim() || !signer.trim()} busy={busy === "Recording…"} busyLabel="Recording…">
            {mode === "none" ? "Record it and send to the Knowledge owner" : "Record the expert's answer"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function FillStep({ gapId, slot, suggestion, busy, run }: { gapId: string; slot: PlaceholderSource; suggestion: string; busy: string | null; run: Run }) {
  const [fill, setFill] = useState(suggestion);
  return (
    <form
      className="gap-ground__form"
      onSubmit={(event) => {
        event.preventDefault();
        void run("Filling…", () => fillPlaceholder(gapId, slot.index, fill.trim()));
      }}
    >
      <p className="hh-meta">
        Source: <span className="hh-id">{slot.ref}</span>
        {slot.kind === "request" ? " (statement from the subject expert, simulated)" : ""}
      </p>
      <blockquote className="source-quote">{slot.quote}</blockquote>
      <Field
        id={`fill-${gapId}-${slot.index}`}
        label={`Fill ${slot.token} with words from this source`}
        hint="Copy the fact from the passage above. Anything not in the source is refused."
        value={fill}
        onChange={(event) => setFill(event.target.value)}
      />
      <div>
        <Button type="submit" disabled={!fill.trim()} busy={busy === "Filling…"} busyLabel="Filling…">
          Fill the placeholder
        </Button>
      </div>
    </form>
  );
}

function DismissForm({ draft, busy, run }: { draft: AuthorDraft; busy: string | null; run: Run }) {
  const [kind, setKind] = useState<"already_answered" | "out_of_scope">("already_answered");
  const [unitId, setUnitId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  return (
    <form
      className="gap-ground__form"
      onSubmit={(event) => {
        event.preventDefault();
        if (words(reason) < MIN_WORDS) {
          setError(`Say why, in at least ${MIN_WORDS} words. The reason is saved with the decision.`);
          return;
        }
        void run("Dismissing…", () => dismissGap(draft.id, kind, reason.trim(), unitId.trim()));
      }}
    >
      <fieldset className="gap-ground__radios">
        <legend className="hh-label">Why dismiss it?</legend>
        <label>
          <input type="radio" name={`dismiss-${draft.id}`} checked={kind === "already_answered"} onChange={() => setKind("already_answered")} /> An approved unit
          already answers it (search missed the wording)
        </label>
        <label>
          <input type="radio" name={`dismiss-${draft.id}`} checked={kind === "out_of_scope"} onChange={() => setKind("out_of_scope")} /> It is outside what
          Harbor does
        </label>
      </fieldset>
      {kind === "already_answered" ? (
        <Field id={`dismiss-unit-${draft.id}`} label="Approved unit that answers it" hint="For example: U-RX-EDU-001-09" value={unitId} onChange={(event) => setUnitId(event.target.value)} />
      ) : null}
      <Field
        id={`dismiss-reason-${draft.id}`}
        label="Reason"
        value={reason}
        error={error || undefined}
        onChange={(event) => {
          setReason(event.target.value);
          setError("");
        }}
      />
      <div>
        <Button type="submit" variant="secondary" busy={busy === "Dismissing…"} busyLabel="Dismissing…">
          Dismiss the question
        </Button>
      </div>
    </form>
  );
}

function CitePassage({ id, busy, onCite }: { id: string; busy: string | null; onCite: (ref: string, quote: string) => Promise<boolean> }) {
  const docs = useQuery("ground-docs", () => getAuthorDocuments(true));
  const [docId, setDocId] = useState("");
  const [quote, setQuote] = useState("");
  const doc = useQuery(`ground-doc:${docId}`, () => (docId ? getDocument(docId, "explore") : Promise.resolve(null)));
  const options = useMemo(() => (doc.data ? sentences(doc.data.body) : []), [doc.data]);
  return (
    <div className="gap-ground__form">
      <label className="hh-label" htmlFor={`${id}-doc`}>
        Source document
      </label>
      <select
        id={`${id}-doc`}
        className="hh-input"
        value={docId}
        onChange={(event) => {
          setDocId(event.target.value);
          setQuote("");
        }}
      >
        <option value="">Choose a document</option>
        {(docs.data?.documents ?? []).map((item) => (
          <option key={item.doc_id} value={item.doc_id}>
            {item.name && item.name !== item.doc_id ? item.name : item.title}
          </option>
        ))}
      </select>
      {docId && options.length ? (
        <fieldset className="gap-ground__sentences">
          <legend className="hh-label">Pick the sentence that states the fact</legend>
          {options.map((sentence, index) => (
            <label key={`${index}-${sentence}`} className="gap-ground__sentence">
              <input type="radio" name={`${id}-quote`} checked={quote === sentence} onChange={() => setQuote(sentence)} /> {sentence}
            </label>
          ))}
        </fieldset>
      ) : null}
      <div>
        <Button variant="primary" disabled={!quote} busy={busy === "Citing…"} busyLabel="Citing…" onClick={() => void onCite(docId, quote)}>
          Cite this passage
        </Button>
      </div>
    </div>
  );
}
