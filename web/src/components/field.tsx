import { TriangleAlert } from "lucide-react";
import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";
import { Icon } from "@/components/icon";
import { cn } from "@/lib/cn";

type Shared = {
  id: string;
  label: ReactNode;
  hint?: string;
  error?: string;
  optional?: boolean;
  /** AI-proposed text the person can insert with one deliberate click. The field itself starts empty. */
  suggestion?: string;
  onUseSuggestion?: () => void;
};

type FieldProps = Shared &
  (
    | ({ multiline?: false } & InputHTMLAttributes<HTMLInputElement>)
    | ({ multiline: true } & TextareaHTMLAttributes<HTMLTextAreaElement>)
  );

export function Field(props: FieldProps) {
  const { id, label, hint, error, optional, multiline, className, suggestion, onUseSuggestion, ...rest } = props;
  const errorId = error ? `${id}-error` : undefined;
  const hintId = hint ? `${id}-hint` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("hh-field", error && "hh-field--error")}>
      <label className="hh-label" htmlFor={id}>
        {label}
        {optional ? <span className="hh-opt"> (optional)</span> : null}
      </label>
      {hint ? (
        <span className="hh-hint" id={hintId}>
          {hint}
        </span>
      ) : null}
      {error ? (
        <span className="hh-error" id={errorId} role="alert">
          <Icon icon={TriangleAlert} />
          {error}
        </span>
      ) : null}
      {multiline ? (
        <textarea
          id={id}
          className={cn("hh-input hh-textarea", className)}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          {...(rest as TextareaHTMLAttributes<HTMLTextAreaElement>)}
        />
      ) : (
        <input
          id={id}
          className={cn("hh-input", className)}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          {...(rest as InputHTMLAttributes<HTMLInputElement>)}
        />
      )}
      {suggestion && onUseSuggestion && !String(rest.value ?? "").trim() ? (
        <span className="hh-suggest">
          <span className="hh-suggest__label">AI suggestion:</span> &ldquo;{suggestion}&rdquo;{" "}
          <button type="button" className="hh-suggest__use" onClick={onUseSuggestion}>
            Use suggestion
          </button>
        </span>
      ) : null}
    </div>
  );
}
