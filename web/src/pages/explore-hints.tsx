import { Lightbulb, X } from "lucide-react";
import { useState } from "react";

const HINTS: Record<string, string> = {
  member:
    "Start on the phone line: pick what the caller asks and hear the price, then the approved wording read word for word. Then try the website estimator and Ask Harbor: the same answer comes back.",
  pharmacy:
    "Press “Member asks a question”: the question and its approved answer appear front and center, with the disclaimer before the price. Ask the next one to see what happens when no approved answer exists. Change the call reason for an unverified caller.",
  insurance:
    "Press “Member asks a question”: the referral rule, then the cost with the disclaimer read first. Change the call reason to see the out-of-pocket blind spot, and a question that belongs to the Pharmacy queue.",
  legal:
    "Start review to approve or send back each item, with the original document under it. Units Knowledge Ops sent come first. Then open the source changes email and press Start review: three changes to wording Legal approved, each with the document and the proposed fix.",
  author:
    "Open “Specialty pharmacy intake SOP” under Documents to review: the full SOP is on the left with each extracted unit highlighted, and you decide one unit at a time on the right. Then open an Unanswered question: see what the AI found, then use the source, ask the expert who owns the fact, or dismiss it.",
  owner:
    "Pick the top unanswered question and decide what happens: send the draft to an author, fix the process, or dismiss it. The reason you give is saved with the decision.",
  channel:
    "Open Try it and send the same question as two roles. Then publish a revision as the Legal approver and come back to Change events.",
};

function readHidden(roleId: string) {
  try {
    return window.localStorage.getItem(`harbor-hint-${roleId}`) === "hidden";
  } catch {
    return false;
  }
}

/** A short first step for someone exploring a role on their own, for example a panelist after the talk. */
export function ExploreHint({ roleId }: { roleId: string }) {
  const [hidden, setHidden] = useState(() => readHidden(roleId));
  const hint = HINTS[roleId];
  if (!hint || hidden) return null;
  return (
    <section className="explore-hint" aria-label="Tip">
      <Lightbulb aria-hidden="true" className="explore-hint__icon" />
      <p>
        <strong>Try this. </strong>
        {hint}
      </p>
      <button
        type="button"
        className="explore-hint__close"
        aria-label="Hide this tip"
        onClick={() => {
          setHidden(true);
          try {
            window.localStorage.setItem(`harbor-hint-${roleId}`, "hidden");
          } catch {
            // Storage can be unavailable; the tip simply returns next time.
          }
        }}
      >
        <X aria-hidden="true" />
      </button>
    </section>
  );
}
