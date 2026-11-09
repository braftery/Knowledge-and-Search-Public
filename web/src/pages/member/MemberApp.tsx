import { useMemberTextSize } from "@/pages/member/text-size";
import { useSearchParams } from "react-router-dom";
import { ChatPanel } from "@/components/chat";
import { useMemberChat } from "@/pages/member/use-member-chat";
import { DrugEstimator } from "@/pages/member/estimators";

const NAV = ["Home", "Care", "Costs", "Help"] as const;

export function MemberApp({ sessionId }: { sessionId: string | null }) {
  useMemberTextSize();
  const [params, setParams] = useSearchParams();
  const tab = NAV.includes(params.get("tab") as (typeof NAV)[number]) ? (params.get("tab") as (typeof NAV)[number]) : "Help";
  const chat = useMemberChat(sessionId);

  function setTab(next: (typeof NAV)[number]) {
    const query = new URLSearchParams(params);
    if (next === "Help") query.delete("tab");
    else query.set("tab", next);
    setParams(query, { replace: true });
  }

  return (
    <div data-theme="member" className="hh-m member-app-stage">
      <div className="member-device">
        <div className="member-device__status" aria-hidden="true">
          <span>9:41</span>
          <span aria-hidden="true">5G</span>
        </div>
        <header className="member-device__wordmark" aria-label="Harbor Health app">
          Harbor Health
        </header>
        <main className="member-device__body">
          {tab === "Help" ? <h1 className="sr-only">Help</h1> : null}
          {tab === "Help" ? (
            <ChatPanel
              fill
              capped
              autoFocus={false}
              items={chat.items}
              pending={chat.pending}
              onClose={() => setTab("Home")}
              onSend={(text) => void chat.ask(text)}
              onChip={chat.onChip}
              onHelp={(yes) => void chat.onHelp(yes)}
              onHandoff={chat.onHandoff}
            />
          ) : (
            <div className="member-device__page">
              <h1 className="member-h2">{tab === "Home" ? "Hello, Dana" : tab}</h1>
              {tab === "Home" ? (
                <>
                  <p className="member-body">What would you like to do?</p>
                  <div className="app-actions">
                    <button className="app-action" type="button" onClick={() => setTab("Costs")}>
                      <strong>Check a drug price</strong>
                      <span>Your drugs, your pharmacy, 30 or 90 days</span>
                    </button>
                    <button className="app-action" type="button" onClick={() => setTab("Help")}>
                      <strong>Ask Harbor a question</strong>
                      <span>Approved answers about your plan</span>
                    </button>
                    <a className="app-action" href="tel:+18005550148">
                      <strong>Call a member advocate</strong>
                      <span>1-800-555-0148, 8 AM to 8 PM (illustrative)</span>
                    </a>
                  </div>
                </>
              ) : null}
              {tab === "Costs" ? <DrugEstimator /> : null}
              {tab === "Care" ? (
                <p className="member-body">
                  To find a doctor or pharmacy, call <a href="tel:+18005550148">1-800-555-0148</a>, 8 AM to 8 PM, seven days a week. Illustrative number and hours.
                </p>
              ) : null}
            </div>
          )}
        </main>
        <nav aria-label="App" className="member-device__nav">
          {NAV.map((item) => (
            <button key={item} type="button" onClick={() => setTab(item)} aria-current={tab === item ? "page" : undefined}>
              {item}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
}
