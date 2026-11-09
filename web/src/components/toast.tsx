import { CheckCircle2 } from "lucide-react";
import { Toaster, toast } from "sonner";
import { Icon } from "@/components/icon";

export function ToastView({ message, onUndo }: { message: string; onUndo?: () => void }) {
  return (
    <div className="hh-toast" role="status" aria-live="polite">
      <Icon icon={CheckCircle2} />
      <span className="hh-toast__text">{message}</span>
      {onUndo ? (
        <button className="hh-btn hh-btn--tertiary hh-btn--compact" type="button" onClick={onUndo}>
          Undo
        </button>
      ) : null}
    </div>
  );
}

export function AppToaster() {
  return (
    <Toaster
      position="bottom-center"
      duration={8000}
      visibleToasts={1}
      offset={16}
      toastOptions={{ unstyled: true }}
    />
  );
}

type UndoToast = {
  message: string;
  onUndo?: () => void;
};

/** One success toast at a time. Stays 8 seconds and pauses while hovered. */
export function showUndoToast({ message, onUndo }: UndoToast) {
  if (!message?.trim()) return;
  toast.custom(
    (id) => (
      <div className="hh-toast" role="status">
        <Icon icon={CheckCircle2} />
        <span className="hh-toast__text">{message}</span>
        {onUndo ? (
          <button
            className="hh-btn hh-btn--tertiary hh-btn--compact"
            type="button"
            onClick={() => {
              toast.dismiss(id);
              onUndo();
            }}
          >
            Undo
          </button>
        ) : null}
      </div>
    ),
    { duration: 8000 },
  );
}
