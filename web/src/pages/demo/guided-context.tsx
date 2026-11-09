import { createContext, useContext, useState, type ReactNode } from "react";
import { setDemoStep, undoWorld, type Mutation, type UndoState } from "@/api/guided";
import { showUndoToast } from "@/components/toast";

type Guided = {
  tick: number;
  busy: string | null;
  problem: string | null;
  undo: UndoState | null;
  run: (label: string, work: () => Promise<Mutation>) => Promise<Mutation | null>;
  note: (result: Mutation) => void;
  clearForStep: (step: number) => Promise<void>;
  undoLast: () => Promise<Mutation | null>;
};

const Context = createContext<Guided | null>(null);

export function GuidedProvider({
  children,
  onRestored,
}: {
  children: ReactNode;
  onRestored?: (demo: { mode?: string; step?: number }) => void;
}) {
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [undo, setUndo] = useState<UndoState | null>(null);

  async function undoLast() {
    setProblem(null);
    try {
      const result = await undoWorld("guided");
      setUndo(null);
      setTick((value) => value + 1);
      if (result.demo) onRestored?.(result.demo);
      showUndoToast({ message: result.message });
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Nothing to undo.";
      setProblem(message);
      return null;
    }
  }

  function accept(result: Mutation) {
    const next = result.undo?.available ? result.undo : null;
    setUndo(next);
    setTick((value) => value + 1);
    showUndoToast({
      message: result.message,
      onUndo: next ? () => void undoLast() : undefined,
    });
  }

  async function run(label: string, work: () => Promise<Mutation>) {
    if (busy) return null;
    setBusy(label);
    setProblem(null);
    try {
      const result = await work();
      accept(result);
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : "The knowledge service could not complete that action.";
      setProblem(message);
      return null;
    } finally {
      setBusy(null);
    }
  }

  function note(result: Mutation) {
    accept(result);
  }

  async function clearForStep(step: number) {
    setUndo(null);
    try {
      await setDemoStep(step);
    } catch (error) {
      const message = error instanceof Error ? error.message : "The demo step could not be saved.";
      setProblem(message);
    }
  }

  return (
    <Context.Provider value={{ tick, busy, problem, undo, run, note, clearForStep, undoLast }}>{children}</Context.Provider>
  );
}

/** The guided runner when inside the guided demo, or null when a screen is reused in the Explore sandbox. */
export function useGuidedOptional() {
  return useContext(Context);
}

export function useGuided() {
  const value = useContext(Context);
  if (!value) throw new Error("Guided demo is missing its provider.");
  return value;
}
