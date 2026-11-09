import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/components/button";

type PresenterBarProps = {
  step: number;
  total: number;
  title: string;
  onBack: () => void;
  onNext: () => void;
  onJumpShort: () => void;
  onReset: () => void;
  onUndo?: () => void;
  canUndo?: boolean;
  backDisabled?: boolean;
  nextDisabled?: boolean;
  notes?: string;
  path?: number[];
  nextLabel?: string;
  stepLabel?: string;
};

export function PresenterBar({
  step,
  total,
  title,
  onBack,
  onNext,
  onJumpShort,
  onReset,
  onUndo,
  canUndo = false,
  backDisabled = false,
  nextDisabled = false,
  notes,
  path,
  nextLabel,
  stepLabel,
}: PresenterBarProps) {
  const [notesOpen, setNotesOpen] = useState(false);
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target && (target.closest("input, textarea, select, [contenteditable='true']") || target.isContentEditable)) {
        return;
      }
      if (event.key === "Escape") setNotesOpen(false);
      if (event.key === "ArrowLeft" && !backDisabled) {
        event.preventDefault();
        onBack();
      }
      if (event.key === "ArrowRight" && !nextDisabled) {
        event.preventDefault();
        onNext();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onBack, onNext, backDisabled, nextDisabled]);

  const steps = path ?? Array.from({ length: total + 1 }, (_, index) => index);
  return (
    <>
      <header className="hh-presenter-landmark" aria-label="Guided demo">
      <div className="hh-presenter" role="toolbar" aria-label="Guided demo">
        <div className="hh-presenter__lead">
          <span className="hh-presenter__kicker">Guided demo</span>
          <ol className="hh-presenter__dots" aria-label={stepLabel ? "All steps done" : `Step ${step + 1} of ${total + 1}`}>
            {steps.map((item) => (
              <li key={item} aria-current={item === step ? "step" : undefined} className={item < step ? "done" : undefined} />
            ))}
          </ol>
          <span className="hh-presenter__step">
            {stepLabel ?? (path ? `${Math.max(1, path.indexOf(step) + 1)} / ${path.length}` : `${step + 1} / ${total + 1}`)}
          </span>
          <span className="hh-presenter__title">{title}</span>
        </div>
        <span className="hh-presenter__pill">Illustrative data</span>
        <div className="hh-presenter__actions">
          {/* Leaving keeps the demo's progress: opening the guided demo again resumes it. Reset starts over. */}
          <Link className="hh-btn hh-btn--tertiary hh-presenter__exit" to="/">
            Exit to home
          </Link>
          {notes ? (
            <Button variant="tertiary" onClick={() => setNotesOpen((open) => !open)} aria-expanded={notesOpen} aria-controls="presenter-notes">
              Notes
            </Button>
          ) : null}
          <Button
            variant="tertiary"
            onClick={() => {
              if (!path && !window.confirm("Switch to the short demo? This restarts the demo at the first step.")) return;
              onJumpShort();
            }}
          >
            {path ? "Restart short demo" : "Switch to short demo"}
          </Button>
          <Button variant="tertiary" onClick={onReset}>
            Reset
          </Button>
          {canUndo && onUndo ? (
            <Button variant="secondary" onClick={onUndo}>
              Undo
            </Button>
          ) : null}
          <Button variant="secondary" onClick={onBack} disabled={backDisabled}>
            Back
          </Button>
          <Button variant="primary" onClick={onNext} disabled={nextDisabled}>
            {nextLabel ?? "Next"}
          </Button>
        </div>
      </div>
      </header>
      {notes && notesOpen ? (
        <aside id="presenter-notes" className="presenter-notes" aria-label="Presenter notes">
          <div className="presenter-notes__head">
            <strong>Presenter notes</strong>
            <Button variant="tertiary" onClick={() => setNotesOpen(false)}>
              Close
            </Button>
          </div>
          <p>{notes}</p>
        </aside>
      ) : null}
    </>
  );
}
