import { Check, Copy } from "lucide-react";
import { useState, type FormEvent } from "react";
import { getFeedbackProduct, getPortalAnswers, getPortalEvents, getPortalQuickStart } from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Button } from "@/components/button";
import { EmptyState } from "@/components/empty-state";
import { RankedBars } from "@/components/ranked-bars";
import { ServiceError } from "@/components/service-state";
import { Skeleton } from "@/components/skeleton";
import { showUndoToast } from "@/components/toast";

const SECTIONS = [
  { id: "quick-start", label: "Quick start" },
  { id: "reference", label: "API reference" },
  { id: "try", label: "Try it" },
  { id: "events", label: "Change events" },
  { id: "backlog", label: "Product backlog" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

const KIND_LABELS: Record<string, string> = {
  hard_to_find: "Hard to find",
  rephrased: "Member rephrased the question",
  clarified: "Bot had to ask a clarifying question",
  handed_off: "Bot handed off to a person",
  slow: "Slow to answer",
};

const BASE = "https://api.harborhealth.example/v1";

export function DocsPage() {
  const [section, setSection] = useState<SectionId>("quick-start");
  return (
    <div className="docs">
      <header className="docs-top">
        <strong className="desk-top__brand">
          Harbor Health <span>Knowledge API</span>
        </strong>
        <span className="docs-top__tag">Developer docs · Mock portal</span>
        <span className="desk-top__user">
          <span className="avatar" aria-hidden="true">
            CT
          </span>
          Channel and AI team
        </span>
      </header>
      <div className="docs-layout">
        <nav className="docs-nav" aria-label="Docs">
          <p className="tools-overline docs-nav__group">Guides</p>
          {SECTIONS.map((item) => (
            <button key={item.id} type="button" aria-current={section === item.id ? "page" : undefined} onClick={() => setSection(item.id)}>
              {item.label}
            </button>
          ))}
        </nav>
        <main className="docs-main">
          {section === "quick-start" ? <QuickStart /> : null}
          {section === "reference" ? <Reference /> : null}
          {section === "try" ? <TryIt /> : null}
          {section === "events" ? <Events /> : null}
          {section === "backlog" ? <Backlog /> : null}
        </main>
      </div>
    </div>
  );
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="docs-code">
      <div className="docs-code__bar">
        <span>{language}</span>
        <Button
          variant="tertiary"
          compact
          onClick={() => {
            void navigator.clipboard?.writeText(code).catch(() => undefined);
            setCopied(true);
            showUndoToast({ message: "Copied to the clipboard." });
            window.setTimeout(() => setCopied(false), 1600);
          }}
        >
          {copied ? <Check aria-hidden="true" width={16} /> : <Copy aria-hidden="true" width={16} />}
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <pre tabIndex={0} aria-label={`${language} example`}>
        <code>{code}</code>
      </pre>
    </div>
  );
}

function QuickStart() {
  const quick = useQuery("portal-quick", () => getPortalQuickStart("explore"));
  if (quick.loading && !quick.data) return <Skeleton width="100%" height="240px" label="Loading the quick start" />;
  if (quick.error || !quick.data) return <ServiceError message={quick.error || "The quick start did not load."} onRetry={quick.reload} />;
  const unitId = (quick.data.sample_unit?.unit_id as string) || "UNIT_ID";
  return (
    <article className="docs-article">
      <p className="tools-overline">Quick start</p>
      <h1 className="docs-h1">Render approved knowledge in your channel</h1>
      <p className="docs-lead">
        Every answer your channel shows comes from an approved unit, by reference. Fetch the unit, render the text for your audience with its citation, and
        subscribe to changes so a Legal revision reaches your channel at once.
      </p>
      <h2 className="docs-h2">1. Request an approved unit for your channel</h2>
      <CodeBlock language="bash" code={`curl -H "Authorization: Bearer YOUR_API_TOKEN" \\\n  "${BASE}/units/${unitId}?channel=member_chat"`} />
      <h2 className="docs-h2">2. Render the text for your audience, with its citation</h2>
      <p className="docs-p">Use the member text in member channels and the advocate text in advocate tools. Always show the citation. Never edit the text.</p>
      {quick.data.sample_unit ? <CodeBlock language="json" code={JSON.stringify(quick.data.sample_unit, null, 2)} /> : <EmptyState heading="No approved unit yet" reason="Approve a unit, then reload this page." />}
      <h2 className="docs-h2">3. Subscribe to changes</h2>
      <p className="docs-p">When Legal publishes a new version, you receive unit.revised. Fetch the unit again and replace your cached copy.</p>
      {quick.data.sample_event ? <CodeBlock language="json" code={JSON.stringify(quick.data.sample_event, null, 2)} /> : null}
      <p className="docs-p">
        Register a webhook to receive events as they happen. Each delivery is signed with HMAC-SHA256 using the secret returned at registration. Page
        through past events with <code>cursor</code> and <code>next_cursor</code>.
      </p>
      <CodeBlock
        language="bash"
        code={`curl -X POST -H "Authorization: Bearer YOUR_API_TOKEN" \\\n  -d '{"url": "https://your-channel.example/hooks", "events": ["unit.revised", "unit.retracted"]}' \\\n  "${BASE}/webhooks"`}
      />
      <h2 className="docs-h2">4. The full contract</h2>
      <p className="docs-p">
        The OpenAPI description lists every route, field and error. Errors use problem JSON with <code>type</code>, <code>title</code>, <code>status</code>,{" "}
        <code>detail</code> and, where useful, the <code>allowed</code> values.{" "}
        <a href="/api/portal/openapi.json" target="_blank" rel="noreferrer">
          Open the OpenAPI description
        </a>
        .
      </p>
      <p className="hh-meta">Mock portal. Responses come from this sandbox&apos;s approved units, so they match what the channels render.</p>
    </article>
  );
}

function Reference() {
  const quick = useQuery("portal-quick", () => getPortalQuickStart("explore"));
  if (quick.loading && !quick.data) return <Skeleton width="100%" height="240px" label="Loading the reference" />;
  if (quick.error || !quick.data) return <ServiceError message={quick.error || "The reference did not load."} onRetry={quick.reload} />;
  return (
    <article className="docs-article">
      <p className="tools-overline">API reference</p>
      <h1 className="docs-h1">Endpoints</h1>
      <p className="docs-lead">Every response returns approved wording and a citation, or an explicit no-answer. The API never generates text.</p>
      <div className="docs-endpoints">
        {quick.data.endpoints.map((endpoint) => (
          <div key={endpoint.path} className="docs-endpoint">
            <span className={`docs-method docs-method--${endpoint.method.toLowerCase()}`}>{endpoint.method}</span>
            <code>{endpoint.path.replace("/api/portal", "/v1").replace("/api/", "/v1/")}</code>
            <p>{endpoint.what}</p>
          </div>
        ))}
      </div>
    </article>
  );
}

function TryIt() {
  const [question, setQuestion] = useState("what do I say before I quote a cost");
  const [role, setRole] = useState("Pharmacy advocate");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) {
      setError("Enter a question.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setResult(await getPortalAnswers(question.trim(), role));
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "The request failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="docs-article">
      <p className="tools-overline">Try it</p>
      <h1 className="docs-h1">GET /v1/answers</h1>
      <p className="docs-lead">One cited unit for a question, scoped to the role&apos;s knowledge bases, or an explicit no-answer.</p>
      <form className="docs-try" onSubmit={send}>
        <label className="hh-label" htmlFor="try-q">
          question
        </label>
        <input id="try-q" className="hh-input" value={question} onChange={(event) => setQuestion(event.target.value)} autoComplete="off" />
        <label className="hh-label" htmlFor="try-role">
          role
        </label>
        <select id="try-role" className="hh-input" value={role} onChange={(event) => setRole(event.target.value)}>
          <option>Pharmacy advocate</option>
          <option>Insurance advocate</option>
          <option>Member</option>
        </select>
        <div>
          <Button type="submit" busy={busy} busyLabel="Sending…">
            Send request
          </Button>
        </div>
        {error ? (
          <p className="hh-error" role="alert">
            {error}
          </p>
        ) : null}
      </form>
      <CodeBlock language="http" code={`GET ${BASE}/answers?question=${encodeURIComponent(question)}&role=${encodeURIComponent(role)}`} />
      {result ? <CodeBlock language="json · 200 OK" code={JSON.stringify(result, null, 2)} /> : null}
    </article>
  );
}

function Events() {
  const events = useQuery("portal-events", () => getPortalEvents("explore"));
  if (events.loading && !events.data) return <Skeleton width="100%" height="200px" label="Loading events" />;
  if (events.error || !events.data) return <ServiceError message={events.error || "Events did not load."} onRetry={events.reload} />;
  return (
    <article className="docs-article">
      <p className="tools-overline">Change events</p>
      <h1 className="docs-h1">Webhooks</h1>
      <p className="docs-lead">Subscribe to unit.revised, unit.retired and unit.flagged. Below is what a subscriber would have received from this sandbox, newest first.</p>
      {events.data.events.length === 0 ? (
        <EmptyState
          heading="No change events yet"
          reason="Events appear here when Legal publishes a revision, resolves a conflict, or a source change flags a unit. Try it as the Legal approver, then come back."
        />
      ) : (
        events.data.events.map((event, index) => <CodeBlock key={index} language={String(event.event)} code={JSON.stringify(event, null, 2)} />)
      )}
    </article>
  );
}

function Backlog() {
  const backlog = useQuery("portal-backlog", () => getFeedbackProduct("explore"));
  if (backlog.loading && !backlog.data) return <Skeleton width="100%" height="200px" label="Loading the backlog" />;
  if (backlog.error || !backlog.data) return <ServiceError message={backlog.error || "The backlog did not load."} onRetry={backlog.reload} />;
  return (
    <article className="docs-article">
      <p className="tools-overline">Product backlog</p>
      <h1 className="docs-h1">Findability issues from advocates and channels</h1>
      <p className="docs-lead">
        Questions that were hard to find, slow, rephrased, clarified or handed off. Content problems go to the knowledge author instead. Member details
        are removed before anything is stored.
      </p>
      {backlog.data.groups.length === 0 ? (
        <EmptyState heading="Nothing open" reason="New findability issues appear here as they are captured." />
      ) : (
        <>
          <RankedBars
            rows={backlog.data.groups.map((group) => ({
              label: KIND_LABELS[group.kind] || group.kind,
              detail: group.examples.map((example) => `“${example}”`).join("; "),
              count: group.count,
            }))}
          />
          <p className="hh-meta">{backlog.data.total} open issues. Illustrative.</p>
        </>
      )}
    </article>
  );
}
