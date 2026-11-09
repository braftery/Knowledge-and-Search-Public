import { useMemo, useState } from "react";
import { addUnitFromSpan } from "@/api/guided";
import { Button } from "@/components/button";
import { Field } from "@/components/field";
import { InlineProblem } from "@/components/service-state";
import { sentences } from "@/pages/author/GapGrounding";

/**
 * Find the exact passage in the document for text the person selected on screen. The panel renders bullets and bold
 * differently from the source, so the match ignores those marks and spacing, then returns the document's own words.
 */
export function exactPassage(body: string, selected: string): string {
  const words = selected
    .replace(/[•*]/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (words.length < 4) return "";
  const match = new RegExp(words.join("[\\s*\\-\\u2022]+")).exec(body);
  return match ? match[0] : "";
}

export function AddUnitPanel({
  docId,
  body,
  covered,
  initialSpan,
  onDone,
  onCancel,
}: {
  docId: string;
  body: string;
  covered: string[];
  initialSpan: string;
  onDone: (unitId: string, message: string) => void;
  onCancel: () => void;
}) {
  const options = useMemo(
    () =>
      sentences(body)
        // Header lines such as "Owner: Pharmacy Knowledge" are document metadata, not statements.
        .filter((sentence) => !/^[A-Z][A-Za-z ]{1,24}:\s/.test(sentence))
        .filter((sentence) => !covered.some((quote) => quote && (quote.includes(sentence) || sentence.includes(quote)))),
    [body, covered],
  );
  const [span, setSpan] = useState(initialSpan);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("procedure");
  const [member, setMember] = useState(false);
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");
  const legal = type === "verbatim" || type === "policy" || /\$\s?\d/.test(span) || /\bcost\b|\bclinical\b/i.test(tags);

  async function create() {
    setBusy(true);
    setProblem("");
    try {
      const result = await addUnitFromSpan(docId, {
        span,
        title,
        type,
        audience: member ? ["advocate", "member"] : ["advocate"],
        tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      });
      onDone(result.unit_id, result.message);
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "That did not save. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="hh-card doc-unit add-unit" aria-labelledby="add-unit-h">
      <h2 className="hh-card__title" id="add-unit-h">
        Add a unit the AI missed
      </h2>
      <p className="tools-body">
        Select a passage in the document on the left, or pick a sentence below. The unit keeps the document's exact words and is tied to that passage. It
        then waits for a decision like any other unit.
      </p>
      {span ? (
        <>
          <h3 className="tools-label">Passage</h3>
          <blockquote className="source-quote">{span}</blockquote>
        </>
      ) : null}
      <label className="hh-label" htmlFor="add-unit-pick">
        {span ? "Or pick a different sentence" : "Pick a sentence the AI did not extract"}
      </label>
      <select id="add-unit-pick" className="hh-input" value={options.includes(span) ? span : ""} onChange={(event) => setSpan(event.target.value)}>
        <option value="">Choose a sentence</option>
        {options.map((sentence) => (
          <option key={sentence} value={sentence}>
            {sentence.length > 110 ? `${sentence.slice(0, 107)}...` : sentence}
          </option>
        ))}
      </select>
      <Field id="add-unit-title" label="Title" hint="Short, in plain words. Leave blank to use the first words." value={title} onChange={(event) => setTitle(event.target.value)} />
      <label className="hh-label" htmlFor="add-unit-type">
        Type
      </label>
      <select id="add-unit-type" className="hh-input" value={type} onChange={(event) => setType(event.target.value)}>
        <option value="procedure">Procedure (a step advocates follow)</option>
        <option value="faq">FAQ (an answer to a common question)</option>
        <option value="policy">Policy (a rule)</option>
        <option value="verbatim">Verbatim (words read exactly as written)</option>
      </select>
      <label className="add-unit__check">
        <input type="checkbox" checked={member} onChange={(event) => setMember(event.target.checked)} /> Members can read this too, not only advocates
      </label>
      <Field id="add-unit-tags" label="Tags, separated by commas" value={tags} onChange={(event) => setTags(event.target.value)} />
      <p className="hh-meta">
        {legal
          ? "This will go to Legal: policy, verbatim, cost and clinical wording always need Legal approval."
          : "You can approve this yourself: procedures and FAQs belong to Knowledge Ops."}
      </p>
      {problem ? <InlineProblem message={problem} /> : null}
      <div className="doc-unit__actions">
        <Button disabled={!span || busy} busy={busy} busyLabel="Adding…" onClick={() => void create()}>
          Add the unit
        </Button>
        <Button variant="tertiary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </article>
  );
}
