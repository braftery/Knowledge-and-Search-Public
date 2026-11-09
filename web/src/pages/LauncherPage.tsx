import { BookOpen, Code2, Headset, LineChart, Mail, PenLine, Smartphone, Gauge } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

type Role = {
  id: string;
  role: string;
  where: string;
  task: string;
  icon: LucideIcon;
  to: string;
  via?: string;
};

const ROLES: Role[] = [
  { id: "member", role: "Member", where: "Phone line, website and app", task: "Call or ask online about a drug price.", icon: Smartphone, to: "/explore/member" },
  { id: "pharmacy", role: "Pharmacy advocate", where: "Contact center desktop", task: "Read the suggested answer for the call.", icon: Headset, to: "/explore/pharmacy" },
  { id: "insurance", role: "Insurance advocate", where: "Contact center desktop", task: "Read the suggested answer for the call.", icon: Headset, to: "/explore/insurance" },
  { id: "legal", role: "Legal approver", where: "Email, then the review page", task: "Start review on the items waiting for a decision.", icon: Mail, to: "/explore/legal" },
  { id: "author", role: "Knowledge Ops author", where: "Single Source Studio", task: "Finish an AI draft and send it to approval.", icon: PenLine, to: "/explore/author" },
  { id: "owner", role: "Knowledge owner", where: "Knowledge insights", task: "Decide what to do about the top unanswered question.", icon: LineChart, to: "/explore/owner" },
  { id: "channel", role: "Channel and AI team", where: "Developer docs", task: "Send a request and see the cited answer.", icon: Code2, to: "/explore/channel" },
];

export function LauncherPage() {
  return (
    <main id="main-content" className="hh launcher" data-theme="tools">
      <header className="launcher__top">
        <span className="launcher__brand">
          Harbor Health <span>Single Source</span>
        </span>
        <span className="hh-presenter__pill launcher__pill">Illustrative data</span>
      </header>
      <div className="launcher__body">
        <section className="launcher__hero">
          <p className="tools-overline">Knowledge and search prototype</p>
          <h1 className="launcher__title">One approved answer, in the place each person already works.</h1>
          <p className="launcher__lead">
            AI turns scripts and policies into small knowledge units. Legal approves each unit once. Every channel and every search then
            returns the same cited, current wording. Harbor Health is a fictional plan, and every figure is illustrative.
          </p>
          <div className="launcher__paths">
            <Link className="launcher__path launcher__path--primary" to="/demo?step=0&path=short">
              <BookOpen aria-hidden="true" />
              <span>
                <strong>Start the short demo</strong>
                <span>About 8 minutes. Extraction, copies and conflicts, Legal approval, scoped search, every channel, the blind spot, and a source change.</span>
              </span>
            </Link>
            <Link className="launcher__path" to="/demo?step=0">
              <BookOpen aria-hidden="true" />
              <span>
                <strong>Start the full demo</strong>
                <span>About 11 minutes. All nine steps.</span>
              </span>
            </Link>
            <Link className="launcher__path" to="/evals">
              <Gauge aria-hidden="true" />
              <span>
                <strong>How well the AI performs</strong>
                <span>Five AI tasks scored against answer keys written before the model ran, each run several times, with every miss shown.</span>
              </span>
            </Link>
            <Link className="launcher__path" to="/pilot">
              <LineChart aria-hidden="true" />
              <span>
                <strong>The case for a pilot</strong>
                <span>Scope, gates, phases, and a value model with inputs you can change.</span>
              </span>
            </Link>
          </div>
        </section>
        <section aria-labelledby="explore-heading">
          <h2 id="explore-heading" className="launcher__h2">
            Explore as one person
          </h2>
          <p className="tools-meta launcher__sub">Each view opens where that person actually works. The sandbox is separate from the guided demo.</p>
          <ul className="launcher__roles">
            {ROLES.map((role) => {
              const Icon = role.icon;
              return (
                <li key={role.id}>
                  <Link to={role.to} className="launcher__role">
                    <span className="launcher__icon" aria-hidden="true">
                      <Icon />
                    </span>
                    <span className="launcher__role-text">
                      <strong>{role.role}</strong>
                      <span className="launcher__where">{role.where}</span>
                      <span>{role.task}</span>
                      {role.via ? <span className="launcher__via">{role.via}</span> : null}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      </div>
    </main>
  );
}
