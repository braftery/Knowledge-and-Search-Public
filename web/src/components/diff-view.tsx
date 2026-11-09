import { StatusBadge, type StatusVariant } from "@/components/status-badge";
import { addedOnly, wordDiff, type DiffPart } from "@/lib/word-diff";

export function DiffLegend() {
  return (
    <div className="hh-legend">
      <span>
        <span className="hh-del">Removed</span> struck through
      </span>
      <span>
        <span className="hh-add">Added</span> underlined
      </span>
    </div>
  );
}

export function DiffText({ parts }: { parts: DiffPart[] }) {
  return (
    <p className="hh-diff" style={{ margin: 0 }}>
      {parts.map((part, index) => {
        if (part.kind === "text") return <span key={index}>{part.text}</span>;
        const className = part.kind === "del" ? "hh-del" : "hh-add";
        return (
          <span key={index} className={className}>
            {part.text}
          </span>
        );
      })}
    </p>
  );
}

type Column = {
  heading: string;
  badge: string;
  variant: StatusVariant;
  parts: DiffPart[];
};

type DiffViewProps = {
  mode?: "inline" | "columns" | "added-only";
  oldText?: string;
  newText?: string;
  parts?: DiffPart[];
  reason?: string;
  kept?: Column;
  retired?: Column;
  legend?: boolean;
};

export function DiffView({
  mode = "inline",
  oldText = "",
  newText = "",
  parts,
  reason,
  kept,
  retired,
  legend = true,
}: DiffViewProps) {
  const inline = parts ?? (mode === "added-only" ? addedOnly(oldText, newText) : wordDiff(oldText, newText));

  return (
    <div className="hh-stack">
      {legend ? <DiffLegend /> : null}
      {mode !== "columns" ? <DiffText parts={inline} /> : null}
      {mode === "columns" && kept && retired ? (
        <>
          {reason ? <p className="tools-body" style={{ margin: 0 }}>{reason}</p> : null}
          <div className="hh-cols">
            <DiffColumn column={kept} />
            <DiffColumn column={retired} />
          </div>
        </>
      ) : null}
    </div>
  );
}

function DiffColumn({ column }: { column: Column }) {
  return (
    <div className="hh-card">
      <div className="hh-col__head">
        <strong>{column.heading}</strong>
        <StatusBadge variant={column.variant}>{column.badge}</StatusBadge>
      </div>
      <DiffText parts={column.parts} />
    </div>
  );
}

