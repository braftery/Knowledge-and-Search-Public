# Decisions, assumptions and open questions

> **Public copy:** this document refers to internal working files (such as audits, critiques, build logs and agent prompts) that are not included in this public copy of the repository.

A running log of the reasoning behind the work. The case weights "show your thinking" as heavily as the prototype. This file feeds the deck's thinking appendix and the Q&A prep. It covers the decisions behind the work, the assumptions, the paths not taken, and what to do next.

## How to keep it current

- **Add an entry whenever a choice is made**, in chat or in code: product, design, build or process. Claude and Cursor both follow this rule (see `CLAUDE.md` and `AGENTS.md`). In chat, say "log that" and Claude adds it.
- **Never delete an entry.** If a decision changes, add a new one that supersedes the old, and mark the old one "Superseded by D-n".
- **Format:** ID, date, the decision, what else was considered, why, the evidence (report section or source ID), and where it shows in the prototype.
- **Report references** like [4.2] point to `humana-knowledge-search/final-report.md`.

Entries before Nov 4 were reconstructed on Nov 4 from the specs, commit history and conversation history. Dates are UTC commit dates.

---

## Product decisions

**D1. The main user is Knowledge Ops authors together with Legal and Compliance approvers.** (Nov 3)
- Considered: advocates (the most visible pain), knowledge owners.
- Why: the case says it is testing "structure, governance, and single-source reuse". Those are author and approver jobs. Advocates and channels are the consumers that prove the reuse; knowledge owners close the loop.
- Shows in: SPEC section 0. The guided demo starts with the author and Legal.

**D2. A knowledge unit is the smallest statement that can be approved on its own, plus the contexts it is approved for.** (Nov 3)
- Considered: article-level units (too coarse to approve or reuse), fixed-size chunks (no approval meaning).
- Why: pharma claims libraries approve a claim once for reuse [2.9]. Carestream shows reuse outside the approved context needs review, so applicability travels with the unit [2.6].
- Shows in: the unit schema (SPEC section 3), the `applicability` field on every card.

**D3. Each unit has a stable ID, an increasing version and an effective date. A published version is never edited.** (Nov 3)
- Considered: editing in place with a change log.
- Why: FDA Structured Product Labeling uses set ID, version and effective date [2.12]. It answers "which wording was in effect on date X", the audit question no vendor documents [1, executive summary].
- Shows in: step 5 (version 2 published, version 1 kept), Explore "Versions", `units_as_of`.

**D4. Channels render a unit by reference. No channel holds a copy.** (Nov 3)
- Considered: publishing text out to each channel's CMS.
- Why: DITA content reuse [2.3]. Copies are the root failure in the case scenario and in the Aetna fine [4.9].
- Shows in: step 5, the agent desktop and member chat updating together; the developer portal's `unit.revised` event.

**D5. The key tradeoff: answers are extractive. Search returns an approved unit's text, never generated prose.** (Nov 3)
- Considered: generated answers with citations; generated summaries for policy units.
- Why: CMS standardized content allows no alteration [4.2]; models adopt wrong retrieved text over 60% of the time [3.6]; generated citations are often unsupported [3.8][3.9]. We give up fluency and some coverage for compliance and auditability.
- Next: generated summaries of policy units that always cite the unit and show the governing verbatim are a phase 2 option (report section 4).
- Shows in: every answer is a unit card or bubble with the unit's exact text.

**D6. The model may only choose among approved, in-scope units, or abstain.** (Nov 3)
- Considered: a numeric retrieval score threshold set on the golden set (the report's recommendation); letting the model answer freely.
- Why: lexical scoring scoped by role finds candidates; the model judges whether any candidate answers the question. Any unit ID outside the candidate set is rejected in code. This keeps the gate outside the model's free text while using AI for the judgment the case wants it to make ("decline when evidence is insufficient").
- Honest note: this differs from the report's score-threshold recommendation. A production version would add a calibrated score threshold under the model's judgment and measure both.
- Shows in: `src/corpus.py` `decide()`; step 4's no-answer.

**D7. Permission scope lives on the unit (`kb_scope`) and is applied before ranking. It is not mirrored from source systems.** (Nov 3)
- Considered: inheriting permissions from SharePoint or the source drives, as Glean and Copilot do.
- Why: mirrored permissions lag [5.19] and inherited permissions overshare [5.18]. Read controls do not protect model output by themselves [5.7a]. Deny when scope is unknown [5.21a].
- Shows in: step 4, the same question returning different scoped results for Pharmacy and Insurance; each card names the knowledge bases searched.

**D8. Two approval paths: Legal for verbatim, policy, clinical and cost content; the Knowledge Ops author for procedures and FAQs.** (Nov 3)
- Considered: everything through Legal.
- Why: the case requires a human gate for legal and clinical content. Sending everything to Legal recreates the approval bottleneck the research names as a cause of decay [1.5][1.7]. KCS allows lighter review for experience-based content [1.1].
- Shows in: step 3 tabs (Legal queue, Knowledge Ops approvals).

**D9. A conflict of authority blocks both units from search until Legal decides, with a required reason.** (Nov 3)
- Considered: keeping the newer one live; letting the author decide.
- Why: the case lists "resolve a conflict of authority" as human only. A wrong pick here is the case's failure scenario.
- Shows in: step 2 escalation, step 3 Conflicts for Legal, the Legal review page's two columns.

**D10. On drift, the approved version stays live, marked "source changed", until a human approves the fix. Cosmetic edits are logged and not flagged.** (Nov 3)
- Considered: auto-applying the AI's proposed fix; pulling the unit from search.
- Why: no source reports accuracy for automated drift detection [5.28][5.13], so every flag goes to human review. Pulling the unit would create an abstention gap for a change that may be cosmetic.
- Shows in: step 7.

**D11. Every unanswered question cluster gets one of three human decisions, with a reason: write a unit, fix the process, or dismiss.** (Nov 3)
- Why: the case's "human only" column: "decide whether a top question deserves a written answer or a fix to the process that causes it". KCS separates findability failures from content gaps [1.1].
- Shows in: step 6, Explore Gaps.

**D12. Feedback is routed by kind: content problems to the author, findability and product problems to a product backlog.** (Nov 4)
- Why: the case's weak signal is "no tool logs the questions that came back empty". Agents and channels can capture more than empty searches: hard-to-find answers, clarifications, hand-offs. Routing keeps authors from receiving engineering problems.
- Shows in: Flag this answer, member "Did that answer help?", My work, Product backlog, Insights.

**D13. Knowledge first: search goes live per knowledge base, over approved units only, after the highest-risk verbatim is governed.** (Nov 3)
- Considered: launching search over legacy documents while units are built.
- Why: KCS: search "can not overcome deficiencies in our content"; mass legacy migration has never worked [1.1]. HORIBA wrote new structured content rather than converting [2.4].
- Shows in: roadmap (deck section 4).

**D14. Measure retrieval before trusting it: a golden set with held-out questions written before any model run, failures kept visible.** (Nov 3)
- Why: the case's "search quality" dimension. Over-tuning to a visible test set is a known trap; showing a failing held-out question is more credible than a perfect score.
- Shows in: step 8, "What we got wrong, kept visible".

## Build and process decisions

**D15. Streamlit, SQLite per browser session, hosted on Streamlit Community Cloud.** (Nov 3)
- Why: the presenter is not an engineer; opening a link must be the only step (SPEC section 10).
- Superseded in part by D24 for the presentation front end, if the rebuild passes review.

**D16. Real model calls, cached and replayed by input hash. A live toggle with caps.** (Nov 3)
- Considered: scripted outputs (the first build had no AI doing work, BUILD_EVALUATION section 2).
- Why: the case scores "AI that does real work". Caching makes the demo reliable on a bad network. Caps (20 per database, 20 per Explore visit, 300 per day) protect spend.

**D17. A guided demo with a 5-minute short path, plus an Explore sandbox for each role on a separate database.** (Nov 3)
- Why: the slot is 30 minutes with 15 of Q&A; the demo gets about 10 minutes and must survive being cut to 5. Explore lets interviewers try their own questions without breaking the guided state.

**D18. Each role is shown where it actually works.** (Nov 3)
- The member in a health plan website and app chat, advocates in an agent desktop, Legal from an email into a review page, authors in a Studio workspace, owners in an insights view, channel teams in developer docs.
- Why: the case asks to "reason from the frontline pain". Time to value differs by role (EXPERIENCE_SPEC, SERVICE_DESIGN section 10).

**D19. A fictional brand, Harbor Health. No Humana likeness, no real vendor UI.** (Nov 3)
- Why: avoids impersonation and keeps the made-up data rule honest.

**D20. Undo instead of "Are you sure?" on every action.** (Nov 3)
- Why: the interaction-design skill: never use a warning when you mean undo. It also makes the live demo recoverable from a misclick.

**D21. Claude owns the UI; Cursor owns the engine, data, fixtures and tests. Prompts are broad.** (Nov 3)
- Why: narrow prompts produced slow, incremental progress. Splitting by skill kept each agent in its strength.

**D22. Scope stays open; quality over coverage.** (Nov 3)
- Considered: freezing scope on Nov 1.
- Why: the owner chose to keep going above the minimum while protecting the demo path with tests.

**D23. Every agent and channel can capture feedback for the knowledge and product teams.** (Nov 4)
- See D12.

**D24. Rebuild the front end as a production web app (React, shadcn/ui, FastAPI over the same engine) in parallel. Streamlit stays as the fallback.** (Nov 4)
- Considered: polishing inside Streamlit; hand-built HTML for key moments.
- Why: Streamlit's styling ceiling made the views look unrealistic. The rebuild runs overnight in two Cursor agents (API, front end) on separate branches.
- Decision point: switch or keep Streamlit by Thursday Nov 5 midday.

**D25. Write the design system before the rebuild.** (Nov 4)
- shadcn/ui as the base, plus a Harbor Health layer: two themes (internal tools and member site), AA-checked tokens, rules from the two design skills, 17 component specs.
- Why: Cursor's earlier UI work lacked a concrete visual target.
- Shows in: `web/design-system/`, and the private design-system artifact.

**D26. Jev is not in the prototype. It goes on the roadmap as a phase 2 "second key" check on answers. No simulated Jev results.** (Nov 4)
- Why: the tools were not connected in the build environment. Faking its output would undercut the governance story.

**D27. The repository stays private with no license. Third-party source copies are not made public.** (Nov 3)

**D28. Show the human gates and the privacy stance on screen, not only in narration.** (Nov 4)
- Added a `DecisionMarker` component to the design system ("AI proposed", "Needs a person", "Human decision"), a privacy line under the member chat input, a line on each advocate's "What I can read" page saying a person grants access, and the proposed launch gate under step 8.
- Why: Responsible AI is a scored dimension, and HUMAN_IN_THE_LOOP.md found the line between AI output and human decisions relied on narration (gap G1).

**D29. Keep the redaction and authoring fixes for the morning, in the engine, rather than patching tonight.** (Nov 4)
- Why: Cursor owns the engine and Agent 1 is adding to `src/engine.py` overnight; a parallel edit would conflict. The fixes are specified in REQUIREMENTS_CHECK.md section 6.
- Superseded in part by D30 for the redaction half, and by D31 for the authoring half.

**D30. Redact a typed question before it enters a model prompt, and widen the identifier patterns. Personal names stay for a later named-entity pass.** (Nov 5)
- Considered: redacting only before storage; a name regex; stripping drug names and conditions (finding H3).
- Why: HIPAA_REVIEW.md H1. Live mode was sending the raw question to the sufficiency task. Ranking stays on the raw text, in process, because the lexical score never leaves the machine. The prompt builders for sufficiency, gap drafts, and cluster labels now redact the question. Demo questions contain none of the new patterns, so saved answers still replay.
- Patterns added, from finding H2 and the overnight list: Medicare Beneficiary Identifiers with and without dashes (the CMS 11-character shape, for example 1EG4-TE5-MK73), email addresses, US ZIP codes (5 digit and ZIP+4), street addresses (a number, a street name, and a suffix such as St, Ave, Rd, Blvd, Dr, Ln), and claim or reference numbers of 10 or more digits. Dollar amounts are held aside so a price is not treated as a ZIP.
- Names are still not redacted. A regex for names also catches plan language, and HIPAA_REVIEW.md section 5 assigns names to a named-entity model with a measured recall. Drug names, conditions, and plan names stay, so a gap remains actionable (section 5 of that review).
- Shows in: `redact_query`, `sufficiency_user`, `gap_user`, `label_user`.

**D31. The author finishes a gap draft or a returned unit, and approval is what makes the original question answerable.** (Nov 5)
- Considered: letting the model re-judge the new unit on every later search; putting gap units into the candidate list that the saved sufficiency prompts use.
- Why: REQUIREMENTS_CHECK.md A1 and A3. The author edits advocate text and member text, and a send is refused while any square-bracket placeholder remains. Policy and verbatim drafts go to the Legal queue (`waiting_units`). Procedure and FAQ drafts go to Knowledge Ops approvals (`author_queue`). The same split applies to a unit Legal sent back. On approval the unit is searchable, the gap is marked closed, and each of that gap's original questions returns the unit for a role whose knowledge bases overlap the unit. Other questions keep the cached candidate list, so the demo path still replays. The direct return is the human approval, which outranks a fresh model judgment for those exact questions.
- Shows in: `edit_gap_draft`, `edit_returned_unit`, `send_gap_to_approval`, `send_returned_to_approval`, and the closed-gap check inside `search` and `member_answer`.
- The type-only split for a gap draft or a returned unit is superseded by D53.

**D32. A drift fix is its own Legal item. Approval publishes the next version. Sending it back leaves the stale flag until the author resolves it.** (Nov 5)
- Considered: adding the proposal as another row in `waiting_units`; clearing the stale flag as soon as Legal sends it back; auto-applying the proposal.
- Why: HUMAN_IN_THE_LOOP.md G3. The demo Legal queue is the extracted units, and mixing a drift proposal into that list would change step 3. `legal_drift_items` shows the old wording, the proposed wording, and the source change after `send_drift_to_legal`. Approval publishes the next version the same way `publish_revision` does: the previous version is superseded, the new version is the one every channel reads, and the member wording picks up the source change when it contains the old span. Sending it back keeps that approved version live and still marked stale. The author clears the stale flag by resolving the return, with a note. Until then the safe default holds (D10).
- Shows in: `legal_drift_items`, `approve_drift_fix`, `return_drift_fix`, `resolve_returned_drift`.

**D33. A live abstention that matches no cluster gets its own drafted gap. Cached mode stays in the unclustered bucket.** (Nov 5)
- Considered: drafting in cached mode from a saved fixture; calling the cluster-label task for a single question; dropping the draft when it contains an invented figure.
- Why: REQUIREMENTS_CHECK.md A2. Live AI uses the existing gap drafting task, so a saved answer still wins and the database and daily call caps still apply. The cluster label is the redacted question, because that label is stored and is also the first line of the drafting prompt. Placeholders from the draft, including square-bracket tokens in the text, are stored with it. The invented-figures check is stored on the gap and does not reject the draft. A missing, capped, or failed call, including a live session with no API key, keeps today's unclustered bucket named "New, not yet clustered". A search that is not recorded does not draft. A question that already belongs to a cluster only increments that cluster.
- Shows in: the abstain path of `search` and `record_search`.

**D34. The pricing unit keeps member chat, the website, and the voice bot on its channel list.** (Nov 5)
- Considered: treating every advocate-audience unit as advocate guidance only; adding the voice bot to `channels_for` for every member audience.
- Why: DECISIONS.md Q5, DEMO.md step 5, and the developer portal payload. The audience correction stores advocate, and the audience default for advocate is advocate guidance alone. The pricing unit also has approved member wording for chat, the website, and the phone, so its channel list is recorded on the override: advocate guidance, member chat, voice bot, and website. The closing unit stays advocate guidance only. A later version copies the channels from the version it supersedes.
- Shows in: `audience_overrides` for `U-RX-EDU-001-09`, `confirm_tags`, and `with_audience_override`.
- Resolves Q5.

**D35. Merge the engine fixes and the API overnight; hold the front end.** (Nov 5)
- PR 31 (engine) and PR 32 (API) passed every test, including the Streamlit demo browser tests, and were merged. PR 30 (front end) finished M1 to M4 of M9, so it stays open; merging an unfinished front end would make a Render deploy show placeholder steps.
- The Streamlit app remains the presentation fallback.

**D36. The front end talks to the API through cookie sessions and the Explore routes.** (Nov 5)
- The API keys each browser by an HttpOnly cookie, so the client no longer passes a session id. Member chat uses the Explore member route, with topic questions sent as topics so a page load never records a clarification. Advocate search uses the Explore ask route (saved answer first).

**D37. Say only what the evidence supports on screen.** (Nov 5)
- From the adversarial critique (CRITIQUE.md): "AI confidence" became "Model's own rating" because model confidence may be miscalibrated [3.11]; the 100% quality tiles now name their base (a 12-question demonstration set; a launch gate needs about 150 labels [3.15]); "Cached AI" became "Saved AI answers" so a non-technical viewer does not read it as fake AI; DEMO.md's conflict count now matches the app.

**D38. Keep the bulk-approval shortcuts in step 3, labeled as demo only.** (Nov 5)
- Considered: removing them, which would make the full path 21 Legal approvals and 9 author approvals.
- Why: the full demo must fit in about 11 minutes. A line under each shortcut says "Demo only. In production each unit is approved on its own review page." (CRITIQUE.md C2). The short path, which runs live, approves its three units one at a time.

**D39. Authoring and drift routes fix the role. The request does not send one.** (Nov 4)
- Considered: a role field on the body, matching the engine's optional role argument; one generic action endpoint.
- Why: the engine refuses the wrong role. The API already splits Legal approval and Knowledge Ops approval into different routes (D8). Author routes call the Knowledge Ops author. Legal drift routes call the Legal approver. A role field would only produce the engine's refusal.
- Shows in: `POST /api/author/gaps/{id}`, `POST /api/author/units/{id}`, `POST /api/legal/drift/approve`, `POST /api/legal/drift/return`, `POST /api/author/drift/resolve`.

**D40. A drift proposal stays off the Legal unit queue. The API lists it on its own.** (Nov 4)
- Considered: adding the proposal to `GET /api/legal/inbox` and to `waiting_units`.
- Why: D32. The guided Legal queue is the extracted units. A drift proposal is a new version of a unit that is already live, and mixing it into that list would change step 3. Approval still publishes the next version. Until a person acts, the approved version stays live (D10).
- Shows in: `GET /api/legal/drift`. The inbox and `GET /api/legal/queue` are unchanged.

**D41. Live gap clusters use the same gaps payload.** (Nov 4)
- Considered: a separate live-gaps route; hiding a live cluster until a person assigns it.
- Why: REQUIREMENTS_CHECK.md A2. A recorded abstention already writes the cluster when Live AI is on. `GET /api/gaps` and `POST /api/gaps/{id}` already read that table. The payload adds `live`, `draft_type`, `draft_member_text`, `unit_id`, and `has_invented_figures`. `placeholders` are the square-bracket tokens, so a comma inside the brackets stays part of the token. That list is the same one that blocks send.
- Shows in: `GET /api/gaps` and the gap object returned by `POST /api/gaps/{id}`.

**D42. Author wording is stored as written. Redaction stays on questions and notes.** (Nov 4)
- Considered: running `redact_query` on the advocate text and the member text before saving a draft.
- Why: D30 redacts a typed question before it is stored or placed in a prompt. The text an author saves is the wording that can be approved and read back word for word (D5). Redacting it would put `[redacted]` inside an answer. Search, feedback, and the live cluster label still redact.
- Shows in: `POST /api/author/gaps/{id}` and `POST /api/author/units/{id}`. A live cluster label still shows `[redacted]`.

**D43. One list shows what the author can still edit.** (Nov 4)
- Considered: making the client infer editable rows from the gap list and the author queue.
- Why: a gap is editable while it is `proposed` or `in_review` and has not been sent. A unit is editable when Legal has returned version 1. An approved unit is refused by the engine, so it is left off the list. Closed, dismissed, and process-fix clusters are left off the list. `can_send` is true only when the advocate text is present and every square-bracket placeholder is gone.
- Shows in: `GET /api/author/edits`.

**D44. The portal and the channels payload pass through the pricing unit's stored channel list.** (Nov 4)
- Considered: adding `voice_bot` in the API whenever the audience includes a member.
- Why: D34 already records advocate guidance, member chat, the voice bot, and the website on `U-RX-EDU-001-09`, and copies that list onto a later version. The API unit shape already returns `channels`. Remapping them in the response would drift from the stored unit. Explore, jump, and the short demo after confirm-tags all show those four. Before confirm-tags, the short demo still has the extracted member audience, and the channel list is advocate guidance, member chat, and the website.
- Shows in: `GET /api/channels`, `GET /api/portal/units/U-RX-EDU-001-09`, and the quick-start sample.

**D45. The guided demo renders each persona's real surface on the guided world.** (Nov 4)
- Considered: a single narrator page that summarized each step; reusing the Explore database so the demo and the sandbox shared one history.
- Why: DEMO.md and `web/design-system/3-Surfaces.md` say the presenter bar sits outside the product and the step below it is the real surface. The API keeps that story on `world=guided`, with `POST /api/session/reset` modes `start` and `short`, and one-level undo. Explore stays a separate database.
- Jump and Reset write the new mode into session storage before the URL changes. Otherwise the session hook sees the old mode, resets a second time, and undo restores the wrong snapshot.
- The shared channel banner says "Live on every channel, version N." The unit id stays on the advocate frame. A prepared revision cites the version that is still live until Publish. Audience suggestions appear only after extraction. A conflict title takes focus only after that conflict is resolved, so opening the list does not jump to the last card.
- The author's edit-and-send view, and Legal's approval of a drift fix, wait until `api/README.md` lists those endpoints. The engine functions exist (D31, D32). The web client will not invent routes.
- Shows in: `/demo`, `web/src/pages/demo/`, and the DecisionMarker on guided steps. Member chat in step 5 has no marker and no unit id.

**D46. Explore Legal is the email client, then one item at a time.** (Nov 4)
- Considered: putting the guided demo's three tabs and the "Approve all" shortcut on the Explore Legal page.
- Why: `3-Surfaces.md` puts Legal in an email client, then a review page. `GET /api/legal/inbox` already returns one list for the Explore world: approvals first, then open conflicts. The shortcut stays on the guided demo, where the presenter needs it. Send back still requires a reason, in place. A conflict still needs a reason and shows the kept wording and the retired wording in two columns.
- Shows in: `/explore/legal`.

**D47. The advocate card marks the approval and the duty to read verbatim.** (Nov 4)
- Considered: leaving the Explore desktop unmarked because the guided demo already shows the markers; putting a marker on the gallery sample.
- Why: HUMAN_IN_THE_LOOP.md H4 and H19. The card is where the advocate sees an approved unit and, for verbatim, must read it word for word. The gallery frame is a component sample, so it stays unmarked. Member website, app, phone, and the step 5 member frame stay unmarked.
- In the 400px knowledge panel the role and time sit on the line under "Human decision", so the label does not break in half.
- Shows in: Pharmacy and Insurance desktops.

## Paths not taken

| Path | Why not |
|---|---|
| Search over raw files, drives or mailboxes | The case scores it weak and calls it a different product. Appears only as the labeled "today" baseline in step 0. |
| Generated answers | D5. |
| Mirrored source-system permissions | D7. |
| Multi-step approval routing (author, then Medical, then Legal) | Phase 2. One gate per content class is enough to show governance. |
| Embedding-based retrieval | Lexical scoring with a synonym and acronym map, scoped by role, then model judgment (D6). The corpus is small, and lexical results are explainable on screen. Embeddings are a production step. |
| Synonyms learned from search logs, confirmed by a human | The map is static in the prototype. Listed in the case's "AI recommends" column; on the roadmap. |
| Pinned answer for a top question | Not built. Same column; roadmap. |
| A UI to grant a role access to a knowledge base | Roles are fixed in `data/roles.json`. Human-only in the case's table; named in HUMAN_IN_THE_LOOP.md. |
| Production authentication | Out of scope (SPEC section 1). |

## Assumptions

The case asks for assumptions about the content, the authors, the consumers, the people who search, and the constraints.

**Content**
- A1. Source scripts mark mandatory wording explicitly ("Verbatim (Legal)"), as the case's sample data does. Real documents may not, so extraction must also infer verbatim from context and send uncertain cases to review.
- A2. The Rx pricing disclaimer is wording the plan's Legal team requires. No CMS rule I found names customer service or pharmacy education calls; 423.2267(e)(40) is an analog [4.3] (report reconciliation notes).
- A3. Most legacy content is duplicated with small wording drift, so near-duplicate detection plus human review finds the copies. The research could not confirm Shelf's 99% threshold would catch slightly different disclaimers [5.28].
- A4. A unit is one to three sentences, small enough for one approver to judge in one read.
- A5. Source documents are versioned text that can be diffed by span. Scanned PDFs would need an OCR step first.

**Authors and approvers**
- A6. Knowledge Ops authors have time to confirm AI extractions and tags; confirming is faster than writing (the leap-of-faith assumption in SERVICE_DESIGN section 7).
- A7. Legal's review capacity is the bottleneck, so only gated content types go to Legal (D8).
- A8. One Legal approval covers both the advocate wording and the member wording of a unit.

**Consumers**
- A9. Advocates need an answer within seconds during a call, and must read verbatim exactly as written.
- A10. Members use the public website chat, the app and the automated phone line for general plan questions; personal questions go to signed-in channels or an advocate.
- A11. Channel and AI teams will integrate through an API and accept render-by-reference rather than keeping their own copies.

**People who search**
- A12. They use plan jargon, acronyms and misspellings; a synonym and acronym map covers most of it.
- A13. The same question from two roles needs two different answers.
- A14. Empty searches are a demand signal, but some are findability problems rather than missing content (report assumptions check: partially confirmed).

**Constraints**
- A15. Made-up data only; 2 to 3 days; a non-technical presenter; one laptop shared to the room and a video call.
- A16. HIPAA applies in production even though the knowledge itself is not PHI (HIPAA_REVIEW.md).
- A17. AI extraction, deduplication and drift detection are accurate enough with human review but not without it. The research rates this "undetermined" (report section 7), so every AI flag goes to a person.
- A18. Restricting answers to approved units with abstention reduces harm without making the system unusable. Also "undetermined" in the research; over-abstention is measured in step 8 for this reason.

## Open questions and risks

- Q1. Where to set abstention, and how to watch over-abstention after launch (D6, A18).
- Q2. Legal throughput at migration volume. How many units per week can Legal approve, and what is the backlog plan?
- Q3. Redaction recall in production (HIPAA_REVIEW.md, findings H1 to H3).
- Q4. Who owns a unit after launch, and what happens when the owner leaves (review dates exist; ownership transfer does not).
- Q5. Data issue: the pricing unit's channel list shows only advocate guidance (to fix in the engine data). Resolved by D34.
- Q6. Whether the web rebuild is ready by Thursday midday (D24).

## How past experience shaped this (owner to fill in)

The case asks for one or two things from past work that shaped the approach. Only the owner can write these. Prompts:
- A time a regulated wording or policy reached customers in two different versions, and what it cost.
- A time a search or support log revealed what people needed before anyone asked.
- A time a human approval step was too slow, and how it was fixed without removing it.

## What to do next (owner to extend)

- Calibrated score threshold under the model's judgment, measured on a 150-label golden set [3.15].
- Learned synonyms and pinned answers with human confirmation.
- Generated policy summaries that cite the unit (phase 2 of D5).
- Jev as a second check on answers (D26).
- A redaction service with measured recall (HIPAA_REVIEW.md section 5).

**D48. Claude takes over the web front end; scope is the guided demo first.** (Nov 5)
- Considered: continuing the Cursor build-review-fix loop.
- Why: each loop cost a relay and half a day, and the remaining work is visual polish and parity with Streamlit, which needs someone checking screenshots. Studio, insights and developer docs come after the guided demo matches Streamlit on both paths, so the Thursday noon decision rests on the screens that would be presented.

**D49. Label the demo as illustrative once per screen, in the chrome, rather than inside every product surface.** (Nov 5)
- Considered: keeping "Illustrative" lines inside each surface.
- Why: repeated lines made the products look like mockups. A persistent "Illustrative data" label in the presenter bar and the Explore bar keeps the rule visible on every screen; figures on the quality tiles keep their own label.

**D50. Roles without an Explore surface open the guided step that shows their work.** (Nov 5)
- Why: an empty placeholder page looks unfinished. The author opens step 1, the knowledge owner step 6, and the channel team step 8, each labeled on the launcher.

**D51. The author's launcher card opens Studio My work, where the authoring loop runs end to end.** (Nov 5)
- Supersedes the author part of D50. The author finishes an AI draft, sends it, approves it if it is a procedure or FAQ, and search then answers the original questions.
- Known gap: an FAQ draft that quotes Legal verbatim is routed to Knowledge Ops approval by type. Production should route any unit containing verbatim or cost wording to Legal regardless of type (open question for the engine). Superseded by D53.

**D52. Every Explore role opens its own product view.** (Nov 5)
- Supersedes D50. The knowledge owner opens Knowledge Insights and the channel team opens the developer docs, both on the Explore sandbox, so Q&A can show any role where it actually works.

**D53. Authoring routes a gap draft or a returned unit to Legal when it is policy or verbatim, quotes approved legal wording, or mentions cost.** (Nov 4)
- Supersedes the known-gap note in D51, and the type-only authoring split in D31.
- Considered: a classifier that labels clinical or cost content; leaving the route on type alone.
- Why: SPEC section 3 sets `requires_legal_gate` for verbatim, policy, and anything clinical or cost-related. Units extracted from documents already follow that rule. The authoring path was using type alone, so an FAQ that quoted the Legal pricing disclaimer could be approved by Knowledge Ops. A simple explainable rule fits the prototype: a person can read the routing reason and see why the unit moved. Production would use a classifier with a human override.
- Rule, first match wins: policy or verbatim type; the advocate text or member text contains the text of an approved unit whose type is verbatim or whose `requires_legal` is 1, compared after normalizing whitespace and straight versus curly quotes, and only when that text is a full sentence or longer; a dollar amount or a cost word as a whole word. Otherwise a procedure or FAQ goes to Knowledge Ops approvals.
- Assumption: a quotable span is the approved unit's advocate text or member text, or one of its sentences. It counts when it has at least five words and a period, question mark, or exclamation mark. Four words or fewer do not count. When several units match, the longest span wins, and equal lengths keep the lowest unit id. A dollar amount is a `$` sign, digits, optional thousands commas, and an optional decimal part, such as `$35` and `$1,200.00`. Cost words, case-insensitive and whole words, are cost, costs, price, prices, pricing, copay, copays, copayment, coinsurance, deductible, premium, out-of-pocket, and MOOP.
- The reason is stored on the unit column `routing_reason` and written to the activity log with the actor's role. The sentences are "Routed to Legal: policy or verbatim type.", "Routed to Legal: quotes approved verbatim wording from <unit title>.", "Routed to Legal: mentions cost.", and "Routed to Knowledge Ops approvals: procedure or FAQ with no verbatim or cost wording."
- Shows in: `send_gap_to_approval`, `send_returned_to_approval`, `GET /api/legal/queue`, `GET /api/legal/inbox`, `GET /api/author/queue`, and the two author send responses.
- Review fix (Claude): a unit Legal sent back always returns to Legal, even when its new wording would not trigger the rule, so the rule never lowers a gate. A quote match ignores the unit's own approved text.


**D54. Show the routing reason wherever a person acts on the routed unit.** (Nov 4)
- Builds on D53. The author sees it in a persistent card and the undo notice after sending; Legal sees it in the email digest and as "Why this came to you" at the top of the review page; the Knowledge Ops approval view shows it for units routed there.
- Considered: showing the reason only in the activity log.
- Why: the case scores an explicit human approval gate, and a viewer should see why an item reached a given approver without narration. The reason is shown as a plain sentence, with a note that the rule can raise a unit to Legal but never lowers a Legal gate. Units seeded before routing existed have no reason and show no note.

**D55. Close the guided demo on a "What changed" screen.** (Nov 4)
- Considered: ending on step 8 with the Next button turned off; adding a ninth numbered step.
- Why: the 5E review found the panel's experience had no Exit. A closing view reached by Finish gives the talk an ending without changing the step count that the script, the Streamlit app and the launcher all use. It traces the pricing disclaimer through the steps the chosen path showed, marks each moment as AI proposed, automatic, or a human decision with a role, repeats the fail-safe rule, and, on the full path, shows the scores labeled illustrative with the proposed launch gate.

**D56. The advocate wraps up each call, and the word-for-word read is the compliance record.** (Nov 4)
- Considered: a free-text call note only; inferring the read from the answer being shown.
- Why: showing approved wording does not prove it was read. The wrap-up asks the one question that matters only when a verbatim unit was shown on the call, plus how the call ended; a follow-up requires a note. The front end is built against the contract in `docs/cursor-prompts/wrapup-and-acknowledgements.md`; the store is Cursor's backend task.

**D57. Advocates confirm they read a revised wording, and the knowledge owner sees who has not.** (Nov 4)
- Considered: a passive "updated" badge on the answer card.
- Why: a revised verbatim that an advocate reads from memory is the failure the system exists to prevent. A banner at the top of the desktop shows the diff and records "I have read the new wording"; Insights lists roles still pending. Legal can publish the revision from the Explore inbox, so the whole loop runs without the guided demo.

**D58. Close the loop with the people who exposed a gap.** (Nov 4)
- Why: when a gap closes, the advocate role that asked sees "New approved answer" with a button that runs the search, and Insights lists the gap under "Closed this week" with the count of past questions it now answers. It uses the gap's roles and status, which the API already returns. Telling the member who asked is roadmap item R1.

**D59. Entice and Enter: show demand on the author's drafts, stakes in the owner's digest, and a first step in every Explore role.** (Nov 4)
- Why: queues listed work without saying why it mattered. Drafts now show how many times the question was asked with no answer; the owner's digest leads with the most-asked unanswered question. Each Explore role opens with a dismissible "Try this" tip, so a panelist exploring alone after the talk has a first action. The dismissal is stored in the browser only.

**D60. Member answers stay general to the plan for now.** (Nov 4)
- Considered: scoping answers by the member's plan and coverage stage, as the 5E review suggested for Engage.
- Why: it changes retrieval and needs golden-set questions per plan, which risks the scored results two days before the presentation. Logged as ROADMAP.md R3.

**D61. Roadmap candidates live in ROADMAP.md.** (Nov 4)
- Why: items deferred by design were spread across HUMAN_IN_THE_LOOP.md, CRITIQUE.md, HIPAA_REVIEW.md and this log. One list with sources feeds the roadmap section of the deck.

**D62. An advocate wrap-up stores the call outcome and whether approved verbatim wording was read word for word.** (Nov 4)
- Considered: a checkbox that only updates the screen; storing the confirmation only in the activity log.
- Why: the advocate's confirmation is the compliance record the system exists to produce. The wrap-up is its own table so one undo removes it with the rest of the action, and Insights can count how many confirmations were required and how many were yes. A follow-up requires a note. Call id, call reason, and note are redacted with the same patterns as feedback before they are stored or placed in the activity line. Unknown unit ids are dropped so a stale card does not block the record. `read_verbatim` stays null when no approved verbatim unit was on the call, and the activity line then omits the read-aloud sentence.
- Shows in: `call_wrapups`, `POST /api/explore/wrapup`, `GET /api/explore/wrapups`, and the wrap-up summary on `GET /api/explore/insights`.

**D63. Each advocate confirms a new approved version of wording that role can search.** (Nov 4)
- Considered: one acknowledgement for the whole company; listing every revision to every role.
- Why: when Legal publishes a new version of wording an advocate reads aloud, each advocate role whose knowledge bases overlap that unit has to see the change and confirm that version. Scope uses the same knowledge-base overlap search uses, so a pharmacy-only unit stays off the insurance advocate's list and out of that role's pending count. A second confirmation for the same role, unit, and version returns the same message and does not write another activity line or take a new undo snapshot. The change list names the wording without the "(Legal)" queue suffix, and `approved_on` is the calendar day stored on the unit.
- Shows in: `change_acks`, `GET /api/explore/changes`, `POST /api/explore/changes/acknowledge`, and the acknowledgements list on Insights.

**D64. Saved model answers cover the Explore surface questions after a revision and after Legal approves gap c0.** (Nov 4)
- Considered: teaching search to reuse a version 1 fixture after the wording changes; writing fixture files by hand.
- Why: a saved sufficiency answer is keyed by the candidate text. Publishing version 2 changes that text, and with Live AI off the search abstains with "No cached result for this input. Turn on Live AI to run the model." The demo has to run from saved answers. `scripts/generate_fixtures.py` records every advocate question in `web/src/pages/advocate/scenarios.ts`, every member topic question, and "whats the rx pricing disclamer i have to read" for the Pharmacy advocate, in four Explore states: fresh, after the version 2 publish, after U-GAP-c0 is sent and approved by Legal, and after both. Gap c0 quotes the pricing disclaimer and mentions price, so the existing routing rule sends it to Legal once the bracketed placeholder is removed. Search itself is unchanged.
- Shows in: `scripts/generate_fixtures.py`, `src/demo_paths.py`, and `fixtures/ai/`.

**D65. The front end reopens the Explore sandbox when the server has lost it.** (Nov 4)
- Considered: asking the person to press Reset the sandbox; keeping sandboxes on a persistent disk.
- Why: Render's disk is cleared on every deploy and restart, while the browser still remembers that the sandbox is open, so every Explore view failed with "Open an Explore role before using the sandbox." The shared request function now opens a fresh sandbox once and retries. Work done in the old sandbox is gone, which is acceptable for a demo sandbox. A persistent disk would cost a paid Render plan and is not needed for the presentation.

**D66. Member and advocate views pair approved wording with mock plan data; the model still writes no member-facing wording.** (Nov 4)
- Considered: a markdown guide that lets the model compose chat replies; leaving the views as wording only.
- Why: the owner's review and AUDIT.md found that every member page showed a disclaimer about prices that did not exist, so the views did not show what the product would do. A real plan site pairs approved wording with plan data from other systems. Numbers come from a mock plan-data service; advice wording comes from approved units by reference, and a number is withheld if its disclaimer is not approved. Letting the model compose replies would undo D6 and the human approval gate the case scores. Back end in `docs/cursor-prompts/member-data-and-chat.md`; front end by Claude.

**D67. Audit batch 1: the member site is signed in, help pages have a task, and the Studio rail navigates.** (Nov 4)
- The member site opens signed in as the fictional Dana R., because personal prices and copays only make sense for a known member. Sign out and sign in still work.
- The duplicate "Drug price estimates" help link opens the estimator page. The system note "This page uses the same approved wording..." is removed from member articles; each article opens with a one-line purpose. "Someone calling for me" gets an add-an-authorized-caller form that sends nothing. Leads are navigation copy and make no plan claims, which stay in approved units.
- In Explore, the Studio rail is real navigation: My work, Library (every unit, newest version, with search and status filters) and Gaps (every cluster and its status). "Copies and conflicts" and "Source changes" are left out of Explore, because the guided demo shows them in steps 2 and 7.

**D68. Audit pass 2: the guided full path gets its own presenter notes, and the hand-approved units lead the step 3 queue.** (Nov 4)
- Considered: changing the API's Legal queue order; leaving the full path to DEMO.md alone.
- Why: the task run found that the in-app notes gave short-path moves on the full path, which published the wrong units and emptied steps 4, 5 and 7. The front end now orders the three demo units first and shows full-path notes for steps 1 and 3; the API order is unchanged, so Streamlit and the tests are unaffected. Step 7 shows the diff between the live text and the AI's proposal, so the proposal reads against version 2. DEMO.md now describes the web app.

**D69. "Not a Humana document" is removed from what the web app displays, and left in the source files.** (Nov 4)
- Considered: editing the four source documents.
- Why: the owner asked to remove the line, which names the interviewer's company inside a fictional plan. Saved model answers are keyed to each document's exact text, so editing the files would invalidate the extraction answers and break guided step 1. The web client removes the phrase from every response it displays. The Streamlit fallback still shows it.

**D70. Plan figures live in a mock plan-data file, separate from the knowledge units.** (Nov 4)
- Builds on D66. Considered: storing copays as knowledge units; letting the model compose a price sentence.
- Why: the audit found member pages showing disclaimers about numbers that did not exist. Premiums, copays, the formulary, and the seven fictional member records live in `data/member_data.json`. Search ranking, the guided world, and the golden set stay as they are. Dana R. (`HBR-20418`) is the signed-in member when a chat request omits `member_id`. Insulin glargine is tier 3 and is priced on its own row, so a preferred 30-day fill is $35. Adalimumab at the specialty pharmacy is 33% coinsurance, shown as $612. Mail order is priced at 90 days. A 30-day mail quote is unavailable. Out-of-network emergency and urgent care use the same illustrative copay as in network, because the plan says they are covered and no separate amount was set. Claim dollars are illustrative snapshots and are not reconciled to the out-of-pocket spent figure. Find care lists three fictional pharmacies, marked preferred or standard.
- Shows in: `data/member_data.json`, `src/member_data.py`, `GET /api/explore/member/profile`, `GET /api/explore/member/drug-price`, `GET /api/explore/member/visit-cost`, and `GET /api/explore/member-record`.

**D71. A quoted price or visit cost is returned only with its approved disclaimer.** (Nov 4)
- Builds on D6 and D66. Considered: showing the number and a note that Legal has not approved the wording; showing the number with no wording.
- Why: the number and the disclaimer are one answer. If `U-RX-EDU-001-09` has no approved, search-visible version with member wording, the drug price is withheld and `withheld_reason` is "Prices appear once Legal approves the pricing disclaimer." The visit cost uses `U-BEN-COST-001-02` and "Costs appear once Legal approves the cost disclaimer." Advocate routes use the advocate text of the same unit. An empty member text does not unlock a number on a member route. A specialty drug at any pharmacy other than the specialty pharmacy is unavailable, with the fixed note "Specialty drugs fill at Harbor Specialty Pharmacy." and `U-RX-EDU-001-13` when that unit is approved. An in-network specialist visit also attaches `U-BEN-COST-001-05` and the note "You need a referral from your primary care doctor first." The profile still lists the plan schedule, labeled illustrative. The quote endpoints are where a member or advocate is told what someone pays. An unverified advocate record drops tier, prices, claims, and out-of-pocket spending. `withheld_reason` is the advocate text of the unit titled "No coverage details to unverified callers."
- Shows in: `api/plan_data.py` and the four Explore routes above.

**D72. Drug prices and visit costs in member chat are chosen by a fixed matcher, before search.** (Nov 4)
- Considered: a model call that picks an intent; leaving every price question on the knowledge path, where it abstains.
- Why: the model still does not write member-facing wording (D6). The reply is one sentence filled from the plan-data fields, and the disclaimer is attached by reference. Topic 0 returns "Which drug? Here are the ones on your list." with the member's drugs as full questions. Topic 1 returns "What kind of visit?" Topics 2, 3, and 4 stay on the approved unit. "Is X covered" answers with the tier and the preferred 30-day price. Days come from "90". Pharmacy comes from "mail", "standard", or "specialty". The defaults are preferred retail and 30 days. A plain "doctor visit" asks which kind. Anything that is not one of these intents, and not out of scope, keeps the existing knowledge path.
- Shows in: `classify_member_question` and `POST /api/explore/member`. Kinds: `price`, `visit_cost`, and the plan-data `clarify`.

**D73. A member question with no plan vocabulary is out of scope and is not a gap.** (Nov 4)
- Considered: logging every abstention, including "what is the weather", as a knowledge gap and a product-backlog item.
- Why: an off-topic question is not evidence that the library is missing a unit. The reply is "I can help with your Harbor plan: drug prices, visit costs, referrals and pharmacy questions." The word list is plan, drug, medication, prescription, pharmacy, refill, price, cost, copay, pay, covered, coverage, doctor, visit, specialist, referral, claim, deductible, insulin, mail, card, benefit, and every formulary name, plus simple plurals. The question is not written to the search log, the gap queue, or feedback. Advocate search is unchanged, so a prior-authorization question from an advocate still clusters. The same question from a member has none of those words, so member chat treats it as out of scope until the list grows.
- Shows in: `POST /api/explore/member` kind `out_of_scope`.

**D74. Questions that have not been grouped are a list, not a draft ready to send.** (Nov 4)
- Considered: leaving "New, not yet clustered" at the top of Insights and in the author's drafts with an empty text and a send action.
- Why: that row has no topic and no wording to approve. `GET /api/gaps` marks it `kind: "unclustered"`. Every other gap is `kind: "cluster"`. Insights leaves it out of `top_gaps` and out of the `open_gaps` count, and returns `new_questions` with the count of distinct questions and up to five redacted examples. The author's edit list omits it. `send_gap_to_approval` refuses it with "Group these questions into a topic first." Out-of-scope chat questions never reach the bucket.
- Shows in: `gap_dict`, `author_edits_view`, `insights_view`, and `send_gap_to_approval`.

**D75. The author sees a gap draft only after the knowledge owner sends it.** (Nov 4)
- Considered: listing every proposed draft on the author's desk; hiding the draft until Legal approval.
- Why: AUDIT.md A16. Insights asks the owner to send a draft to the author, and the author already had every proposed draft, including ones the owner had not decided on. `GET /api/author/edits` now lists a gap only when its status is `in_review` and it has no unit id yet. The owner chooses "write", the gap leaves the owner's proposed list, and it appears for the author. The edit and send actions still accept a `proposed` draft, so the guided step 6 path is unchanged. The Explore sandbox seeds gap c0, "Rx pricing disclaimer to read", as `in_review` with the reason "Asked with no approved answer; sent to the author." so My work starts with that draft. The guided database still seeds c0 as `proposed`.
- Shows in: `author_edits_view`, the Explore branch of `build_database`, and `GET /api/explore/my-work`.

**D76. Guided search calls the model on a cache miss when a key is set.** (Nov 4)
- Considered: leaving the guided world on saved answers only; turning the call on only when the Live AI toggle is on.
- Why: AUDIT.md C1. Saved answers are keyed to one set of approved units. If the presenter approves a different set, step 4 had no fixture and showed the cache sentence. Explore already tries a saved answer and then calls the model. Guided search now does the same, with its own visit counter and the same cap of 20. No key leaves `ai_source` `missing` and does not spend a call. A failed call is returned as `missing` too, so the screen can show one plain line. Saved answers for the three step 4 approval sets are in `fixtures/ai`.
- Shows in: `POST /api/search`, `POST /api/search/both`, and `scripts/generate_fixtures.py`.

**D77. Insights and Quality score the same golden set with the same rules.** (Nov 4)
- Supersedes the conflict-sensitive expected answer inside `score_golden`.
- Considered: keeping `expected_before_resolution` so an open mail-order conflict counts as a correct abstention.
- Why: AUDIT.md C3. Insights showed right answer first as 7 of 7 because the open conflict treated the pharmacy mail-order question as an expected abstention. Guided step 8, after Legal resolves that conflict, showed 8 of 8 on the same file. Both screens now use `expected_unit` from `data/golden_set.csv`. The denominator is the scored answerable rows. A row whose result is "No saved answer" is not a pass and not a miss, and `not_scored` counts it separately. Right answers, wrong units, and wrong no-answers sum to `score_counts.scored`. On the presenter path in DEMO.md the tiles stay 8 of 8, 4 of 4, held-out 2 of 3, and 6 misses.
- Shows in: `score_golden`, `GET /api/quality`, and `GET /api/explore/insights`.

**D78. Units approved before the demo carry a past date and a named fictional approver.** (Nov 4)
- Considered: leaving every approval as "Legal approver" at the minute the page loaded.
- Why: AUDIT.md C7. The Explore seed and the guided jump and short states approve a library before the presenter starts. Those rows use a stable time from 2025-11-02 through 2026-10-15. Legal units are approved by Dana Okafor (Legal). Procedures and FAQs are approved by Sam Patel (Knowledge Ops), unless `routing_reason` says the routing rule sent the unit to Legal. `approver_role` stores Legal or Knowledge Ops. An approval during the session keeps the current time and the generic label, Legal approver or Knowledge Ops author.
- Shows in: `approve_units`, `preapprove_short`, and the unit payload's `approved_by` and `approver_role`.

**D79. Seeded gap counts are illustrative weekly volumes, and findability misses are separate.** (Nov 4)
- Considered: leaving the search-log cluster sizes, which top out at 3.
- Why: AUDIT.md C8. A contact center asks the top missing question hundreds of times a week. `search_count` on a seeded cluster is that illustrative weekly volume. The top content gap, how long a Part D prior authorization takes, is 340. The other seeded clusters run from 12 to 210. Four clusters paraphrase an approved unit and are marked `findability`: the Rx pricing disclaimer, the Rx education closing line, the MA pharmacy greeting, and the member website drug-price wording. Insights lists those under `findability_gaps` and keeps them out of `top_gaps`. Gap c0 stays in the Explore author queue so the authoring walkthrough still starts there. The count is not part of a model prompt, so the saved gap drafts stay valid.
- Shows in: `_seed_gap_volumes`, `GET /api/gaps`, and `GET /api/explore/insights`.

**D80. Explore merges the desk-copy duplicates into the canonical units.** (Nov 4)
- Considered: leaving the near-duplicates approved beside the canonical wording; merging them in the guided worlds too.
- Why: AUDIT.md C13. The Library was showing a desk copy as a second approved answer. In the Explore seed only, `U-RX-EDU-002-08` is merged into `U-RX-EDU-001-10`, `U-RX-EDU-002-14` into `U-RX-EDU-001-16`, `U-RX-EDU-002-05` into `U-RX-EDU-001-06`, `U-RX-EDU-002-02` into `U-RX-EDU-001-03`, and the referral restatement `U-BEN-COST-001-09` into `U-BEN-COST-001-05`. Status is `merged`, `search_visible` is off, and `superseded_by` is the canonical id. The guided worlds keep the previous pool so the presenter-path fixtures stay valid. Explore questions whose candidate list changed have new saved answers.
- Shows in: `_merge_explore_copies` and approved search on the Explore database.

**D81. A blocked best match tells the advocate the wording is under Legal review.** (Nov 4)
- Considered: abstaining with no approved answer, which made the conflict look like a missing unit.
- Why: AUDIT.md C10. When the best lexical match for an advocate search is blocked by an open Legal conflict, and it outranks every approved unit, the result status is `blocked_conflict` and `blocked_note` is "Under Legal review. Use the currently approved rule until Legal decides." `fallback_unit` is the approved rule it conflicts with, when one is live. `unit` is null, so the blocked wording is not the answer. The question is not added to a gap.
- Shows in: `search` and `POST /api/search`.

**D82. Member chat recognizes referrals, authorized callers, and complaints before it says out of scope.** (Nov 4)
- Supersedes the out-of-scope reply in D73. The plan-word list in D73 still keeps advocate search unchanged.
- Considered: leaving "do i need a referral for a cardiologist" and "can my son call for me" on the knowledge path, where they became a clarifying question or the out-of-scope reply.
- Why: AUDIT.md B4 and C9. A referral or specialist word with no cost word answers with `U-BEN-COST-001-05`. A family or caregiver word together with call, calling, or talk answers with `U-RX-EDU-001-05`. Both are kind `answer` and include the citation. Overcharged, charged, bill, billing, upset, angry, complaint, wrong, or refund returns kind `handoff_offer`, the reply "I'm sorry about that. A member advocate can look at your account with you.", and the chips "Talk to a member advocate" and "See my recent claims". That turn is not a gap. Out of scope is used only when no plan, billing, family, or complaint word appears, and the reply ends with "or I can connect you with a member advocate."
- Shows in: `classify_member_question` and `POST /api/explore/member`.

**D90. Member and advocate views show plan numbers with their approved wording; pass 3 front-end fixes.** (Nov 5)
- Numbered from D90 so it cannot collide with Cursor's entries, which start at D76.
- Member site: drug price and visit cost estimators; Plans and Find a pharmacy from plan data; Ask Harbor renders price and visit quotes, clarifying chips and an out-of-scope reply with a hand-off. Every number appears with its approved disclaimer and citation, and the quote says it is illustrative.
- Phone line: a clarifying question plays as a spoken exchange, then the price, then the approved wording read word for word.
- Agent desktop: Member profile, Claims and Prescriptions tabs from the member record; the mail-order caller is unverified, so coverage details are hidden with the approved rule cited; recent contacts are per caller; suggestion cards are headed by the unit title; call notes carry into the wrap-up.
- Guided demo: the closing screen greys out moments that were not run; engine and cache text is never shown to end users; the member panel in step 5 stays on the published version until Publish; the short path counts 1 to 5; switching to the short demo asks first; step 1 explains advocate and member wording.
- Required reasons start empty, with the AI's suggestion inserted only by a click on "Use this". Considered: keeping prefilled reasons for demo speed. Why: prefilled text let a person approve or dismiss without writing anything, which reads as rubber-stamping; one deliberate click keeps the demo fast.

**D91. The front end shows PR 50's new states.** (Nov 5)
- A search match blocked by an open Legal conflict shows "Under Legal review" on the agent desktop instead of a no-answer. Insights marks gaps that are search misses for an existing approved unit. The complaint reply's chips open the hand-off and list the member's recent claims from plan data, instead of being sent to the bot as questions.

**D92. Design docs gain the member profile, moments of truth and the 5E model; PLATFORM.md states the reuse argument.** (Nov 5)
- SERVICE_DESIGN.md 2.6 now says who members are (mostly 65 and older, with a disability minority under 65; mixed channel preference with the phone strong among older members; caregivers who call for them) and the design consequences. Sources outside the research report are linked and marked; most are vendor surveys and are treated as directional.
- SERVICE_DESIGN.md section 11 defines zero, first and second moments of truth for each user and ties each to its value proposition and to where the prototype shows it.
- EXPERIENCE_SPEC.md section 10 defines what great looks like for each stage of the 5E model, with considerations and per-role targets, and what the prototype does today.
- PLATFORM.md describes which components carry over to other AI use cases and how that supports portfolio management. Considered: building a second domain to prove reuse. Why not now: one day before the presentation, a document and a slide carry the argument; the provider directory case is named as the fastest proof.

**D93. Member views put the phone first and offer larger text.** (Nov 5)
- Follows SERVICE_DESIGN.md 2.6 and EXPERIENCE_SPEC.md sections 5 and 10.2: many older members prefer to call, and the member experience must be readable for older eyes.
- The member's Explore views open on the phone line, then the website and the app; the launcher and the "Try this" tip say "call or ask online".
- A labelled "Text size: Standard | Larger" control in the member site header. Considered: an icon-only "A A" control, and browser zoom. Why: the design skills require visible labels on meaning-bearing controls and a clear selected state; raising each text style (about 20%) reflows the page instead of scaling the layout. The change is instant with no animation, works from the keyboard, uses 44 px targets, and is remembered per viewer in the browser only, with the page working the same without storage.

**D94. Pass 4 front-end fixes from the live persona click-through.** (Nov 4)
- A quote shows its disclaimer only when it shows a number, so a not-covered visit no longer carries the covered-visit disclaimer.
- The advocate desktop logs only questions an advocate types. Suggestions come from the call reason, so their misses are not advocate flags. Considered: keeping them as demand signal. Why not: they duplicated known gaps and buried the author's drafts.
- The knowledge panel shows the caller's plan figures beside the approved wording ("From Dana's plan"), hidden for unverified callers, so the price answer is one place, matching the spec's one-action target.
- Wrong-queue calls say which queue owns the question and offer a transfer.
- Legal gets "What did we say on a date?" in the email client's Single Source section, on the existing as-of API.
- The caregiver rule is followed by a next step in chat and on the phone line.
- "Use this" becomes "Use suggestion" (verb + noun).

**D95. Pass 5 member and closing-screen fixes from the five-persona review.** (Nov 5)
- The phone line reads the approved disclaimer before any dollar amount, matching the advocate script's rule. Considered: keeping number first because members asked for the price. Why not: channels must follow the same order, and the VP of Product review found the mismatch.
- The drug page adds "Compare all my drugs": 30-day preferred retail against 90-day mail order per month, with monthly totals, a savings line and each disclaimer unit shown once. Per-month mail cost is the 90-day plan price divided by three, computed in the browser from plan data. Specialty drugs are left out of the comparison and say so.
- The drug page shows Part D deductible status in place of the medical out-of-pocket maximum. Mail order says it fills 90-day supplies only; Harbor Specialty Pharmacy is offered only for specialty drugs.
- Focus moves to the result after an estimate and back to the Ask Harbor button when chat closes. The caller form marks fields required, links the error with aria-describedby and focuses the invalid field.
- At phone width the Explore bar stays, compact, so a member can switch between phone, website and app. Dark bars use a white focus ring.
- The app gets a main landmark, a heading on every tab, a drug estimator under Costs and a call link under Care. Phone numbers are tel: links with hours, labelled made up.
- The closing screen counts step 3 as run when an approved unit is live, and the full path's "After" text claims only moments that ran.
- The Legal conflict reason field asks Legal to check any AI suggestion against both wordings, because the reason is saved as written. Considered: removing "Use suggestion". Why not yet: the suggestion saves time when it is right; the wrong greeting summary is a back-end fix (docs/cursor-prompts/pass5-backend.md).
- Not built here, recommended for the deck: a business-case panel and a phased pilot plan. ROADMAP.md says sequencing is decided in the presentation work, and any baseline numbers would be invented.

**D96. Compliance review fixes on the front end, and what stays open.** (Nov 5)
- The advocate desktop hides an unverified caller's drug list and recent contacts, with the reason, because a drug list reveals formulary status, which `U-RX-EDU-001-07` forbids. The payload still carries them until the back end strips them.
- The cosmetic source change is labelled "Automatic, no person acted". Considered: keeping the Knowledge Ops marker because Knowledge Ops owns the queue. Why not: no person acted, and the record must say so.
- The "What changes your price" panel is removed. It was member wording with no approval. The approved disclaimer already names the same three factors. Considered: keeping it labelled illustrative. Why not: the product's claim is that member wording is approved, and the panel contradicted it.
- Wording history asks for a time (ET) as well as a date, so a revision day returns the version live at that time.
- Kept: a new browser tab resets the guided demo. The presenter relies on it for a clean start the day of the presentation.
- The rest of the compliance findings go to Cursor (docs/cursor-prompts/pass5-backend.md item 7), because they need server-side enforcement.

**D97. Pass 5 follow-ups: links, citations, reasons, intervals, waits.** (Nov 5)
- Member site navigation and footer are links with real addresses, so they open in a new tab and are announced as links. The chat launcher sits in an "Ask Harbor" landmark.
- Member citations read "Source: Harbor Health, {title}, updated {date}", the same format as the price disclaimers, with the title as approved. Considered: the earlier "From Harbor Health {title}" with a lower-cased title. Why not: it read as broken grammar and lost acronyms.
- The Library shows knowledge bases and channels with readable labels.
- Legal's conflict and send-back reasons need at least four words. Considered: a character count. Why not: a word count matches what an auditor needs, a reason that says why.
- Score tiles show a Wilson 95% interval, so 8 of 8 reads "68% to 100%". The golden set is small, and the screen should show how little it proves.
- After three seconds of waiting, chat and advocate search say a new question can take up to 15 seconds. The live model takes 3 to 16 seconds locally.
- Not built before Nov 6: per-unit tag edits in step 1, Legal typing its own revision in step 5, and a Legal workload estimate. They change the guided flow the day before the presentation.

**D98. The front end follows the server-held verification and the new reply kinds.** (Nov 5)
- Verified advocate calls send the member ID and the made-up date of birth to `POST /api/explore/verify` before the record or a search. The scenario carries the date of birth; the client no longer asserts verification. Unverified calls never call it.
- The phone line asks on the `voice_bot` channel. When the server returns `authenticate`, the transcript plays the approved prompt and the caller's identifiers, the server checks them, and the question is asked again. Phone prompts come from the approved IVR units, with the old text only as a fallback. The server checks once per session, so later calls in the same sandbox skip the exchange. Considered: replaying the exchange on every call. Why not: the transcript should show what the server did.
- `safety` replies show as an alert with the approved wording and no "did this help" or topic chips. `plan_figure` replies show like a price, with the figure and its disclaimer.
- The drug comparison says why a price is missing (for example, mail-order prices wait for Legal's decision on the mail-order rule).
- Wrap-ups send `displayed_units` with the version and text on screen. Wording history lists every version live that day when the wording changed.

**D99. Every remaining front-end item from the five reviews.** (Nov 5)
- Supersedes the "not built before Nov 6" lines in D96 and D97 for the business case and the demo reset.
- A pilot page (/pilot), linked from the launcher and the closing screen, has scope, baselines, gates, phases and a value model. Every input is a made-up assumption the presenter can change, and the formula is shown. The one external figure (14% more issues resolved per hour, NBER) is cited with its limit: it measured no compliance or accuracy. Considered: measures only, with no numbers. The owner chose adjustable illustrative inputs.
- A new tab joins a guided demo already in progress in this browser, and Reset stays explicit. Considered: keeping the reset, which the presenter relied on. Why not: the engineering review showed a second tab silently wiped the first tab's work.
- The caregiver held-out miss is labelled as a known miss kept on purpose. The owner chose to keep it, so step 8 stays 6 misses.
- Member site:
  - breadcrumbs are a navigation list of links;
  - footer group titles are headings;
  - footer links land on what they name ("Find a doctor" and "Member advocates" each have a section, and focus moves to it);
  - sign-in errors are linked to their fields, focus moves to the first invalid field, and required fields are stated;
  - 44 px targets for crumbs, footer links and Sign out;
  - the help card is a labelled section;
  - the prototype bar is a labelled section, so there is one banner.
- Members read citations as "Harbor Health plan rules: {title}". Staff keep the version number. The specialist option says "for example, a cardiologist".
- The phone line lets the caller choose which drug or visit type, so every drug on the list can be priced by phone.

**D200. The front end follows the contract from pull request 59.** (Nov 5)
- Numbering: Claude's range D90 to D99 is full, so Claude's entries continue at D200. Cursor's continue after its last number.
- Explore opens the server-held role on every role switch, and views wait until it is open, so no request is refused. A request refused because another role is open reopens the right role and retries once.
- Member requests always name the member. Each phone question is its own call, with its own call id, so the line checks the caller on every call. The greeting, "verified", "no answer" and closing lines come from approved IVR units.
- Step 1 lets a person edit one unit's tags, audience and domain, and records the decision on screen. Step 5 and the Legal email let Legal edit the wording before publishing, and the text explains that typed wording may miss a saved answer while the step 8 score stays fixed.
- Step 7 shows a comma inside Legal wording as sent to Legal.
- A Legal folder, "Reviews and workload", lets Legal extend or retire wording past its review date (four-word reason). It also covers the linked-disclaimer review after a revision and the illustrative workload estimate.
- The advocate's price card shows the approved wording before the amount. A question owned by another queue shows the transfer.
- Members get:
  - a recorded authorized-caller request, with a confirmation number and the approved confirmation wording;
  - approved plain-language definitions under "What these words mean";
  - website sentences read from approved units, with the phone number kept as a tap-to-call link.
- The docs page shows webhook registration and links the OpenAPI description.

**D201. The short demo covers every "great" criterion and two stretch goals.** (Nov 5)
- Supersedes the five-step short path. The short path is now 8 steps:
  - Today;
  - extraction;
  - copies and conflicts;
  - Legal approval;
  - two roles;
  - every channel;
  - the blind spot;
  - the source change.

  Only scoring (step 9) stays full-path only. About 8 minutes.
- Why: judged on the evaluation criteria, the old short path showed no duplicate detection and no stale flag (both "great" criteria). It also showed neither the drift fix nor the blind spot (stretch goals). Considered: keeping five steps and pointing to the full demo. Why not: an interviewer judges what is shown.
- In short mode the copy decisions are already made, so step 3 is a walkthrough of the AI's labels, reasons and the human decisions. The presenter notes and DEMO.md say so. The closing screen lists only the moments that ran, on either path.
- The confirmation after the cosmetic edit now says it went to Legal. The API still returns the older "logged, nothing flagged" message, so a back-end fix is noted for Cursor.

**D202. The Explore author can see a document become knowledge units.** (Nov 5)
- The Knowledge Ops author's Studio in Explore adds **Sources** and **Copies and conflicts**:
  - Sources shows the Rx education script with numbered passages beside the units the AI extracted, their types, tags and audience, and the human confirmation and audience corrections.
  - Copies and conflicts shows the AI's labels, reasons and diffs, and the decisions on them.
- Why: the brief asks for a workflow that turns a document into structured knowledge units. Before this, only guided step 2 showed it, so someone exploring the author or Legal role could not find it. Legal already sees each unit's source passage on its review page.
- In Explore the screens are read-only. The sandbox's extraction has already run, and the guided demo is where extraction runs live. Considered: a live re-extraction button in Explore. Why not: it needs a back-end route to reset and re-run extraction per sandbox, and the guided step already shows it live.
- The guided screens are reused, so both places show the same layout. The rail order now follows the workflow: Sources, then Copies and conflicts, then Library.

**D203. The Knowledge Ops author reviews a document's units one at a time from My work.** (Nov 5)
- Supersedes the read-only Sources screen in D202.
- My work opens with "Documents to review". The Rx education script shows its unit counts: waiting for you, with Legal, blocked, and approved.
- Opening it shows the script on the left, with numbered passages, and one extracted unit on the right. The unit shows its wording, source passage, type, tags, audience, who approves it, the AI's proposal and the routing reason.
- The author approves units waiting for them one at a time, and the review moves to the next. They can step through every unit, or pick a number in the script to jump to it. Legal's units, blocked units and approved units show where they stand.
- Sources opens the same screen.
- Why: the brief asks for a workflow that shows a document being turned into structured knowledge units, and the owner expected to find it in My work with approval one unit at a time. A separate read-only view did not meet that.
- Not built: sending a unit back from this screen. The author has no back-end route to decline a unit today, so "Skip for now" moves on and the unit stays waiting.

**D204. Who reviews what, how a gap is grounded, and what drift means.** (Nov 6)
- **Knowledge Ops** checks the AI's work on every unit extracted from a document. It approves units it owns (procedures and FAQs), sends regulated units to Legal, edits the AI's wording or tags, or rejects a unit that is not a real unit or is a duplicate, with a reason.
- **Legal** sees only units sent to it. It approves, or sends the unit back to Knowledge Ops with a reason. Knowledge Ops edits the unit and resends it.
- Only Legal sends back. Considered: a send-back button for Knowledge Ops. Why not: nobody upstream of Knowledge Ops wrote the unit except the AI, so "reject" or "edit" is the honest action.
- Legal's review page shows the whole original document, with the unit's passage highlighted, beside the proposed wording.
- **No source, no unit.** A gap draft keeps a placeholder wherever a fact must come from a source. Knowledge Ops cannot send it until every placeholder is filled from:
  - an approved source passage, which the system checks the text against; or
  - a dated statement from the fact's named owner, which becomes an attested source document Legal can see.

  If no one owns the fact, the gap returns to the Knowledge owner as a process gap ("the business has no answer yet"), and advocates keep the no-answer with follow-up. Considered: letting the author write from their own knowledge. Why not: an unsourced sentence in an approved unit is exactly the failure this product prevents.
- **Drift** is a change to the source behind an already-approved unit. The AI classifies it:
  - **Cosmetic** (no change in meaning) is logged automatically. Inside Legal wording it still goes to Legal, because Legal owns every character of verbatim text.
  - **Material** flags the unit stale. The approved version stays live while the AI's proposed fix goes to whoever approved the unit: Legal for Legal wording, Knowledge Ops for procedures.
- The Knowledge Ops sandbox shows three of each:
  - documents to review;
  - drafts to finish;
  - source changes.

  Flags move to the Knowledge owner. The back end is specified in `docs/cursor-prompts/sandbox-workflows.md`.

**D100. A drug price carries the disclaimer that matches the supply and pharmacy.** (Nov 4)
- Supersedes the search-visible half of the withhold rule in D71 for the unit attached to a price. The number is still withheld when that unit has no approved version with the wording for the route.
- Considered: rewriting `U-RX-EDU-001-09` so one sentence covered every supply; leaving the 30-day preferred sentence on 90-day and mail-order prices.
- Why: the approved 30-day preferred sentence was being shown next to a 90-day mail price, so the wording contradicted the figure. `U-RX-EDU-PRICE-ANY` is a second approved verbatim unit, "Drug price estimate disclaimer (any supply or pharmacy)", approved by Dana Okafor (Legal) on 2026-09-23. Plan-data replies use `U-RX-EDU-001-09` only for a 30-day supply at a preferred retail pharmacy, and `U-RX-EDU-PRICE-ANY` for every other combination. The new unit has `search_visible` 0 and is not in the extraction corpus, so advocate search and member search keep the same candidate pools. The Legal queue's `approved_count` counts search-visible units, so the short demo stays at 27. The phone line is the existing `voice_bot` channel.
- Shows in: `GET /api/explore/member/drug-price`, member chat price replies, and verified member-record prices.

**D101. A visit quote includes the cost disclaimer only when a cost is shown.** (Nov 4)
- Considered: keeping `U-BEN-COST-001-02` on every visit response, including one that says the visit is not covered.
- Why: the disclaimer explains a number. When `available` is false, no number is shown, so the cost disclaimer is left off `units`. A specialist visit still includes the referral rule `U-BEN-COST-001-05`.
- Shows in: `GET /api/explore/member/visit-cost` and member chat visit replies.

**D102. Member answers on the developer portal use the same plan intents as member chat.** (Nov 4)
- Considered: leaving `GET /api/portal/answers` on knowledge search for every member question.
- Why: "how much is my atorvastatin" abstained on the portal while member chat returned $0. For role Member, price, visit cost, referral, authorized caller, complaint, and out of scope now follow `POST /api/explore/member`. The response adds `kind`, `text` (the reply), `units` in member wording, and `price` or `visit_cost` when the chat reply has one. `member_id` is optional and defaults to Dana R. (`HBR-20418`). A question with no intent keeps the previous shape. The call still does not log the question or spend a live call.
- Shows in: `GET /api/portal/answers`.

**D103. A verified advocate can quote a plan price from the desktop search.** (Nov 4)
- Considered: a separate price endpoint on the advocate desktop; showing figures to every caller.
- Why: "is apixaban cheaper by mail" had both prices in the plan file and no approved knowledge-unit answer. `POST /api/explore/ask` accepts optional `member_id` and `verified`. Without `member_id`, search is unchanged. When the question is a drug price or a visit cost and `verified` is true, the usual search result stays, and the response adds `kind`, the plan payload, and `units` in advocate text. A comparison ("cheaper", or "mail" together with "retail") also returns `price_options` for the 30-day and 90-day preferred retail, standard retail, and mail-order prices. `cheaper`, and "mail" together with "retail", count as cost words in the shared matcher, so member chat recognizes the same questions. When `verified` is false, the response is the approved unverified-caller rule and no figures. An omitted `verified` is false.
- Assumption: the primary `price` still uses the existing day and pharmacy rules, so "cheaper by mail" quotes a 30-day mail fill, which the price table leaves empty, while `price_options` includes the 90-day mail price.
- Shows in: `POST /api/explore/ask`.

**D104. The seeded member flag asks about shipping on a 90-day mail price.** (Nov 4)
- Supersedes the shoe-size example in the Explore feedback seed.
- Considered: keeping "what is the shoe size benefit" as a redaction demo.
- Why: a shoe-size benefit is not a question this plan would receive, and the redaction demo already has other examples. The seeded channel flag is now "member asked whether the 90-day mail price includes shipping", kind `couldnt_find` ("Could not find it").
- Shows in: `explore_feedback` in `data/human_decisions.json` and the Explore feedback queue.

**D105. Emergency and crisis language is a safety reply, before every other member intent.** (Nov 5)
- Considered: treating chest pain as out of scope; asking the model to notice a crisis.
- Why: a medical emergency has to be answered the same way in chat, on the phone, and on the portal, and it cannot wait on search. `U-SAFE-CRISIS-001` is approved by Dana Okafor (Legal), with `approver_name` Riley Chen (Legal and clinical), `search_visible` 0, so the guided candidate pool is unchanged. The member text tells the caller to call 911 and to call or text 988, and it names the illustrative nurse line `1-800-555-0199` that is also on the plan file. The question is stored redacted in `safety_signals`. It is not added to the gap list.
- Shows in: `classify_member_question`, `POST /api/explore/member`, and `GET /api/portal/answers` for role Member. Kind `safety`.

**D106. Price and visit replies name the read order.** (Nov 5)
- Considered: rewriting the reply sentence so the disclaimer comes first inside `reply`.
- Why: the amount and the disclaimer are separate fields. Putting the order on the response lets every channel follow one rule. `read_order` is `["units", "reply"]` for kind `price` and kind `visit_cost`, on member chat, the portal, and a verified advocate ask.
- Shows in: those three responses and `api/README.md`.

**D107. The greeting conflict suggestion states only what the two texts say.** (Nov 5)
- Considered: regenerating a saved model answer. The suggestion is the `reason` string in `data/human_decisions.json`, not a model fixture.
- Why: the desk copy says to say the call may be monitored. It does not drop that disclosure. It does not include the word recorded. The new suggestion says those two things. When Legal resolves a conflict with a reason that matches the suggestion exactly, the decision event stores `reason_source` `ai_suggestion_accepted`. Any other reason is `typed`.
- Shows in: `GET /api/conflicts` and `POST /api/conflicts/resolve`.

**D108. Member questions that were falling through now use plan data or an approved unit.** (Nov 5)
- A drug plus a supply, 90, or mail is a price, so a 90-day mail apixaban question prices with `U-RX-EDU-PRICE-ANY` once the mail-order conflict is resolved.
- "Real person", agent, representative, human, operator, and "talk to someone" return `handoff_offer` with the advocate chip. The sentence is `U-HANDOFF-PERSON-001`.
- Out-of-pocket uses plan data plus `U-BEN-OOP-001`. Brand names and the misspellings Lipitor, Eliquis, Glucophage, atorvastin, and metforman resolve through formulary aliases.
- Complaint chips list four reasons before the advocate chip. Each reason returns an approved unit.
- A caregiver asking for a price receives `U-RX-EDU-001-05` and no price.
- Out-of-network urgent care and the emergency room use `U-BEN-OON-VISIT-001`. The not-covered sentence is `U-BEN-OON-RULE-001`, not the referral unit.
- These units have `search_visible` 0.
- Shows in: `classify_member_question`, `data/member_data.json`, and the plan-data routes.

**D109. The caregiver golden miss stays a miss. Explore search can still answer it.** (Nov 5)
- Considered: changing the guided candidate pool or the saved model answer so step 8 would pass the held-out caregiver question.
- Why: that would move the guided score off 8 of 8, 4 of 4, held-out 2 of 3, and 6 misses. Scoring sets a flag that skips the shortcut. In the explore world only, a pharmacy search for a caregiver price question returns `U-RX-EDU-001-05` with `ai_source` `rule`.
- A blocked unit whose own knowledge base is another role's base returns a transfer, with no "Under Legal review" line.
- Findability gaps set `answered` from whether the mapped unit is approved and searchable.
- Quality scoring turns live calls off for the run, so the owner screen and step 8 use the same saved-answer rules on whichever database they read.
- Shows in: `search`, `GET /api/gaps`, and `score_golden`.

**D110. The API stops reflecting any origin, and a few reads become exact.** (Nov 5)
- CORS allows the Render host and localhost ports 5173, 4173, 3000, and 8000, with credentials.
- As-of accepts RFC 3339 and `YYYY-MM-DD HH:MM ET`, returns 400 on bad input, and adds `versions_that_day`.
- An approved unit is fetchable by id when `search_visible` is 0. A member channel omits `advocate_text`. A channel the unit does not list is 404.
- Unknown `/api` and `/v1` paths return JSON 404.
- A repeated publish that does not change the wording is rejected. An `idempotency_key` returns the first response. Events include `ts` and `previous_version` and are re-appended if undo restores a snapshot.
- `role` stays client-supplied. `api/README.md` says so under Prototype limits, with the production design.
- Shows in: `api/main.py`, `portal_unit`, and `publish_revision`.

**D111. Cost language is wider, and the person who writes a draft is not the person recorded as approving it.** (Nov 5)
- Considered: sending every gap, and every unit with member text, to Legal.
- Why not for the blanket rule: the prior-authorization FAQ has member text and no cost language, and the authoring loop plus its tests depend on Knowledge Ops approving it. The failure that was confirmed was "forty-seven dollars" and "Coverage is guaranteed", which the old detector missed.
- The detector now also matches spelled-out amounts, dollars, free, guarantee, covered, pay, coverage, and percentages. A draft the author wrote stores `drafted_by` Sam Patel (Knowledge Ops). A Legal approval records `approver_name` Dana Okafor (Legal). An author approval of that draft records Alex Nguyen (Knowledge Ops). `approved_by` stays the role label the existing screens and tests read. `approval_method` is `single`, `bulk`, or `seed`.
- Shows in: `_mentions_cost`, `_mark_approved`, and the two approve routes.

**D112. Undo of a publish appends history.** (Nov 5)
- Considered: keeping snapshot restore for publish, which deleted version 2.
- Why: the version that was read on a call has to remain reachable by as-of. Undo of a label that starts with "Published version" does not restore the snapshot. It marks that version superseded, appends a new version with the earlier wording, and writes `unit.retracted` and `unit.revised`. Other undos still restore one snapshot, then copy the event log back and append `action.reversed`.
- Shows in: `POST /api/undo` and `retract_published_version`.

**D113. Verification is stored on the session.** (Nov 5)
- Considered: trusting the `verified` query flag.
- Why: the flag let any client mark a caller verified. `POST /api/explore/verify` checks the member id and the illustrative date of birth and stores the member on the session. Profile, record, drug price, visit cost, and advocate ask read that store. An unverified payload drops the drug list, recent contacts, plan copays, out-of-pocket figures, coverage stage, and deductible. The signed-in Member role is verified for Dana R. on the member site. The automated line uses `POST /api/explore/phone/authenticate` and `channel` `voice_bot`.
- Shows in: `caller_verified`, `confirm_identifiers`, `confirm_phone`, and the plan routes.

**D114. The visit cache cannot serve a superseded version.** (Nov 5)
- Considered: shortening the cache time only.
- Why: an advocate who already had the desktop open was still shown version 1 after publish. Publish clears the ask cache and the member cache. A cached payload whose unit version is no longer approved is ignored.
- Shows in: `run_publish` and `_cached_version_live`.

**D115. A wrap-up stores the version and a hash of the text that was on screen.** (Nov 5)
- The client sends `displayed_units` with `unit_id`, `version`, and `text`. The record stores `text_hash` and `superseded_read`.
- Shows in: `POST /api/explore/wrapup` and `api/README.md`.

**D116. Bulk approval is closed in Explore.** (Nov 5)
- `POST /api/legal/approve-all` and `POST /api/author/approve-all` return 400 in the explore world. Guided shortcuts remain and are `approval_method` `bulk`.
- Shows in: `run_approve_legal_all` and `run_approve_author_all`.

**D117. An amount in unit text is gated for an unverified caller, and plan figures have their own wording.** (Nov 5)
- Considered: removing `U-BEN-COST-001-07` from search. That would change the guided candidate pool.
- Why: the unit stays searchable. When an advocate ask has a member id and the caller is not verified, a unit whose text contains an amount returns the unverified-caller rule instead of the text.
- Tier 3 drugs other than insulin are priced in the deductible stage until `drug_deductible_met` is true. The illustrative 30-day preferred amount is $180, and the 90-day mail amount is $200, with `U-BEN-DEDUCT-001`.
- Mail-order prices are withheld while the mail-order conflict is open.
- In-network urgent care uses `U-BEN-UC-001`. In-network emergency uses `U-BEN-ER-001`. Claims use `U-BEN-CLAIMS-001`.
- `U-RX-EDU-001-13` stays on the expired list. `review_extension` records Dana Okafor's illustrative extension through 2027-01-15 so the specialty answer and the guided pool stay in place. A past-review unit with an empty extension is the fail-closed case for a later unit. Superseded in part by D120: Explore no longer applies that extension.
- A cosmetic edit inside a verbatim span is logged as a System event and listed on the legal drift view as `automatic`. The approved text stays live, which keeps the cosmetic demo line. Superseded in part by D119: an edit inside the verbatim span now goes to Legal.
- Publish writes `source_annotation` so the live wording is not cited as the old extracted span.
- `if_you_approve.appears_in` uses the channel override, so the short path and the full path list the same channels for the pricing unit.
- Shows in: `drug_quote`, `visit_cost_view`, `explore_ask`, `_store_drift`, and `approval_preview`.

**D118. Redaction covers names and the remaining phone shapes, and it runs before a live call.** (Nov 5)
- Considered: a general capitalized-word detector, which would also remove drug names and plan names.
- Why: the redactor uses the fictional roster and the staff names, longest match first, plus a phone pattern that accepts `(617) 555 0199`. `redact_query` already runs before a question is logged, stored, or placed in a model prompt. `replay` redacts the prompt again before `call_model`, after the saved-answer lookup, so fixture keys stay stable.
- Shows in: `redact_query` and `replay`.
- Superseded in part by D119. Names are also redacted by context and by a capitalised run, in addition to the roster.

**D119. Redact a person's name from context and from a capitalised run.** (Nov 5)
- Considered: the roster only. "My name is Sam Okoro" and "Caller Dana Rivera" stayed in the text when the person was not on the roster.
- Why: the whole name becomes one `[redacted]` after "my name is", "I am", "I'm", "this is", "caller", "name:", "for", and "my daughter/son/wife/husband/mother/father/caregiver". A run of two or more capitalised words is redacted unless it is a drug, plan, pharmacy, or place used in the product, or the first word of a sentence followed by one word. The fixture file has at least 30 lines and the test fails on any miss or false positive.
- Shows in: `redact_names` and `fixtures/redaction_cases.txt`.

**D120. Explore fails closed when a review date has passed.** (Nov 5)
- Considered: keeping the seeded extension on `U-RX-EDU-001-13` in both worlds. That hid the fail-closed path.
- Why: Explore skips the extension. A unit past `review_by` with no extension leaves the search pool. If it would have been the best hit, the reply is "This answer is past its review date and is waiting for Legal." Legal can extend the date, with a reason, or retire the unit. Guided keeps the extension, so the guided pool and step 8 stay put.
- Shows in: `_apply_review_extension`, `explore_expired_block`, `POST /api/legal/review/extend`, `POST /api/legal/review/retire`.

**D121. A cosmetic edit inside Legal's verbatim span goes to Legal.** (Nov 5)
- Considered: logging it as an automatic System event. That never reached Legal.
- Why: the approved text stays live. The item is labelled "Cosmetic change inside Legal wording". Legal can accept it as no change or return it. An edit outside the span still logs "Cosmetic edit logged, nothing flagged". The guided step 8 numbers do not move.
- Shows in: `_store_drift` and `approve_drift_fix`.

**D122. The Explore role is the session role.** (Nov 5)
- Considered: trusting the role in the body or the query.
- Why: `POST /api/explore/open` records the role. Later Explore requests use it. A different supplied role is 403 "Open that role first." Guided still takes the role on the request and records the presenter. Portal answers stay unbound so a channel can ask as the role in the query. Roles match case-insensitively. An unknown role is 400 and lists the allowed roles.
- Shows in: `resolve_explore_role` and `POST /api/explore/open`.

**D123. Phone authentication is per call.** (Nov 5)
- Considered: one verification for the whole session.
- Why: a later call was skipping the check. `call_id` on the voice channel and on authenticate limits the check to that call.
- Shows in: `phone_verified` and `confirm_phone`.

**D124. Automated-line wording is an approved unit.** (Nov 5)
- The greeting, anything-else, no-answer, and verified lines are units with `search_visible` 0 and are returned in `ivr_prompts`.
- Shows in: `ivr_prompt_map` and `seed_finish_units`.

**D125. An authorized-caller request is stored and shown on the record.** (Nov 5)
- The request is `pending`, the name is redacted in the log, the confirmation starts with `AC-`, and the advocate record shows "Asked to add an authorized caller".
- Shows in: `POST /api/explore/member/authorized-caller`.

**D126. A per-unit tag edit is a human decision and does not change the guided pool.** (Nov 5)
- Considered: applying the audience change to guided search.
- Why: bulk confirm stays. A guided audience edit that would change who can see the unit is rejected. Explore can record it. Step 1 finishes when the remaining units are confirmed.
- Shows in: `POST /api/demo/units/{unit_id}/tags`.

**D127. Legal may type the published wording.** (Nov 5)
- Considered: publishing only the prepared revision.
- Why: omitted text still publishes the prepared revision, so step 8 holds. Empty text, unchanged text, and wording that breaks the verbatim check are rejected. A typed revision records `approver_name` and `edited_by_legal`. Saved answers stay matched for the prepared text. Typed text can miss a saved answer until a new one exists. The guided score uses the frozen snapshot.
- Shows in: `POST /api/channels/publish`. The message and the Legal email name the advocate desktop, member chat, the website, and the phone line.

**D128. Legal workload is an illustrative estimate.** (Nov 5)
- Counts by type and risk tier. High is 20 minutes, medium 10, low 5. The proposed tiering sends verbatim, cost, and clinical units to Legal, and low-risk units to Knowledge Ops batch review. Every figure is marked illustrative.
- Shows in: `GET /api/legal/workload`.

**D129. Mutating routes use the session role.** (Nov 5)
- Considered: leaving publish and Legal routes open to any session.
- Why: Legal routes require the Legal approver. Knowledge Ops routes require the author. Gap decisions require the Knowledge owner. The 403 names the role. Guided records that role as the presenter so the demo still walks each step. Explore bulk approval still returns the sandbox refusal before the role check.
- Shows in: `require_actor`.

**D130. Undo is scoped to the actor and the resource.** (Nov 5)
- Considered: one undo slot for the whole session.
- Why: a Member session could undo a Legal publish. Undo from another role is 403. A publish undo still appends a version.
- Shows in: `run_undo`.

**D131. Answers share one status and structured citations.** (Nov 5)
- Considered: sending the portal through the same live call as the desktop, with a timeout back to abstain.
- Why: the portal returns `cache_miss` when there is no saved answer, and it does not place a live call. The desktop can still live-call, then abstain. `citations` is structured. The string `citation` stays so existing clients keep working. Price, visit, referral-note, and out-of-pocket sentences are approved template units.
- Shows in: `attach_answer_fields` and `U-TPL-PRICE-001`, `U-TPL-VISIT-001`, `U-TPL-REFERRAL-NOTE-001`, `U-TPL-OOP-001`.

**D132. Errors are problem documents, and roles are case-insensitive.** (Nov 5)
- The body has `type`, `title`, `status`, `detail`, and `error`. `allowed` lists the valid roles or channels when that is the failure. Content type stays `application/json`.
- Shows in: `problem_body`.

**D133. Events carry an id and a time, and webhooks are recorded.** (Nov 5)
- Each event has `event_id`, `occurred_at`, `previous_version`, and `ts`. Portal events take a cursor and return `next_cursor`. `POST /api/portal/webhooks` stores a subscriber and a signing secret. Deliveries are recorded with an HMAC and an attempt count. They are not sent.
- Shows in: `append_event` and `register_webhook`.

**D134. The two price disclaimers are linked siblings.** (Nov 5)
- Considered: publishing one and leaving the other until someone noticed.
- Why: after version 2 of `U-RX-EDU-001-09`, other supplies still used `U-RX-EDU-PRICE-ANY` version 1. Publishing either opens a Legal item, "A linked disclaimer may need the same change". Both stay approved until Legal accepts, which changes no wording.
- Shows in: `open_sibling_review` and `POST /api/legal/link-review/accept`.

**D135. Guided Quality scores a frozen full-path snapshot.** (Nov 5)
- Considered: scoring whatever the session had clicked. A fresh session then reported 0 of 8.
- Why: the snapshot follows the presenter path through publish, the gap note, and drift. A fresh guided session and step 8 both read 8 of 8, 4 of 4, held-out 2 of 3, and 6 misses. The caregiver held-out stays a miss. The unit does answer "no". The miss is retrieval, and the owner chose to keep it visible. A leaks result with zero answers is "not measured". Explore adds role, intent, and robustness slices and a Wilson 95% interval. Those slices do not enter the guided counts.
- Shows in: `guided_score_connection` and `decorate_quality`.

**D136. Explore retrieval has its own guardrails.** (Nov 5)
- Considered: sending 20 candidates into the saved-answer key. The saved answers were recorded for three candidates, so every Explore question would miss.
- Why: Explore still retrieves 20, with spelling and brand synonyms on the rank query. When that prompt has no saved answer, the sandbox replays the top-3 saved answer and still returns the 20 ids. A live call would send 20. The cache key folds case, punctuation, and whitespace. Questions stop at 500 characters. The live cap is per sandbox and per IP. A lookup past 6 seconds abstains. Guided stays at 3 candidates.
- Shows in: `decide`, `candidate_limit`, and `explore_ask`.

**D137. Member chat keeps context and answers the gaps from the Dana and Ana review.** (Nov 5)
- A continuation keeps the drug, the supply, and the pharmacy. A new topic does not inherit the drug. Cheaper comparisons show both prices and the monthly difference. An all-drugs question lists each drug and a total. Two questions answer the first and offer the second as a chip. Glossary, cost help, callback, grievance, and the authorized-caller confirmation are approved units. Dana's claims include an illustrative $140 apixaban charge. Each overcharge reason chip uses an approved unit.
- The plain member sentence for `U-RX-EDU-PRICE-ANY` is applied. That unit is not in the search pool. The member text of `U-RX-EDU-001-09` stays as approved. It is the member search candidate, and a plainer sentence there would change the saved answers and the guided member candidates. Stopped, as the brief required.
- Shows in: `classify_member_question`, `merge_context`, and `seed_finish_units`.

**D138. The automated line covers Dana's list and the same plan questions.** (Nov 5)
- Drugs on the list, 90-day mail, specialist cost, the out-of-pocket maximum, a billing problem, and a callback return chips the caller can choose. The same member intents are used, with `call_id`.
- Shows in: `member_turn` when `channel` is `voice_bot`.

**D139. A fresh guided score matches step 8, and a cross-base referral offers a transfer.** (Nov 5)
- A fresh `POST /api/quality/score` with `world` `guided` reads the frozen snapshot, so hit@1 is 8 of 8. A pharmacy question about a referral returns `transfer` with queue "Insurance queue" while the answer stays an abstention.
- Shows in: `quality_view` and `cross_kb_transfer`.

**D140. Portal and member edges from the pass 5 ledger.** (Nov 5)
- Member routes require a member id. An unknown channel is 400 and lists the allowed channels. The Insurance portal question "what do I say before I quote a cost" returns `U-BEN-COST-001-02` from the published snapshot when the Explore merge has no approving saved answer. An out-of-network specialist cites `U-BEN-OON-RULE-001` and `U-BEN-OON-NEXT-001`. `GET /api/portal/openapi.json` describes the portal routes and the problem schema. The website can fetch `U-SITE-MAIL-001`, `U-SITE-FIND-001`, and `U-SITE-HELP-001`.
- Shows in: `portal_answer`, `portal_one_view`, and `portal_openapi`.

**D141. A new version keeps the linked sibling.** (Nov 5)
- Considered: reading `sibling_of` only from the newest version. Publish inserts the next version without that column, so the newest row is blank and the linked review never opens.
- Why: publish, a drift approval, and a publish undo each copy `sibling_of` onto the new version. If that source row is blank, the link is read from any earlier version that still has it. `GET /api/legal/link-reviews` lists every open review with `unit_id`, `sibling_id`, `label`, and `created_at`, so Legal can accept the one that is waiting. Both versions stay approved.
- Shows in: `copy_sibling_of`, `sibling_id`, `GET /api/legal/link-reviews`, and `POST /api/legal/link-review/accept`.

**D142. The extraction view shows a per-unit tag edit.** (Nov 5)
- Considered: writing the edited tags onto the guided unit row. That would change the guided candidate pool.
- Why: the decision stays in `unit_tag_edits`. The extraction screen returns those tags, audience, and domain, and sets `tags_edited_by` to the Knowledge Ops author. Search keeps reading the unit row. An empty field on the decision leaves that field as stored.
- Shows in: `GET /api/demo/extraction` and `POST /api/demo/units/{unit_id}/tags`.

**D143. A cosmetic comma inside Legal wording says it was sent to Legal.** (Nov 5)
- Considered: leaving every cosmetic edit on the line "Cosmetic edit logged. Nothing was flagged." The guided comma is inside the verbatim span, and that edit is sent to Legal.
- Why: `POST /api/drift` with the prepared cosmetic edit, and the matching Drift screen label, return "Sent to Legal: a comma inside Legal wording. The approved version stays live." A cosmetic edit outside a verbatim span keeps "Cosmetic edit logged. Nothing was flagged." The approved version stays live. Step 8 stays 8 of 8, 4 of 4, held-out 2 of 3, and 6 misses.
- Shows in: `run_drift` and the Drift screen label.

**D144. Knowledge Ops reviews every extracted unit before it can be searched.** (Nov 5)
- Considered: letting the AI publish procedures as soon as they are extracted. Also considered sending every unit to Legal, including the duplicate of an already approved line.
- Why: a procedure or FAQ that the routing rule gives to Knowledge Ops can be approved and then becomes search-visible in Explore. Cost, clinical, policy, and verbatim wording cannot be approved on this route. The error is `This unit goes to Legal: {routing reason}.` Knowledge Ops can still send any waiting unit to Legal. An edit saves new wording, type, tags, or audience and leaves the unit waiting. A rejection needs a reason of at least four words, sets status `rejected`, and keeps the unit out of search. Each action records the actor, the time, and the action. A duplicate of an approved unit stays with Knowledge Ops so they can reject it. The guided world does not load these documents. A sandbox unit with no lexical overlap is left out of the ranked list, so it cannot move the saved top three.
- Evidence: the authoring workflow in this change. Figures in `data/sandbox/` are illustrative.
- Shows in: `POST /api/author/units/{unit_id}/review`, `GET /api/documents/{doc_id}` for `SRC-SPEC-SOP-001`, `SRC-PA-FAQ-001`, and `SRC-CALLBACK-001`.

**D145. No source, no unit.** (Nov 5)
- Considered: letting Knowledge Ops replace a bracket and send the draft, which is how the older gap drafts work. Also considered requiring the cited unit to be approved before a document quote counts.
- Why: the three Explore drafts in Drafts to finish carry `needs_source`. Send is refused with `Ground and fill every placeholder before sending this draft.` until every placeholder is grounded and filled. A `unit` or `document` quote must be an exact substring of that approved unit or of that document, or the error is `That passage is not in the source.` The filled text must appear in the cited passage, ignoring case and whitespace, or the error is `That fact is not in the cited source.` Older drafts keep `needs_source` at 0, so the bracket check is still the only gate. The prior-authorization timing draft can be grounded in `SRC-PA-FAQ-001` before that FAQ is approved, because the quote is a substring of the document. The unit that send creates lists those sources, and Legal sees them.
- Evidence: the gap workflow in this change. The timing figures in `SRC-PA-FAQ-001` are illustrative.
- Shows in: `POST /api/author/gaps/{gap_id}/placeholders/{index}/source`, `POST /api/author/gaps/{gap_id}/placeholders/{index}/fill`, and `POST /api/author/gaps/{gap_id}/send`.

**D146. A named owner can attest a fact that no document states.** (Nov 5)
- Considered: storing the owner's sentence only on the gap row. Also considered blocking the sandbox until a separate owner account exists.
- Why: `kind` `request` opens a source request to `owner_role` with status `pending`. In the sandbox the Knowledge Ops author may answer it, and the record is marked `Simulated owner reply`. The answer writes document `SRC-ATTEST-{n}` with a title, the statement, the signer, the owner role, and the date. `GET /api/documents/{doc_id}` returns that document, and a later fill must quote the statement.
- Evidence: the insulin mail draft. No sandbox document states the 90-day rule. Pharmacy Operations is the named owner. The statement is illustrative.
- Shows in: `GET /api/explore/source-requests`, `POST /api/explore/source-requests/{id}/answer`, and `SRC-ATTEST-{n}`.

**D147. A fact with no owner goes back to the Knowledge owner as a process gap.** (Nov 5)
- Considered: inventing an owner so the draft could still be sent. Also considered deleting the question from the advocate's search.
- Why: `POST /api/author/gaps/{gap_id}/no-source` sets status `process_gap` and the label `The business has no answer yet`. The draft leaves Drafts to finish. Insights lists it on `process_gaps`. An advocate search that abstains on that exact question keeps the no-answer and adds `follow_up`: `The business has no answer yet. Follow up with the knowledge owner.`
- Evidence: the ride draft. No document states it, and this made-up company has no owner for the fact.
- Shows in: `POST /api/author/gaps/{gap_id}/no-source`, `GET /api/explore/insights`, and `POST /api/search`.

**D148. A source change goes to whoever approved the live unit.** (Nov 5)
- Considered: sending every material change to Legal. Also considered taking the approved wording offline while the proposal waits.
- Why: the approved version stays live. The 30-day to 31-day change on the Legal verbatim unit stays on Legal's existing drift routes. The callback-hours change is material and goes to Knowledge Ops, so the three callback procedures are approved in the Explore seed before that case starts. `accept_fix` and `edit_and_accept` publish a new version and keep the old one. `keep_current` needs a reason of at least four words and clears `stale`. A comma added inside a Knowledge Ops procedure is cosmetic: it is logged automatically, the approved text does not change, and nothing is flagged. Legal's drift routes are unchanged.
- Evidence: the three drift cases in the Explore seed. The hours are illustrative.
- Shows in: `GET /api/author/drift`, `POST /api/author/drift/{id}`, and `GET /api/legal/drift`.

**D149. Knowledge Ops My work lists four groups.** (Nov 5)
- Considered: keeping advocate and channel flags on the Knowledge Ops queue next to documents and drafts.
- Why: flags already appear on the Knowledge owner's Insights and on `GET /api/feedback/author`. The records stay. `GET /api/explore/my-work` for the Knowledge Ops author returns only Documents to review, Drafts to finish, Source changes, and Sent back by Legal.
- Evidence: the My work change in this pass. The seeded feedback records are unchanged.
- Shows in: `GET /api/explore/my-work` and `GET /api/explore/insights`.

**D205. The Knowledge Ops sandbox screens follow pull request 67.** (Nov 6)
- Considered: keeping the single Rx script as the only reviewable document, and keeping the plain text editor for every gap draft.
- Why: My work now lists the four groups from `GET /api/explore/my-work`. Any document opens beside its units with Approve, Send to Legal, Edit and Reject; Approve is hidden when the unit requires Legal. A gap draft with placeholder sources opens a grounding screen: per placeholder, cite a sentence from a document or ask the owner, then fill from the cited words only; "No one owns this fact" returns it as a process gap. The older Rx disclaimer draft keeps the plain editor because it has no placeholder sources. The drift screen shows the live wording beside the AI's fix, plus the automatic log and a note that Legal wording drift goes to Legal. Legal's review shows units Knowledge Ops just sent first, so a presenter does not page through the seeded backlog. Assumption: sorting by status `with_legal` on the client is enough, because only Knowledge Ops sends set that status.
- Evidence: browser runs of all three documents, all three gaps, the drift case, and Legal approve and send back. Step 8 still reads 8 of 8, 4 of 4, held-out 2 of 3, 6 misses.
- Shows in: Explore, Knowledge Ops author: My work and Sources. Explore, Legal approver: Start review.


**D206. The sandbox shows exactly three gaps and three drift cases, and Legal sees its drift case.** (Nov 6)
- Considered: leaving the older Rx disclaimer draft in Drafts to finish, and showing only the drift case Knowledge Ops can act on.
- Why: the user expected three gaps and three drift cases on Knowledge Ops' My work and saw four and one. Drafts to finish now lists only drafts with placeholder sources, so the older bracket-only draft is hidden; the Q&A loop in DEMO.md uses the prior authorization gap instead. Source changes lists all three cases: the callback hours (Knowledge Ops decides), the cosmetic comma (logged, read only), and the 30-day to 31-day change (With Legal, read only, from `GET /api/legal/drift`). The Legal drift case had no screen in Explore; the Legal inbox now has a "Source changed under approved wording" email with approve and send back (reason of at least 4 words). The Legal digest lists what Knowledge Ops sent, or says nothing has arrived yet. The "Waiting on Legal" conflicts note left Knowledge Ops' My work.
- Evidence: the user's review of the live site on Nov 6.
- Shows in: Explore, Knowledge Ops author: My work. Explore, Legal approver: Inbox.

**D207. Realistic sandbox documents, and unanswered questions start from what the AI found.** (Nov 6)
- Considered: keeping the short sandbox documents, and keeping one grounding screen where Knowledge Ops picks any passage or asks an owner.
- Why: the user pointed out that a real SOP is a full document, with the units highlighted inside it, and that "Drafts to finish" did not say what the group holds. The three sandbox documents are now 300 to 750 words with purpose, roles, exceptions and revision history; every unit passage is unchanged, so routing and tests hold. Units are numbered in document order. The group is renamed **Unanswered questions**. Each gap shows the AI's candidate source with a trust level: a Harbor document still in the review backlog (use it), unreviewed website copy (ask the expert to confirm), or nothing (ask the expert). The expert can answer, which creates an attested source, or say no policy exists, which makes it a process gap shown on Insights. Dismiss covers questions an approved unit already answers and questions outside what Harbor does. A unit Knowledge Ops owns is approved when it finishes the question; regulated wording still goes to Legal. Before this, a finished FAQ was routed to a Knowledge Ops approvals list that the simplified My work no longer shows, so it had no place to be approved.
- Assumption: the AI's search result is seeded data, labelled illustrative. In production it would come from retrieval over every document Harbor holds.
- Evidence: the user's review on Nov 6. Browser runs of all three questions, the SOP review, Legal, and Insights. Step 8 still reads 8 of 8, 4 of 4, held-out 2 of 3, 6 misses.
- Shows in: Explore, Knowledge Ops author: My work. Explore, Knowledge owner: Insights. `GET /api/author/edits`, `POST /api/author/gaps/{gap_id}/dismiss`, and `no_policy` on the source request answer.

**D208. Eval documents and a blind answer key for extraction, duplicates, and gaps.** (Nov 5)
- Considered: writing the answer key after a model had extracted the documents. Also considered: putting the passages in `data/sandbox/`, which the Explore demo already loads.
- Why: `data/eval/` holds three illustrative Harbor Health documents, each 600 to 900 words, plus an answer key and a trap list. The keys were written on November 5, 2026, before any model run. A key row is never edited after model output exists. If a row is wrong, add a correction row with a note naming the date and the row it corrects. The old row stays. Across the set the units cover verbatim, policy, procedure, and faq, and they cover a Pharmacy advocate, an Insurance advocate, a member, and wording both advocate roles read. The callback policy carries the benefits units and the shared units. A unit's knowledge base can be narrower than the document's: insurance-only lines in that policy are tagged `benefits`, and lines both advocates read are tagged `pharmacy;benefits`. Every figure is illustrative. The guided demo and the Explore sandbox are unchanged.
- Evidence: SPEC section 7. This corpus is the test data for a later extraction, duplicate, search, and gap runner. This change does not run a model and does not add search questions. The question column on a near-miss trap is the question that passage almost answers.
- Shows in: `data/eval/specialty_pharmacy_intake_sop.md`, `data/eval/prior_authorization_faq.md`, `data/eval/member_callback_policy.md`, and `data/eval/keys/`.

**D209. Evals run in a GitHub Action, five times each, scored against blind keys.** (Nov 6)
- Considered: calling the model from the development container, and scoring one saved run per input as the demo does.
- Why: the container cannot reach the model API, and a key in an environment variable would be stored in plain text. The repository secret `ANTHROPIC_API_KEY` is read only by `.github/workflows/evals.yml`, which records every output under `fixtures/eval/run<n>/`, scores them, and commits the outputs and `docs/eval-report.md` to the branch it ran on. Each input runs five times, so the report shows how often the same input gets the same decision. An item counts as right when most runs got it right; the 95% interval is a Wilson interval on that count. The search eval treats every key unit as approved, so it measures search on its own, separate from extraction. The same workflow can record saved answers for inputs Explore would otherwise send to the model live; it records only those, so the guided demo's scores cannot change. D208 is reserved for the eval corpus written in another branch.
- Assumption: the keys and test sets are committed before the first run, and git history shows the order.
- Shows in: `scripts/run_evals.py`, `.github/workflows/evals.yml`, `data/eval/results.json`, `docs/eval-report.md`.

**D210. Lookalike pairs are reported two ways, and the answer key is not edited.** (Nov 6)
- Considered: relabelling the four lookalike rows in `data/eval/keys/traps.csv` from `different` to `conflict` after the first run.
- Why: on every run the model called all four lookalikes (for example "within 2 business days" against "within 2 days") a conflict. The key says `different`. By the app's own taxonomy a conflict is the same subject with a different rule, so the model's label is defensible, and the key's stated intent was only that lookalikes must never be merged as duplicates. Editing the key after seeing output would break the blind-key rule (D208). The report shows both: the exact label (0 of 4) and never merged as duplicates (4 of 4). The second metric was added after the first run, and the report says so.
- Also: definitions and pointer sentences ("The fee is on the rate card. This SOP does not state that fee.") are keyed as text to leave alone, and the model extracts several of them. They stay scored as misses.
- Shows in: `scripts/run_evals.py`, `docs/eval-report.md`, and the results page.

**D218. Blind test sets for search, duplicates, drift, and gaps.** (Nov 6)
- Considered: writing the sets after a first model run, and reusing the six near-miss questions in the keys as the main search traps.
- Why: the sets are committed before the first run of `.github/workflows/evals.yml`, so git history shows they could not be tuned to model output. They were written without opening `data/eval/keys/`. `questions.csv` has 53 questions across the three eval documents and the demo documents: 16 plain, 9 misspelling, 9 acronym, 7 partial, 8 other_role, and 4 near_miss. The near-miss questions are new ones (an expedited clock, an out-of-network copay, a weekend callback, a case-file retention period) so they do not repeat the six in the keys. 12 questions expect "no approved answer". `dedup_pairs.csv` has 33 pairs: 11 duplicate, 12 conflict, 10 different, and 10 of them are Legal wording. A different number of days or dollars on the same subject is a conflict; "different" is only for different subjects. Wording changes to a Legal block with the same terms are labelled duplicate, which matches `data/dedup_variants.csv`. `drift_cases.csv` has 10 edits, 5 cosmetic and 5 material; a contraction inside a Legal verbatim block is material because the drift prompt counts required wording as material. `gap_cases.csv` has 11 questions, 7 with no known fact. A set row is never edited after model output exists; corrections are added as new rows.
- Assumption: the key marks the member-phrased FAQ and callback lines as member audience, and the grievance callback line as benefits only (D208 says insurance-only lines in the callback policy are tagged benefits). Rows that rely on this say so in their notes. If the key disagrees, the row is corrected with a new row.
- Evidence: every `expected_span`, drift `old_text`, and gap `known_fact` was checked in code as an exact substring of its source document. Spans from demo documents were checked against the demo pool with the runner's own matching rule.
- Shows in: `data/eval/sets/`, read by `scripts/run_evals.py`. Every figure is illustrative.

**D219. The first full eval run, and how its results are shown.** (Nov 6)
- What ran: five runs of every input in `data/eval/` (122 saved outputs per run, about $7 of model calls in total). Results are in `data/eval/results.json`, `docs/eval-report.md`, and the `/evals` page.
- How misses are shown: every item wrong on any run is listed with "runs right: n of 5", so a flaky item (right on 3 of 5) is told apart from one wrong on every run. Scores count an item right when most runs got it right.
- Partial answers: the search prompt tells the model to choose a unit only when it fully answers the question. On two-part questions where one part has an approved answer, it abstained 6 of 7 times; the test set expected the partial unit. The page presents this as an open product decision for the pilot, not only a score. Neither the prompt nor the test set was changed after the run.
- A one-line scorer change (a unit that contains the whole expected sentence counts as a hit) was made while checking a miss; it changed no score.
- Shows in: `/evals`, `docs/eval-report.md`.

**D220. Knowledge Ops can add a unit the AI missed, from the exact source passage.** (Nov 6)
- Considered: letting Knowledge Ops type a new unit freely, and leaving missed passages for a later re-extraction.
- Why: extraction will miss statements in real documents, and the reviewer looking at the document is the right person to catch them. The reviewer selects a passage in the document (or picks a sentence from a list, which also works by keyboard) and sets the title, type, audience and tags. `POST /api/author/documents/{doc_id}/units` accepts only a passage that is word for word in the document, at least four words, and not already a unit. The unit keeps the document's words as its text, is tied to that passage (so the same highlighting and drift checks apply), is recorded as drafted by the Knowledge Ops author with a human decision, and waits for a decision like any extracted unit. The routing rule still decides the approver: procedures and FAQs to Knowledge Ops; policy, verbatim, cost and clinical wording to Legal. New units stay out of search until approved.
- Shows in: Explore, Knowledge Ops author: any document under Documents to review or Sources.

**D221. My work holds only decisions; Legal reviews everything on a full page.** (Nov 6)
- Considered: keeping the cosmetic and Legal-routed source changes in Knowledge Ops' My work for context, and letting Legal decide the drift case inside an email.
- Why: the user pointed out that items with nothing to do do not belong in My work, and that every Legal item should open the same full review. Knowledge Ops now has three source changes that each need a decision: a material change (accept, edit, or keep with a reason), a change the AI is unsure about (confirm cosmetic, or treat as material), and a deleted source passage (retire, or keep with a reason). Purely cosmetic edits are logged under Sources, "Changes handled automatically". Legal has three emails, each with Start review: approvals and conflicts, three source changes (two material, one cosmetic inside word-for-word wording, which must match its source exactly), and the version 2 revision. One review screen serves both roles, showing the source document with the changed passage highlighted and the live wording beside the AI's proposal. Unanswered questions with a candidate source now show the whole document or web page with the passage highlighted.
- New back end: `kind` on each source change (`material`, `uncertain`, `removed`, `cosmetic_verbatim`), decisions `confirm_cosmetic` and `retire` on `POST /api/author/drift/{id}`, and `GET /api/legal/source-changes` with `POST /api/legal/source-changes/{id}`. The original 30-day case still runs through the original Legal drift functions, so the guided demo is unchanged.
- Shows in: Explore, Knowledge Ops author: My work and Sources. Explore, Legal approver: Inbox.

**D222. On the advocate desktop, the member's question and its approved answer come first.** (Nov 6)
- Considered: keeping answers in the right-hand panel under search, and simulating a real-time transcript with timed audio.
- Why: the user named the answer to the question just asked as the single most important thing an advocate sees. The Interaction tab now opens with a Live call strip. Each call has two or three scripted member questions in plain words, played one at a time; the latest question is shown large, with the approved answer directly under it: word-for-word wording and plan figures in that order, no approved answer with what to say, the unverified-caller rule, or a transfer for another queue's question. The screen shows the search that ran, so it is clear the sandbox scripts the speech-to-question step. The right panel keeps manual search and plan figures. Only units typed verbatim are labelled "Read word for word first"; others read "Also applies before you quote". The scripted questions use searches with saved model answers, and the recorder now saves any the live site would otherwise call live.
- Also fixed: a search for an unverified caller could crash (`'sqlite3.Row' object has no attribute 'get'`) when the found unit came back as a database row.
- Shows in: Explore, Pharmacy advocate and Insurance advocate.
- Revised the same day after review: an unverified caller's result was presented as the answer to read, although it is a rule for the advocate. It now reads "Verify the caller before you answer", marks the rule "for you, do not read it to the member", and offers a verify step; the answer (disclaimer, then price) appears after it. An expired answer now says so instead of a generic no answer. The right panel no longer repeats suggested answers.

**D223. A curated copy of the repository is published for reviewers.** (Nov 9)
- Supersedes D27 in part: the working repository stays private; this copy is public.
- Why: reviewers asked to see the work. The copy is one commit, without the history, internal working files (build logs, self-critiques, audits, agent prompts, research notes) or copies of third-party sources, which stay private as D27 requires. There is still no license.
- Added for reviewers: `EVAL_PLAYBOOK.md`, `HARNESS.md` and `PORTFOLIO.md`, written after the presentation from the work in this repository.

