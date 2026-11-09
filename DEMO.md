# Demo click script

Illustrative data. Harbor Health is fictional. This script is for the web app at https://harbor-knowledge.onrender.com. The lines below are prompts; say them in your own words.

## Before the talk

- After the last deploy, open the site in a fresh browser tab and click through the short demo once. Render clears its disk when it restarts, so a tab left open across a deploy can be out of step until you press **Reset**.
- The guided demo uses saved model answers, so it does not depend on a live call. Typed questions in Explore that have no saved answer call the model live (about 3 seconds each).
- The presenter bar along the top has **Exit to home**, **Notes** (what to say and press on this step), **Short demo**, **Reset**, **Undo**, **Back** and **Next**. **Exit to home** keeps your progress: opening the same demo again in this browser picks up where you left it. **Reset** starts over. The left and right arrow keys also move between steps.

## Short demo, about 8 minutes

From the home page press **Start the short demo**, or press **Switch to short demo** in the presenter bar. **Next** follows the short path, counted 1 to 8. It covers every "great" criterion (extraction, copies, cited answers, two roles, a stale flag) and two stretch goals (the blind spot that proposes a unit, and the drift fix). Only scoring is left to the full demo.

1. **Today's problem.** Press **Run today's search**. Three documents come back with three wordings, and the differences are highlighted. "Which one is current? Which did Legal approve? Today's tool cannot say."
2. **Extract units.** Extraction is already loaded. Point at the numbered highlights in the script and the matching numbered cards. Press **Confirm tags and audience**. "AI decides the units, types and spans. A person confirms tags and audience. Here the AI said member, and the author corrects it to advocate."
3. **Copies and conflicts.** The author has already worked this queue. Point at one pair: the AI's label, its reason, the highlighted diff, and the human decision under it. "The AI compared 26 pairs: 5 near-duplicates, 2 exact copies and 4 conflicts. A person kept the Legal-signed wording, and the conflicts went to Legal, blocked until Legal decides."
4. **Legal approves.** Press **Approve and publish** three times: the pricing disclaimer, the unverified-caller rule, then the benefits cost disclaimer. Before the first click, point at the verbatim check and the **If you approve this unit** panel. Mention the **Conflicts for Legal** tab: "Three conflicts are open. We planted the mail-order rule. The model also found two we did not plant: one drops the call-recording disclosure, and one makes the member ID mandatory for verification. All three stay blocked until Legal decides."
5. **Search.** Press **Search as both roles**. Each advocate gets a different approved line, and each card names the knowledge bases it searched. Then press **A question with no approved answer**: both roles get a clear no-answer, and the question goes to the gap queue. If there is time, press **A pharmacy-only question**: Pharmacy gets the answer and Insurance does not.
6. **Every channel.** The agent desktop and the member chat show the same unit and version; the note under them names it. Press **Legal revises the wording**; the advocate edit is highlighted, and the member still sees version 1. Press **Publish version 2**. Both channels now show version 2, and version 1 stays in the history.
7. **The blind spot.** "How long a Part D prior auth takes" was asked 342 times with no approved answer. The AI drafted the unit that would close it, with placeholders and no invented figures. Press **Use suggestion**, then **Send draft to author**.
8. **The source changes.** Press **Apply the cosmetic edit**: even a comma inside Legal's wording goes to Legal, and the approved version stays live. Press **Apply the material edit**: the unit is flagged stale and the AI proposes the fix, 30-day to 31-day. Press **Send to Legal**.

Press **Finish** to open the **What changed** screen, and take questions from there.

## Full demo, about 11 minutes

From the home page press **Start the full demo**, or press **Reset** in the presenter bar. Walk steps 1 to 9 with each step's buttons and **Next**. The **Notes** panel shows the full-path moves for steps 2 and 4.

- **Step 2, Extract units.** Press **Extract units with AI** and wait a few seconds, then continue as in the short demo.
- **Step 3, Find copies.** Each pair shows the AI's label, its reason, and a highlighted diff. Press **Keep the Legal-signed v1 wording**, then **Escalate 4 conflicts to Legal**.
- **Step 4, Legal approves.** Press **Approve and publish** once; the pricing disclaimer is first. Then press **Approve all remaining (demo shortcut)** and say that in production each unit has its own review page. Open **Knowledge Ops approvals** and press **Approve all**: procedures and FAQs skip Legal. Open **Conflicts for Legal**, press **Use suggestion** on the mail-order rule (or type a reason), and press **Keep the v1 wording and retire the other** on the mail-order rule.
- **Steps 5 and 6.** As in the short demo.
- **Step 7, Gaps.** The draft's placeholders are highlighted. The reason starts empty: press **Use suggestion** to accept the AI's suggestion, or type your own. Press **Send draft to author**.
- **Step 8, Drift.** Press **Apply the cosmetic edit** first: even a comma inside Legal's wording goes to Legal, and the approved version stays live. Then press **Apply the material edit**: the live unit is flagged, the AI's proposed fix is shown against the live version 2 wording, and it waits for Legal. Press **Send to Legal**.
- **Step 9, Quality.** Press **Score the golden set**. Expect 8 of 8, 4 of 4, held-out 2 of 3, and 6 model misses (illustrative). Open **Held-out questions**: "These were written before any model run. One fails, and we keep it visible." Then open **What failed**.

Press **Finish** for the **What changed** screen.

## Undo and reset

Every action shows a confirmation with **Undo**. **Reset** returns the guided demo to the start.

## If you are cut off

Press **Switch to short demo**, go to step 4 of 8, approve the three units, then go to step 5 of 8. If time is short after that, skip to step 8 for the source change.

## Explore (after the demo, or for Q&A)

From the home page, **Explore as one person** opens each role where that person works. Each view starts with a **Try this** tip. **Reset the sandbox** starts the sandbox over without touching the guided demo.

A full loop for Q&A:

1. **Knowledge Ops author:** open **How long does a standard prior authorization decision take?** under Drafts to finish, cite the FAQ sentence, fill `4 business days`, and send it. The routing rule sends it to Legal and says why.
2. **Legal approver:** start review and approve it. Open **Wording change ready** and publish version 2.
3. **Pharmacy advocate:** the banner asks you to read the new wording; confirm it. The new approved answer appears in the panel. End the call and wrap it up.
4. **Knowledge owner:** Insights shows the closed gap and the wrap-up.

### Advocates: a question arrives live

Open **Pharmacy advocate** or **Insurance advocate**. At the top of the Interaction tab is **Live call**. Press **Member asks a question**: the member's words appear in the transcript, and directly under them, in large type, the approved answer to say. The sandbox has no audio, so these lines are scripted; the screen shows what was searched.
- **Pharmacy, Dana R. (drug price):** "How much is my Eliquis going to cost me?" gives the word-for-word disclaimers, then $180. Press again: "can you set up a ride to my doctor's appointment?" gives no approved answer, so the advocate follows up and the question is logged for Knowledge Ops.
- **Pharmacy, Grace T. (not verified):** "How much will my atorvastatin cost me?" shows **Verify the caller before you answer**, with the rule marked for the advocate, not to read aloud. Press **Grace T. confirmed the member ID and date of birth**: the disclaimer, then $0.
- **Pharmacy, Luis M. (specialty):** the specialty rule is past its review date and waiting for Legal, so the screen says not to read the old wording and to confirm with the member later.
- **Insurance, Maria S. (specialist):** the referral rule, then "how much will that visit cost me?" gives the cost disclaimer first, then $35.
- **Insurance, Robert A.:** the out-of-pocket maximum has no approved answer (the known blind spot). **Ann P.:** a pharmacy question in the Insurance queue shows a transfer.

All figures are illustrative.

### Knowledge Ops sandbox: documents, gaps and drift

Open **Explore as one person**, then **Knowledge Ops author**. My work has four groups. Every figure is illustrative.

**Documents to review (3).** Open **Specialty pharmacy intake SOP**. The full SOP is on the left: purpose, scope, roles, steps, cost, exceptions and revision history. The 5 passages the AI turned into units are highlighted and numbered in document order; the rest is context and is not extracted. Click a number, or use Previous and Next, and decide each unit on the right:
- **Approve** a procedure or FAQ you own.
- **Send to Legal** a cost, clinical or verbatim unit (unit 4, the copay). Approve is not offered for these.
- **Edit** the wording, member wording or tags.
- **Reject** a unit that is not real. The AI flags unit 5, buried in section 7, as a duplicate of an approved unit; reject it with a reason of at least four words.

**Add a unit the AI missed.** Select any sentence in the document on the left (for example, in section 5 of the SOP, "Ask the member where they want the medicine delivered...") and press **Make this a unit**, or press **Add a unit the AI missed** and pick a sentence from the list. Give it a title and type. It keeps the document's exact words, is highlighted and numbered like the others, and is marked as added by Knowledge Ops. A procedure or FAQ can be approved at once; policy, verbatim, cost and clinical wording go to Legal.

The other two documents are **Prior authorization FAQ for advocates** (the clinical unit goes to Legal) and **Member callback policy**.

**Unanswered questions (3).** Questions advocates or members asked that no approved unit answers. For each, the screen shows what the AI found when it searched every Harbor document, how far to trust it, and the AI's draft with a placeholder for the fact. No source, no unit:
1. **How long does a standard prior authorization decision take?** The AI found the answer in the prior authorization FAQ, which is still waiting in Documents to review. Press **Use this source**, then **Approve, or send to Legal**. It is a policy, so it goes to Legal with its source.
2. **Can I get a 90-day insulin supply by mail?** The AI found only a line of website copy that nobody reviewed, last updated in March 2025. Press **Ask an expert to confirm**; the question to Pharmacy Operations quotes the website line. Play the expert: **The expert gives the answer**, for example "A 90-day insulin supply by mail is available after two retail fills. This figure is illustrative.", with a made-up signer. Fill `available after two retail fills` and finish. It is an FAQ you own, so it is approved and searchable.
3. **Can Harbor arrange a ride to my appointment?** No source anywhere. **Ask the expert who owns this** (Care Coordination), then **The expert says no policy exists**. No unit is written; the Knowledge owner's Insights shows it under "The business has no answer yet".

Every question also has **Dismiss**: an approved unit already answers it (name the unit), or it is outside what Harbor does, with a reason.

**Source changes (drift), 3 items, each needing a decision.** Drift is a change to the source document behind an approved unit. Each screen shows the document as it reads now with the changed passage highlighted, the live wording beside the AI's proposed wording, and the decision. The approved version stays live until then.
1. **Weekday callback window.** 5:00 p.m. became 6:00 p.m. Material: accept the fix, edit and accept, or keep the current wording with a reason.
2. **Write the callback reason in the desk note.** "conversation" became "call". The AI is not sure it matters (a call leaves out chat), so it asks: "It's cosmetic: keep the wording" or "It matters: update the unit".
3. **Use the phone number confirmed in this conversation.** The sentence was deleted from the policy. Retire the unit, or keep it live, each with a reason.

Purely cosmetic edits (for example, "word for word" became "word-for-word") never reach My work; they are listed under **Sources**, "Changes handled automatically".

**Legal approver.** The inbox has three emails, and each opens a full review page with **Start review**:
1. **Items waiting for your review:** units to approve (those Knowledge Ops just sent come first), with the original document under each, and conflicts. Approve, or **Send back to Knowledge Ops** with a reason; it then appears in the author's **Sent back by Legal**.
2. **3 source changes need your decision:** the 30-day to 31-day change in the Rx pricing disclaimer (material), a deductible added to what advocates may not quote to an unverified caller (material policy), and a comma added inside the cost disclaimer read word for word (cosmetic, but word-for-word wording must match its source, so Legal confirms).
3. **Wording change ready:** publish version 2 of the pricing disclaimer to every channel.

## If the link will not load

Play the backup recording. The Streamlit app is a fallback with the same guided steps.
