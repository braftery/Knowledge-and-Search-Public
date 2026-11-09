import { createSession } from "@/api/client";
import type { SessionMode } from "@/api/types";

const KEYS = {
  explore: "harbor-explore-session",
  demo: "harbor-demo-session",
  demoStep: "harbor-demo-step",
} as const;

const inflight = new Map<string, Promise<string>>();

export function readDemoStep(): number {
  const raw = sessionStorage.getItem(KEYS.demoStep);
  const step = raw ? Number(raw) : 0;
  return Number.isInteger(step) && step >= 0 && step <= 8 ? step : 0;
}

export function writeDemoStep(step: number) {
  sessionStorage.setItem(KEYS.demoStep, String(step));
}

export function readStoredSession(kind: "explore" | "demo"): { id: string; mode: SessionMode } | null {
  const id = sessionStorage.getItem(KEYS[kind]);
  const mode = sessionStorage.getItem(`${KEYS[kind]}-mode`) as SessionMode | null;
  if (!id || !mode) return null;
  return { id, mode };
}

export function writeStoredSession(kind: "explore" | "demo", id: string, mode: SessionMode) {
  sessionStorage.setItem(KEYS[kind], id);
  sessionStorage.setItem(`${KEYS[kind]}-mode`, mode);
}

export function clearStoredSession(kind: "explore" | "demo") {
  sessionStorage.removeItem(KEYS[kind]);
  sessionStorage.removeItem(`${KEYS[kind]}-mode`);
}

export async function ensureSession(kind: "explore" | "demo", mode: SessionMode): Promise<string> {
  const existing = readStoredSession(kind);
  if (existing && existing.mode === mode) return existing.id;
  const key = `${kind}:${mode}`;
  const pending = inflight.get(key);
  if (pending) return pending;
  const request = createSession(mode)
    .then((session) => {
      writeStoredSession(kind, session.session_id, session.mode || mode);
      return session.session_id;
    })
    .finally(() => {
      inflight.delete(key);
    });
  inflight.set(key, request);
  return request;
}
