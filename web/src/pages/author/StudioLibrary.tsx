import { useMemo, useState } from "react";
import { getGaps, getUnits, type Unit } from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { EmptyState } from "@/components/empty-state";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { StatusBadge, type StatusVariant } from "@/components/status-badge";
import { VerbatimBlock } from "@/components/verbatim-block";
import { RoutingNote } from "@/components/routing-note";
import { readableDate } from "@/lib/dates";
import { baseLabel, channelLabel, joinLabels } from "@/lib/labels";

const STATUS: Record<string, { label: string; variant: StatusVariant }> = {
  approved: { label: "Approved", variant: "approved" },
  proposed: { label: "Waiting for approval", variant: "review" },
  blocked_conflict: { label: "Blocked by a conflict", variant: "blocked" },
  superseded: { label: "Earlier version", variant: "neutral" },
  merged: { label: "Merged into another unit", variant: "neutral" },
  retired: { label: "Retired", variant: "neutral" },
};

const FILTERS = [
  { id: "approved", label: "Approved" },
  { id: "waiting", label: "Waiting" },
  { id: "blocked_conflict", label: "Blocked" },
  { id: "all", label: "All" },
] as const;

const TYPE: Record<string, string> = { verbatim: "Verbatim", policy: "Policy", procedure: "Procedure", faq: "FAQ" };

function statusOf(unit: Unit) {
  return STATUS[unit.status || ""] ?? { label: unit.status || "Unknown", variant: "neutral" as StatusVariant };
}

/** Every unit in the sandbox, newest version of each, searchable. */
export function StudioLibrary() {
  const units = useQuery("library", () => getUnits("", "explore"));
  const [filter, setFilter] = useState<(typeof FILTERS)[number]["id"]>("approved");
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<string | null>(null);

  const latest = useMemo(() => {
    const byId = new Map<string, Unit>();
    for (const unit of units.data?.units ?? []) {
      const current = byId.get(unit.unit_id);
      if (!current || unit.version > current.version) byId.set(unit.unit_id, unit);
    }
    return [...byId.values()].sort((a, b) => a.title.localeCompare(b.title));
  }, [units.data]);

  const shown = latest.filter((unit) => {
    if (filter === "approved" && unit.status !== "approved") return false;
    if (filter === "waiting" && unit.status !== "proposed") return false;
    if (filter === "blocked_conflict" && unit.status !== "blocked_conflict") return false;
    const text = query.trim().toLowerCase();
    if (!text) return true;
    return [unit.title, unit.unit_id, unit.text, unit.member_text].some((value) => (value || "").toLowerCase().includes(text));
  });
  const selected = shown.find((unit) => unit.unit_id === picked) ?? shown[0] ?? null;

  if (units.loading && !units.data) return <Skeleton width="100%" height="320px" label="Loading the library" />;
  if (units.error || !units.data) return <ServiceError message={units.error || "The library did not load."} onRetry={units.reload} />;

  return (
    <div className="work">
      <nav className="work-queue" aria-label="Library">
        <div className="work-queue__head">
          <h1 className="tools-title-sm">Library</h1>
          <span className="hh-meta">{latest.length} units</span>
        </div>
        <div className="lib-tools">
          <input
            className="hh-input"
            aria-label="Search the library"
            placeholder="Search titles, IDs and wording"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="lib-filters" role="group" aria-label="Status">
            {FILTERS.map((item) => (
              <button key={item.id} type="button" className="hh-chip" aria-pressed={filter === item.id} onClick={() => setFilter(item.id)}>
                {item.label}
              </button>
            ))}
          </div>
        </div>
        {shown.length === 0 ? <p className="hh-meta lib-none">No unit matches.</p> : null}
        {shown.map((unit) => (
          <button
            key={unit.unit_id}
            type="button"
            className="work-item"
            aria-current={selected?.unit_id === unit.unit_id ? "true" : undefined}
            onClick={() => setPicked(unit.unit_id)}
          >
            <span className="work-item__title">{unit.title}</span>
            <span className="work-item__meta">
              {unit.unit_id} · {TYPE[unit.type] || unit.type} · {statusOf(unit).label}
            </span>
          </button>
        ))}
      </nav>
      <section className="work-detail" aria-live="polite">
        {selected ? <UnitDetail unit={selected} /> : <EmptyState heading="Nothing to show" reason="Change the filter or the search." />}
      </section>
    </div>
  );
}

function UnitDetail({ unit }: { unit: Unit }) {
  const status = statusOf(unit);
  return (
    <article className="work-card">
      <div className="item-head">
        <div className="item-head__text">
          <h2 className="tools-title">{unit.title}</h2>
          <p className="item-head__meta">
            <span className="hh-id">{unit.unit_id}</span>
            <span aria-hidden="true">·</span>
            <span>Version {unit.version}</span>
            {unit.document_name ? (
              <>
                <span aria-hidden="true">·</span>
                <span>{unit.document_name}</span>
              </>
            ) : null}
          </p>
        </div>
        <div className="item-head__badges">
          <StatusBadge variant="neutral">{TYPE[unit.type] || unit.type}</StatusBadge>
          <StatusBadge variant={status.variant}>{status.label}</StatusBadge>
        </div>
      </div>
      <p className="hh-label">Advocate wording</p>
      {unit.type === "verbatim" ? <VerbatimBlock text={unit.text} /> : <p className="work-text">{unit.text}</p>}
      {unit.member_text ? (
        <>
          <p className="hh-label">Member wording</p>
          <p className="work-text">{unit.member_text}</p>
        </>
      ) : null}
      <dl className="preview-list lib-facts">
        <div>
          <dt>Approved</dt>
          <dd>{unit.approved_by ? `${unit.approved_by}${unit.approved_on ? `, ${readableDate(unit.approved_on)}` : ""}` : "Not yet"}</dd>
        </div>
        <div>
          <dt>Knowledge bases</dt>
          <dd>{joinLabels(unit.kb_scope, baseLabel) || "Not recorded"}</dd>
        </div>
        <div>
          <dt>Channels</dt>
          <dd>{joinLabels(unit.channels, channelLabel) || "Not recorded"}</dd>
        </div>
        <div>
          <dt>Review by</dt>
          <dd>{readableDate(unit.review_by) || "Not set"}</dd>
        </div>
      </dl>
      <RoutingNote reason={unit.routing_reason} />
    </article>
  );
}

const GAP_STATUS: Record<string, { label: string; variant: StatusVariant }> = {
  proposed: { label: "Waiting for the knowledge owner", variant: "review" },
  in_review: { label: "Draft with the author or approver", variant: "review" },
  closed: { label: "Answered", variant: "approved" },
  dismissed: { label: "Dismissed", variant: "neutral" },
  process_fix: { label: "Process fix instead", variant: "neutral" },
};

/** Every unanswered-question cluster and where it stands. */
export function StudioGaps() {
  const gaps = useQuery("studio-gaps", () => getGaps("explore"));
  if (gaps.loading && !gaps.data) return <Skeleton width="100%" height="320px" label="Loading gaps" />;
  if (gaps.error || !gaps.data) return <ServiceError message={gaps.error || "Gaps did not load."} onRetry={gaps.reload} />;
  const rows = [...gaps.data.gaps].sort((a, b) => b.search_count - a.search_count);
  return (
    <div className="studio-scroll">
      <div className="lib-gaps">
        <h1 className="tools-title">Gaps</h1>
        <p className="tools-body">
          Questions people asked that had no approved answer, grouped by topic. The knowledge owner decides what happens to each; drafts sent to you
          appear in My work.
        </p>
        {rows.length === 0 ? <EmptyState heading="No gaps" reason="Every logged question has an approved answer." /> : null}
        <ul className="lib-gap-list">
          {rows.map((gap) => {
            const status = GAP_STATUS[gap.status] ?? { label: gap.status, variant: "neutral" as StatusVariant };
            return (
              <li key={gap.id} className="lib-gap">
                <div>
                  <strong>{gap.cluster}</strong>
                  <p className="hh-meta">
                    Asked {gap.search_count} {gap.search_count === 1 ? "time" : "times"} · {gap.roles.join(", ") || "No role recorded"}
                  </p>
                  {gap.queries.length ? <p className="hh-meta">For example: &ldquo;{gap.queries[0]}&rdquo;</p> : null}
                </div>
                <StatusBadge variant={status.variant}>{status.label}</StatusBadge>
              </li>
            );
          })}
        </ul>
        <p className="hh-meta">Counts are illustrative, from a made-up search log.</p>
      </div>
    </div>
  );
}
