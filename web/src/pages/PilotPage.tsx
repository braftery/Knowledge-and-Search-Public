import { useId, useState } from "react";
import { Link } from "react-router-dom";

/**
 * The case for a pilot. Every input is a made-up assumption the presenter can change on screen, and the formula is shown
 * so anyone can check the arithmetic. The one external figure is cited.
 */

type Inputs = {
  calls: number;
  minutesSaved: number;
  advocateRate: number;
  findings: number;
  findingCost: number;
  changes: number;
  legalHoursSaved: number;
  legalRate: number;
  runCost: number;
};

const DEFAULTS: Inputs = {
  calls: 40000,
  minutesSaved: 0.5,
  advocateRate: 40,
  findings: 6,
  findingCost: 2500,
  changes: 4,
  legalHoursSaved: 6,
  legalRate: 150,
  runCost: 12000,
};

const FIELDS: Array<{ key: keyof Inputs; label: string; hint: string; step: number; prefix?: string }> = [
  { key: "calls", label: "Drug price calls per month", hint: "Pharmacy queue, pilot scope.", step: 1000 },
  { key: "minutesSaved", label: "Minutes saved per call", hint: "Time no longer spent searching three documents.", step: 0.1 },
  { key: "advocateRate", label: "Advocate cost per hour", hint: "Loaded cost.", step: 1, prefix: "$" },
  { key: "findings", label: "QA findings on price wording per month", hint: "Calls where the disclaimer was missing or wrong.", step: 1 },
  { key: "findingCost", label: "Cost to remediate one finding", hint: "Review, coaching, member follow-up.", step: 100, prefix: "$" },
  { key: "changes", label: "Legal wording changes per month", hint: "Each one edited once instead of in every copy.", step: 1 },
  { key: "legalHoursSaved", label: "Hours saved per change", hint: "Finding and checking every copy by hand.", step: 1 },
  { key: "legalRate", label: "Legal and Compliance cost per hour", hint: "Loaded cost.", step: 5, prefix: "$" },
  { key: "runCost", label: "Platform run cost per month", hint: "Hosting, model calls, Knowledge Ops and Legal review time.", step: 500, prefix: "$" },
];

const money = (value: number) => `${value < 0 ? "-" : ""}$${Math.round(Math.abs(value)).toLocaleString("en-US")}`;

export function PilotPage() {
  const [inputs, setInputs] = useState<Inputs>(DEFAULTS);
  const id = useId();
  const time = (inputs.calls * inputs.minutesSaved * inputs.advocateRate) / 60;
  const quality = inputs.findings * inputs.findingCost;
  const legal = inputs.changes * inputs.legalHoursSaved * inputs.legalRate;
  const net = time + quality + legal - inputs.runCost;

  return (
    <main id="main-content" className="hh launcher pilot" data-theme="tools">
      <header className="launcher__top">
        <Link className="launcher__brand" to="/">
          Harbor Health <span>Single Source</span>
        </Link>
        <span className="hh-presenter__pill launcher__pill">Illustrative data</span>
      </header>
      <div className="launcher__body pilot__body">
        <section>
          <p className="tools-overline">The case for a pilot</p>
          <h1 className="launcher__title">Start with one queue, measure it, and decide with the numbers.</h1>
          <p className="launcher__lead">
            Every input below is a made-up assumption for a fictional plan. Change any of them; the arithmetic is shown, so the result is only as good as the
            inputs. The pilot exists to replace these guesses with measured baselines.
          </p>
        </section>

        <section className="pilot__grid" aria-labelledby={`${id}-model`}>
          <div>
            <h2 className="launcher__h2" id={`${id}-model`}>
              Monthly value, illustrative
            </h2>
            <form className="pilot__inputs" onSubmit={(event) => event.preventDefault()}>
              {FIELDS.map((field) => (
                <div key={field.key} className="pilot__field">
                  <label className="hh-label" htmlFor={`${id}-${field.key}`}>
                    {field.label}
                  </label>
                  <div className="pilot__input">
                    <span className="pilot__prefix" aria-hidden="true">
                      {field.prefix ?? ""}
                    </span>
                    <input
                      id={`${id}-${field.key}`}
                      className="hh-input"
                      type="number"
                      inputMode="decimal"
                      min={0}
                      step={field.step}
                      value={inputs[field.key]}
                      aria-describedby={`${id}-${field.key}-hint`}
                      onChange={(event) => setInputs((current) => ({ ...current, [field.key]: Math.max(0, Number(event.target.value) || 0) }))}
                    />
                  </div>
                  <p className="hh-meta" id={`${id}-${field.key}-hint`}>
                    {field.hint}
                  </p>
                </div>
              ))}
              <div>
                <button className="hh-btn hh-btn--tertiary" type="button" onClick={() => setInputs(DEFAULTS)}>
                  Restore the starting assumptions
                </button>
              </div>
            </form>
          </div>
          <div className="pilot__result" aria-live="polite">
            <dl className="preview-list">
              <div>
                <dt>Advocate time</dt>
                <dd>
                  {money(time)} <span className="hh-meta">calls × minutes saved × cost per hour ÷ 60</span>
                </dd>
              </div>
              <div>
                <dt>Fewer wording findings</dt>
                <dd>
                  {money(quality)} <span className="hh-meta">findings avoided × cost per finding</span>
                </dd>
              </div>
              <div>
                <dt>Legal change effort</dt>
                <dd>
                  {money(legal)} <span className="hh-meta">changes × hours saved × cost per hour</span>
                </dd>
              </div>
              <div>
                <dt>Run cost</dt>
                <dd>-{money(inputs.runCost)}</dd>
              </div>
              <div className="pilot__net">
                <dt>Net per month</dt>
                <dd>{money(net)}</dd>
              </div>
            </dl>
            <p className="hh-meta">Illustrative. Assumes every finding on price wording is avoided, which the pilot must test.</p>
            <p className="tools-body">
              External evidence, from a different setting: a staggered rollout of an AI assistant with links to internal knowledge, across 5,179 support agents,
              found 14% more issues resolved per hour and chats 3.8 minutes shorter. That study measured no compliance or answer accuracy, so it supports the
              time line above and says nothing about the wording line.
            </p>
          </div>
        </section>

        <section aria-labelledby={`${id}-pilot`}>
          <h2 className="launcher__h2" id={`${id}-pilot`}>
            The pilot
          </h2>
          <dl className="preview-list pilot__facts">
            <div>
              <dt>Scope</dt>
              <dd>Pharmacy queue, drug price calls only, one knowledge base. Member channels read the same units but stay off until the gates pass.</dd>
            </div>
            <div>
              <dt>Who</dt>
              <dd>About 40 advocates in one site, one Legal approver, two Knowledge Ops authors (illustrative).</dd>
            </div>
            <div>
              <dt>How long</dt>
              <dd>Two weeks to collect baselines, then eight weeks live.</dd>
            </div>
            <div>
              <dt>Baselines to collect first</dt>
              <dd>
                Handle time on price calls; QA audit rate of missing or wrong disclaimers; time from a Legal change to every copy updated; Legal hours per change;
                advocate search success.
              </dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby={`${id}-gates`}>
          <h2 className="launcher__h2" id={`${id}-gates`}>
            Gates
          </h2>
          <div className="close-gates__cols">
            <div className="close-gate">
              <p className="close-gate__title">Before launch</p>
              <ul>
                <li>100% verbatim match on Legal wording</li>
                <li>Zero cross-role leaks</li>
                <li>About 150 labeled questions, with the lower end of the 95% interval above the agreed bar</li>
                <li>Compliance sign-off</li>
              </ul>
            </div>
            <div className="close-gate">
              <p className="close-gate__title">Continue at week 8 if</p>
              <ul>
                <li>QA findings on price wording fall against baseline</li>
                <li>Handle time on price calls does not rise</li>
                <li>Most pilot advocates use search every week</li>
                <li>Legal changes reach every copy the same day</li>
              </ul>
            </div>
            <div className="close-gate">
              <p className="close-gate__title">Stop at once if</p>
              <ul>
                <li>Unapproved wording reaches a member</li>
                <li>A cross-role leak</li>
                <li>Wrong no-answers stay above an agreed share of questions</li>
              </ul>
            </div>
          </div>
        </section>

        <section aria-labelledby={`${id}-connect`}>
          <h2 className="launcher__h2" id={`${id}-connect`}>
            How it connects
          </h2>
          <dl className="preview-list pilot__facts">
            <div>
              <dt>Advocate desktop</dt>
              <dd>A panel in the existing contact center desktop calls the answers API with the advocate's role and the call reason. No new screen to learn.</dd>
            </div>
            <div>
              <dt>Source documents</dt>
              <dd>Scripts and policies stay where authors keep them today. Extraction reads them; a change to a source raises a review and never edits live wording.</dd>
            </div>
            <div>
              <dt>Pricing and benefits</dt>
              <dd>Numbers come from the existing pricing and benefits systems of record. The platform adds the approved wording and withholds a number when that wording is missing.</dd>
            </div>
            <div>
              <dt>Member chat, website and phone line</dt>
              <dd>Each channel fetches units by reference and subscribes to change events, so a Legal revision reaches every channel the same day.</dd>
            </div>
            <div>
              <dt>Build or buy</dt>
              <dd>
                Buy commodity parts: search infrastructure, the model, the contact center desktop. Build the thin layer that no vendor source we read documents: approved
                units with mandatory verbatim, finding every copy, and proving which version was live on a date. Re-test this with vendors (for example, knowledge
                platforms that market a governed layer for health plans) before committing.
              </dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby={`${id}-phases`}>
          <h2 className="launcher__h2" id={`${id}-phases`}>
            After the pilot
          </h2>
          <ol className="pilot__phases">
            <li>
              <strong>All pharmacy calls,</strong> then member chat and the website for price questions, each behind the same gates.
            </li>
            <li>
              <strong>Benefits knowledge base</strong> for the Insurance queue, with its own golden set.
            </li>
            <li>
              <strong>The phone line,</strong> once caller authentication and spoken wording are approved.
            </li>
            <li>
              <strong>Reuse the platform</strong> for another AI use case, such as the provider directory, using the same unit, approval and channel API.
            </li>
          </ol>
          <p className="hh-meta">Each phase starts only after the previous one passes its week-8 gate.</p>
        </section>

        <p>
          <Link className="hh-btn hh-btn--secondary" to="/">
            Back to the prototype home
          </Link>
        </p>
      </div>
    </main>
  );
}
