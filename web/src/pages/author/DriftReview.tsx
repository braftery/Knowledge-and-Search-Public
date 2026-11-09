import { useState } from "react";
import { type AuthorDrift, type DriftAction } from "@/api/guided";
import { Button } from "@/components/button";
import { DecisionMarker } from "@/components/decision-marker";
import { Field } from "@/components/field";
import { StatusBadge } from "@/components/status-badge";
import { SourceDocument } from "@/pages/legal/SourceDocument";

type Mutation = { message: string; undo?: { available?: boolean } };
type Act = (action: DriftAction, body: { reason?: string; text?: string }) => Promise<unknown>;

const MIN_WORDS = 4;
const words = (text: string) => text.trim().split(/\s+/).filter(Boolean).length;

const WHY: Record<string, { ko: string; legal: string }> = {
  material: {
    ko: "The source changed in a way that changes what advocates do. You approved this unit, so the fix comes to you.",
    legal: "The source changed in a way that changes the meaning of wording Legal approved, so the fix comes to you.",
  },
  uncertain: {
    ko: "The AI could not tell whether this change matters, so it asks a person instead of guessing.",
    legal: "The AI could not tell whether this change matters, so it asks a person instead of guessing.",
  },
  removed: {
    ko: "The passage this unit came from was deleted. A unit with no source cannot stay approved without a decision.",
    legal: "The passage this unit came from was deleted. A unit with no source cannot stay approved without a decision.",
  },
  cosmetic_verbatim: {
    ko: "Cosmetic, but inside wording read word for word.",
    legal: "The change is cosmetic, but this is wording advocates read word for word. It must match its source exactly, so even punctuation comes to you.",
  },
};

/**
 * One source change behind an approved unit, for whoever approved that unit. The source document is shown with the
 * new passage highlighted, the live wording beside the AI's proposed fix, and the decisions that fit this kind of
 * change. The approved version stays live until the decision is made.
 */
export function DriftReview({
  item,
  who,
  busy,
  problem,
  act,
}: {
  item: AuthorDrift;
  who: "ko" | "legal";
  busy: string | null;
  problem: string | null;
  act: Act;
}) {
  const kind = item.kind || "material";
  const [mode, setMode] = useState<"" | "edit" | "keep" | "retire">("");
  const [text, setText] = useState(item.new_wording);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const role = who === "ko" ? "Knowledge Ops author" : "Legal approver";

  function withReason(action: DriftAction) {
    if (words(reason) < MIN_WORDS) {
      setError(`Say why, in at least ${MIN_WORDS} words. The reason is saved with the decision.`);
      return;
    }
    void act(action, { reason: reason.trim() });
  }

  return (
    <article className="work-card drift-review">
      <div className="item-head">
        <div className="item-head__text">
          <p className="tools-overline">Source change</p>
          <h2 className="tools-title">{item.title || item.unit_id}</h2>
          <p className="item-head__meta">
            <span className="hh-id">{item.unit_id}</span>
            {item.version ? <span> · live version {item.version}</span> : null}
          </p>
        </div>
        <div className="item-head__badges">
          <StatusBadge variant={kind === "material" || kind === "removed" ? "review" : "neutral"}>{item.kind_label || "Material change"}</StatusBadge>
        </div>
      </div>
      {item.summary ? <p className="tools-body">{item.summary}</p> : null}
      <p className="hh-meta">{(WHY[kind] ?? WHY.material)[who]} The approved version stays live until you decide.</p>

      {kind === "removed" ? (
        <>
          <h3 className="tools-label">Deleted from the source</h3>
          <blockquote className="source-quote drift-removed">{item.source_before}</blockquote>
          {item.doc_id ? <SourceDocument docId={item.doc_id} quote="" world="explore" caption="The document as it reads now. The passage above is no longer in it." /> : null}
          <h3 className="tools-label">Live now, with no source</h3>
          <blockquote className="source-quote">{item.old_wording}</blockquote>
        </>
      ) : (
        <>
          {item.doc_id ? (
            <SourceDocument
              docId={item.doc_id}
              quote={item.source_after || ""}
              world="explore"
              caption={`The document as it reads now, with the changed passage highlighted. It used to read: "${item.source_before}"`}
            />
          ) : null}
          <div className="drift-pair">
            <div>
              <h3 className="tools-label">Live now</h3>
              <blockquote className="source-quote">{item.old_wording}</blockquote>
            </div>
            <div>
              <h3 className="tools-label">AI's proposed wording, from the new source</h3>
              <blockquote className="source-quote">{item.new_wording}</blockquote>
            </div>
          </div>
        </>
      )}
      <DecisionMarker
        kind="ai"
        detail={kind === "uncertain" ? "The model flagged this change as possibly material and asked for a person." : "Change classified and fix proposed by the model."}
      />

      {mode === "" ? (
        <div className="work-actions">
          <DecisionMarker kind="pending" role={role} />
          {kind === "removed" ? (
            <>
              <Button onClick={() => setMode("retire")}>Retire the unit</Button>
              <Button variant="secondary" onClick={() => setMode("keep")}>
                Keep it live
              </Button>
            </>
          ) : kind === "uncertain" || kind === "cosmetic_verbatim" ? (
            <>
              <Button busy={busy === "confirm_cosmetic"} busyLabel="Saving…" disabled={Boolean(busy)} onClick={() => void act("confirm_cosmetic", {})}>
                {kind === "uncertain" ? "It's cosmetic: keep the wording" : "Keep the wording; fix the source back"}
              </Button>
              <Button variant="secondary" busy={busy === "accept_fix"} busyLabel="Publishing…" disabled={Boolean(busy)} onClick={() => void act("accept_fix", {})}>
                {kind === "uncertain" ? "It matters: update the unit" : "Accept: republish to match the source"}
              </Button>
              <Button variant="tertiary" onClick={() => setMode("edit")}>
                Edit and accept
              </Button>
            </>
          ) : (
            <>
              <Button busy={busy === "accept_fix"} busyLabel="Publishing…" disabled={Boolean(busy)} onClick={() => void act("accept_fix", {})}>
                Accept the fix
              </Button>
              <Button variant="secondary" onClick={() => setMode("edit")}>
                Edit and accept
              </Button>
              <Button variant="tertiary" onClick={() => setMode("keep")}>
                Keep the current wording
              </Button>
            </>
          )}
        </div>
      ) : null}
      {mode === "edit" ? (
        <form
          className="gap-ground__form"
          onSubmit={(event) => {
            event.preventDefault();
            void act("edit_and_accept", { text: text.trim() });
          }}
        >
          <label className="hh-label" htmlFor={`drift-text-${item.id}`}>
            New wording
          </label>
          <textarea id={`drift-text-${item.id}`} className="hh-input" rows={3} value={text} onChange={(event) => setText(event.target.value)} />
          <div className="work-actions">
            <Button type="submit" busy={busy === "edit_and_accept"} busyLabel="Publishing…" disabled={!text.trim()}>
              Publish the edited version
            </Button>
            <Button variant="tertiary" onClick={() => setMode("")}>
              Cancel
            </Button>
          </div>
        </form>
      ) : null}
      {mode === "keep" || mode === "retire" ? (
        <form
          className="gap-ground__form"
          onSubmit={(event) => {
            event.preventDefault();
            withReason(mode === "retire" ? "retire" : "keep_current");
          }}
        >
          <Field
            id={`drift-reason-${item.id}`}
            label={mode === "retire" ? "Why retire it?" : "Why keep the current wording?"}
            hint={
              mode === "retire"
                ? "For example: the policy no longer has this step. Advocates stop seeing it at once."
                : kind === "removed"
                  ? "For example: the step moved to the contact-record SOP, which still states it."
                  : "For example: the new hours start next quarter, not today."
            }
            value={reason}
            error={error || undefined}
            onChange={(event) => {
              setReason(event.target.value);
              setError("");
            }}
          />
          <div className="work-actions">
            <Button type="submit" variant="secondary" busy={busy === "keep_current" || busy === "retire"} busyLabel="Saving…">
              {mode === "retire" ? "Retire it" : "Keep it and clear the flag"}
            </Button>
            <Button variant="tertiary" onClick={() => setMode("")}>
              Cancel
            </Button>
          </div>
        </form>
      ) : null}
      {problem ? (
        <p className="hh-error" role="alert">
          {problem}
        </p>
      ) : null}
    </article>
  );
}

/** Cosmetic changes the AI logged without asking anyone. Shown under Sources, never in My work. */
export function DriftLog({ automatic }: { automatic: Array<{ id: number; unit_id: string; summary: string; actor: string }> }) {
  return (
    <section className="drift-log" aria-labelledby="drift-log-h">
      <h2 className="tools-label" id="drift-log-h">
        Changes handled automatically
      </h2>
      <p className="hh-meta">Cosmetic edits to a source, such as punctuation, are logged here without asking anyone. The approved wording does not change.</p>
      {automatic.length ? (
        <ul>
          {automatic.map((entry) => (
            <li key={entry.id}>
              <span className="hh-id">{entry.unit_id}</span>: {entry.summary}
            </li>
          ))}
        </ul>
      ) : (
        <p className="hh-meta">Nothing logged.</p>
      )}
    </section>
  );
}

export type { Mutation };
