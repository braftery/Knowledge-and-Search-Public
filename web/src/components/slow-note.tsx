import { useEffect, useState } from "react";

/**
 * Shown while an answer is loading. After three seconds it says why: a question with no saved answer goes to the
 * live model, which can take up to about 15 seconds. The wait is real, so the person is told what is happening.
 */
export function SlowNote({ active, className = "hh-meta" }: { active: boolean; className?: string }) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    setSlow(false);
    if (!active) return;
    const timer = window.setTimeout(() => setSlow(true), 3000);
    return () => window.clearTimeout(timer);
  }, [active]);
  if (!active || !slow) return null;
  return (
    <p className={className} role="status">
      Still checking the approved answers. A new question can take up to 15 seconds.
    </p>
  );
}
