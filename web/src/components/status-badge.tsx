import { CheckCircle2, Clock, RefreshCw, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { Icon } from "@/components/icon";

export type StatusVariant = "approved" | "review" | "blocked" | "stale" | "neutral";

const ICONS = {
  approved: CheckCircle2,
  review: Clock,
  blocked: TriangleAlert,
  stale: RefreshCw,
} as const;

type StatusBadgeProps = {
  variant: StatusVariant;
  children: ReactNode;
};

export function StatusBadge({ variant, children }: StatusBadgeProps) {
  const glyph = variant === "neutral" ? null : ICONS[variant];
  return (
    <span className={`hh-badge hh-badge--${variant}`}>
      {glyph ? <Icon icon={glyph} /> : null}
      {children}
    </span>
  );
}
