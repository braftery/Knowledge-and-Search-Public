import { useState } from "react";
import { acceptLinkReview, extendReview, getChannels, getExpiredUnits, getWorkload, retireReviewUnit } from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { DecisionMarker } from "@/components/decision-marker";
import { EmptyState } from "@/components/empty-state";
import { Field } from "@/components/field";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { showUndoToast } from "@/components/toast";
import { readableDate } from "@/lib/dates";

const MIN_WORDS = 4;
const words = (text: string) => text.trim().split(/\s+/).filter(Boolean).length;

/**
 * Work that reaches Legal outside the approval queue: wording past its review date, which fails closed until Legal
 * extends or retires it, and a linked disclaimer that may need the same change as one Legal just revised.
 * The workload estimate sits beside it so Legal can see the size of the week.
 */
export function LegalReviews() {
  const [tick, setTick] = useState(0);
  const expired = useQuery(`legal-expired:${tick}`, () => getExpiredUnits("explore"));
  const channels = useQuery(`legal-linked:${tick}`, () => getChannels("explore"));
  const workload = useQuery(`legal-workload:${tick}`, () => getWorkload("explore"));
  const [linkDone, setLinkDone] = useState(false);
  const revised = (channels.data?.live?.version ?? 1) > 1;

  return (
    <article className="mail-read mail-read--wide legal-reviews">
      <h1 className="mail-read__subject">Reviews and workload</h1>

      <section aria-labelledby="past-review-h">
        <h2 className="tools-title-sm" id="past-review-h">
          Past the review date
        </h2>
        <p className="tools-body">Wording past its review date leaves search until you extend it or retire it. Advocates see that it is waiting for Legal.</p>
        {expired.loading && !expired.data ? <Skeleton width="100%" height="80px" label="Loading reviews" /> : null}
        {expired.error ? <ServiceError message={expired.error} onRetry={expired.reload} /> : null}
        {expired.data && !expired.data.units.length ? <EmptyState heading="Nothing past its review date" reason="Every approved unit is inside its review window." /> : null}
        {(expired.data?.units ?? []).map((unit) => (
          <ExpiredItem key={unit.unit_id} unitId={unit.unit_id} title={unit.title} text={unit.text} reviewBy={unit.review_by || ""} onDone={() => setTick((n) => n + 1)} />
        ))}
      </section>

      <section aria-labelledby="linked-h">
        <h2 className="tools-title-sm" id="linked-h">
          Linked disclaimer
        </h2>
        {revised && !linkDone ? (
          <div className="hh-card">
            <DecisionMarker kind="pending" role="Legal approver" />
            <p className="tools-body">
              You published a new version of the pricing estimate disclaimer. The linked disclaimer for other supplies and pharmacies may need the same change.
              Both stay approved and live until you decide.
            </p>
            <Button
              variant="secondary"
              onClick={async () => {
                try {
                  await acceptLinkReview("U-RX-EDU-PRICE-ANY");
                  setLinkDone(true);
                  showUndoToast({ message: "Recorded: the linked disclaimer needs no change." });
                } catch (problem) {
                  const message = problem instanceof Error ? problem.message : "That did not save. Try again.";
                  if (/No linked review is waiting/i.test(message)) setLinkDone(true);
                  showUndoToast({ message });
                }
              }}
            >
              No change needed for the linked disclaimer
            </Button>
          </div>
        ) : (
          <p className="hh-meta">{linkDone ? "Recorded: the linked disclaimer needs no change." : "No linked disclaimer is waiting. A review opens when you publish a revision."}</p>
        )}
      </section>

      <section aria-labelledby="workload-h">
        <h2 className="tools-title-sm" id="workload-h">
          This week's workload, illustrative
        </h2>
        {workload.data ? (
          <>
            <dl className="preview-list">
              <div>
                <dt>Waiting for you</dt>
                <dd>{workload.data.queue_count} units</dd>
              </div>
              <div>
                <dt>By risk</dt>
                <dd>
                  {Object.entries(workload.data.by_risk_tier)
                    .map(([tier, count]) => `${count} ${tier}`)
                    .join(", ")}
                </dd>
              </div>
              <div>
                <dt>Estimated time</dt>
                <dd>
                  {workload.data.estimated_minutes} minutes ({workload.data.total_hours} hours)
                </dd>
              </div>
              <div>
                <dt>Who reviews what</dt>
                <dd>
                  {workload.data.proposed_tiering.legal} {workload.data.proposed_tiering.knowledge_ops_batch}
                </dd>
              </div>
            </dl>
            <p className="hh-meta">{workload.data.assumptions} Illustrative, made-up data.</p>
          </>
        ) : workload.error ? (
          <ServiceError message={workload.error} onRetry={workload.reload} />
        ) : (
          <Skeleton width="100%" height="80px" label="Loading the workload" />
        )}
      </section>
    </article>
  );
}

function ExpiredItem({ unitId, title, text, reviewBy, onDone }: { unitId: string; title: string; text: string; reviewBy: string; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const [date, setDate] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function act(kind: "extend" | "retire") {
    if (words(reason) < MIN_WORDS) {
      setError(`Give a reason of at least ${MIN_WORDS} words. It is saved with the decision.`);
      return;
    }
    if (kind === "extend" && !date) {
      setError("Pick the new review date.");
      return;
    }
    setBusy(true);
    try {
      if (kind === "extend") await extendReview(unitId, reason.trim(), date);
      else await retireReviewUnit(unitId, reason.trim());
      showUndoToast({ message: kind === "extend" ? `Extended the review of ${title}.` : `Retired ${title}.` });
      onDone();
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "That did not save. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="hh-card legal-review-item">
      <p className="tools-label">{title}</p>
      <p className="hh-meta">
        <span className="hh-id">{unitId}</span> · Review was due {readableDate(reviewBy) || "on a date not recorded"}
      </p>
      <p className="tools-body">{text}</p>
      <Field
        id={`reason-${unitId}`}
        label="Reason"
        hint="Required. Saved with the decision."
        error={error}
        value={reason}
        onChange={(event) => {
          setReason(event.target.value);
          setError("");
        }}
      />
      <label className="hh-label" htmlFor={`date-${unitId}`}>
        New review date (to extend)
      </label>
      <input id={`date-${unitId}`} className="hh-input history__date" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
      <div className="legal-review-item__actions">
        <Button variant="primary" busy={busy} busyLabel="Saving…" onClick={() => void act("extend")}>
          Extend the review
        </Button>
        <Button variant="secondary" disabled={busy} onClick={() => void act("retire")}>
          Retire this wording
        </Button>
      </div>
    </div>
  );
}
