import { useEffect, useState } from "react";
import { openExploreRole, setExploreRole } from "@/api/client";
import type { ReactNode } from "react";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { showUndoToast } from "@/components/toast";
import { AgentDesktop } from "@/pages/advocate/AgentDesktop";
import { StudioWork } from "@/pages/author/StudioWork";
import { DocsPage } from "@/pages/channel/DocsPage";
import { InsightsPage } from "@/pages/owner/InsightsPage";
import { LegalInbox } from "@/pages/legal/LegalInbox";
import { MemberApp } from "@/pages/member/MemberApp";
import { MemberSite } from "@/pages/member/MemberSite";
import { PhoneLine } from "@/pages/member/PhoneLine";
import { ExploreHint } from "@/pages/explore-hints";
import { roleById } from "@/pages/roles";
import { readDemoStep } from "@/session";
import { useSession } from "@/pages/use-session";

export function ExploreLayout() {
  const { roleId } = useParams();
  const role = roleById(roleId);
  const [params, setParams] = useSearchParams();
  // The server holds the Explore role. Name it before any child request, and open it whenever the role changes.
  if (role) setExploreRole(role.role);
  const session = useSession("explore", "explore");
  const roleName = role?.role ?? "";
  const [openedRole, setOpenedRole] = useState("");
  useEffect(() => {
    if (!roleName || !session.data) return;
    let live = true;
    void openExploreRole(roleName)
      .catch(() => undefined)
      .finally(() => {
        if (live) setOpenedRole(roleName);
      });
    return () => {
      live = false;
    };
  }, [roleName, session.data]);
  const roleReady = openedRole === roleName;
  // Views wait until the server has this role open, so their first requests are not refused.
  const showView = !session.loading && (roleReady || !session.data);
  if (!role) return <Navigate to="/" replace />;

  const views = role.views;
  const requested = params.get("view");
  const view = views.some((item) => item.id === requested) ? requested : views[0].id;

  function setView(next: string) {
    const query = new URLSearchParams(params);
    if (next === views[0].id) query.delete("view");
    else query.set("view", next);
    setParams(query);
  }

  async function resetSandbox() {
    try {
      const { previous } = await session.replace("explore");
      showUndoToast({
        message: "Sandbox reset.",
        onUndo: previous
          ? () => {
              sessionStorage.setItem("harbor-explore-session", previous.id);
              sessionStorage.setItem("harbor-explore-session-mode", previous.mode);
              session.reload();
            }
          : undefined,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "The sandbox could not be reset.";
      showUndoToast({ message });
    }
  }

  const step = readDemoStep();

  return (
    <div className="hh" data-theme="tools" style={{ minHeight: "100vh", background: "var(--surface)" }}>
      <section className="explore-bar" aria-label="Prototype controls">
        <Link to="/">Prototype home</Link>
        <p className="explore-bar__role">
          Explore as {role.role}
        </p>
        <span className="explore-bar__pill">Illustrative data</span>
        <nav aria-label="Views" className="explore-bar__views">
          {views.map((item) => (
            <button key={item.id} type="button" aria-current={view === item.id ? "page" : undefined} onClick={() => setView(item.id)}>
              {item.label}
            </button>
          ))}
        </nav>
        <button type="button" onClick={() => void resetSandbox()}>
          Reset the sandbox
        </button>
        <Link to={`/demo?step=${step}`}>Back to the guided demo</Link>
      </section>
      <ExploreHint key={role.id} roleId={role.id} />
      <MainOrDiv own={role.id === "member" || role.id === "channel"}>
        {session.showSkeleton ? (
          <div style={{ padding: "var(--space-8)" }}>
            <Skeleton width="320px" height="28px" label="Opening the sandbox" />
          </div>
        ) : null}
        {session.error && role.id !== "member" && role.id !== "pharmacy" && role.id !== "insurance" ? (
          <div style={{ padding: "var(--space-8)" }}>
            <ServiceError message={session.error} onRetry={session.reload} />
          </div>
        ) : null}
        {showView && role.id === "member" && view === "website" ? (
          <MemberSite sessionId={session.data} sessionError={session.error} onRetry={session.reload} />
        ) : null}
        {showView && role.id === "member" && view === "app" ? <MemberApp sessionId={session.data} /> : null}
        {showView && role.id === "member" && view === "phone" ? (
          <PhoneLine sessionId={session.data} sessionError={session.error} onRetry={session.reload} />
        ) : null}
        {showView && (role.id === "pharmacy" || role.id === "insurance") ? (
          <AgentDesktop
            advocateId={role.id}
            sessionId={session.data}
            sessionError={session.error}
            onRetry={session.reload}
          />
        ) : null}
        {showView && role.id === "legal" && session.data ? <LegalInbox /> : null}
        {showView && role.id === "author" && session.data ? <StudioWork /> : null}
        {showView && role.id === "owner" && session.data ? <InsightsPage /> : null}
        {showView && role.id === "channel" && session.data ? <DocsPage /> : null}
      </MainOrDiv>
    </div>
  );
}

/** Staff views get the page's main landmark here. Member and channel views render their own main. */
function MainOrDiv({ own, children }: { own: boolean; children: ReactNode }) {
  return own ? <div id="main-content">{children}</div> : <main id="main-content">{children}</main>;
}
