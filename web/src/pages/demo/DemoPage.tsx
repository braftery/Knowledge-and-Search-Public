import { useEffect } from "react";
import { toast } from "sonner";
import { useSearchParams } from "react-router-dom";
import { resetGuided } from "@/api/guided";
import { PresenterBar } from "@/components/presenter-bar";
import { ServiceError } from "@/components/service-state";
import { CLOSING_NOTES, CLOSING_TITLE, DEMO_NOTES, FULL_PATH_NOTES, DEMO_TITLES, SHORT_PATH, neighbor } from "@/pages/demo/script";
import { ClosingView } from "@/pages/demo/closing";
import { GuidedProvider, useGuided } from "@/pages/demo/guided-context";
import {
  ApproveStep,
  ChannelsStep,
  CopiesStep,
  DriftStep,
  ExtractStep,
  GapsStep,
  QualityStep,
  SearchStep,
  TodayStep,
} from "@/pages/demo/steps";
import { useSession } from "@/pages/use-session";
import { readStoredSession, writeDemoStep, writeStoredSession } from "@/session";

const STEPS = [TodayStep, ExtractStep, CopiesStep, ApproveStep, SearchStep, ChannelsStep, GapsStep, DriftStep, QualityStep];

export function DemoPage() {
  return (
    <GuidedProvider>
      <DemoShell />
    </GuidedProvider>
  );
}

function DemoShell() {
  const [params, setParams] = useSearchParams();
  const ending = params.get("step") === "end";
  const step = ending ? 8 : clampStep(params.get("step"));
  const path = params.get("path") === "short" ? "short" : "full";
  const mode = path === "short" ? "short" : "start";
  const session = useSession("demo", mode);
  const guided = useGuided();
  const Surface = STEPS[step];

  useEffect(() => {
    if (!ending) writeDemoStep(step);
  }, [step, ending]);

  const last = path === "short" ? SHORT_PATH[SHORT_PATH.length - 1] : 8;
  const atLast = !ending && neighbor(step, path, 1) === step;

  function finish() {
    const next = new URLSearchParams(params);
    next.set("step", "end");
    setParams(next);
    toast.dismiss();
  }

  function go(nextStep: number, nextPath: "short" | "full", announce = true) {
    writeDemoStep(nextStep);
    const next = new URLSearchParams(params);
    next.set("step", String(nextStep));
    if (nextPath === "short") next.set("path", "short");
    else next.delete("path");
    setParams(next);
    if (announce) {
      toast.dismiss();
      void guided.clearForStep(nextStep);
    }
  }

  function rememberMode(next: "start" | "short") {
    const stored = readStoredSession("demo");
    writeStoredSession("demo", stored?.id ?? `demo-${Date.now()}`, next);
  }

  async function jumpShort() {
    const result = await guided.run("Opening the short demo…", () => resetGuided("short"));
    if (!result) return;
    rememberMode("short");
    go(0, "short", false);
  }

  async function reset() {
    const result = await guided.run("Resetting the demo…", () => resetGuided("start"));
    if (!result) return;
    rememberMode("start");
    go(0, "full", false);
  }

  async function undo() {
    const result = await guided.undoLast();
    const restored = result?.demo;
    if (!restored) return;
    const nextMode = restored.mode === "short" ? "short" : "start";
    rememberMode(nextMode);
    go(restored.step ?? 0, nextMode === "short" ? "short" : "full", false);
  }

  return (
    <div className="hh" data-theme="tools" style={{ minHeight: "100vh", background: "var(--surface)" }}>
      <PresenterBar
        step={ending ? 9 : step}
        total={8}
        title={ending ? CLOSING_TITLE : DEMO_TITLES[step]}
        stepLabel={ending ? "End" : undefined}
        backDisabled={!ending && neighbor(step, path, -1) === step}
        nextDisabled={ending}
        nextLabel={atLast ? "Finish" : undefined}
        canUndo={!ending && Boolean(guided.undo?.available)}
        onBack={() => (ending ? go(last, path, false) : go(neighbor(step, path, -1), path))}
        onNext={() => (atLast ? finish() : go(neighbor(step, path, 1), path))}
        onJumpShort={() => void jumpShort()}
        onReset={() => void reset()}
        onUndo={() => void undo()}
        notes={ending ? CLOSING_NOTES : (path === "full" && FULL_PATH_NOTES[step]) || DEMO_NOTES[step]}
        path={path === "short" ? [...SHORT_PATH] : undefined}
      />
      <main id="main-content" className="demo-stage">
        <h1 className="sr-only">{ending ? CLOSING_TITLE : DEMO_TITLES[step]}</h1>
        {session.error ? <ServiceError message={session.error} onRetry={session.reload} /> : null}
        {session.data && !ending ? <Surface /> : null}
        {session.data && ending ? <ClosingView path={path} /> : null}
      </main>
    </div>
  );
}

function clampStep(value: string | null) {
  const step = Number(value ?? "0");
  if (!Number.isInteger(step) || step < 0 || step > 8) return 0;
  return step;
}
