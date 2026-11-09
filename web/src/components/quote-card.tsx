import type { UnitRef } from "@/api/types";

/**
 * A number from plan data with the approved wording that must travel with it. The number is never shown
 * without its disclaimer; when the disclaimer is not approved, the API withholds the number and this shows why.
 */
export function QuoteCard({
  amount,
  headline,
  details,
  note,
  withheld,
  units,
  compact = false,
}: {
  amount?: string;
  headline: string;
  details?: string[];
  note?: string;
  withheld?: string;
  units: UnitRef[];
  compact?: boolean;
}) {
  return (
    <div className={compact ? "quote quote--compact" : "quote"}>
      {withheld ? (
        <p className="quote__withheld">{withheld}</p>
      ) : (
        <>
          {amount ? <p className="quote__amount">{amount}</p> : null}
          <p className="quote__headline">{headline}</p>
          {details?.filter(Boolean).length ? <p className="quote__details">{details.filter(Boolean).join(" · ")}</p> : null}
        </>
      )}
      {note ? <p className="quote__note">{note}</p> : null}
      {(amount ? units : units.filter((unit) => !/disclaimer/i.test(unit.title))).map((unit) => (
        <div key={unit.unit_id} className="quote__unit">
          <p className="quote__unit-text">{unit.text}</p>
          <p className="quote__cite">{memberCite(unit)}</p>
        </div>
      ))}
      {amount ? <p className="quote__illustrative">Illustrative price from made-up plan data.</p> : <p className="quote__illustrative">Illustrative, made-up plan data.</p>}
    </div>
  );
}

/** Members read "Harbor Health plan rules: Pricing estimate disclaimer". The version number is for staff, so it stays in citeUnit. */
export function memberCite(unit: UnitRef) {
  const title = (unit.title || "").replace(/\s*\((Legal|Legal verbatim)\)\s*$/, "");
  return title ? `Harbor Health plan rules: ${title}` : unit.citation;
}

/** "Source: Harbor Health, HMO specialist visits require a referral, version 1", from the unit's own title. */
export function citeUnit(unit: UnitRef) {
  const title = (unit.title || "").replace(/\s*\((Legal|Legal verbatim)\)\s*$/, "");
  return title ? `Source: Harbor Health, ${title}, version ${unit.version}` : unit.citation;
}
