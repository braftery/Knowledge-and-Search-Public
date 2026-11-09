import { BellRing, CheckCircle2, Sparkles } from "lucide-react";
import { useState } from "react";
import { acknowledgeChange, getChanges, getGaps, saveWrapup, type UnitChange, type WrapupOutcome } from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { DiffLegend, DiffText } from "@/components/diff-view";
import { showUndoToast } from "@/components/toast";
import { apiDiff } from "@/lib/labels";

/** Fix 3: tells advocates when Legal published new wording they read aloud, and records that they read it. */
export function ChangeBanner({ role, refreshKey }: { role: string; refreshKey: number }) {
  const [tick, setTick] = useState(0);
  const changes = useQuery(`changes:${role}:${refreshKey}:${tick}`, () => getChanges(role));
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");
  const pending = (changes.data?.changes ?? []).filter((change) => !change.acknowledged);
  if (!pending.length) return null;
  const first = pending[0];
  const key = `${first.unit_id}:${first.version}`;

  async function acknowledge(change: UnitChange) {
    setBusy(true);
    setProblem("");
    try {
      const result = await acknowledgeChange(role, change.unit_id, change.version);
      showUndoToast({ message: result.message });
      setOpen(null);
      setTick((value) => value + 1);
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "That did not save. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="desk-change" aria-label="Approved wording changed">
      <div className="desk-change__row">
        <BellRing aria-hidden="true" className="desk-change__icon" />
        <p className="desk-change__text">
          <strong>{first.title}</strong> changed to version {first.version}
          {first.approved_on ? ` on ${formatDay(first.approved_on)}` : ""}.{" "}
          {first.type === "verbatim" ? "You read this wording aloud. Read the new version before your next quote." : "Review what changed."}
          {pending.length > 1 ? ` ${pending.length - 1} more ${pending.length === 2 ? "change" : "changes"} after this one.` : ""}
        </p>
        <Button variant="secondary" compact aria-expanded={open === key} onClick={() => setOpen(open === key ? null : key)}>
          {open === key ? "Hide the change" : "See what changed"}
        </Button>
      </div>
      {open === key ? (
        <div className="desk-change__detail">
          <DiffLegend />
          <p className="desk-change__diff">
            <DiffText parts={apiDiff(first.diff)} />
          </p>
          <p className="hh-meta">
            Approved by {first.approved_by || "Legal approver"}. Version {first.previous_version} stays in the history.
          </p>
          <div className="work-actions">
            <Button busy={busy} busyLabel="Saving…" onClick={() => void acknowledge(first)}>
              I have read the new wording
            </Button>
          </div>
          {problem ? (
            <p className="hh-error" role="alert">
              {problem}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

/** Fix 4: tells advocates when a question their role asked with no answer now has an approved one. */
export function AnsweredNotice({ role, onShow }: { role: string; onShow: (question: string) => void }) {
  const gaps = useQuery(`answered:${role}`, () => getGaps("explore"));
  const [hidden, setHidden] = useState<string[]>([]);
  const closed = (gaps.data?.gaps ?? []).filter(
    (gap) => gap.status === "closed" && gap.roles.includes(role) && !hidden.includes(gap.id),
  );
  if (!closed.length) return null;
  return (
    <div className="desk-answered" role="status">
      {closed.map((gap) => (
        <div key={gap.id} className="desk-answered__item">
          <Sparkles aria-hidden="true" className="desk-answered__icon" />
          <div className="desk-answered__body">
            <p className="desk-answered__title">New approved answer</p>
            <p className="tools-body">
              {gap.draft_title || gap.cluster}.{" "}
              {gap.search_count > 1
                ? `Advocates asked this ${gap.search_count} times and got no answer. An approved answer is live now.`
                : "An advocate asked this and got no answer. An approved answer is live now."}
            </p>
            <div className="desk-answered__actions">
              <Button variant="secondary" compact onClick={() => onShow(gap.queries[0] || gap.query_example)}>
                Show the answer
              </Button>
              <Button variant="tertiary" compact onClick={() => setHidden((list) => [...list, gap.id])}>
                Dismiss
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** A unit the advocate saw on this call, with the version and wording on screen, so the wrap-up records exactly what was read. */
export type ShownUnit = { unit_id: string; verbatim: boolean; title: string; version?: number; text?: string };

const OUTCOMES: Array<{ id: WrapupOutcome; label: string }> = [
  { id: "resolved", label: "Resolved on this call" },
  { id: "follow_up", label: "Needs a follow-up" },
  { id: "transferred", label: "Transferred" },
];

/** Fix 2: after the call, the advocate confirms the verbatim read and how the call ended. */
export function WrapUp({
  role,
  callId,
  callReason,
  shown,
  initialNote = "",
  onSaved,
  onNextCall,
}: {
  initialNote?: string;
  role: string;
  callId: string;
  callReason: string;
  shown: ShownUnit[];
  onSaved: () => void;
  onNextCall: () => void;
}) {
  const verbatim = shown.filter((unit) => unit.verbatim);
  const [read, setRead] = useState<boolean | null>(null);
  const [outcome, setOutcome] = useState<WrapupOutcome | null>(null);
  const [note, setNote] = useState(initialNote);
  const [errors, setErrors] = useState<{ read?: string; outcome?: string; note?: string; form?: string }>({});
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);

  async function save() {
    const next: typeof errors = {};
    if (verbatim.length && read === null) next.read = "Confirm whether you read the approved wording word for word.";
    if (!outcome) next.outcome = "Choose how the call ended.";
    if (outcome === "follow_up" && !note.trim()) next.note = "Add a note so the follow-up has what it needs.";
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      const result = await saveWrapup({
        role,
        call_id: callId,
        call_reason: callReason,
        unit_ids: shown.map((unit) => unit.unit_id),
        displayed_units: shown.map((unit) => ({ unit_id: unit.unit_id, version: unit.version ?? 0, text: unit.text ?? "" })),
        read_verbatim: verbatim.length ? read : null,
        outcome: outcome as WrapupOutcome,
        note: note.trim(),
      });
      setSaved(result.message);
      showUndoToast({ message: result.message });
      onSaved();
    } catch (error) {
      setErrors({ form: error instanceof Error ? error.message : "The wrap-up did not save. Try again." });
    } finally {
      setBusy(false);
    }
  }

  if (saved) {
    return (
      <article className="desk-card desk-card--wide desk-wrap desk-wrap--done" aria-live="polite">
        <p className="desk-wrap__done">
          <CheckCircle2 aria-hidden="true" />
          <span>
            <strong>Wrap-up saved.</strong> {read === true ? "Your word-for-word read is on the record." : ""}
            {outcome === "follow_up" ? " The follow-up is logged with your note." : ""}
          </span>
        </p>
        <div>
          <Button onClick={onNextCall}>Take the next call</Button>
        </div>
      </article>
    );
  }

  return (
    <article className="desk-card desk-card--wide desk-wrap" aria-labelledby="wrap-h">
      <h2 id="wrap-h" className="desk-card__title">
        Wrap up this call
      </h2>
      {verbatim.length ? (
        <fieldset className="desk-wrap__group">
          <legend className="hh-label">
            Did you read {verbatim.length === 1 ? `“${verbatim[0].title}”` : "the approved wording"} word for word?
          </legend>
          <div className="desk-wrap__choices">
            <label>
              <input type="radio" name="wrap-read" checked={read === true} onChange={() => setRead(true)} /> Yes, word for word
            </label>
            <label>
              <input type="radio" name="wrap-read" checked={read === false} onChange={() => setRead(false)} /> No
            </label>
          </div>
          {errors.read ? <p className="hh-error">{errors.read}</p> : null}
          <p className="hh-meta">This answer is the compliance record for the call. It is saved with the unit and version you were shown.</p>
        </fieldset>
      ) : (
        <p className="hh-meta">No verbatim wording was shown on this call, so there is nothing to confirm.</p>
      )}
      <fieldset className="desk-wrap__group">
        <legend className="hh-label">How did the call end?</legend>
        <div className="desk-wrap__choices">
          {OUTCOMES.map((item) => (
            <label key={item.id}>
              <input type="radio" name="wrap-outcome" checked={outcome === item.id} onChange={() => setOutcome(item.id)} /> {item.label}
            </label>
          ))}
        </div>
        {errors.outcome ? <p className="hh-error">{errors.outcome}</p> : null}
      </fieldset>
      <label className="hh-label" htmlFor="wrap-note">
        Note{" "}
        {outcome === "follow_up" ? <span className="hh-opt">(required for a follow-up)</span> : <span className="hh-opt">(optional)</span>}
      </label>
      <input
        id="wrap-note"
        className="hh-input"
        value={note}
        onChange={(event) => setNote(event.target.value)}
        aria-invalid={errors.note ? true : undefined}
      />
      {errors.note ? <p className="hh-error">{errors.note}</p> : null}
      <p className="hh-meta">Member details are removed from the note before it is stored.</p>
      <div className="work-actions">
        <Button busy={busy} busyLabel="Saving…" onClick={() => void save()}>
          Save wrap-up
        </Button>
      </div>
      {errors.form ? (
        <p className="hh-error" role="alert">
          {errors.form}
        </p>
      ) : null}
    </article>
  );
}

function formatDay(value: string) {
  const date = new Date(`${value.slice(0, 10)}T12:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
