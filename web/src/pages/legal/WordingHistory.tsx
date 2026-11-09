import { useMemo, useState, type FormEvent } from "react";
import { getAsOf, getUnits, type AsOf, type Unit } from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { readableDate } from "@/lib/dates";

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

/** Legal's audit question: what did we say, in which wording, on a given date. */
export function WordingHistory() {
  const units = useQuery("legal-history-units", () => getUnits("", "explore"));
  const options = useMemo(() => {
    const byId = new Map<string, Unit>();
    for (const unit of units.data?.units ?? []) {
      if (!(unit.requires_legal || unit.type === "verbatim" || unit.type === "policy")) continue;
      const current = byId.get(unit.unit_id);
      if (!current || unit.version > current.version) byId.set(unit.unit_id, unit);
    }
    return [...byId.values()].sort((a, b) => a.title.localeCompare(b.title));
  }, [units.data]);
  const [unitId, setUnitId] = useState("");
  const [date, setDate] = useState(today());
  const [time, setTime] = useState("12:00");
  const [result, setResult] = useState<AsOf | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const chosen = unitId || options.find((unit) => unit.unit_id === "U-RX-EDU-001-09")?.unit_id || options[0]?.unit_id || "";
  const title = options.find((unit) => unit.unit_id === chosen)?.title ?? "";

  async function look(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await getAsOf(chosen, `${date} ${time || "12:00"}`));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "The lookup failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  if (units.loading && !units.data) return <Skeleton width="100%" height="200px" label="Loading wording" />;
  if (units.error) return <ServiceError message={units.error} onRetry={units.reload} />;

  return (
    <article className="mail-read mail-read--wide history">
      <h1 className="mail-read__subject">What did we say on a date?</h1>
      <p className="tools-body">Pick a regulated unit, a date and a time to see the exact wording that was live then, its version, and who approved it. On a day the wording changed, the time decides which version you see.</p>
      <form className="history__form" onSubmit={look}>
        <div>
          <label className="hh-label" htmlFor="history-unit">
            Wording
          </label>
          <select
            id="history-unit"
            className="hh-input"
            value={chosen}
            onChange={(event) => {
              setUnitId(event.target.value);
              setResult(null);
            }}
          >
            {options.map((unit) => (
              <option key={unit.unit_id} value={unit.unit_id}>
                {unit.title} ({unit.unit_id})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="hh-label" htmlFor="history-date">
            Date
          </label>
          <input
            id="history-date"
            className="hh-input history__date"
            type="date"
            value={date}
            onChange={(event) => {
              setDate(event.target.value);
              setResult(null);
            }}
          />
        </div>
        <div>
          <label className="hh-label" htmlFor="history-time">
            Time (ET)
          </label>
          <input
            id="history-time"
            className="hh-input history__date"
            type="time"
            value={time}
            onChange={(event) => {
              setTime(event.target.value);
              setResult(null);
            }}
          />
        </div>
        <div>
          <Button type="submit" busy={busy} busyLabel="Looking up…">
            Show the wording
          </Button>
        </div>
      </form>
      {error ? (
        <p className="tools-body history__none" role="status">
          {/No version was live/i.test(error) ? `No version of ${title} was live at ${time} ET on ${longDate(date)}.` : error}
        </p>
      ) : null}
      {result ? (
        <section className="history__result" aria-live="polite">
          <p className="tools-label">
            At {time} ET on {longDate(date)}, version {result.version} was live
          </p>
          <p className="hh-meta">
            Effective {readableDate(result.effective_date) || "date not recorded"}
            {result.approver ? `, approved by ${result.approver}` : ""}.
          </p>
          {(result.versions_that_day?.length ?? 0) > 1 ? (
            <div className="history__day">
              <p className="hh-label">The wording changed that day</p>
              <ul>
                {result.versions_that_day?.map((item) => (
                  <li key={item.version}>
                    Version {item.version}: live from {readableDate(item.start)}
                    {item.end ? ` to ${readableDate(item.end)}` : ", still live"}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <p className="hh-label">Advocate wording</p>
          <p className="tools-body history__text">{result.text}</p>
          {result.member_text ? (
            <>
              <p className="hh-label">Member wording</p>
              <p className="tools-body history__text">{result.member_text}</p>
            </>
          ) : null}
        </section>
      ) : null}
    </article>
  );
}

function longDate(value: string) {
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
