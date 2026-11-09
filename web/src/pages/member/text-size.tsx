import { useEffect, useState } from "react";

export type TextSize = "standard" | "larger";

const KEY = "harbor-member-text-size";

function readSize(): TextSize {
  try {
    return window.localStorage.getItem(KEY) === "larger" ? "larger" : "standard";
  } catch {
    return "standard";
  }
}

/**
 * Member text size. Set on the page root so it also reaches the chat panel when it renders outside the page.
 * Remembered per viewer in this browser only; the page works the same without storage.
 */
export function useMemberTextSize() {
  const [size, setSize] = useState<TextSize>(() => readSize());
  useEffect(() => {
    document.documentElement.dataset.memberText = size;
    try {
      window.localStorage.setItem(KEY, size);
    } catch {
      // Storage can be unavailable (private window); the choice still applies for this visit.
    }
  }, [size]);
  useEffect(
    () => () => {
      delete document.documentElement.dataset.memberText;
    },
    [],
  );
  return { size, setSize };
}

/** A labelled two-option control. Changes apply instantly, with no animation, and work from the keyboard. */
export function TextSizeControl({ size, onChange }: { size: TextSize; onChange: (size: TextSize) => void }) {
  return (
    <div className="text-size" role="group" aria-labelledby="text-size-label">
      <span className="text-size__label" id="text-size-label">
        Text size
      </span>
      <button type="button" className="text-size__option" aria-pressed={size === "standard"} onClick={() => onChange("standard")}>
        Standard
      </button>
      <button type="button" className="text-size__option text-size__option--larger" aria-pressed={size === "larger"} onClick={() => onChange("larger")}>
        Larger
      </button>
    </div>
  );
}
