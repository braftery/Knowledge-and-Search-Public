import { useEffect, useRef, useState } from "react";
import { approvedUnit, drugPrice, memberProfile, visitCost } from "@/api/client";
import { Glossary } from "@/pages/member/glossary";
import type { DrugPrice, PlanDrug, UnitRef, VisitCost } from "@/api/types";
import { useQuery } from "@/api/use-query";
import { QuoteCard, memberCite } from "@/components/quote-card";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { VISIT_LABELS, priceHeadline, visitHeadline } from "@/lib/plan-labels";

const PHARMACIES = [
  { id: "preferred_retail", label: "Preferred retail pharmacy" },
  { id: "standard_retail", label: "Standard retail pharmacy" },
  { id: "mail_order", label: "Mail order" },
  { id: "specialty", label: "Harbor Specialty Pharmacy" },
];

/** Drug price estimate for the signed-in member: a number from plan data, shown with the approved disclaimer. */
export function DrugEstimator() {
  const profile = useQuery("member-profile", () => memberProfile());
  const [drugId, setDrugId] = useState("");
  const [pharmacy, setPharmacy] = useState("preferred_retail");
  const [days, setDays] = useState(30);
  const [result, setResult] = useState<DrugPrice | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const resultRef = useRef<HTMLHeadingElement>(null);
  const mailHint = useQuery("site-mail", () => approvedUnit("U-SITE-MAIL-001"));
  useEffect(() => {
    if (result) resultRef.current?.focus();
  }, [result]);

  if (profile.loading && !profile.data) return <Skeleton width="100%" height="160px" label="Loading your drugs" />;
  if (profile.error || !profile.data) return <ServiceError message={profile.error || "Your drug list did not load."} onRetry={profile.reload} />;
  const drugs = profile.data.drugs;
  const chosen = drugId || drugs[0]?.drug_id || "";
  const chosenDrug = drugs.find((drug) => drug.drug_id === chosen);
  const pharmacies = PHARMACIES.filter((item) => item.id !== "specialty" || chosenDrug?.specialty);
  const activePharmacy = pharmacies.some((item) => item.id === pharmacy) ? pharmacy : "preferred_retail";
  const deductible = profile.data.plan.part_d_deductible as { display?: string; note?: string } | undefined;

  async function estimate(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await drugPrice(chosen, activePharmacy, activePharmacy === "mail_order" ? 90 : days));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "The estimate did not load. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="estimator">
      <form className="estimator__form" onSubmit={estimate}>
        <div>
          <label className="hh-label" htmlFor="est-drug">
            Drug
          </label>
          <select
            id="est-drug"
            className="hh-input"
            value={chosen}
            onChange={(event) => {
              setDrugId(event.target.value);
              setResult(null);
            }}
          >
            {drugs.map((drug) => (
              <option key={drug.drug_id} value={drug.drug_id}>
                {drug.name} {drug.strength}
              </option>
            ))}
          </select>
          <p className="member-meta">From your current prescriptions.</p>
        </div>
        <div>
          <label className="hh-label" htmlFor="est-pharmacy">
            Pharmacy
          </label>
          <select
            id="est-pharmacy"
            className="hh-input"
            value={activePharmacy}
            aria-describedby={activePharmacy === "mail_order" ? "est-pharmacy-hint" : undefined}
            onChange={(event) => {
              setPharmacy(event.target.value);
              setResult(null);
            }}
          >
            {pharmacies.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
          {activePharmacy === "mail_order" ? (
            <p className="member-meta" id="est-pharmacy-hint">
              {mailHint.data?.text || "Mail order fills 90-day supplies only."}
            </p>
          ) : null}
        </div>
        <fieldset className="estimator__days">
          <legend className="hh-label">Supply</legend>
          {[30, 90].map((value) => (
            <label key={value}>
              <input
                type="radio"
                name="est-days"
                checked={(activePharmacy === "mail_order" ? 90 : days) === value}
                disabled={activePharmacy === "mail_order" && value === 30}
                onChange={() => {
                  setDays(value);
                  setResult(null);
                }}
              />{" "}
              {value}-day
            </label>
          ))}
        </fieldset>
        <div>
          <button className="hh-btn hh-btn--primary" type="submit" disabled={busy}>
            {busy ? "Estimating…" : "Estimate my price"}
          </button>
        </div>
      </form>
      {error ? <ServiceError message={error} /> : null}
      {result ? (
        <div>
          <h2 className="member-h3 estimator__result-h" tabIndex={-1} ref={resultRef}>
            Your estimate for {result.drug?.name || chosenDrug?.name || "this drug"}
          </h2>
          <QuoteCard
            amount={result.available ? result.price_display : undefined}
            headline={priceHeadline(result)}
            details={[result.available ? "Covered on your plan" : "", result.tier_label, result.coverage_stage]}
            note={result.note}
            withheld={result.withheld_reason || (!result.available && !result.note ? "That option is not available for this drug." : "")}
            units={result.units}
          />
        </div>
      ) : null}
      {deductible?.display ? (
        <p className="member-meta">
          Your drug deductible is {deductible.display}
          {profile.data.drug_deductible ? (profile.data.drug_deductible.met ? ", and you have met it this year" : ", and you have not met it yet this year") : ""}.{" "}
          {deductible.note ? `${deductible.note.replace(/\.$/, "")}.` : ""} Illustrative.
        </p>
      ) : null}
      <CompareDrugs drugs={drugs} />
      <Glossary keys={["tier", "coverage_stage", "deductible", "preferred_pharmacy", "mail_order"]} />
    </div>
  );
}

type CompareRow = { drug: PlanDrug; retail: DrugPrice | null; mail: DrugPrice | null };

const money = (value: number) => `$${value.toFixed(2)}`;
const perMonth = (price: DrugPrice | null) => (price?.available && price.price != null ? price.price / (price.days / 30) : null);

/** Every drug on the member's list at once: 30-day preferred retail against 90-day mail order, per month. */
function CompareDrugs({ drugs }: { drugs: PlanDrug[] }) {
  const [rows, setRows] = useState<CompareRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const headRef = useRef<HTMLHeadingElement>(null);

  async function compare() {
    setBusy(true);
    setError("");
    try {
      const next = await Promise.all(
        drugs
          .filter((drug) => !drug.specialty)
          .map(async (drug) => {
            const [retail, mail] = await Promise.all([
              drugPrice(drug.drug_id, "preferred_retail", 30).catch(() => null),
              drugPrice(drug.drug_id, "mail_order", 90).catch(() => null),
            ]);
            return { drug, retail, mail };
          }),
      );
      setRows(next);
      window.setTimeout(() => headRef.current?.focus(), 0);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "The comparison did not load. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const totals = (rows ?? []).reduce(
    (sum, row) => {
      const retail = perMonth(row.retail);
      const mail = perMonth(row.mail);
      return retail != null && mail != null ? { retail: sum.retail + retail, mail: sum.mail + mail, count: sum.count + 1 } : sum;
    },
    { retail: 0, mail: 0, count: 0 },
  );
  // Why a price is missing, said once: for example, mail-order prices wait while Legal resolves the mail-order rule.
  const withheldNotes = [
    ...new Set(
      (rows ?? []).flatMap((row) => [row.retail, row.mail]).filter((price) => price && !price.available).map((price) => price?.withheld_reason || price?.note || ""),
    ),
  ].filter(Boolean);
  const units: UnitRef[] = [];
  for (const row of rows ?? []) {
    for (const unit of [...(row.retail?.units ?? []), ...(row.mail?.units ?? [])]) {
      if (!units.some((item) => item.unit_id === unit.unit_id)) units.push(unit);
    }
  }

  return (
    <section className="estimator-compare" aria-labelledby="compare-h">
      <h2 className="member-h3" id="compare-h" tabIndex={-1} ref={headRef}>
        Compare all my drugs
      </h2>
      <p className="member-meta">What each drug costs per month at a preferred retail pharmacy and by mail order.</p>
      {!rows ? (
        <div>
          <button className="hh-btn hh-btn--secondary" type="button" onClick={compare} disabled={busy}>
            {busy ? "Comparing…" : "Compare retail and mail order"}
          </button>
        </div>
      ) : null}
      {error ? <ServiceError message={error} onRetry={compare} /> : null}
      {rows ? (
        <>
          <div className="compare-scroll">
            <table className="compare-table">
              <caption className="sr-only">Monthly cost by pharmacy, illustrative</caption>
              <thead>
                <tr>
                  <th scope="col">Drug</th>
                  <th scope="col">Preferred retail, 30-day</th>
                  <th scope="col">Mail order, per month</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const retail = perMonth(row.retail);
                  const mail = perMonth(row.mail);
                  return (
                    <tr key={row.drug.drug_id}>
                      <th scope="row">
                        {row.drug.name} {row.drug.strength}
                      </th>
                      <td>{retail != null ? money(retail) : "Not available"}</td>
                      <td>
                        {mail != null ? money(mail) : "Not available"}
                        {mail != null && row.mail ? <span className="compare-sub">{row.mail.price_display} for 90 days</span> : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              {totals.count ? (
                <tfoot>
                  <tr>
                    <th scope="row">Total per month</th>
                    <td>{money(totals.retail)}</td>
                    <td>{money(totals.mail)}</td>
                  </tr>
                </tfoot>
              ) : null}
            </table>
          </div>
          {totals.count && totals.retail - totals.mail >= 0.01 ? (
            <p className="compare-savings">
              Mail order could save about {money(totals.retail - totals.mail)} a month, or {money((totals.retail - totals.mail) * 12)} a year.
            </p>
          ) : null}
          {withheldNotes.map((note) => (
            <p key={note} className="member-meta">
              {note}
            </p>
          ))}
          {drugs.some((drug) => drug.specialty) ? <p className="member-meta">Specialty drugs are filled by Harbor Specialty Pharmacy and are not compared here.</p> : null}
          <div className="quote">
            {units.map((unit) => (
              <div key={unit.unit_id} className="quote__unit">
                <p className="quote__unit-text">{unit.text}</p>
                <p className="quote__cite">{memberCite(unit)}</p>
              </div>
            ))}
            <p className="quote__illustrative">Illustrative prices from made-up plan data.</p>
          </div>
        </>
      ) : null}
    </section>
  );
}

/** Visit cost estimate: plan cost share with the approved cost disclaimer, and the referral rule for specialists. */
export function VisitEstimator() {
  const [visit, setVisit] = useState("primary_care");
  const [network, setNetwork] = useState("in");
  const [result, setResult] = useState<VisitCost | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function estimate(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(await visitCost(visit, network));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "The estimate did not load. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="estimator">
      <form className="estimator__form" onSubmit={estimate}>
        <div>
          <label className="hh-label" htmlFor="est-visit">
            Kind of visit
          </label>
          <select
            id="est-visit"
            className="hh-input"
            value={visit}
            onChange={(event) => {
              setVisit(event.target.value);
              setResult(null);
            }}
          >
            {Object.entries(VISIT_LABELS).map(([id, label]) => (
              <option key={id} value={id}>
                {id === "specialist" ? `${label} (for example, a cardiologist)` : label}
              </option>
            ))}
          </select>
        </div>
        <fieldset className="estimator__days">
          <legend className="hh-label">Is the doctor in your network?</legend>
          {[
            ["in", "In network"],
            ["out", "Out of network"],
          ].map(([value, label]) => (
            <label key={value}>
              <input
                type="radio"
                name="est-network"
                checked={network === value}
                onChange={() => {
                  setNetwork(value);
                  setResult(null);
                }}
              />{" "}
              {label}
            </label>
          ))}
        </fieldset>
        <div>
          <button className="hh-btn hh-btn--primary" type="submit" disabled={busy}>
            {busy ? "Estimating…" : "Estimate my cost"}
          </button>
        </div>
      </form>
      {error ? <ServiceError message={error} /> : null}
      {result ? (
        <div aria-live="polite">
          <QuoteCard
            amount={result.available ? result.cost_display : undefined}
            headline={visitHeadline(result)}
            note={result.note}
            withheld={result.withheld_reason || (!result.available && !result.note ? "This visit is not covered out of network on your plan." : "")}
            units={result.units}
          />
        </div>
      ) : null}
    </div>
  );
}
