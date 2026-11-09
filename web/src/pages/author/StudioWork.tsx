import { useEffect, useMemo, useState } from "react";
import {
  approveAuthor,
  editGapDraft,
  editReturnedUnit,
  getAuthorDocuments,
  getAuthorDrift,
  getAuthorEdits,
  actOnAuthorDrift,
  getGaps,
  getMyWork,
  resolveFeedback,
  sendGapDraft,
  sendReturnedUnit,
  undoWorld,
  type AuthorDocument,
  type AuthorDraft,
  type AuthorDrift,
  type AuthorReturned,
  type MyWorkItem,
} from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { DecisionMarker } from "@/components/decision-marker";
import { EmptyState } from "@/components/empty-state";
import { Field } from "@/components/field";
import { RoutingNote } from "@/components/routing-note";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { showUndoToast } from "@/components/toast";
import { VerbatimBlock } from "@/components/verbatim-block";
import { StudioShell, type StudioSection } from "@/pages/demo/chrome";
import { StudioGaps, StudioLibrary } from "@/pages/author/StudioLibrary";
import { CopiesStep } from "@/pages/demo/steps";
import { DocumentReview } from "@/pages/author/DocumentReview";
import { GapGrounding } from "@/pages/author/GapGrounding";
import { DriftLog, DriftReview } from "@/pages/author/DriftReview";
import { routingWhy } from "@/lib/labels";

type QueueItem =
  | { id: string; group: string; title: string; meta: string; kind: "approve"; work: MyWorkItem }
  | { id: string; group: string; title: string; meta: string; kind: "feedback"; work: MyWorkItem }
  | { id: string; group: string; title: string; meta: string; kind: "draft"; draft: AuthorDraft }
  | { id: string; group: string; title: string; meta: string; kind: "returned"; returned: AuthorReturned }
  | { id: string; group: string; title: string; meta: string; kind: "other"; work: MyWorkItem }
  | { id: string; group: string; title: string; meta: string; kind: "drift"; drift: AuthorDrift }
  | { id: string; group: string; title: string; meta: string; kind: "document"; docId: string };

const GROUP_ORDER = [
  "Documents to review",
  "Sent back by Legal",
  "Unanswered questions",
  "Source changes",
  "Waiting for your approval",
  "Flagged by advocates and channels",
  "Source changed",
  "New extractions to confirm",
];

function gapStatus(draft: AuthorDraft, open: number) {
  if (draft.can_send) return "Ready to send";
  if ((draft.placeholder_sources ?? []).some((source) => source.kind === "request" && !source.quote)) return "Waiting for the expert";
  if ((draft.placeholder_sources ?? []).some((source) => source.sourced)) return `${open} to fill from the source`;
  const trust = draft.candidate?.trust;
  if (trust === "review_backlog" || trust === "approved") return "AI found a Harbor document";
  if (trust === "unreviewed") return "AI found unreviewed text";
  return "No source found";
}

function docMeta(doc: AuthorDocument) {
  return [
    doc.waiting_for_ko ? `${doc.waiting_for_ko} waiting for you` : "none waiting for you",
    doc.with_legal ? `${doc.with_legal} with Legal` : "",
    doc.sent_back ? `${doc.sent_back} sent back` : "",
    doc.approved ? `${doc.approved} approved` : "",
  ]
    .filter(Boolean)
    .join(" · ");
}

function placeholderCount(...texts: string[]) {
  return texts.join(" ").match(/\[[^\]]+\]/g)?.length ?? 0;
}

const EXPLORE_SECTIONS: StudioSection[] = ["work", "sources", "copies", "library", "gaps"];

export function StudioWork() {
  const [section, setSection] = useState<StudioSection>("work");
  const nav = { onNavigate: setSection, sections: EXPLORE_SECTIONS };
  // Sources shows the document turned into units; Copies and conflicts shows the AI's matching and the decisions on it.
  if (section === "sources") {
    return (
      <StudioShell current="sources" onNavigate={setSection} sections={EXPLORE_SECTIONS}>
        <SourcesList />
      </StudioShell>
    );
  }
  if (section === "copies") return <CopiesStep explore={nav} />;
  if (section === "library" || section === "gaps") {
    return (
      <StudioShell current={section} onNavigate={setSection} sections={EXPLORE_SECTIONS}>
        {section === "library" ? <StudioLibrary /> : <StudioGaps />}
      </StudioShell>
    );
  }
  return <MyWork onNavigate={setSection} />;
}

function MyWork({ onNavigate }: { onNavigate: (section: StudioSection) => void }) {
  const [tick, setTick] = useState(0);
  const work = useQuery(`mywork:${tick}`, () => getMyWork());
  const edits = useQuery(`edits:${tick}`, () => getAuthorEdits("explore"));
  const gapList = useQuery(`gaps-x:${tick}`, () => getGaps("explore"));
  const drift = useQuery(`author-drift:${tick}`, () => getAuthorDrift());
  const [docOpen, setDocOpen] = useState<string | null>(null);
  const askedAs = useMemo(() => {
    const map: Record<string, string[]> = {};
    for (const gap of gapList.data?.gaps ?? []) map[gap.id] = gap.queries;
    return map;
  }, [gapList.data]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [sent, setSent] = useState<{ title: string; message: string; reason: string; published?: boolean } | null>(null);

  const items = useMemo<QueueItem[]>(() => {
    const list: QueueItem[] = [];
    const driftById = new Map((drift.data?.items ?? []).map((item) => [`drift-${item.id}`, item]));
    for (const item of work.data?.items ?? []) {
      if (item.kind === "gap" || item.kind === "returned") continue;
      if (item.kind === "document" && item.document) {
        list.push({ id: item.id, group: item.group, title: item.title, meta: docMeta(item.document), kind: "document", docId: item.document.doc_id });
      } else if (item.kind === "drift") {
        const found = driftById.get(item.id);
        if (found)
          list.push({
            id: item.id,
            group: item.group,
            title: found.title || item.title,
            meta: `${found.kind_label || "Source change"} · approved version stays live`,
            kind: "drift",
            drift: found,
          });
      } else if (item.kind === "approve") {
        list.push({ id: item.id, group: item.group, title: item.title, meta: item.unit?.unit_id ?? "", kind: "approve", work: item });
      } else if (item.kind === "feedback") {
        list.push({
          id: item.id,
          group: item.group,
          title: item.feedback?.question || item.title,
          meta: item.feedback?.kind_label || "Flag",
          kind: "feedback",
          work: item,
        });
      } else {
        list.push({ id: item.id, group: item.group, title: item.title, meta: "", kind: "other", work: item });
      }
    }
    for (const returned of edits.data?.returned ?? []) {
      list.push({ id: `ret-${returned.unit_id}`, group: "Sent back by Legal", title: returned.title, meta: returned.unit_id, kind: "returned", returned });
    }
    // Only drafts that follow "no source, no unit" are shown; the older bracket-only draft stays out of the sandbox queue.
    for (const draft of (edits.data?.gaps ?? []).filter((item) => (item.placeholder_sources ?? []).length > 0)) {
      const grounded = draft.placeholder_sources ?? [];
      const open = grounded.length ? grounded.filter((source) => !source.filled).length : draft.open_placeholders.length;
      list.push({
        id: `gap-${draft.id}`,
        group: "Unanswered questions",
        title: draft.draft_title || draft.cluster,
        meta: [
          draft.search_count ? `Asked ${draft.search_count} ${draft.search_count === 1 ? "time" : "times"}` : "",
          gapStatus(draft, open),
        ]
          .filter(Boolean)
          .join(" · "),
        kind: "draft",
        draft,
      });
    }
    const demand = (item: QueueItem) => (item.kind === "draft" ? item.draft.search_count ?? 0 : 0);
    return list.sort((a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group) || demand(b) - demand(a));
  }, [work.data, edits.data, drift.data]);

  // The document item opens its own screen, so the detail pane starts on the first other item.
  const selected = items.find((item) => item.id === selectedId) ?? items.find((item) => item.kind !== "document") ?? null;

  async function run(
    label: string,
    action: () => Promise<{ message: string; routing_reason?: string; undo?: { available?: boolean } }>,
    sentTitle?: string,
  ) {
    setBusy(label);
    setProblem(null);
    try {
      const result = await action();
      const why = routingWhy(result.routing_reason);
      if (sentTitle) setSent({ title: sentTitle, message: result.message, reason: result.routing_reason || "", published: Boolean((result as { published?: boolean }).published) });
      else setSent(null);
      showUndoToast({
        message: why ? `${result.message} ${why.why}` : result.message,
        onUndo: result.undo?.available
          ? () => {
              void undoWorld("explore").then(() => {
                setSent(null);
                setTick((value) => value + 1);
              });
            }
          : undefined,
      });
      setTick((value) => value + 1);
      return true;
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "That did not save. Try again.");
      return false;
    } finally {
      setBusy(null);
    }
  }

  if ((work.loading && !work.data) || (edits.loading && !edits.data)) {
    return (
      <StudioShell current="work" onNavigate={onNavigate} sections={EXPLORE_SECTIONS}>
        <div className="studio-scroll">
          <Skeleton width="280px" height="28px" label="Loading My work" />
          <Skeleton width="100%" height="200px" />
        </div>
      </StudioShell>
    );
  }
  if (work.error || edits.error) {
    return (
      <StudioShell current="work" onNavigate={onNavigate} sections={EXPLORE_SECTIONS}>
        <div className="studio-scroll">
          <ServiceError message={work.error || edits.error || "My work did not load."} onRetry={() => setTick((value) => value + 1)} />
        </div>
      </StudioShell>
    );
  }

  if (docOpen) {
    const docId = docOpen;
    const leave = (next: StudioSection) => {
      setDocOpen(null);
      setTick((value) => value + 1);
      onNavigate(next);
    };
    return (
      <StudioShell current="work" onNavigate={leave} sections={EXPLORE_SECTIONS}>
        <DocumentReview
          docId={docId}
          onBack={() => {
            setDocOpen(null);
            setTick((value) => value + 1);
          }}
        />
      </StudioShell>
    );
  }

  const groups = GROUP_ORDER.map((group) => ({ group, items: items.filter((item) => item.group === group) })).filter((g) => g.items.length);

  return (
    <StudioShell current="work" counts={{ work: items.length }} onNavigate={onNavigate} sections={EXPLORE_SECTIONS}>
      <div className="work">
        <nav className="work-queue" aria-label="My work">
          <div className="work-queue__head">
            <h1 className="tools-title-sm">My work</h1>
            <span className="hh-meta">{items.length} items</span>
          </div>
          {groups.map((group) => (
            <section key={group.group} className="work-group">
              <h2 className="tools-overline work-group__title">
                {group.group} <span className="hh-count">{group.items.length}</span>
              </h2>
              {group.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="work-item"
                  aria-current={selected?.id === item.id ? "true" : undefined}
                  onClick={() => {
                    if (item.kind === "document") {
                      setDocOpen(item.docId);
                      return;
                    }
                    setSelectedId(item.id);
                    setProblem(null);
                    setSent(null);
                  }}
                >
                  <span className="work-item__title">{item.title}</span>
                  {item.meta ? <span className="work-item__meta">{item.meta}</span> : null}
                </button>
              ))}
            </section>
          ))}
        </nav>
        <section className="work-detail" aria-live="polite">
          {sent ? (
            <article className="hh-card work-sent">
              <div className="item-head">
                <div className="item-head__text">
                  <h2 className="tools-title-sm">{sent.title}</h2>
                  <p className="item-head__meta">{sent.message}</p>
                </div>
                <div className="item-head__badges">
                  {sent.published ? <StatusBadge variant="approved">Approved</StatusBadge> : <StatusBadge variant="review">Waiting for approval</StatusBadge>}
                </div>
              </div>
              <RoutingNote reason={sent.reason} />
              <p className="hh-meta">
                {sent.published ? "Search can use it now." : "It stays out of search until the approver decides."} Undo is in the notice at the bottom of the
                screen.
              </p>
            </article>
          ) : null}
          {!selected ? (
            <>
              <EmptyState
                heading="Nothing needs you right now"
                reason="Items arrive here when a document is extracted, Legal sends a unit back, a question has no approved answer, or a source changes."
              />

            </>
          ) : null}
          {selected?.kind === "approve" ? (
            <ApproveDetail item={selected.work} busy={busy} problem={problem} onApprove={(unitId) => void run("Approving…", () => approveAuthor(unitId, "explore"))} />
          ) : null}
          {selected?.kind === "feedback" ? (
            <FeedbackDetail
              key={selected.id}
              item={selected.work}
              busy={busy}
              problem={problem}
              onResolve={(id, note) => void run("Resolving…", () => resolveFeedback(id, note, "explore"))}
            />
          ) : null}
          {selected?.kind === "draft" && (selected.draft.placeholder_sources ?? []).length ? (
            <GapGrounding key={selected.id} draft={selected.draft} askedAs={askedAs[selected.draft.id] ?? []} busy={busy} problem={problem} run={run} />
          ) : null}
          {selected?.kind === "drift" ? (
            <DriftReview
              key={selected.id}
              item={selected.drift}
              who="ko"
              busy={busy}
              problem={problem}
              act={(action, body) => run(action, () => actOnAuthorDrift(selected.drift.id, action, body))}
            />
          ) : null}
          {selected?.kind === "draft" && !(selected.draft.placeholder_sources ?? []).length ? (
            <DraftEditor
              key={selected.id}
              title={selected.title}
              subtitle={`${askedLabel(askedAs[selected.draft.id]?.length ?? 0, selected.draft.search_count)} · ${typeLabel(selected.draft.draft_type)}`}
              initialText={selected.draft.draft_text}
              initialMember={selected.draft.draft_member_text}
              invented={selected.draft.invented_figures}
              askedAs={askedAs[selected.draft.id] ?? []}
              busy={busy}
              problem={problem}
              onSave={(text, member) => run("Saving…", () => editGapDraft(selected.draft.id, text, member))}
              onSend={() => run("Sending…", () => sendGapDraft(selected.draft.id), selected.title)}
            />
          ) : null}
          {selected?.kind === "returned" ? (
            <DraftEditor
              key={selected.id}
              title={selected.title}
              subtitle={(selected.returned.reason || selected.returned.notes) ? `Legal sent this back: ${selected.returned.reason || selected.returned.notes}` : "Legal sent this back."}
              initialText={selected.returned.text}
              initialMember={selected.returned.member_text}
              invented={[]}
              askedAs={[]}
              busy={busy}
              problem={problem}
              onSave={(text, member) => run("Saving…", () => editReturnedUnit(selected.returned.unit_id, text, member))}
              onSend={() => run("Sending…", () => sendReturnedUnit(selected.returned.unit_id), selected.title)}
            />
          ) : null}
          {selected?.kind === "other" ? (
            <article className="hh-card">
              <h2 className="tools-title">{selected.title}</h2>
              <p className="tools-body">This item is shown in the guided demo.</p>
            </article>
          ) : null}
        </section>
      </div>
    </StudioShell>
  );
}

/** Every source document, with where its units stand. Opening one shows the document beside its units. */
function SourcesList() {
  const docs = useQuery("sources-list", () => getAuthorDocuments(true));
  const drift = useQuery("sources-drift-log", () => getAuthorDrift());
  const [open, setOpen] = useState<string | null>(null);
  if (open) return <DocumentReview docId={open} onBack={() => setOpen(null)} />;
  if (docs.loading && !docs.data) return <Skeleton width="100%" height="200px" label="Loading source documents" />;
  if (docs.error || !docs.data) return <ServiceError message={docs.error || "The documents did not load."} onRetry={docs.reload} />;
  return (
    <div className="studio-scroll">
      <h1 className="tools-title">Source documents</h1>
      <p className="tools-body">Each document and the knowledge units extracted from it. Open one to see every unit beside the passage it came from.</p>
      <ul className="sources-list">
        {docs.data.documents.map((doc) => (
          <li key={doc.doc_id}>
            <button type="button" className="work-item" onClick={() => setOpen(doc.doc_id)}>
              <span className="work-item__title">{doc.name && doc.name !== doc.doc_id ? doc.name : doc.title}</span>
              <span className="work-item__meta">
                <span className="hh-id">{doc.doc_id}</span> · {docMeta(doc)}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <DriftLog automatic={drift.data?.automatic ?? []} />
    </div>
  );
}

function askedLabel(questions: number, count?: number) {
  const n = count ?? questions;
  if (!n) return "Asked with no approved answer";
  return `Asked ${n} ${n === 1 ? "time" : "times"} with no approved answer`;
}

function typeLabel(type: string) {
  const labels: Record<string, string> = { verbatim: "Verbatim", policy: "Policy", procedure: "Procedure", faq: "FAQ" };
  return labels[type] || type || "Unit";
}

function ApproveDetail({
  item,
  busy,
  problem,
  onApprove,
}: {
  item: MyWorkItem;
  busy: string | null;
  problem: string | null;
  onApprove: (unitId: string) => void;
}) {
  const unit = item.unit;
  if (!unit) return null;
  return (
    <article className="work-card">
      <div className="item-head">
        <div className="item-head__text">
          <h2 className="tools-title">{unit.title}</h2>
          <p className="item-head__meta">
            <span className="hh-id">{unit.unit_id}</span>
          </p>
        </div>
        <div className="item-head__badges">
          <StatusBadge variant="neutral">{typeLabel(unit.type)}</StatusBadge>
          <StatusBadge variant="review">Waiting for your approval</StatusBadge>
        </div>
      </div>
      <p className="tools-body">Procedures and FAQs do not need Legal. You approve them, and search can use them at once.</p>
      <RoutingNote reason={unit.routing_reason} heading="Why this came to you" />
      {unit.type === "verbatim" ? <VerbatimBlock text={unit.text} /> : <p className="work-text">{unit.text}</p>}
      <div className="work-actions">
        <DecisionMarker kind="pending" role="Knowledge Ops author" />
        <Button onClick={() => onApprove(unit.unit_id)} busy={busy === "Approving…"} busyLabel="Approving…" disabled={Boolean(busy)}>
          Approve as Knowledge Ops
        </Button>
      </div>
      {problem ? <p className="hh-error" role="alert">{problem}</p> : null}
    </article>
  );
}

function FeedbackDetail({
  item,
  busy,
  problem,
  onResolve,
}: {
  item: MyWorkItem;
  busy: string | null;
  problem: string | null;
  onResolve: (id: number, note: string) => void;
}) {
  const feedback = item.feedback;
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  if (!feedback) return null;
  return (
    <article className="work-card">
      <div className="item-head">
        <div className="item-head__text">
          <h2 className="tools-title">{feedback.kind_label || "Flagged answer"}</h2>
          <p className="item-head__meta">
            <span>From an advocate or channel</span>
            {feedback.unit_id ? (
              <>
                <span aria-hidden="true">·</span>
                <span className="hh-id">{feedback.unit_id}</span>
              </>
            ) : null}
          </p>
        </div>
        <div className="item-head__badges">
          <StatusBadge variant="review">Open</StatusBadge>
        </div>
      </div>
      <blockquote className="work-quote">{feedback.question || "No question recorded."}</blockquote>
      {feedback.note ? <p className="tools-body">Note: {feedback.note}</p> : null}
      <p className="hh-meta">Member details were removed before this was stored.</p>
      <Field
        id={`resolve-${feedback.id}`}
        label="Resolution"
        hint="Required. Saved with the record."
        placeholder="For example: rewrote the member sentence and sent it to Legal…"
        value={note}
        error={error || undefined}
        onChange={(event) => {
          setNote(event.target.value);
          setError("");
        }}
      />
      <div className="work-actions">
        <Button
          onClick={() => {
            if (!note.trim()) {
              setError("Add a resolution note. It is saved with the record.");
              return;
            }
            onResolve(feedback.id, note.trim());
          }}
          busy={busy === "Resolving…"}
          busyLabel="Resolving…"
          disabled={Boolean(busy)}
        >
          Resolve
        </Button>
      </div>
      {problem ? <p className="hh-error" role="alert">{problem}</p> : null}
    </article>
  );
}

function DraftEditor({
  title,
  subtitle,
  initialText,
  initialMember,
  invented,
  askedAs,
  busy,
  problem,
  onSave,
  onSend,
}: {
  title: string;
  subtitle: string;
  initialText: string;
  initialMember: string;
  invented: string[];
  askedAs: string[];
  busy: string | null;
  problem: string | null;
  onSave: (text: string, member: string) => Promise<boolean>;
  onSend: () => Promise<boolean>;
}) {
  const [text, setText] = useState(initialText);
  const [member, setMember] = useState(initialMember);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    setText(initialText);
    setMember(initialMember);
    setDirty(false);
  }, [initialText, initialMember]);
  const open = placeholderCount(text, member);

  return (
    <article className="work-card">
      <div className="item-head">
        <div className="item-head__text">
          <h2 className="tools-title">{title}</h2>
          <p className="item-head__meta">{subtitle}</p>
        </div>
        <div className="item-head__badges">
          <DecisionMarker kind="ai" />
          {open ? (
            <StatusBadge variant="review">{`${open} ${open === 1 ? "placeholder" : "placeholders"} left`}</StatusBadge>
          ) : (
            <StatusBadge variant="approved">Ready to send</StatusBadge>
          )}
        </div>
      </div>
      <p className="tools-body">
        Replace every bracketed placeholder with a fact from an approved source. Then send it to approval. Legal sees policy and verbatim units; you
        approve procedures and FAQs.
      </p>
      {askedAs.length ? (
        <div className="work-asked">
          <p className="tools-label">Asked as</p>
          <ul>
            {askedAs.map((question) => (
              <li key={question}>&ldquo;{question}&rdquo;</li>
            ))}
          </ul>
          <p className="hh-meta">Once approved, search answers these questions with this unit.</p>
        </div>
      ) : null}
      {invented.length ? <StatusBadge variant="blocked">{`Check these figures against a source: ${invented.join(", ")}`}</StatusBadge> : null}
      <Field
        id="draft-text"
        label="Advocate wording"
        multiline
        rows={9}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setDirty(true);
        }}
      />
      <Field
        id="draft-member"
        label="Member wording"
        optional
        multiline
        rows={4}
        value={member}
        onChange={(event) => {
          setMember(event.target.value);
          setDirty(true);
        }}
      />
      <div className="work-actions">
        <Button
          variant="secondary"
          disabled={Boolean(busy) || !dirty}
          busy={busy === "Saving…"}
          busyLabel="Saving…"
          onClick={() => {
            void onSave(text, member).then((ok) => ok && setDirty(false));
          }}
        >
          Save draft
        </Button>
        <Button
          disabled={Boolean(busy)}
          busy={busy === "Sending…"}
          busyLabel="Sending…"
          onClick={() => {
            const go = dirty ? onSave(text, member).then((ok) => (ok ? onSend() : false)) : onSend();
            void go;
          }}
        >
          Send to approval
        </Button>
      </div>
      {problem ? <p className="hh-error" role="alert">{problem}</p> : null}
    </article>
  );
}
