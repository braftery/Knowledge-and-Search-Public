import { useState } from "react";
import type { SessionMode } from "@/api/types";
import { useQuery } from "@/api/use-query";
import { clearStoredSession, ensureSession, readStoredSession, writeStoredSession } from "@/session";

export function useSession(kind: "explore" | "demo", mode: SessionMode) {
  const [generation, setGeneration] = useState(0);
  const query = useQuery(`session:${kind}:${mode}:${generation}`, () => ensureSession(kind, mode));

  async function replace(nextMode: SessionMode) {
    const previous = readStoredSession(kind);
    clearStoredSession(kind);
    try {
      const id = await ensureSession(kind, nextMode);
      setGeneration((value) => value + 1);
      return { id, previous };
    } catch (error) {
      if (previous) writeStoredSession(kind, previous.id, previous.mode);
      throw error;
    }
  }

  return { ...query, replace };
}
