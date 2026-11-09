import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { memberAnswer } from "@/api/client";
import { useQuery } from "@/api/use-query";
import { ChatLauncher, ChatPanel } from "@/components/chat";
import { ServiceError } from "@/components/service-state";
import { AnswerSkeleton } from "@/components/skeleton";
import { memberUpdated, plainMemberTitle } from "@/pages/member/plain";
import { readableDate } from "@/lib/dates";
import { useMemberChat } from "@/pages/member/use-member-chat";
import { DrugEstimator, VisitEstimator } from "@/pages/member/estimators";
import { TextSizeControl, useMemberTextSize } from "@/pages/member/text-size";
import { approvedUnit, memberProfile, requestAuthorizedCaller } from "@/api/client";
import { Glossary } from "@/pages/member/glossary";
import type { UnitRef } from "@/api/types";
import { memberCite } from "@/components/quote-card";

const VISIT_TOPIC = "Cost of a doctor visit";

/** The help topic that duplicates the estimator page opens the estimator instead. */
const ESTIMATOR_TOPIC = "Drug price estimates";

const ARTICLE_LEADS: Record<string, string> = {
  "Cost of a doctor visit": "What you pay depends on the kind of visit and whether the doctor is in your network.",
  "Specialist referrals": "Before you book a specialist, check whether you need a referral.",
  "Specialty pharmacy": "Where specialty drugs are filled and how they reach you.",
  "Someone calling for me": "Let a family member or caregiver call Harbor about your drugs.",
};

const PAGES = [
  { id: "find-care", label: "Find care" },
  { id: "drug-costs", label: "Drug costs" },
  { id: "plans", label: "Plans" },
  { id: "help", label: "Member help" },
] as const;

type PageId = (typeof PAGES)[number]["id"] | "sign-in" | "article";

type MemberSiteProps = {
  sessionId: string | null;
  sessionError?: string | null;
  onRetry?: () => void;
};

export function MemberSite({ sessionId, sessionError, onRetry }: MemberSiteProps) {
  const [params, setParams] = useSearchParams();
  const chatOpen = params.get("chat") === "open";
  // When chat closes, put focus back on the button that opens it, so keyboard and screen reader users keep their place.
  const chatWasOpen = useRef(chatOpen);
  useEffect(() => {
    if (chatWasOpen.current && !chatOpen) document.querySelector<HTMLButtonElement>(".member-launcher .hh-launcher")?.focus();
    chatWasOpen.current = chatOpen;
  }, [chatOpen]);
  const requestedPage = (params.get("page") as PageId | null) || "drug-costs";
  const [signedIn, setSignedIn] = useState(true);
  const text = useMemberTextSize();
  const page: PageId = requestedPage === "article" && params.get("topic") === ESTIMATOR_TOPIC ? "drug-costs" : requestedPage;
  const topicLabel = params.get("topic") || "";
  const topics = useMemberChat(sessionId, () => {
    const next = new URLSearchParams(params);
    next.delete("chat");
    next.set("page", "article");
    next.set("topic", "Someone calling for me");
    setParams(next);
  });
  /** Pages with an estimator show the approved wording with the estimate, so they fetch no separate article. */
  const hasEstimator = page === "drug-costs" || (page === "article" && topicLabel === VISIT_TOPIC);
  const articleQuestion =
    page === "article" && !hasEstimator ? topics.topics.data?.find((topic) => topic.label === topicLabel)?.question || "" : "";
  const article = useQuery(
    `article:${sessionId ?? "none"}:${articleQuestion}`,
    () => memberAnswer(sessionId as string, articleQuestion),
    Boolean(sessionId && articleQuestion),
  );

  function setChat(open: boolean) {
    const next = new URLSearchParams(params);
    if (open) next.set("chat", "open");
    else next.delete("chat");
    setParams(next, { replace: true });
  }

  /** "find-care#doctor" opens Find care at its doctor section. */
  function pageParams(target: string, topic = "") {
    const [nextPage, section] = target.split("#");
    const next = new URLSearchParams(params);
    if (section) next.set("section", section);
    else next.delete("section");
    if (nextPage === "drug-costs") next.delete("page");
    else next.set("page", nextPage);
    if (topic) next.set("topic", topic);
    else next.delete("topic");
    next.delete("chat");
    return next;
  }

  function openPage(nextPage: string, topic = "") {
    setParams(pageParams(nextPage, topic));
  }

  /** Navigation is a real link: it can be opened in a new tab, and screen readers announce it as a link. */
  function linkProps(nextPage: string) {
    return {
      href: `?${pageParams(nextPage).toString()}`,
      onClick: (event: ReactMouseEvent<HTMLAnchorElement>) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
        event.preventDefault();
        openPage(nextPage);
      },
    };
  }

  return (
    <div data-theme="member" className="hh-m member-site">
      <header className="member-header" aria-label="Harbor Health">
        <a className="member-wordmark" {...linkProps("drug-costs")}>
          Harbor Health
        </a>
        <nav aria-label="Site" className="member-nav">
          {PAGES.map((item) => (
            <a key={item.id} className="member-nav__link" aria-current={page === item.id ? "page" : undefined} {...linkProps(item.id)}>
              {item.label}
            </a>
          ))}
        </nav>
        <div className="member-header__tools">
        <TextSizeControl size={text.size} onChange={text.setSize} />
        {signedIn ? (
          <span className="member-user">
            <span className="member-user__avatar" aria-hidden="true">
              DR
            </span>
            <span className="member-user__name">Dana R.</span>
            <button
              className="member-textlink"
              type="button"
              onClick={() => {
                setSignedIn(false);
                openPage("sign-in");
              }}
            >
              Sign out
            </button>
          </span>
        ) : (
          <button className="hh-btn hh-btn--secondary" type="button" onClick={() => openPage("sign-in")}>
            Sign in
          </button>
        )}
        </div>
      </header>
      <main>
        {page === "sign-in" && signedIn ? (
          <div className="member-page member-article">
            <h1 className="member-display">You are signed in</h1>
            <p className="member-body">You are signed in as the fictional member Dana R.</p>
            <p>
              <a className="hh-btn hh-btn--secondary" {...linkProps("drug-costs")}>
                Go to drug costs
              </a>
            </p>
          </div>
        ) : null}
        {page === "sign-in" && !signedIn ? (
          <SignIn
            onSignedIn={() => {
              setSignedIn(true);
              openPage("drug-costs");
            }}
          />
        ) : null}
        {page === "find-care" ? <FindCare /> : null}
        {page === "plans" ? <PlanSummary /> : null}
        {page === "help" ? (
          <HelpIndex
            topics={topics.topics.data}
            error={topics.topics.error}
            onOpen={(label) => (label === "drug-costs" || label === ESTIMATOR_TOPIC ? openPage("drug-costs") : openPage("article", label))}
          />
        ) : null}
        {page === "drug-costs" || page === "article" ? (
          <article className="member-page">
            <nav aria-label="Breadcrumb" className="member-meta member-crumb">
              <ol>
                <li>
                  <a className="member-textlink" {...linkProps("drug-costs")}>
                    Home
                  </a>
                </li>
                <li>
                  <a className="member-textlink" {...linkProps("help")}>
                    Member help
                  </a>
                </li>
                <li aria-current="page">{page === "article" ? topicLabel || "Help article" : "Estimate a drug price"}</li>
              </ol>
            </nav>
            <div className="member-split">
              <div className="member-article">
                <h1 className="member-display">{page === "article" ? topicLabel || "Help article" : "Estimate a drug price"}</h1>
                <p className="member-body-lg">
                  {page === "article" ? ARTICLE_LEADS[topicLabel] || "" : "See what a prescription may cost before you fill it."}
                </p>
                {sessionError ? <ServiceError message={sessionError} onRetry={onRetry} /> : null}
                {!sessionId && !sessionError ? (
                  <ServiceError message="Explore mode needs a session from the API before this page can show an approved answer." />
                ) : null}
                {sessionId && page === "article" && !hasEstimator && !articleQuestion && !topics.topics.loading ? (
                  <ServiceError message="That help topic is not on the list from the knowledge service." />
                ) : null}
                {article.showSkeleton ? <AnswerSkeleton /> : null}
                {article.error ? <ServiceError message={article.error} onRetry={article.reload} /> : null}
                {article.data ? <ArticleBody answer={article.data} /> : null}
                {sessionId && page === "drug-costs" ? <DrugEstimator /> : null}
                {sessionId && page === "article" && topicLabel === VISIT_TOPIC ? <VisitEstimator /> : null}
                {page === "article" && topicLabel === "Someone calling for me" ? <AuthorizedCallerForm /> : null}
                {page === "drug-costs" ? (
                  <>
                    <h2 className="member-h3 member-section-h">Related help</h2>
                    <div className="member-related">
                      <button type="button" className="member-related__card" onClick={() => setChat(true)}>
                        <strong>Can my specialty drug come by mail?</strong>
                        <span>Ask Harbor</span>
                      </button>
                      <button type="button" className="member-related__card" onClick={() => openPage("help")}>
                        <strong>Someone calling for me</strong>
                        <span>Member help</span>
                      </button>
                      <button type="button" className="member-related__card" onClick={() => openPage("find-care")}>
                        <strong>Find a pharmacy near you</strong>
                        <span>Find care</span>
                      </button>
                    </div>
                  </>
                ) : null}
              </div>
              <section className="hh-card member-help-card" aria-label="Get help">
                <h2 className="member-h3">Get help</h2>
                <SiteSentence unitId="U-SITE-HELP-001" />
                <button className="hh-btn hh-btn--secondary" type="button" onClick={() => setChat(true)}>
                  Ask Harbor
                </button>
              </section>
            </div>
          </article>
        ) : null}
      </main>
      <SiteFooter linkProps={linkProps} />
      <aside className="member-launcher" aria-label="Ask Harbor">
        {chatOpen ? (
          <ChatPanel
            items={topics.items}
            pending={topics.pending}
            onClose={() => setChat(false)}
            onSend={(text) => void topics.ask(text)}
            onChip={topics.onChip}
            onHelp={(yes) => void topics.onHelp(yes)}
            onHandoff={topics.onHandoff}
          />
        ) : (
          <ChatLauncher open={chatOpen} onToggle={() => setChat(true)} />
        )}
      </aside>
    </div>
  );
}

function ArticleBody({
  answer,
}: {
  answer: { abstained: boolean; member_text: string; title: string; updated?: string; effective_date?: string };
}) {
  if (answer.abstained || !answer.member_text) {
    return <p className="member-body">I don't have an approved answer for that yet. I can connect you with a member advocate.</p>;
  }
  const updated = memberUpdated(answer);
  return (
    <>
      <p className="member-body">{answer.member_text}</p>
      <p className="member-meta member-source">
        Harbor Health plan rules: {plainMemberTitle(answer.title)}
        {updated ? `, updated ${readableDate(updated)}` : ""}.
      </p>
    </>
  );
}

function HelpIndex({
  topics,
  error,
  onOpen,
}: {
  topics: { label: string; question: string }[] | null;
  error: string | null;
  onOpen: (label: string) => void;
}) {
  useSection("advocates");
  return (
    <div className="member-page member-article">
      <h1 className="member-display">Member help</h1>
      <p className="member-body-lg">Find answers about your Harbor plan, or ask Harbor in chat.</p>
      <section className="hh-card member-advocates" aria-labelledby="section-advocates">
        <h2 className="member-h3" id="section-advocates" tabIndex={-1}>
          Talk to a member advocate
        </h2>
        <SiteSentence unitId="U-SITE-HELP-001" />
      </section>
      {error ? <ServiceError message={error} /> : null}
      <h2 className="member-h3">Help topics</h2>
      <ul className="member-help-list">
        <li>
          <button type="button" className="member-textlink" onClick={() => onOpen("drug-costs")}>
            Estimate a drug price
          </button>
        </li>
        {(topics ?? []).filter((topic) => topic.label !== ESTIMATOR_TOPIC).map((topic) => (
          <li key={topic.label}>
            <button type="button" className="member-textlink" onClick={() => onOpen(topic.label)}>
              {topic.label}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}


function SignIn({ onSignedIn }: { onSignedIn: () => void }) {
  return (
    <div className="member-page member-article">
      <h1 className="member-display">Sign in</h1>
      <p className="member-body">This illustrative site signs in as the fictional member Dana R. with any member ID and password.</p>
      <SignInFields onSignedIn={onSignedIn} />
    </div>
  );
}

function SignInFields({ onSignedIn }: { onSignedIn: () => void }) {
  const [errors, setErrors] = useState<{ id: string; password: string }>({ id: "", password: "" });
  const idRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  return (
    <form
      className="member-signin"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const memberId = String(data.get("member-id") || "").trim();
        const password = String(data.get("password") || "");
        const next = { id: memberId ? "" : "Enter the member ID on your card.", password: password ? "" : "Enter your password." };
        setErrors(next);
        if (next.id) idRef.current?.focus();
        else if (next.password) passwordRef.current?.focus();
        if (memberId && password) onSignedIn();
      }}
    >
      <p className="member-meta">Both fields are required.</p>
      <label className="hh-label" htmlFor="member-id">
        Member ID
      </label>
      <input
        id="member-id"
        ref={idRef}
        name="member-id"
        className="hh-input"
        autoComplete="username"
        required
        aria-invalid={errors.id ? true : undefined}
        aria-describedby={errors.id ? "member-id-error" : undefined}
        onChange={() => errors.id && setErrors((current) => ({ ...current, id: "" }))}
      />
      {errors.id ? (
        <p className="hh-error" id="member-id-error">
          {errors.id}
        </p>
      ) : null}
      <label className="hh-label" htmlFor="password">
        Password
      </label>
      <input
        id="password"
        ref={passwordRef}
        name="password"
        className="hh-input"
        type="password"
        autoComplete="current-password"
        required
        aria-invalid={errors.password ? true : undefined}
        aria-describedby={errors.password ? "password-error" : undefined}
        onChange={() => errors.password && setErrors((current) => ({ ...current, password: "" }))}
      />
      {errors.password ? (
        <p className="hh-error" id="password-error">
          {errors.password}
        </p>
      ) : null}
      <button className="hh-btn hh-btn--primary" type="submit">
        Sign in
      </button>
      <p className="member-body" data-result role="status" />
    </form>
  );
}

function SiteFooter({ linkProps }: { linkProps: (page: string) => { href: string; onClick: (event: ReactMouseEvent<HTMLAnchorElement>) => void } }) {
  const columns = [
    ["Plans", ["Medicare Advantage", "plans"], ["Drug coverage", "drug-costs"]],
    ["Care", ["Find a doctor", "find-care#doctor"], ["Find a pharmacy", "find-care#pharmacy"]],
    ["Help", ["Estimate a drug price", "drug-costs"], ["Member advocates", "help#advocates"]],
  ] as const;
  return (
    <footer className="member-footer">
      <div className="member-footer__grid">
        {columns.map((column) => (
          <div key={column[0]}>
            <h2 className="member-footer__title">{column[0]}</h2>
            {column.slice(1).map((item) => {
              const [label, page] = item as [string, string];
              return (
                <p key={label} className="member-footer__link">
                  <a {...linkProps(page)}>{label}</a>
                </p>
              );
            })}
          </div>
        ))}
        <div>
          <h2 className="member-footer__title">Call us</h2>
          <p className="member-footer__link">
            <a href="tel:+18005550148">1-800-555-0148</a>
          </p>
          <p className="member-footer__link">8 AM to 8 PM, seven days a week</p>
        </div>
      </div>
      <p className="member-footer__note">Illustrative site. Harbor Health is fictional, and the number and hours are made up.</p>
    </footer>
  );
}

function AuthorizedCallerForm() {
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("Daughter or son");
  const [error, setError] = useState("");
  const [sent, setSent] = useState("");
  const nameRef = useRef<HTMLInputElement>(null);
  const [confirmation, setConfirmation] = useState<{ number: string; unit: UnitRef | null } | null>(null);
  const [busy, setBusy] = useState(false);
  if (sent && confirmation) {
    return (
      <div className="hh-card member-form-done" role="status">
        <p className="member-body">
          <strong>Request recorded.</strong> Confirmation number {confirmation.number}.
        </p>
        {confirmation.unit ? (
          <>
            <p className="member-body">{confirmation.unit.text}</p>
            <p className="quote__cite">{memberCite(confirmation.unit)}</p>
          </>
        ) : null}
        <p className="member-meta">Illustrative site: the request is recorded in this sandbox only.</p>
      </div>
    );
  }
  return (
    <form
      className="hh-card member-form"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        if (!name.trim()) {
          setError("Enter the caller's full name.");
          nameRef.current?.focus();
          return;
        }
        setBusy(true);
        void Promise.all([requestAuthorizedCaller(name.trim(), relationship), approvedUnit("U-BEN-CALLER-CONFIRM-001")])
          .then(([result, unit]) => {
            setConfirmation({ number: result.confirmation || "pending", unit });
            setSent(name.trim());
          })
          .catch((problem) => setError(problem instanceof Error ? problem.message : "The request did not go through. Try again."))
          .finally(() => setBusy(false));
      }}
    >
      <h2 className="member-h3">Add an authorized caller</h2>
      <p className="member-meta">Both fields are required.</p>
      <label className="hh-label" htmlFor="caller-name">
        Caller's full name
      </label>
      <input
        id="caller-name"
        ref={nameRef}
        className="hh-input"
        value={name}
        required
        autoComplete="off"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? "caller-name-error" : undefined}
        onChange={(event) => {
          setName(event.target.value);
          setError("");
        }}
      />
      {error ? (
        <p className="hh-error" id="caller-name-error">
          {error}
        </p>
      ) : null}
      <label className="hh-label" htmlFor="caller-rel">
        Relationship to you
      </label>
      <select id="caller-rel" className="hh-input" value={relationship} onChange={(event) => setRelationship(event.target.value)}>
        <option>Daughter or son</option>
        <option>Spouse or partner</option>
        <option>Other family member</option>
        <option>Caregiver</option>
      </select>
      <div>
        <button className="hh-btn hh-btn--primary" type="submit" disabled={busy}>
          {busy ? "Sending…" : "Send request"}
        </button>
      </div>
    </form>
  );
}

/** Scroll to and focus the section named in ?section=, so a footer link lands on what it says. */
function useSection(id: string) {
  const [params] = useSearchParams();
  const section = params.get("section");
  useEffect(() => {
    if (section !== id) return;
    const target = document.getElementById(`section-${id}`);
    target?.scrollIntoView({ block: "start" });
    target?.focus();
  }, [section, id]);
}

function FindCare() {
  useSection("doctor");
  useSection("pharmacy");
  const profile = useQuery("member-profile", () => memberProfile());
  const pharmacies = ((profile.data?.plan as { pharmacies?: Array<{ name: string; network: string; city: string; display: string }> } | undefined)
    ?.pharmacies ?? []);
  return (
    <div className="member-page member-article">
      <h1 className="member-display">Find care</h1>
      <section aria-labelledby="section-doctor">
        <h2 className="member-h3" id="section-doctor" tabIndex={-1}>
          Find a doctor
        </h2>
        <SiteSentence unitId="U-SITE-FIND-001" />
        <ReferralRule />
      </section>
      <h2 className="member-h3" id="section-pharmacy" tabIndex={-1}>
        Find a pharmacy
      </h2>
      <p className="member-body-lg">Pharmacies in your plan's network.</p>
      {profile.error ? <ServiceError message={profile.error} onRetry={profile.reload} /> : null}
      <ul className="member-list-cards">
        {pharmacies.map((item) => (
          <li key={item.name} className="hh-card">
            <strong>{item.name}</strong>
            <span className="member-tag">{item.display}</span>
            <span className="member-meta">{item.city}</span>
          </li>
        ))}
      </ul>
      <p className="member-meta">Illustrative pharmacies.</p>
    </div>
  );
}

function PlanSummary() {
  const profile = useQuery("member-profile", () => memberProfile());
  const plan = profile.data?.plan as Record<string, { display?: string } | string> | undefined;
  // Each figure travels with the approved wording that explains it. A figure whose wording is not approved is held back.
  const rows: Array<[string, string, string]> = [
    ["Monthly premium", "premium", ""],
    ["Primary care visit", "primary_care", "U-BEN-COST-001-02"],
    ["Specialist visit", "specialist", "U-BEN-COST-001-02"],
    ["Urgent care", "urgent_care", "U-BEN-UC-001"],
    ["Emergency room", "emergency", "U-BEN-ER-001"],
    ["Medical deductible", "medical_deductible", "U-BEN-COST-001-02"],
    ["Out-of-pocket maximum", "out_of_pocket_maximum", "U-BEN-OOP-001"],
    ["Part D drug deductible", "part_d_deductible", "U-BEN-DEDUCT-001"],
    ["Out of network", "out_of_network", ""],
  ];
  const unitIds = [...new Set(rows.map(([, , unit]) => unit).filter(Boolean))];
  const units = useQuery("plan-units", async () => {
    const found = await Promise.all(unitIds.map((unitId) => approvedUnit(unitId)));
    return found.filter((unit): unit is UnitRef => Boolean(unit));
  });
  const approved = (unitId: string) => !unitId || Boolean(units.data?.some((unit) => unit.unit_id === unitId));
  const show = (key: string) => {
    const value = plan?.[key];
    return typeof value === "string" ? value : value?.display || "";
  };
  return (
    <div className="member-page member-article">
      <h1 className="member-display">Your plan</h1>
      <p className="member-body-lg">{profile.data?.member.plan || "Harbor Medicare Advantage HMO"}</p>
      {profile.error ? <ServiceError message={profile.error} onRetry={profile.reload} /> : null}
      {profile.data ? (
        <dl className="member-plan">
          {rows
            .filter(([, key]) => show(key))
            .map(([label, key, unitId]) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd>{units.loading && unitId ? "…" : approved(unitId) ? show(key) : "Call us for this figure"}</dd>
              </div>
            ))}
          {profile.data.oop && approved("U-BEN-OOP-001") ? (
            <div>
              <dt>Paid toward your maximum this year</dt>
              <dd>{profile.data.oop.spent_display}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      {units.data?.length ? (
        <section className="quote plan-notes" aria-label="About these figures">
          <h2 className="member-h3">About these figures</h2>
          {units.data.map((unit) => (
            <div key={unit.unit_id} className="quote__unit">
              <p className="quote__unit-text">{unit.text}</p>
              <p className="quote__cite">{memberCite(unit)}</p>
            </div>
          ))}
        </section>
      ) : null}
      <Glossary keys={["deductible", "oop_max", "coverage_stage"]} />
      <p className="member-meta">Illustrative figures for a fictional plan.</p>
    </div>
  );
}

/** The specialist referral rule, read from its approved unit so the page never restates it in its own words. */
function ReferralRule() {
  const unit = useQuery("referral-unit", () => approvedUnit("U-BEN-COST-001-05"));
  if (!unit.data) return null;
  return (
    <div className="quote__unit">
      <p className="member-body">{unit.data.text}</p>
      <p className="quote__cite">{memberCite(unit.data)}</p>
    </div>
  );
}

/** A plan sentence from its approved website unit, with the phone number as a tap-to-call link. */
function SiteSentence({ unitId }: { unitId: string }) {
  const unit = useQuery(`site:${unitId}`, () => approvedUnit(unitId));
  if (!unit.data) return null;
  const parts = unit.data.text.split("1-800-555-0148");
  return (
    <p className="member-body">
      {parts.map((part, index) => (
        <span key={index}>
          {part}
          {index < parts.length - 1 ? <a href="tel:+18005550148">1-800-555-0148</a> : null}
        </span>
      ))}
    </p>
  );
}
