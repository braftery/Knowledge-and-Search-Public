import { useState } from "react";
import { actOnGap, getGaps, getInsights, getUnits, undoWorld, type Gap } from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { DecisionMarker } from "@/components/decision-marker";
import { EmptyState } from "@/components/empty-state";
import { Field } from "@/components/field";
import { MetricTile } from "@/components/metric-tile";
import { RankedBars } from "@/components/ranked-bars";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { showUndoToast } from "@/components/toast";
import { readableDate } from "@/lib/dates";
import { intervalNote } from "@/lib/stats";

const TILE_LABELS: Record<string, string> = {
  hit_at_1: "Right answer first",
  over_abstain: "Wrong no-answers",
  leaks: "Cross-role leaks",
};

function plural(count: number, one: string, many: string) {
  return `${count === 0 ? "no" : count} ${count === 1 ? one : many}`;
}

export function InsightsPage() {
  const [tick, setTick] = useState(0);
  const insights = useQuery(`insights:${tick}`, () => getInsights());
  const allGaps = useQuery(`insights-gaps:${tick}`, () => getGaps("explore"));
  const unitList = useQuery("insights-units", () => getUnits("", "explore"));
  const titles = new Map((unitList.data?.units ?? []).map((unit) => [unit.unit_id, unit.title.replace(/\s*\((Legal|Legal verbatim)\)\s*$/, "")]));
  const [picked, setPicked] = useState<string | null>(null);

  if (insights.loading && !insights.data) {
    return (
      <div className="ins">
        <InsightsHeader />
        <div className="ins-body">
          <Skeleton width="420px" height="28px" label="Loading insights" />
          <Skeleton width="100%" height="140px" />
        </div>
      </div>
    );
  }
  if (insights.error || !insights.data) {
    return (
      <div className="ins">
        <InsightsHeader />
        <div className="ins-body">
          <ServiceError message={insights.error || "Insights did not load."} onRetry={insights.reload} />
        </div>
      </div>
    );
  }
  const data = insights.data;
  const open = data.top_gaps.filter((gap) => gap.status === "proposed");
  const selected = open.find((gap) => gap.id === picked) ?? open[0] ?? null;
  const flags = data.feedback.by_kind ?? [];
  const closed = (allGaps.data?.gaps ?? []).filter((gap) => gap.status === "closed");
  const answeredPast = closed.reduce((sum, gap) => sum + gap.search_count, 0);
  const top = [...open].sort((a, b) => b.search_count - a.search_count)[0];
  const wrapups = data.wrapups;
  const acks = data.acknowledgements ?? [];
  const mostFlagged = (data.feedback as { most_flagged?: Array<{ unit_id: string; count: number }> }).most_flagged ?? [];

  return (
    <div className="ins">
      <InsightsHeader />
      <div className="ins-body">
        <section className="ins-digest" aria-label="This week">
          <p className="tools-overline">This week</p>
          <p className="ins-digest__text">
            {top ? (
              <>
                &ldquo;{top.cluster}&rdquo; was asked {plural(top.search_count, "time", "times")} with no approved answer, so each of those
                conversations ended without approved wording.{" "}
              </>
            ) : null}
            {plural(data.open_gaps, "unanswered question cluster", "unanswered question clusters")} in all,{" "}
            {plural(data.drift_waiting, "source change", "source changes")} waiting for Legal, and{" "}
            {plural(data.expired_count, "unit", "units")} past the review date.
          </p>
          {closed.length ? (
            <p className="ins-digest__win">
              {plural(closed.length, "gap", "gaps")} closed, covering {plural(answeredPast, "question", "questions")} that had no answer before.
            </p>
          ) : null}
        </section>

        <section className="ins-tiles" aria-label="Retrieval quality">
          {data.tiles.map((tile) => (
            <MetricTile key={tile.key} label={TILE_LABELS[tile.key] ?? tile.label} value={tile.display} context={`${tile.detail}.${intervalNote(tile.detail) ? ` ${intervalNote(tile.detail)}` : ""}`} />
          ))}
          <MetricTile
            label="Held-out questions"
            value={`${data.held_out.pass} of ${data.held_out.total}`}
            context="Pass. Written before any tuning."
          />
        </section>
        <p className="hh-meta ins-tiles__note">Scores for this sandbox with its current approvals. Illustrative.</p>

        <div className="ins-grid">
          <section className="ins-panel" aria-labelledby="gaps-h">
            <div className="ins-panel__head">
              <h2 id="gaps-h" className="tools-title-sm">
                Top unanswered questions
              </h2>
              <span className="hh-meta">Ranked by demand. Counts are illustrative.</span>
            </div>
            {open.length === 0 ? (
              <EmptyState heading="No open gaps" reason="Every logged question has a decision." />
            ) : (
              <ul className="ins-gaps">
                {[...open]
                  .sort((a, b) => b.search_count - a.search_count)
                  .map((gap) => {
                    const top = Math.max(...open.map((item) => item.search_count), 1);
                    return (
                      <li key={gap.id}>
                        <button
                          type="button"
                          className="ins-gap"
                          aria-current={selected?.id === gap.id ? "true" : undefined}
                          onClick={() => setPicked(gap.id)}
                        >
                          <span className="ins-gap__text">
                            <strong>{gap.cluster}</strong>
                            <span className="hh-meta">
                              {gap.roles.join(", ")}
                              {gap.findability ? " · Search miss: an approved unit exists" : ""}
                            </span>
                          </span>
                          <span className="hh-rank__track" aria-hidden="true">
                            <span className="hh-rank__bar" style={{ width: `${Math.max(6, Math.round((100 * gap.search_count) / top))}%`, display: "block" }} />
                          </span>
                          <span className="hh-rank__n">{gap.search_count}</span>
                        </button>
                      </li>
                    );
                  })}
              </ul>
            )}
          </section>

          <aside className="ins-side">
            {(data.process_gaps ?? []).length ? (
              <section className="ins-panel" aria-labelledby="process-h">
                <h2 id="process-h" className="tools-title-sm">
                  The business has no answer yet
                </h2>
                <p className="hh-meta">
                  Knowledge Ops asked the expert who owns the fact, and there is no policy. No unit can be written until the business decides. Advocates
                  keep the no-answer with a follow-up.
                </p>
                <ul className="ins-process">
                  {(data.process_gaps ?? []).map((gap) => (
                    <li key={gap.id}>
                      <strong>{gap.cluster}</strong>
                      {gap.reason ? <span className="hh-meta"> {gap.reason}</span> : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {selected ? (
              <GapDecision key={selected.id} gap={selected} onDone={() => setTick((value) => value + 1)} />
            ) : null}
            {closed.length ? (
              <section className="ins-panel" aria-labelledby="closed-h">
                <h2 id="closed-h" className="tools-title-sm">
                  Closed this week
                </h2>
                <ul className="ins-closed">
                  {closed.map((gap) => (
                    <li key={gap.id}>
                      <StatusBadge variant="approved">Answered</StatusBadge>
                      <span>
                        <strong>{gap.draft_title || gap.cluster}</strong>
                        <span className="hh-meta">
                          {" "}
                          {gap.unit_id} · {plural(gap.search_count, "past question", "past questions")} now answered · {gap.roles.join(", ")} told in
                          their desktop
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {wrapups || acks.length ? (
              <section className="ins-panel" aria-labelledby="calls-h">
                <h2 id="calls-h" className="tools-title-sm">
                  On the calls
                </h2>
                {wrapups ? (
                  <p className="tools-body">
                    {wrapups.verbatim_required
                      ? `Verbatim read confirmed on ${wrapups.verbatim_confirmed} of ${plural(wrapups.verbatim_required, "call", "calls")} that showed Legal wording.`
                      : "No wrapped-up call has shown Legal wording yet."}{" "}
                    {wrapups.follow_ups ? `${plural(wrapups.follow_ups, "follow-up", "follow-ups")} open.` : ""}
                  </p>
                ) : null}
                {acks.map((ack) => (
                  <p className="tools-body" key={`${ack.unit_id}-${ack.version}`}>
                    <strong>
                      {ack.title}, version {ack.version}
                    </strong>
                    : {ack.acknowledged_by.length ? `read by ${ack.acknowledged_by.join(", ")}` : "not yet read by any advocate role"}
                    {ack.pending.length ? `; waiting on ${ack.pending.join(", ")}` : ""}.
                  </p>
                ))}
              </section>
            ) : null}
            <section className="ins-panel" aria-labelledby="attn-h">
              <h2 id="attn-h" className="tools-title-sm">
                Needs attention
              </h2>
              {data.drift.waiting ? (
                <div className="ins-attn">
                  <StatusBadge variant="stale">Source changed</StatusBadge>
                  <p className="tools-body">{data.drift.summary || "A source change is waiting for Legal. The approved version stays live until Legal decides."}</p>
                </div>
              ) : (
                <p className="hh-meta">No source change is waiting for Legal.</p>
              )}
              {data.expired_units.map((unit) => (
                <div className="ins-attn" key={unit.unit_id}>
                  <StatusBadge variant="stale">Past review date</StatusBadge>
                  <p className="tools-body">
                    <strong>{unit.title}</strong> was due for review on {readableDate((unit as { review_by?: string }).review_by) || "an earlier date"}. It stays live and is
                    flagged for its owner.
                  </p>
                </div>
              ))}
            </section>
          </aside>
        </div>

        <div className="ins-grid">
          <section className="ins-panel" aria-labelledby="flags-h">
            <div className="ins-panel__head">
              <h2 id="flags-h" className="tools-title-sm">
                What advocates and channels flagged this week
              </h2>
              <span className="hh-meta">Content issues go to the author; findability issues go to the product backlog.</span>
            </div>
            {flags.length ? (
              <RankedBars rows={flags.map((item) => ({ label: item.label, count: item.count }))} maxVisible={8} />
            ) : (
              <p className="hh-meta">Nothing flagged this week.</p>
            )}
          </section>
          <section className="ins-panel" aria-labelledby="mf-h">
            <h2 id="mf-h" className="tools-title-sm">
              Most-flagged units
            </h2>
            {mostFlagged.length ? (
              <ul className="ins-flagged">
                {mostFlagged.slice(0, 4).map((item) => (
                  <li key={item.unit_id}>
                    <span>
                      <span className="ins-flagged__title">{titles.get(item.unit_id) ?? item.unit_id}</span>
                      <span className="hh-id"> {item.unit_id}</span>
                    </span>
                    <span className="hh-rank__n">{item.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="hh-meta">No unit has been flagged this week.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function InsightsHeader() {
  return (
    <header className="desk-top">
      <h1 className="desk-top__brand">
        Harbor Health <span>Knowledge Insights</span>
      </h1>
      <span className="desk-top__queue">Weekly view</span>
      <span className="desk-top__user">
        <span className="avatar" aria-hidden="true">
          KO
        </span>
        Knowledge owner
      </span>
    </header>
  );
}

function GapDecision({ gap, onDone }: { gap: Gap; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const suggested = `Asked ${gap.search_count} ${gap.search_count === 1 ? "time" : "times"} with no approved answer.`;
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const placeholders = (gap.draft_text.match(/\[[^\]]+\]/g) || []).length;

  async function decide(action: "write" | "fix_process" | "dismiss", label: string) {
    if (!reason.trim()) {
      setError("Add a reason. It is saved with the decision and shown to the author.");
      return;
    }
    setBusy(label);
    setError("");
    try {
      const result = await actOnGap(gap.id, action, reason.trim(), "explore");
      showUndoToast({
        message: result.message,
        onUndo: result.undo?.available ? () => void undoWorld("explore").then(onDone) : undefined,
      });
      onDone();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "That did not save. Try again.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="ins-panel ins-decide" aria-labelledby="decide-h">
      <div className="ins-panel__head">
        <h2 id="decide-h" className="tools-title-sm">
          {gap.cluster}
        </h2>
        <DecisionMarker kind="pending" role="Knowledge owner" />
      </div>
      <p className="tools-body">
        The AI drafted &ldquo;{gap.draft_title}&rdquo; with {plural(placeholders, "placeholder", "placeholders")} for the author to fill from an
        approved source.
      </p>
      <Field
        id={`reason-${gap.id}`}
        label="Reason for your decision"
        hint="Required. Saved with the decision."
        value={reason}
        suggestion={suggested}
        onUseSuggestion={() => {
          setReason(suggested);
          setError("");
        }}
        error={error || undefined}
        onChange={(event) => {
          setReason(event.target.value);
          setError("");
        }}
      />
      <div className="work-actions">
        <Button busy={busy === "Sending…"} busyLabel="Sending…" disabled={Boolean(busy)} onClick={() => void decide("write", "Sending…")}>
          Send draft to author
        </Button>
        <Button variant="secondary" disabled={Boolean(busy)} busy={busy === "Saving…"} busyLabel="Saving…" onClick={() => void decide("fix_process", "Saving…")}>
          Fix the process instead
        </Button>
        <Button variant="tertiary" disabled={Boolean(busy)} onClick={() => void decide("dismiss", "Dismissing…")}>
          Dismiss
        </Button>
      </div>
    </section>
  );
}
