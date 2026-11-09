import type { ReactNode } from "react";

type EmptyStateProps = {
  heading: string;
  reason: string;
  steps?: string[];
  action?: ReactNode;
  /** Heading level; 2 by default, so an empty state right under a page heading keeps the outline in order. */
  level?: 2 | 3;
};

export function EmptyState({ heading, reason, steps, action, level = 2 }: EmptyStateProps) {
  const Heading = level === 3 ? "h3" : "h2";
  return (
    <div className="hh-empty">
      <Heading className="hh-empty__title">{heading}</Heading>
      <p>{reason}</p>
      {steps && steps.length > 0 ? (
        <ol>
          {steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      ) : null}
      {action}
    </div>
  );
}
