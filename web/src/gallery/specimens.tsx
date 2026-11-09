import type { ReactNode } from "react";
import { Copy, Flag } from "lucide-react";
import { AnswerCard } from "@/components/answer-card";
import { Button } from "@/components/button";
import { ChatLauncher, ChatPanel } from "@/components/chat";
import { Citation } from "@/components/citation";
import { Cover } from "@/components/cover";
import { DataTable } from "@/components/data-table";
import { DiffLegend, DiffText } from "@/components/diff-view";
import { EmptyState } from "@/components/empty-state";
import { Field } from "@/components/field";
import { Icon } from "@/components/icon";
import { MetricTile } from "@/components/metric-tile";
import { PresenterBar } from "@/components/presenter-bar";
import { RankedBars } from "@/components/ranked-bars";
import { AnswerSkeleton } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Tabs } from "@/components/tabs";
import { ToastView } from "@/components/toast";
import { VerbatimBlock } from "@/components/verbatim-block";
import type { DiffPart } from "@/lib/word-diff";

const pricingDiff: DiffPart[] = [
  { kind: "text", text: "Prices shown are estimates and " },
  { kind: "del", text: "may" },
  { kind: "add", text: "can" },
  { kind: "text", text: " change. Your cost depends on your plan" },
  { kind: "add", text: " and the pharmacy you choose" },
  { kind: "text", text: "." },
];

const keptLine: DiffPart[] = [
  { kind: "text", text: "Tell the caller this call may be recorded for quality." },
];

const retiredLine: DiffPart[] = [
  { kind: "del", text: "Tell the caller this call may be recorded for quality." },
];

export type Specimen = {
  id: string;
  title: string;
  height: number;
  theme: "tools" | "member";
  node: ReactNode;
};

const noop = () => undefined;

export const specimens: Specimen[] = [
  {
    id: "cover",
    title: "Cover",
    height: 400,
    theme: "tools",
    node: <Cover />,
  },
  {
    id: "button",
    title: "Button",
    height: 400,
    theme: "tools",
    node: (
      <div className="hh-stack">
        <div className="hh-row">
          <Button>Approve and publish</Button>
          <Button variant="secondary">Send back to Knowledge Ops</Button>
          <Button variant="tertiary">Open the source document</Button>
        </div>
        <div className="hh-row">
          <Button busy busyLabel="Publishing…">
            Publishing…
          </Button>
          <Button variant="secondary" compact>
            <Icon icon={Copy} />
            Copy wording
          </Button>
        </div>
      </div>
    ),
  },
  {
    id: "status-badge",
    title: "StatusBadge",
    height: 400,
    theme: "tools",
    node: (
      <div className="hh-row">
        <StatusBadge variant="approved">Approved</StatusBadge>
        <StatusBadge variant="review">Waiting for Legal</StatusBadge>
        <StatusBadge variant="blocked">Conflict</StatusBadge>
        <StatusBadge variant="stale">Source changed</StatusBadge>
        <StatusBadge variant="neutral">Draft</StatusBadge>
      </div>
    ),
  },
  {
    id: "tabs",
    title: "Tabs",
    height: 400,
    theme: "tools",
    node: (
      <Tabs
        label="Queues"
        value="legal"
        onChange={noop}
        tabs={[
          { id: "legal", label: "Legal queue", count: 3 },
          { id: "ops", label: "Knowledge Ops approvals", count: 9 },
          { id: "conflicts", label: "Conflicts for Legal", count: 2 },
        ]}
      />
    ),
  },
  {
    id: "field",
    title: "Field",
    height: 400,
    theme: "tools",
    node: (
      <div className="hh-stack">
        <Field id="q" label="Search approved answers" placeholder="For example, mail-order refills…" autoComplete="off" />
        <Field
          id="r"
          multiline
          label="Reason for sending back"
          hint="The author sees this with the unit."
          error="Add a reason. Legal's reason is sent to the author with the unit."
          defaultValue=""
        />
        <Field id="n" label="Note" optional />
      </div>
    ),
  },
  {
    id: "toast",
    title: "Toast",
    height: 400,
    theme: "tools",
    node: <ToastView message="Published version 2 of the pricing disclaimer." onUndo={noop} />,
  },
  {
    id: "verbatim",
    title: "VerbatimBlock",
    height: 400,
    theme: "tools",
    node: (
      <VerbatimBlock text="Prices shown are estimates and can change. Your cost depends on your plan and the pharmacy you choose." />
    ),
  },
  {
    id: "citation",
    title: "Citation",
    height: 400,
    theme: "tools",
    node: (
      <div className="hh-stack">
        <Citation
          audience="internal"
          title="Pricing disclaimer"
          version={2}
          approver="Legal"
          date="Oct 12"
          sourceHref="#source"
        />
        <div data-theme="member" className="hh-m">
          <Citation audience="member" title="drug pricing" date="Oct 12" />
        </div>
      </div>
    ),
  },
  {
    id: "diff",
    title: "DiffView",
    height: 400,
    theme: "tools",
    node: (
      <div className="hh-stack">
        <DiffLegend />
        <DiffText parts={pricingDiff} />
        <div className="hh-cols">
          <div className="hh-card">
            <div className="hh-col__head">
              <strong>Kept</strong>
              <StatusBadge variant="approved">Approved</StatusBadge>
            </div>
            <DiffText parts={keptLine} />
          </div>
          <div className="hh-card">
            <div className="hh-col__head">
              <strong>Retired</strong>
              <StatusBadge variant="neutral">Retired</StatusBadge>
            </div>
            <DiffText parts={retiredLine} />
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "answer-card",
    title: "AnswerCard",
    height: 400,
    theme: "tools",
    node: (
      <AnswerCard
        question="How much will my prescription cost?"
        verbatim
        wording="Prices shown are estimates and can change. Your cost depends on your plan and the pharmacy you choose."
        citation={{ title: "Pricing disclaimer", version: 2, approver: "Legal", date: "Oct 12" }}
      />
    ),
  },
  {
    id: "empty",
    title: "EmptyState",
    height: 432,
    theme: "tools",
    node: (
      <div className="hh-stack">
        <EmptyState
          heading="No approved answer for this question"
          reason="The question was logged for the knowledge team."
          steps={["Tell the member you will follow up.", "Check the plan documents in the member's portal."]}
          action={
            <Button variant="tertiary" compact>
              <Icon icon={Flag} />
              Flag this answer
            </Button>
          }
        />
        <EmptyState
          heading="All caught up"
          reason="Nothing is waiting for Legal. New items arrive by email."
          action={
            <Button variant="secondary" compact>
              Open the library
            </Button>
          }
        />
      </div>
    ),
  },
  {
    id: "skeleton",
    title: "Skeleton",
    height: 400,
    theme: "tools",
    node: <AnswerSkeleton />,
  },
  {
    id: "table",
    title: "DataTable",
    height: 400,
    theme: "tools",
    node: (
      <DataTable
        caption="Units"
        selectedId="PRC-001"
        rows={[
          { id: "PRC-001", title: "Pricing disclaimer", status: "approved" as const, kb: "Pharmacy, Insurance", review: "Mar 1" },
          { id: "PRV-004", title: "Unverified caller rule", status: "review" as const, kb: "Insurance", review: "Feb 15" },
        ]}
        getId={(row) => row.id}
        columns={[
          {
            id: "unit",
            header: "Unit",
            render: (row) => (
              <>
                {row.title}
                <div className="hh-id">{row.id}</div>
              </>
            ),
          },
          {
            id: "status",
            header: "Status",
            render: (row) =>
              row.status === "approved" ? (
                <StatusBadge variant="approved">Approved</StatusBadge>
              ) : (
                <StatusBadge variant="review">Waiting for Legal</StatusBadge>
              ),
          },
          { id: "kb", header: "Knowledge base", render: (row) => row.kb },
          { id: "review", header: "Review by", numeric: true, render: (row) => row.review },
        ]}
      />
    ),
  },
  {
    id: "metric",
    title: "MetricTile",
    height: 400,
    theme: "tools",
    node: (
      <div className="hh-row" style={{ alignItems: "stretch" }}>
        <MetricTile label="Right answer first" value="18 of 20" context="golden questions, illustrative" />
        <MetricTile label="Held-out questions" value="4 of 5" context="pass, written before tuning" />
      </div>
    ),
  },
  {
    id: "ranked",
    title: "RankedBars",
    height: 400,
    theme: "tools",
    node: (
      <div style={{ maxWidth: 640 }}>
        <RankedBars
          rows={[
            { label: "Mail-order refill timing", detail: "Pharmacy, Member", count: 14 },
            { label: "Prior authorization status", detail: "Insurance", count: 8 },
            { label: "Out-of-network costs", detail: "Insurance, Member", count: 5 },
          ]}
        />
      </div>
    ),
  },
  {
    id: "presenter",
    title: "PresenterBar",
    height: 400,
    theme: "tools",
    node: (
      <PresenterBar
        step={3}
        total={5}
        title="Legal approves"
        onBack={noop}
        onNext={noop}
        onJumpShort={noop}
        onReset={noop}
      />
    ),
  },
  {
    id: "launcher",
    title: "ChatLauncher",
    height: 400,
    theme: "member",
    node: <ChatLauncher open={false} onToggle={noop} />,
  },
  {
    id: "chat",
    title: "ChatPanel",
    height: 740,
    theme: "member",
    node: (
      <ChatPanel
        autoFocus={false}
        onClose={noop}
        onSend={noop}
        items={[
          {
            kind: "message",
            id: "hi",
            from: "bot",
            text: "Hi, I can answer questions about your Harbor Health plan. What can I help with?",
          },
          { kind: "chips", id: "topics", labels: ["Drug costs", "Mail-order refills", "Find a pharmacy"] },
          { kind: "message", id: "me", from: "member", text: "How much will my prescription cost?" },
          {
            kind: "message",
            id: "ans",
            from: "bot",
            text: "Prices shown are estimates and can change. Your cost depends on your plan and the pharmacy you choose.",
            citation: { title: "drug pricing", date: "Oct 12" },
          },
          { kind: "help", id: "help", question: "", unitId: "" },
        ]}
      />
    ),
  },
];

export function SpecimenFrame({ specimen }: { specimen: Specimen }) {
  const padClass = specimen.theme === "member" ? "hh-m hh-pad" : "hh hh-pad";
  return (
    <section
      id={specimen.id}
      data-theme={specimen.theme}
      aria-label={specimen.title}
      style={{
        width: 960,
        height: specimen.height,
        background: "var(--surface)",
        overflow: "hidden",
      }}
    >
      {specimen.id === "cover" ? specimen.node : <div className={padClass}>{specimen.node}</div>}
    </section>
  );
}
