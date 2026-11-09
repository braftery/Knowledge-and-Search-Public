import { Link, useSearchParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import {
  actOnGap,
  applyDrift,
  approveAuthor,
  approveAuthorAll,
  approveLegal,
  approveLegalAll,
  confirmTags,
  declineLegal,
  escalateConflicts,
  extractUnits,
  getAuthorQueue,
  getChannels,
  getConflicts,
  getCopies,
  getDrift,
  getExtraction,
  getGaps,
  getLegalQueue,
  getQuality,
  getSearchPrompts,
  getToday,
  getVersions,
  keepCanonical,
  publishChannels,
  resolveConflict,
  runToday,
  scoreQuality,
  searchBoth,
  sendDrift,
  type ChannelsView,
  type SearchHit,
  type Unit,
  setUnitTags,
} from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Citation } from "@/components/citation";
import { DecisionMarker } from "@/components/decision-marker";
import { DiffLegend, DiffText } from "@/components/diff-view";
import { EmptyState } from "@/components/empty-state";
import { Field } from "@/components/field";
import { MetricTile } from "@/components/metric-tile";
import { ServiceError } from "@/components/service-state";
import { StatusBadge } from "@/components/status-badge";
import { Tabs } from "@/components/tabs";
import { VerbatimBlock } from "@/components/verbatim-block";
import { DataTable } from "@/components/data-table";
import { addedOnly, apiDiff, baseLabel, plainTitle, relationLabel, statusLabel } from "@/lib/labels";
import { wordDiff } from "@/lib/word-diff";
import { plainMemberTitle } from "@/pages/member/plain";
import { ApprovalReview, ConflictColumns } from "@/pages/legal/ApprovalReview";
import { ActionButton, Illustrative, NumberedSource, StepBar, StudioShell, SurfaceLoading, type StudioSection } from "@/pages/demo/chrome";
import { useGuided, useGuidedOptional } from "@/pages/demo/guided-context";
import { intervalNote } from "@/lib/stats";

const NO_ANSWER =
  "No approved answer for this question. Tell the member you will follow up, and use Flag this answer if you think one should exist. The question was logged for the knowledge team.";

function ResultBadge({ value }: { value: string }) {
  const text = plainResult(value);
  if (/^pass/i.test(text)) return <StatusBadge variant="approved">Pass</StatusBadge>;
  if (/^fail/i.test(text)) return <StatusBadge variant="blocked">Fail</StatusBadge>;
  return <StatusBadge variant="neutral">{text}</StatusBadge>;
}

function plainResult(value: string) {
  return /not cached/i.test(value || "") ? "No saved answer" : value;
}

const SHORTCUT_NOTE = "Demo only. In production each unit is approved on its own review page.";

export function TodayStep() {
  const guided = useGuided();
  const today = useQuery(`today:${guided.tick}`, () => getToday());
  if (today.showSkeleton || (!today.data && !today.error)) return <SurfaceLoading label="Loading today's search" />;
  if (today.error || !today.data) return <ServiceError message={today.error || "Today's search did not load."} onRetry={today.reload} />;
  const view = today.data;
  return (
    <div className="desk" data-theme="tools">
      <header className="desk-top">
        <strong className="desk-top__brand">
          Harbor Health <span>Contact Center</span>
        </strong>
        <span className="desk-top__queue">Pharmacy queue</span>
        <span className="desk-top__user">
          <span className="avatar" aria-hidden="true">JH</span>
          Jordan Hale
        </span>
      </header>
      <div className="desk-call">
        <div>
          <p className="desk-call__name">Dana R.</p>
          <p className="desk-call__meta">HBR-20418 · Harbor Medicare Advantage HMO · Fictional caller</p>
        </div>
        <StatusBadge variant="approved">Verified</StatusBadge>
      </div>
      <StepBar>
        {view.ran ? null : (
          <ActionButton busyLabel="Running the search…" onClick={() => void guided.run("Running the search…", () => runToday())}>
            Run today's search
          </ActionButton>
        )}
      </StepBar>
      <div className="studio-scroll">
        <h1 className="tools-title">Today's document search</h1>
        <p className="tools-body">
          Query: {view.query}. {view.message}
        </p>
        <Illustrative />
        {view.ran ? (
          <>
            <DiffLegend />
            <p className="hh-meta">Differences are shown against script v1.</p>
            <div className="today-grid">
              {view.cards.map((card) => (
                <article className="hh-card" key={card.title}>
                  <h2 className="hh-card__title">{card.title}</h2>
                  <p className="hh-meta">{card.signed}</p>
                  <DiffText parts={apiDiff(card.diff)} />
                </article>
              ))}
            </div>
          </>
        ) : (
          <EmptyState heading="No documents yet" reason="Run the search to see what an advocate gets today." />
        )}
      </div>
    </div>
  );
}

/** Explore reuses a guided screen read-only, with the Studio rail as real navigation. */
export type ExploreNav = { onNavigate: (section: StudioSection) => void; sections: StudioSection[] };

export function ExtractStep({ explore }: { explore?: ExploreNav } = {}) {
  const guided = useGuidedOptional();
  const world = explore ? "explore" : "guided";
  const extraction = useQuery(`extract:${world}:${guided?.tick ?? 0}`, () => getExtraction(world));
  if (extraction.showSkeleton || (!extraction.data && !extraction.error)) return <SurfaceLoading label="Loading the extraction" />;
  if (extraction.error || !extraction.data) {
    return <ServiceError message={extraction.error || "The extraction did not load."} onRetry={extraction.reload} />;
  }
  const view = extraction.data;
  return (
    <StudioShell current="sources" counts={{ sources: view.unit_count }} onNavigate={explore?.onNavigate} sections={explore?.sections}>
      {guided ? (
        <StepBar>
          {!view.extracted ? (
            <ActionButton busyLabel="Extracting units…" onClick={() => void guided.run("Extracting units…", () => extractUnits())}>
              Extract units with AI
            </ActionButton>
          ) : null}
          {view.extracted && !view.tags_confirmed ? (
            <ActionButton busyLabel="Confirming tags…" onClick={() => void guided.run("Confirming tags…", () => confirmTags())}>
              Confirm tags and audience
            </ActionButton>
          ) : null}
        </StepBar>
      ) : null}
      <div className="studio-scroll">
        <h1 className="tools-title">{explore ? `${view.document.title}: from document to knowledge units` : "New extractions to confirm"}</h1>
        {explore ? (
          <p className="tools-body">
            The AI read this script, split it into {view.unit_count} units, typed each one, tagged it, and tied it to the numbered passage it came from. A
            person confirmed the tags and audience. Each unit then goes to Knowledge Ops or Legal for approval. Pick a number in the script to find its unit.
          </p>
        ) : null}
        <p className="tools-body">
          {explore ? "" : `${view.message} `}Verbatim units matching the source: {view.verbatim_matching_source} of {view.verbatim_total}.
        </p>
        <Illustrative />
        {view.extracted && view.audience_corrections.length > 0 ? (
          <div className="hh-stack">
            <p className="hh-meta">
              Each unit holds advocate wording and, where members need it, member wording. Both are approved by Legal. The audience decides who
              may search the unit; each channel then shows the wording written for its reader.
            </p>
            {view.audience_corrections.map((item) =>
              item.applied ? (
                <DecisionMarker
                  key={item.unit_id}
                  kind="human"
                  role="Knowledge Ops author"
                  decision={`${item.title}: audience set to ${item.audience}. AI had suggested ${item.ai_audience}.`}
                />
              ) : (
                <DecisionMarker
                  key={item.unit_id}
                  kind="ai"
                  detail={`${item.title}: audience ${item.ai_audience}. A person sets ${item.audience}.`}
                />
              ),
            )}
          </div>
        ) : null}
        <div className="split-2">
          <div>
            <h2 className="tools-label">Source: {view.document.title}</h2>
            <NumberedSource
              body={view.document.body}
              quotes={view.units.map((unit) => ({ number: unit.number || 0, quote: unit.source_quote || "" }))}
            />
          </div>
          <div>
            <h2 className="tools-label">{view.extracted ? "Extracted units" : "Extracted units will appear here"}</h2>
            {view.extracted ? (
              <div className="panel-scroll" role="region" aria-label="Extracted units" tabIndex={0}>
                {view.units.map((unit) => (
                  <UnitExtract key={unit.unit_id} unit={unit} confirmed={view.tags_confirmed} />
                ))}
              </div>
            ) : (
              <EmptyState heading="No units yet" reason="Extract units with AI to propose wording, type, and source span." />
            )}
          </div>
        </div>
      </div>
    </StudioShell>
  );
}

function UnitExtract({ unit, confirmed }: { unit: Unit; confirmed: boolean }) {
  const tags = unit.tags || [];
  const audience = (unit.audience || []).join(", ");
  return (
    <article className="hh-card unit-card" id={`unit-${unit.number}`}>
      <div className="hh-card__head">
        <h3 className="hh-card__title">
          <span className="unit-card__num">{unit.number}</span>
          {unit.title}
        </h3>
        <StatusBadge variant="neutral">{typeName(unit.type)}</StatusBadge>
      </div>
      <p className="tools-body unit-card__text">{unit.text}</p>
      <div className="unit-card__tags" aria-label="Tags">
        {tags.map((tag) => (
          <span key={tag} className="tag-chip">
            {tag}
          </span>
        ))}
        <span className="unit-card__aud">Audience: {audience || "not set"}</span>
      </div>
      <div className="unit-card__foot">
        {confirmed ? (
          <DecisionMarker kind="human" role="Knowledge Ops author" decision="Tags and audience confirmed." />
        ) : unit.tags_edited_by ? (
          <DecisionMarker kind="human" role={unit.tags_edited_by} decision="Tags, audience and domain edited for this unit." />
        ) : (
          <DecisionMarker kind="ai" detail="Type, tags and audience suggested by the model." />
        )}
        <span className="hh-id">{unit.unit_id}</span>
      </div>
      {!confirmed ? <TagEditor unit={unit} /> : null}
    </article>
  );
}

function typeName(type: string) {
  const labels: Record<string, string> = { verbatim: "Verbatim", policy: "Policy", procedure: "Procedure", faq: "FAQ" };
  return labels[type] || type;
}

export function CopiesStep({ explore }: { explore?: ExploreNav } = {}) {
  const guided = useGuidedOptional();
  const world = explore ? "explore" : "guided";
  const copies = useQuery(`copies:${world}:${guided?.tick ?? 0}`, () => getCopies(world));
  const [tab, setTab] = useState("near_duplicate");
  if (copies.showSkeleton || (!copies.data && !copies.error)) return <SurfaceLoading label="Loading copies" />;
  if (copies.error || !copies.data) return <ServiceError message={copies.error || "Copies did not load."} onRetry={copies.reload} />;
  const view = copies.data;
  if (!view.ready) {
    return (
      <StudioShell current="copies">
        <div className="studio-scroll">
          <EmptyState heading="No units to compare yet" reason="Extract units from the script first." action={<PrereqLink step={1} label="Go to step 2: extract units" />} />
        </div>
      </StudioShell>
    );
  }
  const visible = tab === "all" ? view.pairs : view.pairs.filter((pair) => pair.relation === tab);
  return (
    <StudioShell current="copies" counts={{ copies: view.counts.all }} onNavigate={explore?.onNavigate} sections={explore?.sections}>
      <StepBar>
        {guided && view.can_keep_canonical ? (
          <ActionButton busyLabel="Keeping v1…" onClick={() => void guided.run("Keeping v1…", () => keepCanonical())}>
            Keep the Legal-signed v1 wording
          </ActionButton>
        ) : null}
        {guided && view.can_escalate ? (
          <ActionButton
            busyLabel="Sending conflicts…"
            onClick={() => void guided.run("Sending conflicts…", () => escalateConflicts())}
          >
            {`Escalate ${view.counts.conflict} conflicts to Legal`}
          </ActionButton>
        ) : null}
      </StepBar>
      <div className="studio-scroll">
        <h1 className="tools-title">Copies and conflicts</h1>
        <p className="tools-body">
          AI compared {view.counts.all} pairs. {view.message}
        </p>
        <Illustrative />
        <div className="legend-row">
          <DiffLegend />
          <span className="hh-meta">Column B is compared against column A.</span>
        </div>
        <Tabs
          label="Copy groups"
          value={tab}
          onChange={setTab}
          tabs={[
            { id: "near_duplicate", label: "Near-duplicates", count: view.counts.near_duplicate },
            { id: "exact", label: "Exact copies", count: view.counts.exact },
            { id: "conflict", label: "Conflicts", count: view.counts.conflict },
            { id: "all", label: "All pairs", count: view.counts.all },
          ]}
        />
        {tab === "conflict" ? (
          <p className="tools-body">Both versions stay blocked from search until Legal picks one and records a reason.</p>
        ) : null}
        {tab === "all" ? (
          <DataTable
            caption="Every pair the model judged"
            rows={view.pairs}
            getId={(row) => `${row.a_id}-${row.b_id}`}
            columns={[
              { id: "a", header: "Unit A", render: (row) => row.a_id },
              { id: "b", header: "Unit B", render: (row) => row.b_id },
              { id: "label", header: "AI label", render: (row) => relationLabel(row.relation) },
              { id: "rating", header: "Model's own rating", render: (row) => String(row.confidence ?? "") },
              { id: "reason", header: "AI reason", render: (row) => row.reason },
            ]}
          />
        ) : (
          <div className="hh-stack">
            {visible.map((pair) => (
              <article className="hh-card pair-card" key={`${pair.a_id}-${pair.b_id}`}>
                <div className="hh-card__head">
                  <h2 className="hh-card__title">{pair.a_title}</h2>
                  <div className="item-head__badges">
                    <StatusBadge variant={pair.relation === "conflict" ? "blocked" : "review"}>{relationLabel(pair.relation)}</StatusBadge>
                  </div>
                </div>
                <div className="pair-cols">
                  <div className="pair-col">
                    <p className="pair-col__head">
                      <strong>A · {pair.a_doc}</strong>
                      <span className="hh-meta">{statusLabel(pair.a_status)}</span>
                    </p>
                    <DiffText parts={apiDiff(pair.diff).filter((part) => part.kind !== "add")} />
                    <span className="hh-id">{pair.a_id}</span>
                  </div>
                  <div className="pair-col">
                    <p className="pair-col__head">
                      <strong>B · {pair.b_doc}</strong>
                      <span className="hh-meta">{statusLabel(pair.b_status)}</span>
                    </p>
                    <DiffText parts={apiDiff(pair.diff).filter((part) => part.kind !== "del")} />
                    <span className="hh-id">{pair.b_id}</span>
                  </div>
                </div>
                <div className="pair-why">
                  <DecisionMarker kind="ai" />
                  <p className="tools-body">{pair.reason}</p>
                  <span className="hh-meta pair-why__rating">Model&apos;s own rating: {String(pair.confidence ?? "not recorded")} (not calibrated)</span>
                </div>
                <div className="pair-foot">
                  <PairDecision line={pair.human_line} />
                </div>
              </article>
            ))}
            {tab === "near_duplicate" && view.website_merge ? <WebsiteMerge merge={view.website_merge} /> : null}
          </div>
        )}
      </div>
    </StudioShell>
  );
}

function PairDecision({ line }: { line: string }) {
  if (!line) return null;
  if (line.startsWith("Human decision")) {
    return <DecisionMarker kind="human" role="Knowledge Ops author" decision={line.replace(/^Human decision:\s*/, "")} />;
  }
  if (line.startsWith("Legal resolved")) {
    return <DecisionMarker kind="human" role="Legal approver" decision={line} />;
  }
  if (line.toLowerCase().includes("legal")) return <DecisionMarker kind="pending" role="Legal approver" />;
  return <DecisionMarker kind="pending" role="Knowledge Ops author" />;
}

function WebsiteMerge({
  merge,
}: {
  merge: { into_unit_id: string; member_text: string; units: Array<{ unit_id: string; text: string; status: string }>; merged: boolean };
}) {
  return (
    <article className="hh-card">
      <h2 className="hh-card__title">Website price disclaimer</h2>
      <DecisionMarker kind="ai" detail="Split one website sentence group into 3 units." />
      {merge.merged ? (
        <DecisionMarker
          kind="human"
          role="Knowledge Ops author"
          decision={`Merged into the member wording of ${merge.into_unit_id}. Search cannot see the three pieces.`}
        />
      ) : (
        <DecisionMarker kind="pending" role="Knowledge Ops author" />
      )}
      {merge.units.map((unit) => (
        <p className="hh-meta" key={unit.unit_id}>
          {unit.unit_id} ({statusLabel(unit.status)}). {unit.text}
        </p>
      ))}
      <p className="tools-body">Member wording: {merge.member_text}</p>
    </article>
  );
}

export function ApproveStep() {
  const guided = useGuided();
  const legal = useQuery(`legal:${guided.tick}`, () => getLegalQueue());
  const author = useQuery(`author:${guided.tick}`, () => getAuthorQueue());
  const conflicts = useQuery(`conflicts:${guided.tick}`, () => getConflicts());
  const [tab, setTab] = useState("legal");
  const legalSeen = useRef(0);
  if (legal.data && legal.data.count > legalSeen.current) legalSeen.current = legal.data.count;
  const legalPosition = Math.max(1, legalSeen.current - (legal.data?.count ?? 0) + 1);
  if ((legal.loading && !legal.data) || (author.loading && !author.data) || (conflicts.loading && !conflicts.data)) {
    return <SurfaceLoading label="Loading the approval queues" />;
  }
  if (legal.error || !legal.data) return <ServiceError message={legal.error || "The Legal queue did not load."} onRetry={legal.reload} />;
  if (author.error || !author.data) return <ServiceError message={author.error || "The author queue did not load."} onRetry={author.reload} />;
  if (conflicts.error || !conflicts.data) return <ServiceError message={conflicts.error || "Conflicts did not load."} onRetry={conflicts.reload} />;

  const waiting = [...legal.data.waiting].sort((a, b) => demoRank(a.unit_id) - demoRank(b.unit_id));
  const current = waiting[0];
  const authors = author.data.waiting;
  const authorCurrent = authors[0];

  return (
    <div className="review-page" data-theme="tools">
      <div className="studio-scroll" style={{ paddingBottom: 0 }}>
        <Tabs
          label="Approval queues"
          value={tab}
          onChange={setTab}
          tabs={[
            { id: "legal", label: "Legal queue", count: legal.data.count },
            { id: "author", label: "Knowledge Ops approvals", count: author.data.count },
            { id: "conflicts", label: "Conflicts for Legal", count: conflicts.data.count_open },
          ]}
        />
      </div>
      {tab === "legal" && current && legal.data.can_approve_all ? (
        <div className="studio-scroll demo-shortcut">
          <div className="step-actions">
            <ActionButton variant="secondary" busyLabel="Approving the queue…" onClick={() => void guided.run("Approving the queue…", () => approveLegalAll())}>
              Approve all remaining (demo shortcut)
            </ActionButton>
          </div>
          <p className="hh-meta">{SHORTCUT_NOTE}</p>
        </div>
      ) : null}
      {tab === "legal" && current ? (
        <ApprovalReview
          unit={current}
          position={legalPosition}
          total={Math.max(legalSeen.current, waiting.length)}
          approveLabel="Approve and publish"
          busyLabel="Publishing…"
          approverRole="Legal approver"
          busy={guided.busy}
          onApprove={() => void guided.run("Publishing…", () => approveLegal(current.unit_id))}
          onDecline={(reason) => void guided.run("Sending back…", () => declineLegal(current.unit_id, reason))}
        />
      ) : null}
      {tab === "legal" && !current ? (
        <div className="studio-scroll">
          {legal.data.ready ? (
            <EmptyState heading="All caught up" reason={legal.data.message || "New items arrive by email."} />
          ) : (
            <EmptyState heading="Nothing to approve yet" reason="Units reach Legal after they are extracted and their copies are settled." action={<PrereqLink step={1} label="Go to step 2: extract units" />} />
          )}
          {legal.data.held.length > 0 ? (
            <details>
              <summary>
                {legal.data.held.length} units stay unapproved
              </summary>
              {legal.data.held.map((item) => (
                <p className="hh-meta" key={item.unit_id}>
                  {item.unit_id}. {item.title}. {item.notes}
                </p>
              ))}
            </details>
          ) : null}
        </div>
      ) : null}
      {tab === "author" && authorCurrent ? (
        <>
          {author.data.can_approve_all ? (
            <div className="studio-scroll demo-shortcut">
              <div className="step-actions">
                <ActionButton variant="secondary" busyLabel="Approving procedures…" onClick={() => void guided.run("Approving procedures…", () => approveAuthorAll())}>
                  Approve all (demo shortcut)
                </ActionButton>
              </div>
              <p className="hh-meta">{SHORTCUT_NOTE}</p>
            </div>
          ) : null}
          <ApprovalReview
            unit={authorCurrent}
            position={1}
            total={authors.length}
            approveLabel="Approve as Knowledge Ops"
            busyLabel="Approving…"
            approverRole="Knowledge Ops author"
            busy={guided.busy}
            onApprove={() => void guided.run("Approving…", () => approveAuthor(authorCurrent.unit_id))}
          />
        </>
      ) : null}
      {tab === "author" && !authorCurrent ? (
        <div className="studio-scroll">
          <EmptyState heading="Nothing waiting" reason={author.data.message} />
        </div>
      ) : null}
      {tab === "conflicts" ? (
        <div className="studio-scroll">
          <h1 className="tools-title">Conflicts for Legal</h1>
          <p className="tools-body">{conflicts.data.message} {conflicts.data.count_open} open.</p>
          {[...conflicts.data.plans]
            .sort((a, b) => Number(!/mail/i.test(a.label)) - Number(!/mail/i.test(b.label)))
            .map((plan) => (
            <ConflictColumns
              key={plan.id}
              plan={plan}
              busy={guided.busy}
              onResolve={(reason) => void guided.run(`Resolving ${plan.label}…`, () => resolveConflict(reason, plan.id))}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function SearchStep() {
  const guided = useGuided();
  const prompts = useQuery("prompts", () => getSearchPrompts());
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (prompts.data && !query) setQuery(prompts.data.cost);
  }, [prompts.data, query]);

  if (prompts.error) return <ServiceError message={prompts.error} onRetry={prompts.reload} />;

  async function runQuery(next: string, record: boolean) {
    setQuery(next);
    const result = await guided.run("Searching…", () => searchBoth(next, record));
    if (result && "results" in result) setHits(result.results as SearchHit[]);
  }

  return (
    <div>
      <StepBar>
        <ActionButton busyLabel="Searching…" onClick={() => void runQuery(query || prompts.data?.cost || "", true)} disabled={!prompts.data}>
          Search as both roles
        </ActionButton>
        <ActionButton variant="secondary" busyLabel="Searching…" onClick={() => void runQuery(prompts.data?.abstain || "", true)} disabled={!prompts.data}>
          A question with no approved answer
        </ActionButton>
        <ActionButton
          variant="secondary"
          busyLabel="Searching…"
          onClick={() => void runQuery(prompts.data?.pharmacy_only || "", false)}
          disabled={!prompts.data}
        >
          A pharmacy-only question
        </ActionButton>
      </StepBar>
      <div className="compare-stage">
        <RoleFrame role="Pharmacy advocate" advocate="Jordan Hale" caller="Dana R." hit={hits?.[0] ?? null} pending={!hits} />
        <RoleFrame role="Insurance advocate" advocate="Priya Shah" caller="Maria S." hit={hits?.[1] ?? null} pending={!hits} />
      </div>
    </div>
  );
}

function RoleFrame({
  role,
  advocate,
  caller,
  hit,
  pending,
}: {
  role: string;
  advocate: string;
  caller: string;
  hit: SearchHit | null;
  pending: boolean;
}) {
  const bases = (hit?.searched || []).map(baseLabel);
  return (
    <article className="compare-frame" aria-label={role}>
      <p className="compare-frame__label">{role}</p>
      <header className="desk-top">
        <strong className="desk-top__brand">
          Harbor Health <span>Contact Center</span>
        </strong>
        <span className="desk-top__user">
          <span className="avatar" aria-hidden="true">
            {advocate
              .split(" ")
              .map((part) => part[0])
              .join("")}
          </span>
          {advocate}
        </span>
      </header>
      <div className="desk-call">
        <p className="desk-call__name">{caller}</p>
        <p className="desk-call__meta">Fictional caller</p>
      </div>
      {bases.length ? (
        <div className="scope-bar">
          <span className="hh-meta">Searched only</span>
          {bases.map((base) => (
            <span key={base} className="tag-chip scope-chip">
              {base}
            </span>
          ))}
        </div>
      ) : null}
      <div className="studio-scroll">
        {pending ? <p className="tools-body">Press Search as both roles. Each role searches only the knowledge bases it may read.</p> : null}
        {hit?.abstained || (hit && !hit.unit) ? (
          <div className="hh-stack">
            <p className="hh-answer__q">{hit.query}</p>
            <EmptyState heading="No approved answer" reason={NO_ANSWER} />
            {hit.note && !isEngineNote(hit.note) ? <p className="hh-meta">Why the AI found no answer: {hit.note}</p> : null}
          </div>
        ) : null}
        {hit?.unit ? <AdvocateAnswer hit={hit} unit={hit.unit} /> : null}
      </div>
    </article>
  );
}

function AdvocateAnswer({ hit, unit }: { hit: SearchHit; unit: Unit }) {
  return (
    <article className="hh-answer" style={{ maxWidth: "none" }}>
      <p className="hh-answer__q">{hit.query}</p>
      <DecisionMarker
        kind="human"
        role={unit.approved_by || "Legal approver"}
        timestamp={unit.approved_on}
        decision={`Approved version ${unit.version}.`}
      />
      {unit.type === "verbatim" ? <VerbatimBlock text={unit.text} /> : <p className="tools-body">{unit.text}</p>}
      {unit.type === "verbatim" ? <p className="hh-meta">The advocate reads this word for word. Paraphrasing is not allowed.</p> : null}
      <Citation
        audience="internal"
        title={plainTitle(unit.title)}
        version={unit.version}
        approver={unit.approved_by}
        date={(unit.approved_on || unit.effective_date || "").slice(0, 10)}
      />
    </article>
  );
}

export function ChannelsStep() {
  const guided = useGuided();
  const channels = useQuery(`channels:${guided.tick}`, () => getChannels());
  const [preview, setPreview] = useState(false);
  const [typed, setTyped] = useState<{ text: string; member_text: string } | null>(null);
  const liveId = channels.data?.live?.unit_id;
  const versions = useQuery(`versions:${liveId ?? "none"}:${guided.tick}`, () => getVersions(liveId as string), Boolean(liveId));

  if (channels.showSkeleton || (!channels.data && !channels.error)) return <SurfaceLoading label="Loading channels" />;
  if (channels.error || !channels.data) return <ServiceError message={channels.error || "Channels did not load."} onRetry={channels.reload} />;
  const view = channels.data;
  if (!view.ready || !view.live) {
    return (
      <div className="studio-scroll">
        <EmptyState heading="No approved pricing disclaimer yet" reason={view.message} action={<PrereqLink step={3} label="Go to step 4: Legal approves" />} />
      </div>
    );
  }
  const showingPreview = preview && !view.revised && view.revision_preview;
  return (
    <div>
      <StepBar>
        {!view.revised && !preview ? (
          <ActionButton busyLabel="Preparing the revision…" onClick={() => setPreview(true)}>
            Legal revises the wording
          </ActionButton>
        ) : null}
        {showingPreview ? (
          <ActionButton
            busyLabel="Publishing…"
            onClick={() =>
              void guided.run("Publishing…", async () => {
                const prepared = view.revision_preview;
                const edited = typed && prepared && (typed.text !== prepared.advocate_text || typed.member_text !== prepared.member_text);
                const result = await publishChannels("guided", edited ? typed : undefined);
                setPreview(false);
                setTyped(null);
                return result;
              })
            }
          >
            {`Publish version ${view.revision_preview?.next_version ?? view.live.version + 1}`}
          </ActionButton>
        ) : null}
      </StepBar>
      <p className="version-strip">
        {showingPreview
          ? `A revision is prepared. Version ${view.live.version} is still live.`
          : `Live on every channel, version ${view.live.version}.`}
      </p>
      {showingPreview && view.revision_preview ? (
        <details className="legal-edit" onToggle={(event) => {
          const prepared = view.revision_preview;
          if ((event.currentTarget as HTMLDetailsElement).open && !typed && prepared) setTyped({ text: prepared.advocate_text, member_text: prepared.member_text });
        }}>
          <summary>Legal edits the wording before publishing</summary>
          <label className="hh-label" htmlFor="legal-edit-advocate">
            Advocate wording
          </label>
          <textarea
            id="legal-edit-advocate"
            className="hh-input legal-edit__text"
            rows={4}
            value={typed?.text ?? view.revision_preview.advocate_text}
            onChange={(event) => setTyped((current) => ({ text: event.target.value, member_text: current?.member_text ?? view.revision_preview?.member_text ?? "" }))}
          />
          <label className="hh-label" htmlFor="legal-edit-member">
            Member wording
          </label>
          <textarea
            id="legal-edit-member"
            className="hh-input legal-edit__text"
            rows={4}
            value={typed?.member_text ?? view.revision_preview.member_text}
            onChange={(event) => setTyped((current) => ({ text: current?.text ?? view.revision_preview?.advocate_text ?? "", member_text: event.target.value }))}
          />
          <p className="hh-meta">
            Publishing checks typed wording against the source, routes any cost wording, and records it as edited by Legal. Wording that differs from the
            prepared revision may not match a saved model answer until one is recorded. The step 8 score stays on its fixed snapshot.
          </p>
        </details>
      ) : null}
      <div className="compare-stage">
        <article className="compare-frame" aria-label="Pharmacy advocate">
          <p className="compare-frame__label">Pharmacy advocate</p>
          <div className="studio-scroll">
            <DecisionMarker
              kind="human"
              role={view.live.approved_by || "Legal approver"}
              timestamp={view.live.approved_on}
              decision={`Version ${view.live.version} is approved.`}
            />
            {showingPreview ? <DecisionMarker kind="ai" detail="Prepared edit to the advocate wording." /> : null}
            {showingPreview ? <DecisionMarker kind="pending" role="Legal approver" /> : null}
            {showingPreview ? (
              <VerbatimBlock>
                <DiffText parts={apiDiff(view.revision_preview?.advocate_diff)} />
              </VerbatimBlock>
            ) : view.revised && hasChange(view.advocate_diff) ? (
              <VerbatimBlock>
                <DiffText parts={addedOnly(view.advocate_diff)} />
              </VerbatimBlock>
            ) : (
              <VerbatimBlock text={view.live.text} />
            )}
            <Citation
              audience="internal"
              title={view.live.title}
              version={view.live.version}
              approver={view.live.approved_by}
              date={(view.live.approved_on || "").slice(0, 10)}
            />
            <p className="hh-meta">{view.live.unit_id}</p>
            <ChannelHistory view={view} versions={versions.data?.versions} />
          </div>
        </article>
        <article className="compare-frame" aria-label="Member chat" data-theme="member">
          <p className="compare-frame__label">Member</p>
          <div className="hh-m channel-phone-stage">
            <div className="member-device member-device--inline" role="region" aria-label="Harbor Health app, Ask Harbor">
              <div className="member-device__status">
                <span>9:41</span>
                <span>Harbor Health</span>
              </div>
              <div className="member-device__wordmark">Ask Harbor</div>
              <div className="hh-chat__body">
            <div className="hh-bubble hh-bubble--me">How much will my prescription cost?</div>
            <div className="hh-bubble hh-bubble--bot">
              {/* Members only ever see published wording: a pending revision stays on the advocate side until Publish. */}
              {view.revised && hasChange(view.member_diff) ? (
                <DiffText parts={addedOnly(view.member_diff)} />
              ) : (
                <p className="member-body">{view.live.member_text}</p>
              )}
              <Citation
                audience="member"
                title={plainMemberTitle(view.live.title)}
                date={(view.live.effective_date || view.live.approved_on || "").slice(0, 10)}
              />
            </div>
              </div>
            </div>
            <p className="hh-meta">The member sees approved wording only.</p>
          </div>
        </article>
      </div>
      <p className="single-source-note">
        One unit, two channels: both frames show <span className="hh-id">{view.live.unit_id}</span>, version {view.live.version}. The advocate reads its
        advocate wording; the member reads its member wording. Publishing a new version changes both at once.
      </p>
    </div>
  );
}

function hasChange(parts: ChannelsView["advocate_diff"]) {
  return (parts || []).some((part) => part.kind !== "equal");
}

function ChannelHistory({ view, versions }: { view: ChannelsView; versions?: Unit[] }) {
  if (!view.previous && !(versions && versions.length > 1)) return null;
  return (
    <details>
      <summary>Version 1 stays in the history</summary>
      {view.previous ? <p className="tools-body">{view.previous.text}</p> : null}
      <p className="hh-meta">
        {(versions || []).map((item) => `Version ${item.version} ${statusLabel(item.status)}`).join(". ")}
      </p>
    </details>
  );
}

export function GapsStep() {
  const guided = useGuided();
  const gaps = useQuery(`gaps:${guided.tick}`, () => getGaps());
  const [picked, setPicked] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const rows = gaps.data?.gaps || [];
  const selected = rows.find((gap) => gap.id === picked) || rows.find((gap) => gap.draft_text) || rows[0];

  useEffect(() => {
    if (!selected) return;
    if (!picked) setPicked(selected.id);
  }, [selected, picked]);

  if (gaps.showSkeleton || (!gaps.data && !gaps.error)) return <SurfaceLoading label="Loading gaps" />;
  if (gaps.error || !gaps.data) return <ServiceError message={gaps.error || "Gaps did not load."} onRetry={gaps.reload} />;
  if (!selected) {
    return (
      <div className="studio-scroll">
        <EmptyState heading="No unanswered cluster" reason={gaps.data.message} />
      </div>
    );
  }

  async function decide(action: "write" | "fix_process" | "dismiss") {
    if (!reason.trim()) {
      setError("Add a reason. It is saved with the decision.");
      return;
    }
    const labels = { write: "Sending the draft…", fix_process: "Saving the process fix…", dismiss: "Dismissing…" };
    await guided.run(labels[action], () => actOnGap(selected.id, action, reason.trim()));
  }

  return (
    <div data-theme="tools">
      <header className="legal-top">
        <strong className="desk-top__brand">
          Harbor Health <span>Knowledge Insights</span>
        </strong>
        <span className="desk-top__queue">Gaps</span>
        <span className="desk-top__user">
          <span className="avatar" aria-hidden="true">KO</span>
          Knowledge owner
        </span>
      </header>
      {selected.status === "proposed" ? (
        <StepBar>
          {selected.draft_text ? (
            <ActionButton busyLabel="Sending the draft…" onClick={() => void decide("write")}>
              Send draft to author
            </ActionButton>
          ) : null}
          <ActionButton variant="secondary" busyLabel="Saving the process fix…" onClick={() => void decide("fix_process")}>
            Fix the process instead
          </ActionButton>
          <ActionButton variant="tertiary" busyLabel="Dismissing…" onClick={() => void decide("dismiss")}>
            Dismiss
          </ActionButton>
        </StepBar>
      ) : null}
      <div className="split-2 studio-scroll">
        <div>
          <h1 className="tools-title">Unanswered questions</h1>
          <p className="tools-body">Counts are illustrative, from a made-up search log.</p>
          <div className="hh-stack">
            {rows.map((gap) => (
              <button
                key={gap.id}
                type="button"
                className="gap-pick"
                aria-current={gap.id === selected.id ? "true" : undefined}
                onClick={() => {
                  setPicked(gap.id);
                  setReason("");
                  setError("");
                }}
              >
                <span>{gap.cluster}</span>
                <span className="hh-count">{gap.search_count}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="hh-stack">
          {selected.status !== "proposed" ? (
            <DecisionMarker kind="human" role="Knowledge owner" decision={`${gapStatus(selected.status)}. ${selected.reason}`} />
          ) : (
            <div className="gap-decide">
              <DecisionMarker kind="pending" role="Knowledge owner" />
              <Field
                id="gap-reason"
                label="Reason for your decision"
                hint="Required. Saved with the decision and shown to the author."
                error={error}
                value={reason}
                suggestion={`Asked ${selected.search_count} ${selected.search_count === 1 ? "time" : "times"} with no approved answer.`}
                onUseSuggestion={() => {
                  setReason(`Asked ${selected.search_count} ${selected.search_count === 1 ? "time" : "times"} with no approved answer.`);
                  setError("");
                }}
                onChange={(event) => {
                  setReason(event.target.value);
                  setError("");
                }}
              />
            </div>
          )}
          {selected.draft_text ? (
            <article className="hh-card draft-card">
              <div className="hh-card__head">
                <div>
                  <h2 className="hh-card__title">{selected.draft_title}</h2>
                  <p className="item-head__meta">
                    <span>
                      Asked {selected.search_count} {selected.search_count === 1 ? "time" : "times"}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span>Suggested knowledge base: {baseLabel(selected.suggested_kb)}</span>
                  </p>
                </div>
                <div className="item-head__badges">
                  {selected.status === "proposed" ? <DecisionMarker kind="ai" /> : null}
                </div>
              </div>
              <PlaceholderSummary text={selected.draft_text} />
              <DraftText text={selected.draft_text} />
              {selected.invented_figures.length > 0 ? (
                <StatusBadge variant="blocked">Contains a figure not in the questions or approved units: {selected.invented_figures.join(", ")}</StatusBadge>
              ) : (
                <StatusBadge variant="approved">No invented figures</StatusBadge>
              )}
              {selected.checklist.length > 0 ? (
                <div className="draft-check">
                  <h3 className="tools-label">The author must confirm</h3>
                  <ul>
                    {selected.checklist.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </article>
          ) : (
            <EmptyState
              heading="New questions, not yet clustered"
              reason="These had no approved answer and match no existing cluster. Member identifiers are removed before logging."
              steps={selected.queries}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function gapStatus(status: string) {
  if (status === "in_review") return "Sent to the author";
  if (status === "process_fix") return "Marked as a process fix";
  if (status === "dismissed") return "Dismissed";
  return status;
}

function DraftText({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).map((block) => block.trim()).filter(Boolean);
  return (
    <div className="draft-text">
      {blocks.map((block, index) => {
        const label = /^([A-Z][^:\n]{1,60}):\s*/.exec(block);
        const body = label ? block.slice(label[0].length) : block;
        return (
          <div key={index} className="draft-block">
            {label ? <p className="draft-block__label">{label[1]}</p> : null}
            <p className="tools-body">{withPlaceholders(body)}</p>
          </div>
        );
      })}
    </div>
  );
}

function withPlaceholders(text: string) {
  return text.split(/(\[[^\]]+\])/g).map((part, index) =>
    part.startsWith("[") && part.endsWith("]") ? (
      <mark key={index} className="placeholder">
        {part}
      </mark>
    ) : (
      <span key={index}>{part}</span>
    ),
  );
}

function PlaceholderSummary({ text }: { text: string }) {
  const count = (text.match(/\[[^\]]+\]/g) || []).length;
  if (!count) return null;
  return (
    <p className="draft-summary">
      <StatusBadge variant="review">{`${count} ${count === 1 ? "placeholder" : "placeholders"} to fill`}</StatusBadge>
      <span className="hh-meta">The AI left a placeholder wherever a fact must come from an approved source.</span>
    </p>
  );
}

export function DriftStep() {
  const guided = useGuided();
  const drift = useQuery(`drift:${guided.tick}`, () => getDrift());
  if (drift.showSkeleton || (!drift.data && !drift.error)) return <SurfaceLoading label="Loading source changes" />;
  if (drift.error || !drift.data) return <ServiceError message={drift.error || "Source changes did not load."} onRetry={drift.reload} />;
  const view = drift.data;
  if (!view.ready) {
    return (
      <StudioShell current="changes">
        <div className="studio-scroll">
          <EmptyState heading="Nothing to compare yet" reason={view.message} action={<PrereqLink step={3} label="Go to step 4: Legal approves" />} />
        </div>
      </StudioShell>
    );
  }
  return (
    <StudioShell current="changes">
      <StepBar>
        {!view.material && !view.cosmetic ? (
          <ActionButton variant="secondary" busyLabel="Logging the comma…" onClick={() =>
              void guided.run("Logging the comma…", async () => {
                const result = await applyDrift("cosmetic");
                // The comma sits inside Legal's wording, so it goes to Legal; say so in the confirmation too.
                const toLegal = Boolean((result as { drift?: { verbatim_to_legal?: boolean } }).drift?.verbatim_to_legal);
                return toLegal ? { ...result, message: "Sent to Legal: a comma inside Legal wording. The approved version stays live." } : result;
              })
            }>
            Apply the cosmetic edit
          </ActionButton>
        ) : null}
        {!view.material ? (
          <ActionButton busyLabel="Checking the source…" onClick={() => void guided.run("Checking the source…", () => applyDrift("material"))}>
            Apply the material edit
          </ActionButton>
        ) : null}
        {view.material && !view.sent ? (
          <ActionButton busyLabel="Sending to Legal…" onClick={() => void guided.run("Sending to Legal…", () => sendDrift())}>
            Send to Legal
          </ActionButton>
        ) : null}
      </StepBar>
      <div className="studio-scroll">
        <h1 className="tools-title">Source changes</h1>
        <p className="tools-body">
          {view.sent
            ? `The material change went to Legal with the AI's proposed fix. ${view.live_version ? `Version ${view.live_version}` : "The approved version"} stays live until Legal accepts it.`
            : view.verbatim_to_legal
              ? "The Rx education script changed. Each edit is checked against the approved unit before anything goes live."
              : plainDriftMessage(view.message)}
        </p>
        <Illustrative />
        {view.cosmetic && view.verbatim_to_legal ? (
          <div className="hh-card">
            <DecisionMarker kind="pending" role="Legal approver" />
            <p className="tools-body">
              Sent to Legal: a cosmetic change inside Legal wording. Even a comma inside a verbatim span is Legal's decision. The approved version stays live
              until Legal accepts it as no change or returns it.
            </p>
          </div>
        ) : view.cosmetic ? (
          <p className="hh-meta">
            <span className="hh-mark hh-mark--ai">Automatic, no person acted</span> Cosmetic edit logged, nothing flagged.
          </p>
        ) : view.prepared?.cosmetic ? (
          <div className="hh-card">
            <DecisionMarker kind="ai" detail="Prepared cosmetic edit: a comma after supply." />
            <DiffText parts={apiDiff(view.prepared.cosmetic.diff)} />
          </div>
        ) : null}
        {view.material ? (
          <div className="split-2">
            <article className="hh-card">
              <h2 className="tools-label">Live now</h2>
              <DecisionMarker kind="human" role="Legal approver" decision={`Version ${view.live_version} stays live.`} />
              {view.stale ? <StatusBadge variant="stale">Source changed</StatusBadge> : null}
              <p className="tools-body">{view.live_text}</p>
            </article>
            <article className="hh-card">
              <h2 className="tools-label">Proposed wording</h2>
              <DecisionMarker kind="ai" detail={view.summary || "Proposed update from the source edit."} />
              <DecisionMarker kind="pending" role="Legal approver" />
              <DiffText
                parts={
                  view.live_text && view.proposed_text ? wordDiff(view.live_text, view.proposed_text) : apiDiff(view.prepared?.material?.diff)
                }
              />
            </article>
          </div>
        ) : view.prepared?.material ? (
          <div className="hh-card">
            <DecisionMarker kind="ai" detail="Prepared material edit: 30-day supply becomes 31-day supply." />
            <DiffText parts={apiDiff(view.prepared.material.diff)} />
          </div>
        ) : null}
      </div>
    </StudioShell>
  );
}

/** Cache and model-status text is for the team, never for an advocate or member on screen. */
function isEngineNote(note: string) {
  return /cached|live ai|no saved answer|model call/i.test(note);
}

/**
 * Misses arrive with internal check codes and ids ("T4 c6 draft ..."). An audience reads the finding, so the code
 * prefix goes, and the gap id is described in words.
 */
function plainMiss(text: string) {
  const plain = text
    .replace(/^T\d+\s+/, "")
    .replace(/^c\d+ draft contains a figure not in the questions or an approved unit: ([^\s.]+)\.?/, "A gap draft contains a figure, $1, that is not in the questions or in any approved unit.");
  return plain.charAt(0).toUpperCase() + plain.slice(1);
}

function plainDriftMessage(message: string) {
  return /^Cached mode/i.test(message)
    ? "Two source edits are prepared for this demo: a cosmetic comma, and 30-day supply changed to 31-day supply."
    : message;
}

/** The three units the presenter approves by hand come first on both paths. */
const DEMO_FIRST = ["U-RX-EDU-001-09", "U-RX-EDU-001-07", "U-BEN-COST-001-02"];

function demoRank(unitId: string) {
  const index = DEMO_FIRST.indexOf(unitId);
  return index === -1 ? DEMO_FIRST.length : index;
}

const TILE_LABELS: Record<string, string> = {
  hit_at_1: "Right answer first",
  correct_abstain: "Correct no-answers",
  over_abstain: "Wrong no-answers",
  leaks: "Cross-role leaks",
  dedup_precision: "Copy precision",
  dedup_recall: "Copy recall",
};

export function QualityStep() {
  const guided = useGuided();
  const quality = useQuery(`quality:${guided.tick}`, () => getQuality());
  const [tab, setTab] = useState("held");
  if (quality.showSkeleton || (!quality.data && !quality.error)) return <SurfaceLoading label="Loading quality" />;
  if (quality.error || !quality.data) return <ServiceError message={quality.error || "Quality did not load."} onRetry={quality.reload} />;
  const view = quality.data;
  if (!view.scored) {
    return (
      <div>
        <StepBar>
          <ActionButton busyLabel="Scoring…" onClick={() => void guided.run("Scoring…", () => scoreQuality())}>
            Score the golden set
          </ActionButton>
        </StepBar>
        <div className="studio-scroll">
          <h1 className="tools-title">Retrieval quality</h1>
          <p className="tools-body">{view.message}</p>
          <Illustrative />
        </div>
      </div>
    );
  }
  const held = view.golden_table?.held_out || [];
  const misses = view.misses || [];
  return (
    <div data-theme="tools">
      <header className="desk-top">
        <strong className="desk-top__brand">
          Harbor Health <span>Knowledge Insights</span>
        </strong>
        <span className="desk-top__queue">Quality</span>
        <span className="desk-top__user">
          <span className="avatar" aria-hidden="true">KO</span>
          Knowledge owner
        </span>
      </header>
      <div className="studio-scroll">
      <h1 className="tools-title">Retrieval quality</h1>
      <p className="tools-body">
        Held-out questions {view.held_out_pass} of {view.held_out_total} pass. {view.open_conflicts?.length ?? 0} open conflicts blocked
        for Legal. {misses.length} model misses stay visible. Illustrative.
      </p>
      <DecisionMarker kind="pending" role="Product owner with Compliance" />
      <p className="tools-body">
        Launch requires a full verbatim match, zero cross-role leaks, and Compliance sign-off. These gates are proposed.
        This set has {view.scored_questions ?? 0} scored questions, a demonstration set; a launch gate needs about 150 labeled questions.
      </p>
      <div className="tile-row">
        {(view.tiles || []).map((tile) => (
          <MetricTile
            key={tile.key}
            label={TILE_LABELS[tile.key] || tile.label}
            value={tile.display}
            context={`${tile.detail}. ${intervalNote(tile.detail)} Illustrative.`.replace("  ", " ")}
          />
        ))}
      </div>
      {view.verbatim_source?.display ? (
        <p className="tools-body">
          {view.verbatim_source.label}: {view.verbatim_source.display}. {(view.verbatim_source.note || "").replace("the T1 source check", "the source check")}
        </p>
      ) : null}
      <Tabs
        label="Quality detail"
        value={tab}
        onChange={setTab}
        tabs={[
          { id: "held", label: "Held-out questions", count: held.length },
          { id: "failed", label: "What failed", count: misses.length },
          { id: "golden", label: "Golden set", count: view.golden_table?.rows.length || 0 },
        ]}
      />
      {tab === "held" ? (
        <DataTable
          caption="Held-out questions written before any model run"
          rows={held}
          getId={(row) => row.Question}
          columns={[
            { id: "result", header: "Result", render: (row) => <ResultBadge value={row.Result} /> },
            { id: "question", header: "Question", render: (row) => row.Question },
            { id: "role", header: "Role", render: (row) => row.Role },
            { id: "expected", header: "Expected", render: (row) => row.Expected },
            { id: "got", header: "Got", render: (row) => plainResult(row.Got) },
          ]}
        />
      ) : null}
      {tab === "failed" ? (
        <div className="hh-stack">
          {misses.map((miss) => (
            <article className="hh-card" key={miss.miss}>
              <p className="tools-body">{plainMiss(miss.miss)}</p>
              <p className="hh-meta">{miss.next_step}</p>
              {/caregiver/i.test(miss.miss) ? (
                <p className="hh-meta">
                  Known miss, kept visible on purpose. Explore search answers it after a retrieval fix, and this guided score stays as measured.
                </p>
              ) : null}
            </article>
          ))}
        </div>
      ) : null}
      {tab === "golden" ? (
        <DataTable
          caption="Golden set"
          rows={view.golden_table?.rows || []}
          getId={(row) => `${row.Question}-${row.Role}`}
          columns={[
            { id: "result", header: "Result", render: (row) => <ResultBadge value={row.Result} /> },
            { id: "question", header: "Question", render: (row) => row.Question },
            { id: "role", header: "Role", render: (row) => row.Role },
            { id: "expected", header: "Expected", render: (row) => row.Expected },
            { id: "got", header: "Got", render: (row) => plainResult(row.Got) },
          ]}
        />
      ) : null}
      </div>
    </div>
  );
}

/** A deep link into a later step explains what is missing and offers the step that unlocks it. */
function PrereqLink({ step, label }: { step: number; label: string }) {
  const [params] = useSearchParams();
  const next = new URLSearchParams(params);
  next.set("step", String(step));
  return (
    <Link className="hh-btn hh-btn--secondary" to={`/demo?${next.toString()}`}>
      {label}
    </Link>
  );
}

/** One unit's tags, audience and domain, edited by a person before the bulk confirm. Recorded as a human decision. */
function TagEditor({ unit }: { unit: Unit }) {
  const guided = useGuided();
  const [open, setOpen] = useState(false);
  const [tags, setTags] = useState((unit.tags || []).join(", "));
  const [audience, setAudience] = useState((unit.audience || []).join(", ") === "advocate, member" ? "both" : (unit.audience || [])[0] || "advocate");
  const [domain, setDomain] = useState(unit.domain || "");
  const [error, setError] = useState("");
  const id = `tags-${unit.unit_id}`;
  if (!open) {
    return (
      <>
        <button type="button" className="hh-btn hh-btn--tertiary hh-btn--compact" onClick={() => setOpen(true)}>
          Edit tags for this unit
        </button>
      </>
    );
  }
  return (
    <form
      className="tag-editor"
      onSubmit={(event) => {
        event.preventDefault();
        const list = tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean);
        setError("");
        // guided.run saves through the shared runner, so the unit list reloads and shows the edited tags.
        void guided
          .run("Saving tags…", () => setUnitTags(unit.unit_id, { audience, domain: domain.trim(), tags: list }))
          .then((result) => {
            if (!result) {
              setError("The tags did not save. Read the message above, then try again.");
              return;
            }
            setOpen(false);
          });
      }}
    >
      <label className="hh-label" htmlFor={`${id}-tags`}>
        Tags, separated by commas
      </label>
      <input id={`${id}-tags`} className="hh-input" value={tags} onChange={(event) => setTags(event.target.value)} />
      <label className="hh-label" htmlFor={`${id}-aud`}>
        Audience
      </label>
      <select id={`${id}-aud`} className="hh-input" value={audience} onChange={(event) => setAudience(event.target.value)}>
        <option value="advocate">Advocate</option>
        <option value="member">Member</option>
        <option value="both">Both</option>
      </select>
      <label className="hh-label" htmlFor={`${id}-domain`}>
        Domain
      </label>
      <input id={`${id}-domain`} className="hh-input" value={domain} onChange={(event) => setDomain(event.target.value)} />
      <p className="hh-meta">In the guided demo, an audience change that would change who can search the unit is refused, so the measured scores stay comparable.</p>
      {error ? (
        <p className="hh-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="tag-editor__actions">
        <button type="submit" className="hh-btn hh-btn--primary hh-btn--compact">
          Save tags
        </button>
        <button type="button" className="hh-btn hh-btn--tertiary hh-btn--compact" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </form>
  );
}
