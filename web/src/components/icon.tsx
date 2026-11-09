import type { LucideIcon } from "lucide-react";

type IconProps = {
  icon: LucideIcon;
  className?: string;
};

/** Lucide at the system sizes: 18px in text, 16px inside a badge (via .hh-badge .hh-icon). */
export function Icon({ icon: Glyph, className = "hh-icon" }: IconProps) {
  return <Glyph className={className} aria-hidden="true" strokeWidth={2} />;
}
