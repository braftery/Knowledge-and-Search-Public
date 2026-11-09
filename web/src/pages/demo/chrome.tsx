import type { ReactNode } from "react";
import { Button } from "@/components/button";
import { InlineProblem } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { useGuided, useGuidedOptional } from "@/pages/demo/guided-context";

export function StepBar({ children }: { children: ReactNode }) {
  // Outside the guided demo (a screen reused in Explore) there are no step actions to show.
  const guided = useGuidedOptional();
  if (!guided) return null;
  return (
    <div className="step-bar">
      <div className="step-actions">{children}</div>
      {guided.problem ? <InlineProblem message={guided.problem} /> : null}
    </div>
  );
}

export function SurfaceLoading({ label }: { label: string }) {
  return (
    <div className="studio-scroll" aria-busy="true">
      <Skeleton width="280px" height="28px" label={label} />
      <Skeleton width="100%" height="160px" />
    </div>
  );
}

export function Illustrative({ children }: { children?: ReactNode }) {
  void children;
  return null;
}

const RAIL = [
  { id: "work", label: "My work" },
  { id: "sources", label: "Sources" },
  { id: "copies", label: "Copies and conflicts" },
  { id: "library", label: "Library" },
  { id: "gaps", label: "Gaps" },
  { id: "changes", label: "Source changes" },
] as const;

export type StudioSection = (typeof RAIL)[number]["id"];

export function StudioShell({
  current,
  counts,
  children,
  onNavigate,
  sections,
}: {
  current: StudioSection;
  counts?: Partial<Record<StudioSection, number>>;
  children: ReactNode;
  /** When set, the rail is real navigation limited to `sections`. In the guided demo it only marks the step's place. */
  onNavigate?: (section: StudioSection) => void;
  sections?: StudioSection[];
}) {
  const items = sections ? RAIL.filter((item) => sections.includes(item.id)) : RAIL;
  return (
    <div className="studio">
      <nav className="studio-rail" aria-label="Single Source">
        <p className="studio-rail__brand">Harbor Health</p>
        <p className="studio-rail__product">Single Source</p>
        {items.map((item) =>
          onNavigate ? (
            <button
              key={item.id}
              type="button"
              className="studio-rail__item studio-rail__item--link"
              aria-current={item.id === current ? "page" : undefined}
              onClick={() => onNavigate(item.id)}
            >
              {item.label}
              {typeof counts?.[item.id] === "number" ? <span className="hh-count">{counts[item.id]}</span> : null}
            </button>
          ) : (
            <span key={item.id} className="studio-rail__item" aria-current={item.id === current ? "page" : undefined}>
              {item.label}
              {typeof counts?.[item.id] === "number" ? <span className="hh-count">{counts[item.id]}</span> : null}
            </span>
          ),
        )}
      </nav>
      <div className="studio-main">{children}</div>
    </div>
  );
}

function SourcePlain({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <>
      {lines.map((line, index) => {
        const heading = /^(#{1,3})\s+(.*)$/.exec(line);
        if (heading) {
          const Tag = heading[1].length === 1 ? "h2" : "h3";
          return (
            <Tag key={index} className="source-h">
              {heading[2]}
            </Tag>
          );
        }
        const end = index < lines.length - 1 ? "\n" : "";
        // Light rendering for real documents: bold question lines, bullets, and table rows. Highlighted passages are never touched.
        if (/^\|[-\s|]+\|$/.test(line)) return null;
        const row = /^\|(.*)\|$/.exec(line);
        if (row) {
          return (
            <span key={index} className="source-row">
              {row[1].split("|").map((cell, cellIndex) => (
                <span key={cellIndex} className="source-cell">
                  {cell.trim()}
                </span>
              ))}
              {end}
            </span>
          );
        }
        const bold = /^\*\*(.+)\*\*$/.exec(line);
        if (bold) {
          return (
            <span key={index}>
              <strong>{bold[1]}</strong>
              {end}
            </span>
          );
        }
        const bullet = /^- (.*)$/.exec(line);
        return (
          <span key={index}>
            {bullet ? `\u2022 ${bullet[1]}` : line}
            {end}
          </span>
        );
      })}
    </>
  );
}

type Quote = { number: number; quote: string };

export function NumberedSource({ body, quotes, active, onPick }: { body: string; quotes: Quote[]; active?: number; onPick?: (number: number) => void }) {
  const ranges: Array<{ start: number; end: number; number: number }> = [];
  const ordered = [...quotes].filter((item) => item.quote).sort((a, b) => b.quote.length - a.quote.length);
  for (const item of ordered) {
    const start = body.indexOf(item.quote);
    if (start < 0) continue;
    const end = start + item.quote.length;
    if (ranges.some((range) => start < range.end && end > range.start)) continue;
    ranges.push({ start, end, number: item.number });
  }
  ranges.sort((a, b) => a.start - b.start);

  const nodes: ReactNode[] = [];
  let cursor = 0;
  ranges.forEach((range, index) => {
    if (range.start > cursor) nodes.push(<SourcePlain key={`t-${index}`} text={body.slice(cursor, range.start)} />);
    nodes.push(
      <mark
        key={`m-${range.number}`}
        className={`source-mark${active === range.number ? " source-mark--active" : ""}`}
        id={`src-${range.number}`}
        aria-current={active === range.number ? "true" : undefined}
      >
        {onPick ? (
          <button type="button" className="source-num source-num--button" aria-label={`Unit ${range.number}`} onClick={() => onPick(range.number)}>
            {range.number}
          </button>
        ) : (
          <span className="source-num">{range.number}</span>
        )}
        {body.slice(range.start, range.end)}
      </mark>,
    );
    cursor = range.end;
  });
  if (cursor < body.length) nodes.push(<SourcePlain key="tail" text={body.slice(cursor)} />);

  return (
    <div className="source-doc" aria-label="Source script" role="region" tabIndex={0}>
      {nodes}
    </div>
  );
}

export function ActionButton({
  children,
  busyLabel,
  onClick,
  variant = "primary",
  disabled = false,
}: {
  children: string;
  busyLabel: string;
  onClick: () => void;
  variant?: "primary" | "secondary" | "tertiary";
  disabled?: boolean;
}) {
  const guided = useGuided();
  const busy = guided.busy === busyLabel;
  return (
    <Button variant={variant} busy={busy} busyLabel={busyLabel} disabled={disabled || Boolean(guided.busy)} onClick={onClick}>
      {children}
    </Button>
  );
}
