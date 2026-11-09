import { useRef, useState } from "react";
import {
  approveLegal,
  actOnLegalSourceChange,
  getLegalSourceChanges,
  type AuthorDrift,
  type DriftAction,
  declineLegal,
  getChannels,
  getInbox,
  publishChannels,
  resolveConflict,
  undoWorld,
  type Inbox,
  type Mutation,
} from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { DiffLegend, DiffText } from "@/components/diff-view";
import { EmptyState } from "@/components/empty-state";
import { InlineProblem, ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { showUndoToast } from "@/components/toast";
import { ApprovalReview, ConflictColumns } from "@/pages/legal/ApprovalReview";
import { DriftReview } from "@/pages/author/DriftReview";
import { apiDiff, routingWhy } from "@/lib/labels";
import { WordingHistory } from "@/pages/legal/WordingHistory";
import { LegalReviews } from "@/pages/legal/LegalReviews";

type Folder = "inbox" | "sent" | "history" | "reviews";
type Stage = "mail" | "review" | "changes" | "revision";

/** A unit Knowledge Ops sent: from one of the sandbox documents, or a finished gap draft. */
function fromKnowledgeOps(item: Inbox["items"][number]) {
  return item.kind === "approval" && (item.unit?.status === "with_legal" || (item.unit?.unit_id ?? "").startsWith("U-GAP-"));
}

export function LegalInbox() {
  const [tick, setTick] = useState(0);
  const inbox = useQuery(`legal-inbox:${tick}`, () => getInbox("explore"));
  const [folder, setFolder] = useState<Folder>("inbox");
  const channels = useQuery(`legal-rev:${tick}`, () => getChannels("explore"));
  const [mail, setMail] = useState<"digest" | "revision" | "changes">("digest");
  const changes = useQuery(`legal-changes:${tick}`, () => getLegalSourceChanges());
  const changeItems = changes.data?.items ?? [];
  const revision = channels.data?.revision_ready && !channels.data?.revised ? channels.data.revision_preview : undefined;
  const [typed, setTyped] = useState<{ text: string; member_text: string } | null>(null);
  const reading = mail === "revision" && revision ? "revision" : mail === "changes" && changeItems.length ? "changes" : "digest";
  const [stage, setStage] = useState<Stage>("mail");
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const totalRef = useRef(0);
  const changesTotalRef = useRef(0);

  async function undo() {
    setProblem(null);
    try {
      const result = await undoWorld("explore");
      showUndoToast({ message: result.message });
      setTick((value) => value + 1);
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "Nothing to undo.");
    }
  }

  async function act(label: string, work: () => Promise<Mutation>) {
    if (busy) return;
    setBusy(label);
    setProblem(null);
    try {
      const result = await work();
      showUndoToast({
        message: result.message,
        onUndo: result.undo?.available ? () => void undo() : undefined,
      });
      setTick((value) => value + 1);
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "The knowledge service could not complete that action.");
    } finally {
      setBusy(null);
    }
  }

  // Shown before the inbox loading state, so a reload after each decision does not reset the review or its count.
  if (stage === "changes") {
    return (
      <SourceChangesStage
        items={changeItems}
        total={changesTotalRef.current || changeItems.length}
        busy={busy}
        problem={problem}
        onBack={() => setStage("mail")}
        act={(id, action, body) => act(action, () => actOnLegalSourceChange(id, action, body))}
      />
    );
  }
  if (inbox.showSkeleton || (!inbox.data && !inbox.error)) {
    return (
      <div className="mail-stage" aria-busy="true">
        <Skeleton width="280px" height="28px" label="Loading the inbox" />
        <Skeleton width="100%" height="420px" />
      </div>
    );
  }
  if (inbox.error || !inbox.data) {
    return (
      <div className="mail-stage">
        <ServiceError message={inbox.error || "The inbox did not load."} onRetry={inbox.reload} />
      </div>
    );
  }

  if (stage === "revision" && revision && channels.data?.live) {
    return (
      <div className="review-page" data-theme="tools">
        <div className="legal-bar">
          <Button variant="tertiary" onClick={() => setStage("mail")}>
            Back to email
          </Button>
          {problem ? <InlineProblem message={problem} /> : null}
        </div>
        <header className="legal-top">
          <strong className="desk-top__brand">
            Harbor Health <span>Single Source · Legal review</span>
          </strong>
          <span className="desk-top__queue">Wording change</span>
        </header>
        <div className="studio-scroll">
          <article className="mail-read">
                <h1 className="mail-read__subject">Wording change ready: {channels.data.live.title}</h1>
                <div className="mail-read__from">
                  <span className="avatar" aria-hidden="true">
                    SS
                  </span>
                  <span>
                    <strong>Single Source</strong>
                    <span className="hh-meta"> to Legal approvers · 9:20 AM</span>
                  </span>
                </div>
                <div className="mail-read__body">
                  <p className="tools-body">
                    The revision changes &ldquo;{revision.find}&rdquo; to &ldquo;{revision.replace}&rdquo;. Publishing makes version {revision.next_version} live
                    on the advocate desktop, member chat, the website and the phone line at once. Version {revision.next_version - 1} stays in the history, and
                    advocates are asked to confirm they read the new wording.
                  </p>
                  <DiffLegend />
                  <p className="hh-label">Advocate wording</p>
                  <p className="tools-body mail-diff">
                    <DiffText parts={apiDiff(revision.advocate_diff)} />
                  </p>
                  {revision.member_text ? (
                    <>
                      <p className="hh-label">Member wording</p>
                      <p className="tools-body mail-diff">
                        <DiffText parts={apiDiff(revision.member_diff)} />
                      </p>
                    </>
                  ) : null}
                  <details className="legal-edit legal-edit--mail">
                    <summary>Edit the wording before publishing</summary>
                    <label className="hh-label" htmlFor="mail-edit-advocate">
                      Advocate wording
                    </label>
                    <textarea
                      id="mail-edit-advocate"
                      className="hh-input legal-edit__text"
                      rows={4}
                      value={typed?.text ?? revision.advocate_text}
                      onChange={(event) => setTyped((current) => ({ text: event.target.value, member_text: current?.member_text ?? revision.member_text }))}
                    />
                    <label className="hh-label" htmlFor="mail-edit-member">
                      Member wording
                    </label>
                    <textarea
                      id="mail-edit-member"
                      className="hh-input legal-edit__text"
                      rows={4}
                      value={typed?.member_text ?? revision.member_text}
                      onChange={(event) => setTyped((current) => ({ text: current?.text ?? revision.advocate_text, member_text: event.target.value }))}
                    />
                    <p className="hh-meta">Typed wording is checked against the source and recorded as edited by you.</p>
                  </details>
                  <Button
                    busy={busy === "Publishing version…"}
                    busyLabel="Publishing…"
                    onClick={() => {
                      const edited = typed && (typed.text !== revision.advocate_text || typed.member_text !== revision.member_text);
                      void act("Publishing version…", () => publishChannels("explore", edited ? typed : undefined)).then(() => {
                        setTyped(null);
                        setMail("digest");
                        setStage("mail");
                      });
                    }}
                  >
                    Publish version {revision.next_version} to every channel
                  </Button>
                </div>
              </article>
        </div>
      </div>
    );
  }
  if (stage === "review") {
    return (
      <ReviewStage
        inbox={inbox.data}
        total={totalRef.current || inbox.data.count}
        busy={busy}
        problem={problem}
        onBack={() => setStage("mail")}
        onApprove={(unitId) => void act("Publishing…", () => approveLegal(unitId, "explore"))}
        onDecline={(unitId, reason) => void act("Sending back…", () => declineLegal(unitId, reason, "explore"))}
        onResolve={(conflictId, reason) => {
          const label = inbox.data?.items.find((item) => item.id === conflictId)?.conflict?.label || conflictId;
          void act(`Resolving ${label}…`, () => resolveConflict(reason, conflictId, "explore"));
        }}
      />
    );
  }

  return (
    <div className="mail-stage">
      <div className="mail-window">
        <nav className="mail-folders" aria-label="Folders">
          <p className="mail-brand">Harbor Health</p>
          <button type="button" className="mail-folder" aria-current={folder === "inbox" ? "page" : undefined} onClick={() => setFolder("inbox")}>
            Inbox
            <span className="hh-count">{inbox.data.count}</span>
          </button>
          <button type="button" className="mail-folder" aria-current={folder === "sent" ? "page" : undefined} onClick={() => setFolder("sent")}>
            Sent
          </button>
          <p className="mail-brand mail-brand--sub">Single Source</p>
          <button type="button" className="mail-folder" aria-current={folder === "history" ? "page" : undefined} onClick={() => setFolder("history")}>
            Wording history
          </button>
          <button type="button" className="mail-folder" aria-current={folder === "reviews" ? "page" : undefined} onClick={() => setFolder("reviews")}>
            Reviews and workload
          </button>
        </nav>
        {folder === "reviews" ? (
          <LegalReviews />
        ) : folder === "history" ? (
          <WordingHistory />
        ) : folder === "sent" ? (
          <div className="mail-read mail-read--wide">
            <EmptyState heading="Nothing in Sent" reason="Decisions stay on the review record. This inbox does not send mail." />
          </div>
        ) : (
          <>
            <div className="mail-list">
              <div className="mail-search">
                <input className="hh-input" aria-label="Search mail" placeholder="Search mail…" readOnly />
              </div>
              {changeItems.length ? (
                <button
                  type="button"
                  className="mail-item mail-item--unread"
                  aria-current={reading === "changes" ? "true" : undefined}
                  onClick={() => setMail("changes")}
                >
                  <span className="mail-item__row">
                    <span className="mail-item__from">Single Source</span>
                    <span className="mail-item__time">9:25 AM</span>
                  </span>
                  <span className="mail-item__subject">{changeItems.length} source changes need your decision</span>
                  <span className="mail-item__preview">{changeItems.map((item) => item.title || item.unit_id).join("; ")}</span>
                </button>
              ) : null}
              {revision && channels.data?.live ? (
                <button
                  type="button"
                  className="mail-item mail-item--unread"
                  aria-current={reading === "revision" ? "true" : undefined}
                  onClick={() => setMail("revision")}
                >
                  <span className="mail-item__row">
                    <span className="mail-item__from">Single Source</span>
                    <span className="mail-item__time">9:20 AM</span>
                  </span>
                  <span className="mail-item__subject">Wording change ready: {channels.data.live.title}</span>
                  <span className="mail-item__preview">A revision is ready to publish as version {revision.next_version} to every channel.</span>
                </button>
              ) : null}
              <button
                type="button"
                className="mail-item mail-item--unread"
                aria-current={reading === "digest" ? "true" : undefined}
                onClick={() => setMail("digest")}
              >
                <span className="mail-item__row">
                  <span className="mail-item__from">Single Source</span>
                  <span className="mail-item__time">9:12 AM</span>
                </span>
                <span className="mail-item__subject">{inbox.data.count > 0 ? `${inbox.data.count} items waiting for your review` : "Nothing is waiting"}</span>
                <span className="mail-item__preview">{inbox.data.message}</span>
              </button>
              {OTHER_MAIL.map((mail) => (
                <div key={mail.subject} className="mail-item mail-item--read">
                  <span className="mail-item__row">
                    <span className="mail-item__from">{mail.from}</span>
                    <span className="mail-item__time">{mail.time}</span>
                  </span>
                  <span className="mail-item__subject">{mail.subject}</span>
                  <span className="mail-item__preview">{mail.preview}</span>
                </div>
              ))}
            </div>
            {reading === "changes" ? (
              <article className="mail-read">
                <h1 className="mail-read__subject">{changeItems.length} source changes need your decision</h1>
                <div className="mail-read__from">
                  <span className="avatar" aria-hidden="true">
                    SS
                  </span>
                  <span>
                    <strong>Single Source</strong>
                    <span className="hh-meta"> to Legal approvers · 9:25 AM</span>
                  </span>
                </div>
                <div className="mail-read__body">
                  <p className="tools-body">The source documents behind wording you approved changed. The approved versions stay live until you decide.</p>
                  <ul className="mail-routes">
                    {changeItems.map((item) => (
                      <li key={item.id} className="tools-body">
                        <strong>{item.title || item.unit_id}</strong>. {item.kind_label}.
                      </li>
                    ))}
                  </ul>
                  <Button
                    onClick={() => {
                      changesTotalRef.current = changeItems.length;
                      setStage("changes");
                    }}
                  >
                    Start review
                  </Button>
                </div>
              </article>
            ) : reading === "revision" && revision && channels.data?.live ? (
              <article className="mail-read">
                <h1 className="mail-read__subject">Wording change ready: {channels.data.live.title}</h1>
                <div className="mail-read__from">
                  <span className="avatar" aria-hidden="true">
                    SS
                  </span>
                  <span>
                    <strong>Single Source</strong>
                    <span className="hh-meta"> to Legal approvers · 9:20 AM</span>
                  </span>
                </div>
                <div className="mail-read__body">
                  <p className="tools-body">
                    A revision of {channels.data.live.title} is ready to publish as version {revision.next_version} to every channel. Open the review to see the
                    change, edit it if needed, and publish.
                  </p>
                  <Button onClick={() => setStage("revision")}>Start review</Button>
                </div>
              </article>
            ) : (
            <article className="mail-read">
                <h1 className="mail-read__subject">
                  {inbox.data.count > 0 ? `${inbox.data.count} items waiting for your review` : "Nothing is waiting"}
                </h1>
                <div className="mail-read__from">
                  <span className="avatar" aria-hidden="true">
                    SS
                  </span>
                  <span>
                    <strong>Single Source</strong>
                    <span className="hh-meta"> to Legal approvers · 9:12 AM</span>
                  </span>
                </div>
                <div className="mail-read__body">
                  <p className="tools-body">{inbox.data.message}</p>
                  <h2 className="hh-label">Sent by Knowledge Ops</h2>
                  {inbox.data.items.some(fromKnowledgeOps) ? (
                    <ul className="mail-routes">
                      {inbox.data.items.filter(fromKnowledgeOps).map((item) => (
                        <li key={item.id} className="tools-body">
                          <strong>{item.title}</strong> ({item.unit?.document_name || "gap draft"}). You review these first.
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="tools-body">
                      Nothing yet. When Knowledge Ops sends a unit from one of its documents, or a finished gap draft, it arrives here and you review it first.
                      Switch to the Knowledge Ops author to send some.
                    </p>
                  )}
                  <h2 className="hh-label">Already in your queue</h2>
                  {inbox.data.items.some((item) => item.routing_reason) ? (
                    <>
                      <p className="tools-body">New since your last review, and why each one came to you:</p>
                      <ul className="mail-routes">
                        {inbox.data.items
                          .filter((item) => item.routing_reason)
                          .map((item) => (
                            <li key={item.id} className="tools-body">
                              <strong>{item.title}</strong>. {routingWhy(item.routing_reason)?.why}
                            </li>
                          ))}
                      </ul>
                    </>
                  ) : null}
                  {inbox.data.count > 0 ? (
                    <p className="tools-body">
                      Approvals come first. A conflict stays blocked until you keep one wording and record a reason. Nothing reaches an
                      advocate or a member until you approve it.
                    </p>
                  ) : null}
                  {inbox.data.count > 0 ? (
                    <Button
                      onClick={() => {
                        totalRef.current = inbox.data?.count ?? 0;
                        setStage("review");
                      }}
                    >
                      Start review
                    </Button>
                  ) : (
                    <EmptyState heading="All caught up" reason="New items arrive by email." />
                  )}
                  <p className="hh-meta mail-read__foot">You receive this because you approve regulated wording in Single Source.</p>
                </div>
              </article>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function ReviewStage({
  inbox,
  total,
  busy,
  problem,
  onBack,
  onApprove,
  onDecline,
  onResolve,
}: {
  inbox: Inbox;
  total: number;
  busy: string | null;
  problem: string | null;
  onBack: () => void;
  onApprove: (unitId: string) => void;
  onDecline: (unitId: string, reason: string) => void;
  onResolve: (conflictId: string, reason: string) => void;
}) {
  // Units Knowledge Ops just sent come first, so the newest decisions are reviewed before the older backlog.
  const sentByKnowledgeOps = (item: Inbox["items"][number]) => (fromKnowledgeOps(item) ? 0 : 1);
  const current = [...inbox.items].sort((a, b) => sentByKnowledgeOps(a) - sentByKnowledgeOps(b))[0];
  const position = current ? Math.max(1, total - inbox.count + 1) : total;
  return (
    <div className="review-page" data-theme="tools">
      <div className="legal-bar">
        <Button variant="tertiary" onClick={onBack}>
          Back to email
        </Button>
        {problem ? <InlineProblem message={problem} /> : null}
      </div>
      {!current ? (
        <div className="studio-scroll">
          <EmptyState heading="All caught up" reason="New items arrive by email." />
        </div>
      ) : null}
      {current?.kind === "approval" && current.unit ? (
        <ApprovalReview
          world="explore"
          unit={current.unit}
          position={position}
          total={Math.max(total, 1)}
          approveLabel="Approve and publish"
          busyLabel="Publishing…"
          approverRole="Legal approver"
          busy={busy}
          onApprove={() => onApprove(current.unit?.unit_id || current.id)}
          onDecline={(reason) => onDecline(current.unit?.unit_id || current.id, reason)}
        />
      ) : null}
      {current?.kind === "conflict" && current.conflict ? (
        <>
          <header className="legal-top">
            <strong className="desk-top__brand">
              Harbor Health <span>Single Source · Legal review</span>
            </strong>
            <span className="desk-top__queue">
              Item {position} of {Math.max(total, 1)}
            </span>
          </header>
          <div className="studio-scroll">
            <ConflictColumns
              plan={current.conflict}
              busy={busy}
              autoFocus
              onResolve={(reason) => onResolve(current.conflict?.id || current.id, reason)}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

const OTHER_MAIL = [
  { from: "Compliance calendar", time: "Yesterday", subject: "Annual notice of change review starts Monday", preview: "Reviewers are assigned by plan. Your list is attached." },
  { from: "Dana Okafor", time: "Mon", subject: "Re: Specialty pharmacy wording", preview: "Thanks. The v1 wording is the one we signed last year." },
  { from: "Single Source", time: "Oct 28", subject: "Weekly digest: 3 units approved, 1 sent back", preview: "Approval time this week: 1.4 days on average." },
];

/** Every source change waiting for Legal, one at a time, on the same full page as the other reviews. */
function SourceChangesStage({
  items,
  total,
  busy,
  problem,
  onBack,
  act,
}: {
  items: AuthorDrift[];
  total: number;
  busy: string | null;
  problem: string | null;
  onBack: () => void;
  act: (id: number, action: DriftAction, body: { reason?: string; text?: string }) => Promise<unknown>;
}) {
  const current = items[0];
  const position = current ? total - items.length + 1 : total;
  return (
    <div className="review-page" data-theme="tools">
      <div className="legal-bar">
        <Button variant="tertiary" onClick={onBack}>
          Back to email
        </Button>
      </div>
      <header className="legal-top">
        <strong className="desk-top__brand">
          Harbor Health <span>Single Source · Legal review</span>
        </strong>
        <span className="desk-top__queue">
          Source change {position} of {Math.max(total, 1)}
        </span>
      </header>
      <div className="studio-scroll">
        {current ? (
          <DriftReview key={current.id} item={current} who="legal" busy={busy} problem={problem} act={(action, body) => act(current.id, action, body)} />
        ) : (
          <EmptyState heading="All caught up" reason="Every source change has a decision." />
        )}
      </div>
    </div>
  );
}
