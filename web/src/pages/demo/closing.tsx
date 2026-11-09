import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { getChannels, getDemoState, getDrift, getGaps, getQuality } from "@/api/guided";
import { SHORT_PATH } from "@/pages/demo/script";
import { useQuery } from "@/api/use-query";
import { DecisionMarker } from "@/components/decision-marker";
import { Skeleton } from "@/components/skeleton";
import { useGuided } from "@/pages/demo/guided-context";

type Moment = { step: number; what: string; who: "ai" | "human" | "system"; role?: string; detail: string };

const MOMENTS: Moment[] = [
  { step: 1, what: "Extracted from the Rx education script", who: "ai", detail: "Found the span, typed it as verbatim, suggested tags and audience." },
  { step: 1, what: "Tags and audience confirmed", who: "human", role: "Knowledge Ops author", detail: "Corrected the audience from member to advocate." },
  { step: 2, what: "Copies and conflicts found", who: "ai", detail: "Labeled each pair and explained the difference." },
  { step: 2, what: "The Legal-signed wording kept", who: "human", role: "Knowledge Ops author", detail: "Conflicts escalated to Legal; both sides stay blocked." },
  { step: 3, what: "Approved once, as a unit", who: "human", role: "Legal approver", detail: "Checked the verbatim against its source and saw who would see it." },
  { step: 4, what: "Returned to the right role only", who: "system", detail: "Scoped to the role's knowledge bases, cited, or a clear no-answer." },
  { step: 5, what: "Revised once, live everywhere", who: "human", role: "Legal approver", detail: "Advocate desktop, member chat and phone line changed together." },
  { step: 6, what: "A missing answer became a draft", who: "ai", detail: "Clustered unanswered questions and drafted a unit with placeholders." },
  { step: 7, what: "A source change was caught", who: "ai", detail: "The approved version stayed live while Legal reviews the fix." },
  { step: 8, what: "Measured before trusted", who: "system", detail: "Scored against a golden set, with held-out questions kept visible." },
];

const TILE_LABELS: Record<string, string> = {
  hit_at_1: "Right answer first",
  correct_abstain: "Correct no-answers",
  over_abstain: "Wrong no-answers",
  leaks: "Cross-role leaks",
  dedup_precision: "Copy detection precision",
  dedup_recall: "Copy detection recall",
};

const COLUMNS = [
  { title: "AI does", items: ["Extract and classify units", "Find copies and conflicts", "Scope, rank and cite answers", "Decline when evidence is thin", "Cluster unanswered questions", "Flag source changes"] },
  { title: "AI proposes, a person confirms", items: ["Tags, audience and domain", "Which copy to keep", "Drafts that close a gap", "Fixes after a source change"] },
  { title: "Only a person", items: ["Approve legal, policy and cost wording", "Resolve a conflict of authority", "Publish a revision", "Grant access to a knowledge base"] },
];

export function ClosingView({ path }: { path: "short" | "full" }) {
  const guided = useGuided();
  const channels = useQuery(`close-ch:${guided.tick}`, () => getChannels());
  const quality = useQuery(`close-q:${guided.tick}`, () => getQuality());
  const gaps = useQuery(`close-g:${guided.tick}`, () => getGaps());
  const drift = useQuery(`close-d:${guided.tick}`, () => getDrift());
  const demo = useQuery(`close-s:${guided.tick}`, () => getDemoState());
  const doneSteps = new Set((demo.data?.steps ?? []).filter((item) => item.done).map((item) => item.number));
  // An approval that reached the live channels counts as step 3 run, however it was made.
  const done = (step: number) =>
    !demo.data || doneSteps.has(step) || (step === 3 && Boolean(channels.data?.live)) || (step === 8 && Boolean(quality.data?.scored));
  const shown = path === "short" ? new Set<number>(SHORT_PATH) : null;
  const moments = MOMENTS.filter((moment) => !shown || shown.has(moment.step));
  const skipped = moments.filter((moment) => !done(moment.step)).length;
  const version = channels.data?.live?.version ?? 1;
  const approved = Boolean(channels.data?.live);
  const sentGaps = (gaps.data?.gaps ?? []).filter((gap) => gap.status !== "proposed").length;
  const tiles = quality.data?.scored ? quality.data.tiles ?? [] : [];

  return (
    <article className="close" aria-labelledby="close-h">
      <header className="close-head">
        <p className="tools-overline">What changed</p>
        <h2 id="close-h" className="close-title">
          From three wordings nobody could vouch for to one approved answer, everywhere.
        </h2>
      </header>

      <section className="close-compare" aria-label="Before and after">
        <div className="close-col close-col--before">
          <h3 className="tools-title-sm">Before</h3>
          <ul>
            <li>Three documents, three wordings of the same disclaimer.</li>
            <li>No one could say which wording Legal approved, or whether it was current.</li>
            <li>A change meant finding and editing every copy, in every channel, by hand.</li>
          </ul>
        </div>
        <ArrowRight className="close-arrow" aria-hidden="true" />
        <div className="close-col close-col--after">
          <h3 className="tools-title-sm">After</h3>
          <ul>
            <li>
              {approved
                ? `One approved unit, now at version ${version}, cited the same way in every channel.`
                : "One unit per fact, cited the same way in every channel once Legal approves it."}
            </li>
            <li>Each role sees only its own knowledge, and gets a clear no-answer instead of a guess.</li>
            <li>
              Legal changes the wording once.{" "}
              {[
                version > 1 ? `Every channel updated together, and version ${version - 1} stays in the history.` : "When Legal publishes a new version, every channel updates together.",
                done(6) && sentGaps ? `Unanswered questions became drafts (${sentGaps} sent to an author).` : "",
                done(7) && drift.data?.sent ? "A source change went to Legal while the approved version stayed live." : "",
              ]
                .filter(Boolean)
                .join(" ")}
            </li>
          </ul>
        </div>
      </section>

      <section className="close-trace" aria-labelledby="trace-h">
        <h3 id="trace-h" className="tools-title-sm">
          One disclaimer, traced through the system
        </h3>
        {skipped ? (
          <p className="hh-meta">
            {skipped} {skipped === 1 ? "moment was" : "moments were"} not run in this demo and {skipped === 1 ? "is" : "are"} shown in grey.
          </p>
        ) : null}
        <ol className="close-steps">
          {moments.map((moment, index) => (
            <li
              key={`${moment.step}-${index}`}
              className={`close-step close-step--${moment.who}${done(moment.step) ? "" : " close-step--skipped"}`}
            >
              <span className="close-step__n">Step {moment.step + 1}</span>
              <span className="close-step__body">
                <strong>{moment.what}</strong>
                <span className="hh-meta">{moment.detail}</span>
              </span>
              {!done(moment.step) ? <span className="hh-meta">Not run in this demo</span> : null}
              {done(moment.step) && moment.who === "ai" ? <DecisionMarker kind="ai" /> : null}
              {done(moment.step) && moment.who === "human" ? <DecisionMarker kind="human" role={moment.role} /> : null}
              {done(moment.step) && moment.who === "system" ? <span className="hh-mark hh-mark--ai close-auto">Automatic, no new wording</span> : null}
            </li>
          ))}
        </ol>
      </section>

      <section className="close-gates" aria-labelledby="gates-h">
        <h3 id="gates-h" className="tools-title-sm">
          Where people stay in the loop
        </h3>
        <div className="close-gates__cols">
          {COLUMNS.map((column) => (
            <div key={column.title} className="close-gate">
              <p className="close-gate__title">{column.title}</p>
              <ul>
                {column.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="tools-body close-failsafe">Every gate fails safe: until a person acts, nothing new goes live and the approved version stays live.</p>
        <p className="tools-body">
          <Link to="/pilot">See the pilot plan: scope, gates, phases, and an illustrative value model</Link>
        </p>
      </section>

      {path === "full" ? (
        <section className="close-scores" aria-label="Retrieval quality">
          {quality.loading && !quality.data ? <Skeleton width="100%" height="64px" label="Loading scores" /> : null}
          {tiles.length ? (
            <ul className="close-tiles">
              {tiles.map((tile) => (
                <li key={tile.key}>
                  <strong>{tile.display}</strong>
                  <span>{TILE_LABELS[tile.key] ?? tile.label}</span>
                </li>
              ))}
              {quality.data?.held_out_total ? (
                <li>
                  <strong>
                    {quality.data.held_out_pass} of {quality.data.held_out_total}
                  </strong>
                  <span>Held-out questions</span>
                </li>
              ) : null}
            </ul>
          ) : (
            <p className="hh-meta">Score the golden set in the last step to show the numbers here.</p>
          )}
          <p className="hh-meta">Illustrative scores on made-up data. Proposed launch gate: 100% verbatim match, zero cross-role leaks, and Compliance sign-off.</p>
        </section>
      ) : null}
    </article>
  );
}
