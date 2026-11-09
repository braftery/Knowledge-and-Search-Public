# Where a human stays in the loop

> **Public copy:** this document refers to internal working files (such as agent prompts) that are not included in this public copy of the repository.

The case lists "you know where a human must stay in the loop" as a signal, scores "explicit human approval gate for legal / clinical content" under Responsible AI, and its rules say: "The AI proposes extracted knowledge, classifications, and updates; humans review and publish." This file lists every human decision point, checks whether the prototype shows it, and says how to call it out.

Reviewed on Nov 4, 2026, against the Streamlit prototype on main.

## The principle in one line

AI does the high-volume work (extract, classify, match, rank, scope, abstain, cluster, flag). A person makes every decision that changes what a member or advocate is told, or who can see it. When a person has not decided yet, the safe default holds: nothing new goes live, and the approved version stays live.

## 1. Every human decision point

"Explicit in UI" means a viewer can tell, without narration, that a person is deciding and the AI is not. Yes, Partly or No.

| # | Decision | Who | What AI did first | Safe default until a person acts | Where in the prototype | Explicit in UI |
|---|---|---|---|---|---|---|
| H1 | Confirm tags, domain and audience of extracted units | Knowledge Ops author | Extracted units, classified type, suggested tags and audience | Units stay proposed; nothing is searchable | Step 1, "Confirm tags and audience"; Studio "New extractions to confirm" | Partly: the button says confirm, and the AI's member audience is corrected to advocate, but AI-suggested fields are not marked as such |
| H2 | Choose among near-duplicates: merge, keep the canonical, keep both | Knowledge Ops author | Found pairs, labeled each (duplicate, near-duplicate, conflict), gave a reason and a diff | Both stay out of search | Step 2, "Keep the Legal-signed v1 wording"; Explore Copies | Yes: each pair shows "AI label" and a separate decision line |
| H3 | Escalate a conflict of authority to Legal | Knowledge Ops author | Flagged a semantic conflict | Both units blocked from search | Step 2, "Escalate 4 conflicts to Legal" | Yes |
| H4 | Approve or send back legal, policy, cost and clinical units | Legal approver | Checked the verbatim matches its source span; previewed who will see it | Unit stays out of search | Step 3 Legal queue; Legal review inbox (approve, or send back with a required reason) | Yes: "Approve and publish", the verbatim check and "If you approve this unit" |
| H5 | Approve procedure and FAQ units | Knowledge Ops author | Same as H4 | Unit stays out of search | Step 3, Knowledge Ops approvals tab; Studio "Waiting for your approval" | Yes |
| H6 | Resolve a conflict of authority | Legal approver | Proposed which wording to keep and why | Both blocked | Step 3, Conflicts for Legal; Legal inbox conflict view, reason required | Yes |
| H7 | Retire a unit (and its wording) when a conflict is resolved | Legal approver | Proposed which to retire | Both blocked | Same as H6: "Keep the v1 wording and retire the other" | Yes |
| H8 | Publish a revised wording to every channel | Legal approver | Diffed the advocate and member wording | Version 1 stays live | Step 5, "Legal revises the wording" then "Publish version 2"; Explore Revise | Yes |
| H9 | Decide what to do with a top unanswered question: write, fix the process, dismiss | Knowledge owner | Clustered the questions, ranked by demand, drafted a unit with placeholders, flagged invented figures | Search keeps abstaining; nothing is published | Step 6; Explore Gaps; Insights | Yes: the reason is required and editable |
| H10 | Write the unit that closes a gap, filling every placeholder from an approved source | Knowledge Ops author | Drafted it | Draft only; never searchable | Studio "Drafts assigned to you" | Partly: the draft is shown with "AI draft", but the author cannot edit it or send it on in the prototype |
| H11 | Approve the unit written to close a gap | Legal or the Knowledge Ops author, chosen by the routing rule | Same as H4 | Not searchable | Shown end to end: the author sends the finished draft, the rule chooses Legal or Knowledge Ops approvals, and approval makes the original questions answerable | Yes |
| H12 | Approve a fix when a source document changes | Legal approver | Detected the change, separated cosmetic from material, proposed new wording | Old version stays live, marked "source changed" | Step 7, "Send to Legal"; Studio "Source changed" | Partly: the hand-off is shown, Legal's approval of the fix is not (gap G3) |
| H13 | Resolve a flagged answer or a backlog item, with a note | Knowledge Ops author; product team | Routed it by kind, redacted it | Item stays open | Studio "Flagged by advocates and channels"; Product backlog | Yes: resolution note required |
| H14 | Grant a role access to a knowledge base | Knowledge owner with Security | Nothing: the case lists it as human only | Deny by default | Not in the prototype; roles are fixed in `data/roles.json` (gap G4) | No |
| H15 | Retire the source of record (a whole document) | Legal or the content owner | Nothing | Document stays a source | Not in the prototype (gap G5) | No |
| H16 | Confirm a synonym or acronym learned from search logs | Knowledge Ops author | Would propose it | Not used in search | Not built: the map is static | No |
| H17 | Confirm a pinned answer for a top question | Knowledge owner | Would propose it | No pin | Not built | No |
| H18 | Release the system: accept golden-set results before launch | Product owner with Compliance | Scored the golden and held-out sets | No launch | Step 8 shows the scores; the sign-off itself is not shown | Partly |
| H19 | Read the verbatim to the member, exactly | Advocate | Returned the approved unit | n/a | Agent desktop "Read to member, word for word" | Yes |
| H20 | Hand off from the bot to a person | Member advocate | The bot asked a clarifying question, then offered a hand-off | n/a | Member chat hand-off | Yes |
| H21 | Confirm the verbatim was read word for word, and how the call ended | Advocate | Recorded which approved units and versions were shown on the call | No confirmation recorded; the gap shows in Insights | Agent desktop: "Wrap up this call" after End call (needs the wrap-up API, see `docs/cursor-prompts/wrapup-and-acknowledgements.md`) | Yes |
| H22 | Read a revised verbatim before quoting it again | Advocate | Detected that a unit the role can search has a new version, and diffed it | The banner stays until the advocate confirms | Agent desktop change banner: "I have read the new wording"; Insights lists roles still pending | Yes |

## 2. Against the case's own table

| Case column | Item | Prototype |
|---|---|---|
| AI decides | Extract units; classify type | Step 1, real model calls |
| AI decides | Deduplicate | Step 2, real model judgments on pairs |
| AI decides | Embed for retrieval | Lexical scoring with a synonym map, then model judgment (DECISIONS.md D6 and Paths not taken) |
| AI decides | Flag drift / expiry | Step 7 drift; review dates flagged in Insights and Explore |
| AI decides | Blend and rank; scope to readable knowledge bases; decline when evidence is insufficient | Step 4 |
| AI decides | Cluster the questions that returned no answer | Step 6 |
| AI recommends, human confirms | Proposed wording updates | Steps 5 and 7 (H8, H12) |
| AI recommends, human confirms | Suggested tags and domain | Step 1 (H1) |
| AI recommends, human confirms | Merge or split suggestions | Step 2 (H2) |
| AI recommends, human confirms | Proposed new units from unanswered questions | Step 6 (H9, H10) |
| AI recommends, human confirms | Synonyms and acronyms learned from logs | Not built (H16) |
| AI recommends, human confirms | A pinned answer for a top question | Not built (H17) |
| Human only | Approve or publish legal or clinical content | Step 3 (H4) |
| Human only | Retire the source of record | Partly: units are retired on conflict resolution (H7); documents are not (H15) |
| Human only | Resolve a conflict of authority | Step 3 (H6) |
| Human only | Grant a role access to a knowledge base | Not built (H14) |
| Human only | Approve a unit written to close a gap | Shown end to end (H11). Legal or the author is chosen by the routing rule |
| Human only | Decide whether a top question gets a written answer or a process fix | Step 6 (H9) |

## 3. Gaps, and what to do about each

| Gap | What is missing | Recommendation | Effort |
|---|---|---|---|
| G1 | AI output and human decisions look alike on screen. A viewer relies on narration to know which is which. | Add one consistent marker everywhere: "AI proposed" on anything the model produced and a person has not yet confirmed; "Human decision" with role, name and date on anything a person decided. Spec added to the design system as `DecisionMarker`. | Small, high value |
| G2 | The guided demo still stops at "Send draft to author", so the author does not fill the draft on that screen (H10). H11 is shown end to end in the authoring path, with Legal or the author chosen by the routing rule. | The case's (d) is satisfied as written ("turns into a proposed unit for an author to write"). For Q&A, say what happens next. If time allows, let the author edit the draft and send it to Legal, where it appears in the queue. | Medium |
| G3 | After "Send to Legal" in step 7, the drift fix does not appear in Legal's queue. | Show the proposed fix as an item in the Legal review inbox with the old and new wording, so Legal's approval publishes the new version. | Medium |
| G4 | No access-grant step. | Do not build. Say it in the presentation: access to a knowledge base is granted by a person, recorded with the unit's scope, and denied by default. One line on the roles page in Explore would make it visible. | Tiny |
| G5 | No document-level retirement. | Do not build. Name it in the roadmap. | None |
| G6 | Synonyms and pinned answers are not built. | Roadmap, with "AI proposes, author confirms". | None |
| G7 | No visible release sign-off. | Add a line to step 8: "Launch requires 100% verbatim match, zero cross-role leaks and Compliance sign-off" (proposed gates, illustrative). | Tiny |

## 4. How to call it out in the presentation

One slide, three columns, mirroring the case's table: "AI does", "AI proposes, a person confirms", "Only a person". Under each, the demo moment that proves it (step numbers above). Then two sentences:

- "Every gate fails safe: until a person acts, nothing new goes live and the approved version stays live."
- "We kept people on every decision that changes what a member hears or who can see it, because the research found no published accuracy for automated duplicate, conflict or drift detection [5.28][5.13]."

Name the gaps honestly when asked: access grants, document retirement, learned synonyms and pinned answers are human-confirmed by design and on the roadmap, and are not built in the prototype.
