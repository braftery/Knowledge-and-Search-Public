export const DEMO_TITLES = [
  "Today: one disclaimer, three wordings",
  "AI turns a script into knowledge units",
  "AI finds copies and conflicts",
  "Legal approves units, not documents",
  "One question, two roles, scoped answers",
  "Author once, every channel updates",
  "Unanswered questions become the next units",
  "When the source changes, the unit is flagged",
  "We measure retrieval before we trust it",
] as const;

export const DEMO_NOTES = [
  "Press Run today's search. Three documents come back with three wordings, and the differences are highlighted. Which one is current? Which did Legal approve? Today's tool cannot say.",
  "Extraction is already loaded. Point at the numbered highlights in the script and the matching numbered cards. Press Confirm tags and audience. AI decides the units, types and spans. A person confirms tags and audience. Here the AI said member, and the author corrects it to advocate.",
  "The author has already worked this queue. Point at one pair: the AI's label, its reason, and the highlighted diff, then the human decision under it. The AI compared 26 pairs and found 5 near-duplicates, 2 exact copies and 4 conflicts. A person kept the Legal-signed wording, and the conflicts went to Legal, blocked until Legal decides.",
  "Press Approve and publish three times: the pricing disclaimer, the unverified-caller rule, then the benefits cost disclaimer. Point at the verbatim check and the If you approve this unit panel. The model found two disagreements between script versions that we did not plant. One drops a call-recording disclosure. Both stay blocked until Legal decides.",
  "Press Search as both roles. Each advocate gets a different approved line, and each card names the knowledge bases it searched. Then press A question with no approved answer. Both roles get a clear no-answer, and the question goes to the gap queue.",
  "The agent desktop and the member chat show the same unit and version. Press Legal revises the wording. The advocate edit is highlighted, and the member still sees version 1 until you publish. Press Publish version 2. Both channels now show version 2, and version 1 stays in the history.",
  "The draft's placeholders are highlighted. The reason starts empty: press Use suggestion to accept the AI's suggestion, or type your own. Press Send draft to author.",
  "Press Apply the cosmetic edit first: even a comma inside Legal's wording goes to Legal, and the approved version stays live. Then press Apply the material edit: the live unit is flagged stale, and the AI proposes the fix, 30-day to 31-day. Press Send to Legal.",
  "Press Score the golden set. Open Held-out questions: these were written before any model run. One fails, and we keep it visible. Then open What failed.",
] as const;

/** The full path starts from nothing, so steps 1 and 3 need different presenter moves than the short path. */
export const FULL_PATH_NOTES: Partial<Record<number, string>> = {
  2: "Each pair shows the AI's label, its reason, and a highlighted diff. Press Keep the Legal-signed v1 wording, then Escalate 4 conflicts to Legal.",
  1: "Press Extract units with AI and wait a few seconds. Point at the numbered highlights in the script and the matching numbered cards. Press Confirm tags and audience. AI decides the units, types and spans. A person confirms tags and audience. Here the AI said member, and the author corrects it to advocate.",
  3: "Press Approve and publish once: the pricing disclaimer is first. Point at the verbatim check and the If you approve this unit panel. Then press Approve all remaining (demo shortcut) and say each unit has its own review page in production. Open Knowledge Ops approvals and press Approve all: procedures and FAQs skip Legal. Open Conflicts for Legal, press Use suggestion on the mail-order rule (or type a reason), and keep the v1 wording.",
};

export const CLOSING_TITLE = "What changed";

export const CLOSING_NOTES =
  "Walk the trace top to bottom: every AI step is marked, and every decision that changes what a member hears has a named role. Land on the fail-safe line, then take questions from here.";

export const SHORT_PATH = [0, 1, 2, 3, 4, 5, 6, 7] as const;

export function neighbor(step: number, path: "short" | "full", direction: 1 | -1) {
  const list = path === "short" ? SHORT_PATH : [0, 1, 2, 3, 4, 5, 6, 7, 8];
  const index = list.indexOf(step as (typeof SHORT_PATH)[number]);
  const current = index === -1 ? 0 : index;
  const next = Math.min(list.length - 1, Math.max(0, current + direction));
  return list[next];
}
