import { useEffect, useId, useRef, useState } from "react";
import type { ConflictPlan, Unit, World } from "@/api/guided";
import { SourceDocument } from "@/pages/legal/SourceDocument";
import { Button } from "@/components/button";
import { DecisionMarker } from "@/components/decision-marker";
import { DiffLegend, DiffText } from "@/components/diff-view";
import { Field } from "@/components/field";
import { RoutingNote } from "@/components/routing-note";
import { StatusBadge } from "@/components/status-badge";
import { VerbatimBlock } from "@/components/verbatim-block";
import { apiDiff, channelLabel, joinLabels } from "@/lib/labels";
import { readableDate } from "@/lib/dates";

export function ApprovalReview({
  unit,
  position,
  total,
  approveLabel,
  busyLabel,
  approverRole,
  onApprove,
  onDecline,
  busy,
  world = "guided",
}: {
  unit: Unit;
  position: number;
  total: number;
  approveLabel: string;
  busyLabel: string;
  approverRole: string;
  onApprove: () => void;
  onDecline?: (reason: string) => void;
  busy: string | null;
  /** Which world's document store to read the original document from. */
  world?: World;
}) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const preview = unit.if_you_approve;
  const verbatim = unit.type === "verbatim";
  const matches = verbatim && !unit.source_mismatch && !unit.verbatim_altered;
  const blocked = Boolean(unit.source_mismatch || unit.verbatim_altered);

  useEffect(() => {
    setOpen(false);
    setReason("");
    setError("");
    titleRef.current?.focus();
  }, [unit.unit_id]);

  return (
    <section className="review" aria-label="Legal review">
      <header className="legal-top">
        <h1 className="desk-top__brand">
          Harbor Health <span>Single Source · Legal review</span>
        </h1>
        <span className="desk-top__queue">
          Item {position} of {total}
        </span>
      </header>
      <div className="legal-bar">
        <DecisionMarker kind="pending" role={approverRole} />
        <Button
          variant="primary"
          busy={busy === busyLabel}
          busyLabel={busyLabel}
          disabled={blocked || Boolean(busy)}
          onClick={onApprove}
        >
          {approveLabel}
        </Button>
        {onDecline ? (
          <Button variant="secondary" disabled={Boolean(busy)} onClick={() => setOpen((value) => !value)}>
            Send back to Knowledge Ops
          </Button>
        ) : null}
      </div>
      {open && onDecline ? (
        <SendBack
          reason={reason}
          error={error}
          busy={busy === "Sending back…"}
          onChange={(value) => {
            setReason(value);
            setError("");
          }}
          onSubmit={() => {
            if (!reason.trim()) {
              setError("Add a reason before sending this back. The author sees the reason.");
              return;
            }
            if (wordCount(reason) < MIN_REASON_WORDS) {
              setError(`Tell the author what to change, in at least ${MIN_REASON_WORDS} words.`);
              return;
            }
            onDecline(reason.trim());
          }}
        />
      ) : null}
      <div className="studio-scroll">
        <div className="item-head">
          <div className="item-head__text">
            <h2 className="tools-title" tabIndex={-1} ref={titleRef}>
              {unit.title}
            </h2>
            <p className="item-head__meta">
              <span className="hh-id">{unit.unit_id}</span>
              {unit.document_name || unit.source_doc ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{unit.document_name || unit.source_doc}</span>
                </>
              ) : unit.unit_id.startsWith("U-GAP-") ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span>Written by the author to close an unanswered question</span>
                </>
              ) : null}
            </p>
          </div>
          <div className="item-head__badges">
            <StatusBadge variant="neutral">{typeLabel(unit.type)}</StatusBadge>
            {verbatim ? (
              <StatusBadge variant={matches ? "approved" : "blocked"}>
                {matches ? "Verbatim matches source" : "Verbatim does not match source"}
              </StatusBadge>
            ) : null}
          </div>
        </div>
        <RoutingNote reason={unit.routing_reason} heading="Why this came to you" />
        <section className="preview-panel" aria-label="If you approve this unit">
          <h3 className="tools-title-sm">If you approve this unit</h3>
          <dl className="preview-list">
            <div>
              <dt>Who can search it</dt>
              <dd>{preview?.searchable_by?.length ? preview.searchable_by.join(", ") : "Not recorded"}</dd>
            </div>
            <div>
              <dt>Channels</dt>
              <dd>{preview?.appears_in?.length ? joinLabels(preview.appears_in, channelLabel) : "Not recorded"}</dd>
            </div>
            <div>
              <dt>Replaces</dt>
              <dd>{(preview?.replaces || "No other wording").replace(/\b1 other wordings\b/, "1 other wording")}</dd>
            </div>
            <div>
              <dt>Applies to</dt>
              <dd>{preview?.applies_to || unit.applicability || "Not recorded"}</dd>
            </div>
            <div>
              <dt>Approved by</dt>
              <dd>{preview?.approved_by || approverRole}</dd>
            </div>
            <div>
              <dt>Effective</dt>
              <dd>{readableDate(unit.effective_date) || "When you approve"}</dd>
            </div>
          </dl>
        </section>
        <div className="approve-grid">
          <div>
            <h3 className="tools-label">Wording you are approving</h3>
            {verbatim ? <VerbatimBlock text={unit.text} /> : <p className="tools-body approve-wording">{unit.text}</p>}
            {unit.member_text ? (
              <>
                <h3 className="tools-label">Member wording</h3>
                <p className="tools-body approve-wording">{unit.member_text}</p>
              </>
            ) : null}
          </div>
          <div>
            <h3 className="tools-label">Source passage it came from</h3>
            <blockquote className="source-quote">{unit.source_quote || "No source passage is recorded."}</blockquote>
            <p className="hh-meta">{unit.document_name || unit.source_doc}</p>
          </div>
        </div>
        {unit.source_doc ? <SourceDocument docId={unit.source_doc} quote={unit.source_quote || ""} world={world} /> : null}
      </div>
    </section>
  );
}

function SendBack({
  reason,
  error,
  busy,
  onChange,
  onSubmit,
}: {
  reason: string;
  error: string;
  busy: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}) {
  const id = useId();
  return (
    <form
      className="send-back"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <Field
        id={`${id}-reason`}
        label="Reason"
        hint="Required. The author sees this with the unit."
        error={error}
        value={reason}
        onChange={(event) => onChange(event.target.value)}
      />
      <Button variant="primary" type="submit" busy={busy} busyLabel="Sending back…">
        Send back to Knowledge Ops
      </Button>
    </form>
  );
}

export function ConflictColumns({
  plan,
  busy,
  onResolve,
  autoFocus = false,
}: {
  plan: ConflictPlan;
  busy: string | null;
  onResolve: (reason: string) => void;
  autoFocus?: boolean;
}) {
  const id = useId();
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const titleRef = useRef<HTMLHeadingElement>(null);
  const wasOpen = useRef(plan.open);

  useEffect(() => {
    setReason("");
    setError("");
    if (autoFocus || (wasOpen.current && !plan.open)) titleRef.current?.focus();
    wasOpen.current = plan.open;
  }, [plan.id, plan.open, plan.reason_suggestion, autoFocus]);

  if (!plan.open) {
    return (
      <article className="hh-card">
        <h3 className="tools-title-sm" tabIndex={-1} ref={titleRef}>
          {plan.label}
        </h3>
        <DecisionMarker
          kind="human"
          role="Legal approver"
          decision={`Kept the ${plan.chosen_doc} wording and retired the other. ${plan.recorded_reason}`}
        />
      </article>
    );
  }

  return (
    <article className="hh-card conflict-card">
      <div className="hh-card__head">
        <h3 className="tools-title-sm" tabIndex={-1} ref={titleRef}>
          {plan.label}
        </h3>
        <StatusBadge variant="blocked">Blocked</StatusBadge>
      </div>
      <DecisionMarker kind="ai" detail={plan.reason_suggestion} />
      <DecisionMarker kind="pending" role="Legal approver" />
      <DiffLegend />
      {plan.comparisons.map((item) => (
        <div className="conflict-pair" key={item.unit_id}>
          <div className="approve-grid">
            <div className="hh-card">
              <div className="hh-card__head">
                <strong>Kept wording</strong>
                <StatusBadge variant="review">Proposed keep</StatusBadge>
              </div>
              <p className="tools-label">{plan.chosen_title}</p>
              <p className="hh-meta">{plan.chosen_doc}</p>
              <DiffText parts={apiDiff(item.diff).filter((part) => part.kind !== "add")} />
            </div>
            <div className="hh-card">
              <div className="hh-card__head">
                <strong>Retired wording</strong>
                <StatusBadge variant="blocked">Would retire</StatusBadge>
              </div>
              <p className="tools-label">{item.title}</p>
              <p className="hh-meta">{item.doc}</p>
              <DiffText parts={apiDiff(item.diff).filter((part) => part.kind !== "del")} />
            </div>
          </div>
        </div>
      ))}
      <form
        className="send-back"
        onSubmit={(event) => {
          event.preventDefault();
          if (!reason.trim()) {
            setError("Add a reason. Legal's reason is saved with the decision.");
            return;
          }
          if (wordCount(reason) < MIN_REASON_WORDS) {
            setError(`Say why this wording is kept, in at least ${MIN_REASON_WORDS} words. The reason goes into the audit record.`);
            return;
          }
          onResolve(reason.trim());
        }}
      >
        <Field
          id={`${id}-conflict`}
          label="Reason"
          hint="Required. Both versions stay blocked until Legal records a reason. Check any AI suggestion against both wordings first; the reason is saved as you leave it."
          error={error}
          value={reason}
          suggestion={plan.reason_suggestion || undefined}
          onUseSuggestion={() => {
            setReason(plan.reason_suggestion || "");
            setError("");
          }}
          onChange={(event) => {
            setReason(event.target.value);
            setError("");
          }}
        />
        <Button
          variant={plan.resolve_in_demo ? "primary" : "secondary"}
          type="submit"
          busy={busy === `Resolving ${plan.label}…`}
          busyLabel={`Resolving ${plan.label}…`}
          disabled={Boolean(busy)}
        >
          {plan.resolve_in_demo ? "Keep the v1 wording and retire the other" : `Keep the ${plan.chosen_doc} wording`}
        </Button>
      </form>
    </article>
  );
}

/** A recorded reason has to say something an auditor can read later; "ok" does not. */
const MIN_REASON_WORDS = 4;

function wordCount(text: string) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function typeLabel(type: string) {
  const labels: Record<string, string> = { verbatim: "Verbatim", policy: "Policy", procedure: "Procedure", faq: "FAQ" };
  return labels[type] || (type ? type.charAt(0).toUpperCase() + type.slice(1) : "Unit");
}
