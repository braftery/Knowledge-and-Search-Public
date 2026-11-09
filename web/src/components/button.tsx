import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "tertiary";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  compact?: boolean;
  busy?: boolean;
  busyLabel?: string;
  href?: string;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    compact = false,
    busy = false,
    busyLabel,
    href,
    className,
    children,
    type = "button",
    ...rest
  },
  ref,
) {
  const classes = cn(
    "hh-btn",
    variant === "primary" && "hh-btn--primary",
    variant === "secondary" && "hh-btn--secondary",
    variant === "tertiary" && "hh-btn--tertiary",
    compact && "hh-btn--compact",
    className,
  );
  const content: ReactNode = busy ? (
    <>
      <span className="hh-spinner" aria-hidden="true" />
      {busyLabel ?? children}
    </>
  ) : (
    children
  );

  if (href) {
    return (
      <a className={classes} href={href} aria-busy={busy || undefined}>
        {content}
      </a>
    );
  }

  return (
    <button ref={ref} className={classes} type={type} aria-busy={busy || undefined} {...rest}>
      {content}
    </button>
  );
});
