import { Lock } from "lucide-react";
import type { MemberRecord } from "@/api/types";
import { citeUnit } from "@/components/quote-card";

type Plan = Record<string, { display?: string } | string | unknown>;

function show(plan: Plan | undefined, key: string) {
  const value = plan?.[key];
  if (typeof value === "string") return value;
  if (value && typeof value === "object" && "display" in value) return String((value as { display?: string }).display || "");
  return "";
}

/** Shown in place of coverage details when the caller is not verified, citing the approved rule. */
export function Withheld({ record }: { record: MemberRecord }) {
  const rule = record.units?.[0];
  return (
    <div className="desk-withheld">
      <Lock aria-hidden="true" />
      <div>
        <p className="desk-withheld__title">Coverage details are hidden until the caller is verified.</p>
        <p>{record.withheld_reason}</p>
        {rule ? <p className="hh-meta">{citeUnit(rule)}</p> : null}
      </div>
    </div>
  );
}

export function ProfileTab({ record }: { record: MemberRecord }) {
  const plan = record.plan as Plan;
  const rows: Array<[string, string]> = [
    ["Plan", record.member.plan],
    ["Coverage stage", record.coverage_stage],
    ["Primary care visit", show(plan, "primary_care")],
    ["Specialist visit", show(plan, "specialist")],
    ["Urgent care", show(plan, "urgent_care")],
    ["Emergency room", show(plan, "emergency")],
    ["Out-of-pocket maximum", record.oop ? `${record.oop.spent_display} of ${record.oop.limit_display} used` : ""],
    ["Part D deductible", record.drug_deductible ? (record.drug_deductible.met ? "Met" : "Not met") : ""],
  ];
  const hide = record.verified === false;
  return (
    <article className="desk-card desk-card--wide">
      <h2 className="desk-card__title">Member profile</h2>
      {hide ? <Withheld record={record} /> : null}
      <dl className="desk-profile">
        {rows
          .filter(([, value]) => value)
          .filter(([label]) => !hide || label === "Plan")
          .map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
      </dl>
      <p className="hh-meta">Illustrative plan data for a fictional member.</p>
    </article>
  );
}

export function ClaimsTab({ record }: { record: MemberRecord }) {
  if (record.verified === false || !record.claims) {
    return (
      <article className="desk-card desk-card--wide">
        <h2 className="desk-card__title">Claims</h2>
        <Withheld record={record} />
      </article>
    );
  }
  return (
    <article className="desk-card desk-card--wide">
      <h2 className="desk-card__title">Claims</h2>
      <table className="desk-table">
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Provider</th>
            <th scope="col">Billed</th>
            <th scope="col">Plan paid</th>
            <th scope="col">Member paid</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {record.claims.map((claim, index) => (
            <tr key={index}>
              <td>{claim.date}</td>
              <td>{claim.provider_type}</td>
              <td>{claim.amount_billed_display}</td>
              <td>{claim.plan_paid_display}</td>
              <td>{claim.member_paid_display}</td>
              <td>{claim.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hh-meta">Illustrative claims.</p>
    </article>
  );
}

export function PrescriptionsTab({ record }: { record: MemberRecord }) {
  const hide = record.verified === false;
  return (
    <article className="desk-card desk-card--wide">
      <h2 className="desk-card__title">Prescriptions</h2>
      {hide ? <Withheld record={record} /> : null}
      {hide ? <p className="hh-meta">The drug list stays hidden until the caller is verified, because it shows what the plan covers.</p> : null}
      <table className="desk-table" hidden={hide}>
        <thead>
          <tr>
            <th scope="col">Drug</th>
            {hide ? null : <th scope="col">Tier</th>}
            {hide ? null : <th scope="col">30-day, preferred pharmacy</th>}
          </tr>
        </thead>
        <tbody>
          {record.drugs.map((drug) => {
            const price = record.prices?.find((item) => item.drug_id === drug.drug_id);
            return (
              <tr key={drug.drug_id}>
                <td>
                  {drug.name} {drug.strength}
                  {drug.specialty ? <span className="hh-meta"> · Specialty</span> : null}
                </td>
                {hide ? null : <td>{price?.tier_label || (drug.tier ? `Tier ${drug.tier}` : "")}</td>}
                {hide ? null : <td>{price?.available ? price.price_display : price?.note || "Not available"}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
      {hide ? null : (
        <p className="hh-meta">
          Read the pricing disclaimer word for word before you quote any price. Illustrative prices.
        </p>
      )}
    </article>
  );
}

/** Plan figures for this call, shown in the knowledge panel next to the approved wording that must come first. */
export function PlanFacts({ record, kind }: { record: MemberRecord; kind: "drugs" | "costs" }) {
  if (record.verified === false) return <Withheld record={record} />;
  const plan = record.plan as Plan;
  const first = record.member.name.split(" ")[0];
  return (
    <section className="desk-facts" aria-labelledby="desk-facts-h">
      <h2 id="desk-facts-h" className="tools-label">
        From {first}&apos;s plan
      </h2>
      {kind === "drugs" ? (
        <dl className="desk-facts__list">
          {record.drugs.map((drug) => {
            const price = record.prices?.find((item) => item.drug_id === drug.drug_id);
            return (
              <div key={drug.drug_id}>
                <dt>
                  {drug.name} {drug.strength}
                  <span className="hh-meta"> · {price?.tier_label || ""}</span>
                </dt>
                <dd>{price?.available ? price.price_display : price?.note || "Not available"}</dd>
              </div>
            );
          })}
        </dl>
      ) : (
        <dl className="desk-facts__list">
          {[
            ["Specialist visit, in network", show(plan, "specialist")],
            ["Primary care visit", show(plan, "primary_care")],
            ["Out-of-pocket maximum", record.oop ? `${record.oop.spent_display} of ${record.oop.limit_display} used` : ""],
          ]
            .filter(([, value]) => value)
            .map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
        </dl>
      )}
      <p className="hh-meta">
        {kind === "drugs" ? "30-day supply, preferred retail pharmacy. " : ""}Read the approved disclaimer word for word before you give any amount. Illustrative.
      </p>
    </section>
  );
}
