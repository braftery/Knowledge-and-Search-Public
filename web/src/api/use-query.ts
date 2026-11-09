import { useEffect, useRef, useState } from "react";

type QueryState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  showSkeleton: boolean;
};

/** Skeletons wait 200ms, then stay at least 400ms, so a fast response does not flicker. */
export function useQuery<T>(key: string, load: () => Promise<T>, enabled = true): QueryState<T> & { reload: () => void } {
  const [tick, setTick] = useState(0);
  const loadRef = useRef(load);
  loadRef.current = load;
  const [state, setState] = useState<QueryState<T>>({
    data: null,
    error: null,
    loading: enabled,
    showSkeleton: false,
  });

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, error: null, loading: false, showSkeleton: false });
      return;
    }
    let cancel = false;
    const started = Date.now();
    setState((current) => ({ ...current, loading: true, error: null }));
    const showTimer = window.setTimeout(() => {
      if (!cancel) {
        setState((current) => (current.loading ? { ...current, showSkeleton: true } : current));
      }
    }, 200);
    loadRef.current()
      .then(async (data) => {
        const elapsed = Date.now() - started;
        if (elapsed > 200 && elapsed < 600) {
          await new Promise((resolve) => window.setTimeout(resolve, 600 - elapsed));
        }
        if (!cancel) setState({ data, error: null, loading: false, showSkeleton: false });
      })
      .catch((error: unknown) => {
        if (!cancel) {
          const message = error instanceof Error ? error.message : "Something went wrong.";
          setState({ data: null, error: message, loading: false, showSkeleton: false });
        }
      });
    return () => {
      cancel = true;
      window.clearTimeout(showTimer);
    };
  }, [key, enabled, tick]);

  return { ...state, reload: () => setTick((value) => value + 1) };
}
