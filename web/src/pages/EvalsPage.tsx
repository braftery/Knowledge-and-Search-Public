import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

/**
 * Scores from the latest eval run (scripts/run_evals.py). Every item ran several times; an item counts as right when
 * most runs got it right. The interval is a 95% Wilson interval on that count. Every miss is listed.
 */

type Summary = {
  name: string;
  items: number;
  runs: number;
  majority_correct: number;
  majority_rate: number | null;
  interval_95: [number, number];
  correct_every_run: number;
  per_run_correct: number[];
  consistency: { items: number; same_every_run: number; share: number | null };
};

type Miss = Record<string, unknown>;

type Results = {
  available: boolean;
  message?: string;
  generated_at?: string;
  model?: string;
  runs?: number;
  sets?: Record<string, number>;
  extraction?: { units_found: Summary; verbatim_exact: Summary; type_correct: Summary; left_alone: Summary; misses: Miss[]; documents: Array<{ file: string; key_units: number; leave_alone: number }> };
  search?: { overall: Summary; answerable: Summary; abstain: Summary; by_trap_kind: Record<string, Summary>; leaks: number; misses: Miss[] };
  duplicates?: { overall: Summary; by_kind: Record<string, Summary>; false_merges_across_runs: number; lookalikes_not_merged?: Summary; misses: Miss[] };
  drift?: { overall: Summary; material_fix_matches_new_source: { matches: number; total: number }; misses: Miss[] };
  gaps?: { overall: Summary; misses: Miss[] };
};

const KIND_NAMES: Record<string, string> = {
  plain: "Plain questions",
  misspelling: "Misspellings",
  acronym: "Acronyms",
  near_miss: "Near misses (should get no answer)",
  partial: "Partial answers",
  other_role: "Another role's knowledge",
  near_duplicate: "Near duplicates",
  conflict: "Conflicts",
  lookalike: "Lookalikes (differ by one word or number)",
};

function readableTime(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "America/New_York" }) + " ET";
}

const pct = (value: number) => `${Math.round(value * 100)}%`;

function Score({ summary, lead }: { summary?: Summary; lead?: string }) {
  if (!summary || !summary.items) return <p className="hh-meta">Not run yet.</p>;
  const [low, high] = summary.interval_95;
  const rate = summary.majority_rate ?? 0;
  const same = summary.consistency;
  return (
    <div className="eval-score">
      <div className="eval-score__head">
        <strong className="eval-score__big">
          {summary.majority_correct} of {summary.items}
        </strong>
        <span>{lead ?? summary.name}</span>
      </div>
      <div className="eval-bar" role="img" aria-label={`${pct(rate)} right, 95% interval ${pct(low)} to ${pct(high)}`}>
        <span className="eval-bar__range" style={{ left: pct(low), width: pct(Math.max(0.005, high - low)) }} />
        <span className="eval-bar__point" style={{ left: pct(rate) }} />
      </div>
      <p className="hh-meta">
        95% interval {pct(low)} to {pct(high)}. Right on every one of {summary.runs} runs: {summary.correct_every_run}.{" "}
        {same.items ? `Same result on every run: ${same.same_every_run} of ${same.items}.` : ""}
      </p>
    </div>
  );
}

function Breakdown({ rows }: { rows?: Record<string, Summary> }) {
  const entries = Object.entries(rows ?? {}).filter(([, summary]) => summary.items);
  if (!entries.length) return null;
  return (
    <table className="eval-table">
      <thead>
        <tr>
          <th scope="col">Kind</th>
          <th scope="col">Right on most runs</th>
          <th scope="col">95% interval</th>
          <th scope="col">Same every run</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([kind, summary]) => (
          <tr key={kind}>
            <th scope="row">{KIND_NAMES[kind] ?? kind}</th>
            <td>
              {summary.majority_correct} of {summary.items}
            </td>
            <td>
              {pct(summary.interval_95[0])} to {pct(summary.interval_95[1])}
            </td>
            <td>
              {summary.consistency.same_every_run} of {summary.consistency.items}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Misses({ misses }: { misses?: Miss[] }) {
  if (!misses?.length) return <p className="hh-meta">No misses.</p>;
  return (
    <details className="eval-misses">
      <summary>
        Every miss ({misses.length}). Shown as recorded, not edited.
      </summary>
      <ul>
        {misses.map((miss, index) => (
          <li key={index}>
            {Object.entries(miss)
              .filter(([key]) => key !== "eval")
              .map(([key, value]) => (
                <span key={key} className="eval-miss__field">
                  <span className="eval-miss__key">{key.replace(/_/g, " ")}:</span> {typeof value === "string" ? value : JSON.stringify(value)}
                </span>
              ))}
          </li>
        ))}
      </ul>
    </details>
  );
}

export function EvalsPage() {
  const [data, setData] = useState<Results | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/api/evals")
      .then((response) => response.json())
      .then(setData)
      .catch(() => setError("The eval results did not load."));
  }, []);

  return (
    <main id="main-content" className="hh launcher pilot evals" data-theme="tools">
      <header className="launcher__top">
        <Link className="launcher__brand" to="/">
          Harbor Health <span>Single Source</span>
        </Link>
        <span className="hh-presenter__pill launcher__pill">Illustrative data</span>
      </header>
      <div className="launcher__body pilot__body">
        <section>
          <p className="tools-overline">How well the AI performs</p>
          <h1 className="launcher__title">Each AI task, tested against answer keys written before the model ran.</h1>
          <p className="launcher__lead">
            Five model tasks, each scored on made-up documents and questions. Every input ran {data?.runs ?? "several"} times, so you can see both whether
            the AI is right and whether it gives the same answer twice. An item counts as right when most runs got it right.
          </p>
          {data?.available ? (
            <p className="hh-meta">
              Run {readableTime(data.generated_at)} with {data.model}. Answer keys and test sets were committed before any model output existed; the git history shows the
              order.
            </p>
          ) : null}
        </section>

        {error ? <p className="hh-error">{error}</p> : null}
        {!data && !error ? <p className="hh-meta">Loading the latest results…</p> : null}
        {data && !data.available ? <p className="tools-body">{data.message}</p> : null}

        {data?.available ? (
          <>
            <section className="eval-section" aria-labelledby="ev-search">
              <h2 className="launcher__h2" id="ev-search">
                1. Search answer
              </h2>
              <p className="tools-body">
                Given a question and the approved units the role may read, does the AI pick the unit that answers it, and say no when none does? This test
                treats every unit in the answer keys as approved, so it measures search on its own.
              </p>
              <div className="eval-grid">
                <Score summary={data.search?.answerable} lead="answerable questions got the right unit" />
                <Score summary={data.search?.abstain} lead="unanswerable questions got no answer" />
              </div>
              <Breakdown rows={data.search?.by_trap_kind} />
              <p className="hh-meta">
                Partial answers are a design choice, not only a score. The search prompt tells the AI to pick a unit only when it fully answers the
                question. Asked a two-part question where only one part has an approved answer, it said no answer almost every time, as instructed. The test
                set expected the partial unit. Whether advocates should see a partial answer, flagged as partial, is a decision for the pilot.
              </p>
              <p className="tools-body">
                Answers from another role's knowledge: <strong>{data.search?.leaks ?? 0}</strong>. Role scope is enforced in code before the AI sees any
                unit.
              </p>
              <Misses misses={data.search?.misses} />
            </section>

            <section className="eval-section" aria-labelledby="ev-extract">
              <h2 className="launcher__h2" id="ev-extract">
                2. Extraction
              </h2>
              <p className="tools-body">
                Given a whole document, does the AI find every knowledge unit, copy Legal's wording character for character, and leave purpose, scope and
                revision history alone?
              </p>
              <div className="eval-grid">
                <Score summary={data.extraction?.units_found} lead="expected units found" />
                <Score summary={data.extraction?.verbatim_exact} lead="Legal wording copied exactly" />
                <Score summary={data.extraction?.type_correct} lead="unit types right" />
                <Score summary={data.extraction?.left_alone} lead="context passages left alone" />
              </div>
              <p className="hh-meta">
                Most passages the AI should have left alone are definitions and pointers such as "the fee is on the rate card; this document does not state
                it". The key says leave them alone; the AI often keeps them. They are counted as misses.
              </p>
              <Misses misses={data.extraction?.misses} />
            </section>

            <section className="eval-section" aria-labelledby="ev-dup">
              <h2 className="launcher__h2" id="ev-dup">
                3. Duplicates and conflicts
              </h2>
              <p className="tools-body">
                Given two wordings, does the AI tell a true duplicate from a conflict, and from a lookalike that differs by one word or number?
              </p>
              <div className="eval-grid">
                <Score summary={data.duplicates?.overall} lead="pairs given the exact expected label" />
                <Score summary={data.duplicates?.lookalikes_not_merged} lead="lookalikes never merged as duplicates" />
              </div>
              <Breakdown rows={data.duplicates?.by_kind} />
              <p className="hh-meta">
                The answer key labels a lookalike "different". The model calls it a conflict: the same subject with a different rule, which is how the app
                uses that word. Both numbers are shown; the key was not edited after the run. The second number was added after the first run.
              </p>
              <p className="tools-body">
                Lookalikes wrongly merged, across all runs: <strong>{data.duplicates?.false_merges_across_runs ?? 0}</strong>.
              </p>
              <Misses misses={data.duplicates?.misses} />
            </section>

            <section className="eval-section" aria-labelledby="ev-drift">
              <h2 className="launcher__h2" id="ev-drift">
                4. Source changes
              </h2>
              <p className="tools-body">Given an edit to a source document, does the AI tell a cosmetic change from a material one?</p>
              <Score summary={data.drift?.overall} lead="edits classified correctly" />
              {data.drift ? (
                <p className="hh-meta">
                  For material edits, the proposed fix matched the new source wording in {data.drift.material_fix_matches_new_source.matches} of{" "}
                  {data.drift.material_fix_matches_new_source.total} runs.
                </p>
              ) : null}
              <Misses misses={data.drift?.misses} />
            </section>

            <section className="eval-section" aria-labelledby="ev-gap">
              <h2 className="launcher__h2" id="ev-gap">
                5. Drafts for unanswered questions
              </h2>
              <p className="tools-body">
                Given a question with no approved answer, does the AI draft a unit without inventing a fact, and leave a placeholder where a source is
                needed?
              </p>
              <Score summary={data.gaps?.overall} lead="drafts with no invented facts" />
              <Misses misses={data.gaps?.misses} />
            </section>

            <section className="eval-section" aria-labelledby="ev-limits">
              <h2 className="launcher__h2" id="ev-limits">
                What these numbers do not show
              </h2>
              <ul className="tools-body eval-limits">
                <li>The sets are small, so the intervals are wide. The pilot plan calls for about 150 labelled questions before launch.</li>
                <li>The documents and questions are made up. Real Harbor documents will be longer and messier.</li>
                <li>
                  The answer keys and test sets were written by AI coding agents, not by people, and committed before any run. A set written by Harbor
                  staff would be stronger.
                </li>
                <li>Live search in the app also depends on a first-stage word match, which the search test includes, and on extraction, which it does not.</li>
              </ul>
            </section>
          </>
        ) : null}

        <p>
          <Link className="hh-btn hh-btn--secondary" to="/">
            Back to the prototype home
          </Link>
        </p>
      </div>
    </main>
  );
}
