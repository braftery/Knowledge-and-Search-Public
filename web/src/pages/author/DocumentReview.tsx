import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getDocument, reviewUnit, undoWorld, type ReviewAction, type Unit } from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { DecisionMarker } from "@/components/decision-marker";
import { Field } from "@/components/field";
import { InlineProblem, ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { RoutingNote } from "@/components/routing-note";
import { StatusBadge } from "@/components/status-badge";
import { showUndoToast } from "@/components/toast";
import { readableDate } from "@/lib/dates";
import { NumberedSource } from "@/pages/demo/chrome";
import { AddUnitPanel, exactPassage } from "@/pages/author/AddUnitPanel";

type Stage = "yours" | "legal" | "sent_back" | "blocked" | "approved" | "rejected" | "other";

/** Where a unit stands for the Knowledge Ops author. */
export function unitStage(unit: Unit): Stage {
  switch (unit.status) {
    case "extracted":
      return "yours";
    case "with_legal":
      return "legal";
    case "returned":
      return "sent_back";
    case "approved":
      return "approved";
    case "rejected":
      return "rejected";
    case "blocked_conflict":
      return "blocked";
    case "proposed":
      return unit.requires_legal ? "legal" : "yours";
    default:
      return "other";
  }
}

const STAGE_BADGE: Record<Stage, { label: string; variant: "approved" | "review" | "blocked" | "neutral" }> = {
  yours: { label: "Waiting for you", variant: "review" },
  legal: { label: "With Legal", variant: "neutral" },
  sent_back: { label: "Sent back by Legal", variant: "blocked" },
  blocked: { label: "Blocked by a conflict", variant: "blocked" },
  approved: { label: "Approved", variant: "approved" },
  rejected: { label: "Rejected", variant: "neutral" },
  other: { label: "Not in review", variant: "neutral" },
};

const MIN_WORDS = 4;
const words = (text: string) => text.trim().split(/\s+/).filter(Boolean).length;

/**
 * One source document and the units the AI extracted from it, reviewed one at a time. The document is on the left
 * with each unit's passage numbered; the unit under review is on the right. Knowledge Ops approves units it owns,
 * sends regulated units to Legal, edits the AI's wording or tags, or rejects a unit with a reason.
 */
export function DocumentReview({ docId, onBack }: { docId: string; onBack?: () => void }) {
  const [tick, setTick] = useState(0);
  const doc = useQuery(`doc-review:${docId}:${tick}`, () => getDocument(docId, "explore"));
  const [onlyMine, setOnlyMine] = useState(true);
  const [current, setCurrent] = useState<string | null>(null);
  const [mode, setMode] = useState<"" | "edit" | "reject">("");
  const [busy, setBusy] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [draft, setDraft] = useState({ text: "", member: "", tags: "" });
  const [adding, setAdding] = useState<string | null>(null);
  const [selection, setSelection] = useState("");

  // Number units in the order their passages appear in the document, so unit 1 is the first highlight.
  const units = useMemo(() => {
    const body = doc.data?.body ?? "";
    const at = (unit: Unit) => {
      const found = body.indexOf(unit.source_span || unit.source_quote || "");
      return found < 0 ? Number.MAX_SAFE_INTEGER : found;
    };
    return [...(doc.data?.units ?? [])].sort((a, b) => at(a) - at(b)).map((unit, index) => ({ ...unit, number: index + 1 }));
  }, [doc.data]);
  const mine = units.filter((unit) => unitStage(unit) === "yours");
  const list = onlyMine && mine.length ? mine : units;
  const index = Math.max(0, list.findIndex((unit) => unit.unit_id === current));
  const unit = list[index];

  useEffect(() => {
    setMode("");
    setReason("");
    setProblem(null);
    if (!unit) return;
    setDraft({ text: unit.text, member: unit.member_text || "", tags: (unit.tags || []).join(", ") });
    // Scroll the document panel only, so the page header and the way back stay in view.
    const mark = document.getElementById(`src-${unit.number}`);
    const panel = mark?.closest(".source-doc") as HTMLElement | null;
    if (mark && panel) {
      const offset = mark.getBoundingClientRect().top - panel.getBoundingClientRect().top;
      panel.scrollTo({ top: Math.max(0, panel.scrollTop + offset - 48), behavior: "smooth" });
    }
  }, [unit?.unit_id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (doc.loading && !doc.data) return <Skeleton width="100%" height="320px" label="Loading the document" />;
  if (doc.error || !doc.data) return <ServiceError message={doc.error || "The document did not load."} onRetry={doc.reload} />;
  const view = doc.data;
  const added = units.filter((item) => item.drafted_by === "Knowledge Ops author").length;
  const byAi = units.length - added;
  const count = (stage: Stage) => units.filter((item) => unitStage(item) === stage).length;

  async function act(target: Unit, action: ReviewAction, body: Parameters<typeof reviewUnit>[2] = {}) {
    setBusy(action);
    setProblem(null);
    try {
      const result = await reviewUnit(target.unit_id, action, body);
      showUndoToast({
        message: result.message,
        onUndo: result.undo?.available ? () => void undoWorld("explore").then(() => setTick((value) => value + 1)) : undefined,
      });
      if (action !== "edit") {
        const rest = mine.filter((item) => item.unit_id !== target.unit_id);
        setCurrent(rest[0]?.unit_id ?? target.unit_id);
      }
      setMode("");
      setTick((value) => value + 1);
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "That did not save. Try again.");
    } finally {
      setBusy("");
    }
  }

  const stage = unit ? unitStage(unit) : "other";
  return (
    <div className="doc-review">
      <header className="doc-review__head">
        {onBack ? (
          <button type="button" className="hh-btn hh-btn--tertiary hh-btn--compact" onClick={onBack}>
            <ChevronLeft aria-hidden="true" /> My work
          </button>
        ) : null}
        <h1 className="tools-title">{view.name || view.title}</h1>
        <p className="tools-body">
          The AI read the whole document, pulled out {byAi} knowledge units, proposed a type, tags and audience for each, and tied each one to the
          passage it came from. Check them one at a time: approve the ones you own, send regulated ones to Legal, fix what the AI got wrong, or reject
          what is not a real unit.
        </p>
        <p className="doc-review__counts">
          <StatusBadge variant="review">{count("yours")} waiting for you</StatusBadge>
          <StatusBadge variant="neutral">{count("legal")} with Legal</StatusBadge>
          {count("sent_back") ? <StatusBadge variant="blocked">{count("sent_back")} sent back by Legal</StatusBadge> : null}
          {count("blocked") ? <StatusBadge variant="blocked">{count("blocked")} blocked by a conflict</StatusBadge> : null}
          <StatusBadge variant="approved">{count("approved")} approved</StatusBadge>
          {count("rejected") ? <StatusBadge variant="neutral">{count("rejected")} rejected</StatusBadge> : null}
        </p>
      </header>
      <div className="doc-review__body">
        <section className="doc-review__source" aria-label="Source document">
          <h2 className="tools-label">The full document</h2>
          <p className="hh-meta doc-review__docmeta">
            {units.length
              ? `Highlighted and numbered: the ${byAi} passages the AI turned into knowledge units${added ? `, and ${added} you added` : ""}. Click a number to review that unit. Everything else is context, such as purpose, roles and revision history, and is not extracted.`
              : "The AI extracted no units from this document. It is listed because the AI can cite it when it looks for the answer to an unanswered question."}
          </p>
          <div className="doc-review__add">
            {selection ? (
              <>
                <span className="hh-meta">Selected: "{selection.length > 80 ? `${selection.slice(0, 77)}...` : selection}"</span>
                <Button variant="primary" onClick={() => setAdding(selection)}>
                  Make this a unit
                </Button>
              </>
            ) : (
              <>
                <span className="hh-meta">Missed something? Select a passage below to make it a unit.</span>
                <Button variant="secondary" onClick={() => setAdding("")}>
                  Add a unit the AI missed
                </Button>
              </>
            )}
          </div>
          <div
            onMouseUp={() => {
              const picked = window.getSelection()?.toString() ?? "";
              setSelection(picked.trim() ? exactPassage(view.body, picked) : "");
            }}
          >
          <NumberedSource
            body={view.body}
            quotes={units.map((item) => ({ number: item.number, quote: item.source_span || item.source_quote || "" }))}
            active={unit?.number}
            onPick={(number) => {
              const picked = units.find((item) => item.number === number);
              if (!picked) return;
              if (onlyMine && unitStage(picked) !== "yours") setOnlyMine(false);
              setCurrent(picked.unit_id);
            }}
          />
          </div>
        </section>
        <section className="doc-review__unit" aria-labelledby="doc-unit-h" aria-live="polite">
          <div className="doc-review__nav">
            <label className="doc-review__filter">
              <input
                type="checkbox"
                checked={onlyMine && mine.length > 0}
                disabled={!mine.length}
                onChange={(event) => {
                  setOnlyMine(event.target.checked);
                  setCurrent(null);
                }}
              />{" "}
              Only units waiting for me
            </label>
            <span className="hh-meta">{unit ? `Unit ${index + 1} of ${list.length}` : ""}</span>
            <div className="doc-review__arrows">
              <Button variant="secondary" disabled={index <= 0} onClick={() => setCurrent(list[index - 1]?.unit_id ?? null)}>
                <ChevronLeft aria-hidden="true" /> Previous
              </Button>
              <Button variant="secondary" disabled={index >= list.length - 1} onClick={() => setCurrent(list[index + 1]?.unit_id ?? null)}>
                Next <ChevronRight aria-hidden="true" />
              </Button>
            </div>
          </div>
          {!mine.length ? <p className="hh-meta">Nothing in this document is waiting for you. Showing every unit.</p> : null}
          {adding !== null ? (
            <AddUnitPanel
              key={adding}
              docId={docId}
              body={view.body}
              covered={units.map((item) => item.source_span || item.source_quote || "")}
              initialSpan={adding}
              onCancel={() => setAdding(null)}
              onDone={(unitId, message) => {
                setAdding(null);
                setSelection("");
                window.getSelection()?.removeAllRanges();
                showUndoToast({ message, onUndo: () => void undoWorld("explore").then(() => setTick((value) => value + 1)) });
                setOnlyMine(true);
                setCurrent(unitId);
                setTick((value) => value + 1);
              }}
            />
          ) : null}
          {adding === null && unit ? (
            <article className="hh-card doc-unit">
              <div className="hh-card__head">
                <h2 className="hh-card__title" id="doc-unit-h">
                  <span className="unit-card__num">{unit.number}</span>
                  {unit.title}
                </h2>
                <div className="item-head__badges">
                  <StatusBadge variant="neutral">{typeName(unit.type)}</StatusBadge>
                  <StatusBadge variant={STAGE_BADGE[stage].variant}>{STAGE_BADGE[stage].label}</StatusBadge>
                </div>
              </div>
              <p className="hh-meta">
                <span className="hh-id">{unit.unit_id}</span>
              </p>
              {mode === "edit" ? (
                <form
                  className="doc-unit__edit"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void act(unit, "edit", {
                      text: draft.text.trim(),
                      member_text: draft.member.trim(),
                      tags: draft.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
                    });
                  }}
                >
                  <label className="hh-label" htmlFor="doc-edit-text">
                    Advocate wording
                  </label>
                  <textarea id="doc-edit-text" className="hh-input" rows={4} value={draft.text} onChange={(event) => setDraft({ ...draft, text: event.target.value })} />
                  <label className="hh-label" htmlFor="doc-edit-member">
                    Member wording (optional)
                  </label>
                  <textarea id="doc-edit-member" className="hh-input" rows={3} value={draft.member} onChange={(event) => setDraft({ ...draft, member: event.target.value })} />
                  <label className="hh-label" htmlFor="doc-edit-tags">
                    Tags, separated by commas
                  </label>
                  <input id="doc-edit-tags" className="hh-input" value={draft.tags} onChange={(event) => setDraft({ ...draft, tags: event.target.value })} />
                  <div className="doc-unit__actions">
                    <Button variant="primary" type="submit" busy={busy === "edit"} busyLabel="Saving…">
                      Save the edit
                    </Button>
                    <Button variant="tertiary" onClick={() => setMode("")}>
                      Cancel
                    </Button>
                  </div>
                </form>
              ) : (
                <>
                  <h3 className="tools-label">Advocate wording</h3>
                  <p className="tools-body approve-wording">{unit.text}</p>
                  {unit.member_text ? (
                    <>
                      <h3 className="tools-label">Member wording</h3>
                      <p className="tools-body approve-wording">{unit.member_text}</p>
                    </>
                  ) : null}
                </>
              )}
              <h3 className="tools-label">Source passage it came from</h3>
              <blockquote className="source-quote">{unit.source_span || unit.source_quote || "No source passage is recorded."}</blockquote>
              <dl className="preview-list">
                <div>
                  <dt>Tags</dt>
                  <dd>{(unit.tags || []).join(", ") || "None"}</dd>
                </div>
                <div>
                  <dt>Audience</dt>
                  <dd>{(unit.audience || []).join(", ") || "Not set"}</dd>
                </div>
                <div>
                  <dt>Who approves</dt>
                  <dd>{unit.requires_legal ? "Legal, after you send it" : "Knowledge Ops (you)"}</dd>
                </div>
              </dl>
              {unit.drafted_by === "Knowledge Ops author" ? (
                <DecisionMarker kind="human" role="Knowledge Ops author" decision="Added from the source passage. The AI did not extract it." />
              ) : (
                <DecisionMarker kind="ai" detail="Span, type, tags and audience proposed by the model." />
              )}
              {unit.duplicate_of && stage === "yours" ? (
                <p className="hh-meta doc-unit__flag">
                  The AI thinks this repeats approved unit <span className="hh-id">{unit.duplicate_of}</span>. If the wording matches, reject it as a duplicate.
                </p>
              ) : null}
              {unit.routing_reason ? <RoutingNote reason={unit.routing_reason} /> : null}

              {stage === "yours" && mode === "" ? (
                <div className="doc-unit__actions">
                  <DecisionMarker kind="pending" role="Knowledge Ops author" />
                  {unit.requires_legal ? (
                    <Button variant="primary" busy={busy === "send_to_legal"} busyLabel="Sending…" onClick={() => void act(unit, "send_to_legal")}>
                      Send to Legal
                    </Button>
                  ) : (
                    <>
                      <Button variant="primary" busy={busy === "approve"} busyLabel="Approving…" onClick={() => void act(unit, "approve")}>
                        Approve
                      </Button>
                      <Button variant="secondary" busy={busy === "send_to_legal"} busyLabel="Sending…" onClick={() => void act(unit, "send_to_legal")}>
                        Send to Legal anyway
                      </Button>
                    </>
                  )}
                  <Button variant="secondary" onClick={() => setMode("edit")}>
                    Edit
                  </Button>
                  <Button variant="tertiary" onClick={() => setMode("reject")}>
                    Reject
                  </Button>
                </div>
              ) : null}
              {stage === "yours" && mode === "reject" ? (
                <form
                  className="doc-unit__reject"
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (words(reason) < MIN_WORDS) {
                      setProblem(`Say why, in at least ${MIN_WORDS} words. The reason is saved with the decision.`);
                      return;
                    }
                    void act(unit, "reject", { reason: reason.trim() });
                  }}
                >
                  <Field
                    id="doc-reject-reason"
                    label="Why reject this unit?"
                    hint="For example: it repeats an approved unit, or it is a heading, not a fact. Saved with the decision."
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                  />
                  <div className="doc-unit__actions">
                    <Button variant="primary" type="submit" busy={busy === "reject"} busyLabel="Rejecting…">
                      Reject the unit
                    </Button>
                    <Button variant="tertiary" onClick={() => setMode("")}>
                      Cancel
                    </Button>
                  </div>
                </form>
              ) : null}
              {problem ? <InlineProblem message={problem} /> : null}
              {stage === "legal" ? <DecisionMarker kind="pending" role="Legal approver" /> : null}
              {stage === "legal" ? <p className="hh-meta">With Legal. It stays out of search until Legal approves it or sends it back to you.</p> : null}
              {stage === "sent_back" ? <p className="hh-meta">Legal sent this back. Open it under Sent back by Legal in My work to edit and resend it.</p> : null}
              {stage === "blocked" ? <p className="hh-meta">Another document words this differently. Both stay out of search until Legal picks one.</p> : null}
              {stage === "rejected" ? <DecisionMarker kind="human" role="Knowledge Ops author" decision="Rejected. It will never be searchable." /> : null}
              {stage === "approved" ? (
                <DecisionMarker
                  kind="human"
                  role={unit.approved_by || "Approver"}
                  decision={`Approved${unit.approved_on ? ` ${readableDate(unit.approved_on)}` : ""}. Search can use it.`}
                />
              ) : null}
            </article>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function typeName(type: string) {
  const names: Record<string, string> = { verbatim: "Verbatim", policy: "Policy", procedure: "Procedure", faq: "FAQ" };
  return names[type] || type;
}
