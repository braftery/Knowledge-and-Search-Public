# Experience Spec: Touchpoints for Single Source

> **Public copy:** this document refers to internal working files (such as the build evaluation) that are not included in this public copy of the repository.

The formal vision for each user's experience: where they meet Single Source, what they get first, how fast, and how we will check the build against it.

**How this fits with the other documents.**
- `SERVICE_DESIGN.md` says who the users are, their jobs, pains, unmet needs and value propositions. Section 10 summarizes the touchpoints in this document.
- This document turns that into one experience per touchpoint.
- `APP_SPEC.md` and `BUILD_EVALUATION.md` cover the guided demo. Explore mode builds the touchpoints below.

**Labels.** Section references such as "2.3" point to `SERVICE_DESIGN.md`. Every time target is an *(assumption)* to validate with real users. All names, plans and figures are illustrative. The fictional plan is Harbor Health. No mockup may copy the look of Humana's or any real company's website, app or tools.

---

## 1. Principles for every touchpoint

1. **Meet people where they already work.**
   - Only Knowledge Ops and Legal open the workspace.
   - Advocates, members and channel teams get the output inside the tools they already use.
2. **Time to value first.**
   - The first screen of every touchpoint delivers that user's first value moment (section 10 of the service design).
   - Nothing stands in front of it: no empty dashboards, no setup, no navigation to learn.
3. **One unit, everywhere.**
   - Every channel renders the same approved unit by reference.
   - A revision reaches all of them at once, and the version shown is the same everywhere.
4. **Show provenance, scaled to the audience.**
   - Authors and Legal see IDs, versions, sources and approvers.
   - Advocates see a short citation.
   - Members see a plain citation, never a unit ID or the word "unit".
5. **Say when there is no approved answer.**
   - Every touchpoint that answers questions has a designed "no approved answer" state with a next step.
   - The question goes to the gap queue.
6. **AI proposes, people decide.**
   - Every AI output is labeled as AI.
   - Approval, conflict resolution and publication are human actions with a recorded reason where the service design requires one.
7. **Accessibility floor.**
   - WCAG 2.1 AA, text at least 16 px, and full keyboard use.
   - Meaning never carried by color alone.

---

## 2. Knowledge Ops author: Single Source Studio

**Touchpoint.** A dedicated desktop web workspace, used all day as the author's main job, on a large screen.

**Pains it answers (2.1).**
- Copies of the same content in many documents, with no way to find them all.
- Slow updates.
- Content written as long documents, not reusable pieces.

**Unmet needs (2.1).**
- One place to change a statement.
- Automated discovery of copies and conflicts, with a human deciding.
- A signal of what to write next.

**Value proposition (5).** Change a statement once, and see every copy and conflict found for you.

**First value moment and target.**
- Sign-in lands on **My work**: a queue of what needs the author now.
- Target: working the first item in under 1 minute.
- After uploading a document, its proposed units are ready to review in under 5 minutes.

**The first screen must show.**
- **My work**, grouped and counted: new extractions to confirm, copies and conflicts to settle, units waiting for the author's approval, drift flags, and gaps assigned to the author.
- One primary action per group, opening the first item.
- A search box across all units.

**Primary actions.**
- Confirm extracted units, with tags and audience.
- Choose the canonical wording for copies.
- Escalate conflicts to Legal.
- Approve non-gated units: procedure and FAQ.
- Send a gap draft to authoring.

**Deliberately left out.**
- Channel previews beyond the approval preview.
- Analytics, which belong to the Knowledge owner.

**Look and feel.** A dense, multi-pane desktop layout: queue on the left, item in the center, source passage on the right.

**Acceptance checks.**
- At 1280 x 800 after sign-in, My work and the first item's primary action are visible without scrolling.
- Every queue item opens in one click, and every queue shows its count.
- No empty state without a reason and a next step.

---

## 3. Legal / Compliance approver: Legal review inbox

**Touchpoint.**
- An email or Teams notification ("3 units await your review") that deep-links to a review page.
- Used a few times a week, between other work. High stakes.

**Pains it answers (2.2).**
- Approval sits on whole documents, and later edits are not re-signed.
- A revision does not reach every copy.
- Proving what was said on a date takes manual reconstruction.

**Unmet needs (2.2).**
- Approval at the statement level, with the contexts it covers.
- Every channel reflecting a revision at once.
- A version history by date.
- Final say on conflicts.

**Value proposition (5).** Approve statements, not documents, and see exactly what will go live and where.

**First value moment and target.**
- The notification opens straight to one unit, with everything needed to decide on that page.
- Target: under 2 minutes from opening the notification to a recorded decision.

**The first screen must show.**
- The wording, with verbatim marked.
- The source passage with the span highlighted.
- The verbatim check result.
- **If you approve:** who can search it, which channels show it, what it applies to, and which wordings it replaces.
- Approve, or decline with a required reason.
- How many items remain.

**Primary actions.**
- Approve.
- Decline with a reason.
- Resolve a conflict: pick a wording and record a reason.
- Publish a revision.
- Look up what was live on a date.

**Deliberately left out.**
- The library.
- Authoring.
- Any navigation beyond the review queue and version lookup.

**Look and feel.** A focused, single-column review page, reached from a notification mock.

**Acceptance checks.**
- From the notification, the decision controls are visible without scrolling at 1280 x 800.
- Declining or resolving without a reason shows an inline error and keeps the input.
- Every decision is logged with role, time and reason.

---

## 4. Advocates (Pharmacy, Insurance): Agent desktop knowledge panel

**Touchpoint.**
- A knowledge panel docked inside the advocate's existing agent desktop, used during a live call.
- Humana's Agent Assist is the kind of tool this sits in (company-stated) [5.31a].

**Pains it answers (2.3).**
- Searches return documents, not answers: finding information quickly was the top-ranked challenge, at 58.6% [1.8].
- Advocates cannot tell which wording is current or approved.
- Verbatim is buried in long documents.
- Gaps are invisible to anyone who could fix them.

**Unmet needs (2.3).**
- One cited answer.
- Exact verbatim, marked.
- Results limited to the advocate's role.
- An explicit "no approved answer" so they know to escalate.

**Value proposition (5).** One cited answer with exact verbatim, limited to the advocate's role.

**First value moment and target.**
- The panel already shows answers suggested from the call reason before the advocate types.
- Target: under 10 seconds and at most one action from the member's question to reading the wording.

**The first screen must show.**
- Call context: fictional member, plan and call reason.
- Suggested answers for that call reason.
- A search box.
- For the chosen answer: the wording at the top, with verbatim in a "Read to member" block, a short citation, and a copy button.

**No-answer state.**
- "No approved answer", in plain words.
- What to do next: escalate, or offer a callback.
- Confirmation that the question was logged for the knowledge team.

**Deliberately left out.**
- Lists of documents, metadata, tags, and anything outside the advocate's knowledge bases.

**Look and feel.**
- A fictional agent desktop: call controls and member summary on the left, the knowledge panel on the right.
- The panel is about 400 px wide, so it works beside other tools.

**Acceptance checks.**
- At 1280 x 800, a suggested answer's wording is readable without scrolling.
- A typed question returns one answer or the no-answer state, never a list of documents.
- Pharmacy and Insurance see different answers to the same cost question.
- A pharmacy-only question returns no answer for Insurance.

---

## 5. Member: Harbor Health app, website and phone line

**Touchpoint.**
- The plan's mobile app chat, the website help pages, and the automated phone line.
- The member never sees the platform.

**Pains it answers (2.6).**
- Different answers from the website, the bot and an advocate.
- Wrong information can cause real harm, as in the Aetna case [4.9].

**Unmet need (2.6).** The same correct answer in every channel, with the right disclaimers.

**Value proposition (5).** The same correct answer in every channel.

**First value moment and target.**
- One turn: the first reply answers the question in member wording with its disclaimer, or hands off to a person with context.
- General plan information needs no sign-in. Member-specific figures need one; the prototype shows the site signed in as a fictional member, with prices from mock plan data and the approved disclaimer attached to every number.

**Designing for who members are (2.6).**
- The phone line is a first-class channel. Many older members prefer to call, and many members are helped by a family member or caregiver who calls for them.
- Spoken answers lead with the number, use short sentences, and end with an offer of a person. A clarifying question on the phone becomes a short exchange ("Which drug? You can say atorvastatin, metformin, or apixaban").
- Every member page and chat reply offers the phone number and a person. Nothing requires the app.
- Readability: at least 16 px text, high contrast, large targets, plain language. The member site has a labelled "Text size: Standard | Larger" control that raises every member text style by about 20% and reflows the page; the choice carries to the app and the phone transcript. TTY and interpreter access are on the roadmap.
- In Explore, the member opens on the phone line first, then the website and the app, to reflect that order of preference.

**The first screen must show.**
- **App chat:** suggested questions, an input, and replies in member wording with a plain citation ("Source: Harbor Health, pricing disclaimer, version 2").
- **Website:** a help page that renders the same member wording, with "Last updated" and the version.
- **Phone line:** a transcript of the automated voice reading the same member wording.

**No-answer state.**
- "I do not have an approved answer for that."
- An offer to connect to a person.
- No guessing, and no advocate-facing text.

**Deliberately left out.**
- Unit IDs, tags, approvers, internal notes, and the word "unit".

**Look and feel.** A phone frame for the app, a web page frame for the website, and a call transcript for the phone line, all branded Harbor Health.

**Acceptance checks.**
- The same question shows identical member wording in the app, the website and the phone transcript.
- After Legal publishes a revision, all three show the new version.
- No member-facing view contains a unit ID or advocate text.

---

## 6. Knowledge owner: Knowledge insights

**Touchpoint.** A weekly insights view inside the workspace, plus a weekly digest that links to it.

**Pains it answers (2.5).**
- No tool logs empty searches.
- Priorities come from anecdotes.

**Unmet needs (2.5).**
- Clustered, counted unanswered questions, each with a draft.
- The choice between writing content and fixing the process.

**Value proposition (5).** A ranked list of real unanswered questions with drafted answers.

**First value moment and target.**
- The top unanswered clusters are ranked by demand, each with a drafted unit and a one-step decision.
- Target: under 5 minutes to assign the top gaps.

**The first screen must show.**
- Top gaps, ranked, with counts, roles and a draft.
- Drift flags waiting for Legal.
- Units past their review date.
- Quality: right answer first, correct and wrong no-answers, cross-role leaks, and held-out results.

**Primary actions.**
- Send a draft to an author, fix the process instead, or dismiss. Each needs a reason.
- Open a drift flag or an expired unit.

**Deliberately left out.** Authoring and approval.

**Look and feel.** A dashboard with ranked lists and metric tiles, using position and length rather than gauges.

**Acceptance checks.**
- Counts come from logged searches.
- Every metric shows its denominator and "Illustrative".
- Every item links to the place it can be acted on.

---

## 7. Channel and AI feature teams: Developer portal

**Touchpoint.** A developer portal with API reference, change events and a changelog, used when building or debugging a channel.

**Pains it answers (2.4).**
- Each team writes its own version.
- Retrieval over raw documents gives inconsistent, sometimes non-compliant answers [3.6].
- Every new AI deployment needs a grounded source [5.31a].

**Unmet needs (2.4).**
- A governed source of approved units with IDs, versions and scopes.
- Change notifications.
- A citation to show in the channel.

**Value proposition (5).** A governed, versioned source to ground on.

**First value moment and target.** A first successful call returns an approved unit with version and citation, in under 15 minutes from opening the portal.

**The first screen must show.**
- A quick start with a copyable sample request.
- The sample response: unit ID, version, advocate text, member text, applicability, effective date, approver and channels.
- The "unit revised" event that channels subscribe to.

**Deliberately left out.** End-user screens.

**Look and feel.** A documentation layout with a code panel.

**Acceptance checks.**
- The sample response matches the live unit in the sandbox.
- After a revision, the event shows the new version.

---

## 8. How Explore mode maps to this spec

| Touchpoint | Explore entry | Status |
|---|---|---|
| Single Source Studio | Explore: Knowledge Ops author | Pages exist (PR 15). Needs a My work landing page and the pane layout |
| Legal review inbox | Explore: Legal approver | Queue and conflicts exist (PR 15). Needs the notification entry and the single-page review flow |
| Agent desktop knowledge panel | Explore: Pharmacy and Insurance advocates | Search exists (PR 15). Needs the agent desktop frame, call context and suggested answers |
| Member app, website, phone line | Explore: Member | App chat exists (PR 15). Needs the website and phone transcript views and the engine's member answers |
| Knowledge insights | Explore: Knowledge owner | Gaps, drift, quality and review dates exist (PR 15). Needs a single ranked dashboard |
| Developer portal | Explore: Channel and AI team | The unit feed exists (PR 15). Needs the quick start and change events |

**Build order for Friday:** the advocate panel and member surfaces first, then the Legal review inbox, then re-framing the Studio, insights and developer portal.

---

## 9. Using this spec to evaluate the build

For each touchpoint, check three things:
1. The first screen shows its first value moment at 1280 x 800 without scrolling.
2. The time to value target is met in a timed walkthrough.
3. Every acceptance check passes.

Then confirm the principles in section 1 hold across all touchpoints. In particular, check:
- the same unit and version appear everywhere;
- no member view shows internal data;
- every question-answering touchpoint has a designed no-answer state.


---

## 10. The 5E model: what great looks like at each stage

The 5E model describes an experience in five stages: **Entice** (what draws a person in), **Enter** (what guides them in), **Engage** (the core of the experience), **Exit** (how it ends, ideally with the person better off), and **Extend** (what keeps them connected afterward).

Two adjustments for this product:
- **Staff use is required, members choose.** Authors, approvers and advocates do not decide whether to use the tool. For them, Entice means "what makes me act now and trust it", and Extend means "what makes me rely on it instead of my own copy". Members choose a channel every time, so for them Entice and Extend are about trust and habit.
- **The moment of truth runs through the middle.** Enter leads to the first moment of truth, Engage delivers it, and Exit and Extend set up the second moment, when the answer meets reality (`SERVICE_DESIGN.md` section 11).

### 10.1 Entice

**Definition.** What draws the person to the experience at the moment they need it.

**What great looks like.**
- The person is pulled in by their own need, at the right time, with a reason to act now.
- The invitation names the stakes in their terms: "3 members asked this today", "you read this wording aloud and it changed".
- For members, the plan is the obvious place to ask, in the channel they already use, including the phone.

**Considerations.**
- Mandated users ignore noise. Every notification must carry a reason and a single action, or it trains people to skip it.
- Regulated content changes are urgent for advocates and should interrupt; routine updates should not.
- Older members often start with a phone call or a family member. Enticement for them means the number and a person are always visible, not a push to download an app.

**By role.**
| Role | Great looks like |
|---|---|
| Member | The help page, the chat and the phone menu all offer "what will my drug cost?" in their words |
| Advocate | The suggested answer is already on screen when the call connects, matched to the call reason |
| Knowledge Ops author | Each queue item shows its demand ("asked 340 times") and why it came to them |
| Legal approver | The email says how many items wait and why each came to Legal |
| Knowledge owner | The weekly digest leads with the most-asked unanswered question and what it costs |
| Channel and AI team | The portal promises a cited answer in one call and shows it on the first page |

**Prototype today.** Legal email with routing reasons; author drafts with demand; owner digest leading with the top gap; advocate suggestions per call reason. Gaps: no proactive member outreach.

### 10.2 Enter

**Definition.** What guides the person from arrival to their first useful action.

**What great looks like.**
- The first screen shows the first value moment, with no setup and nothing to learn (principle 2).
- One obvious first action, and a visible way to get a person.
- The person can tell immediately whether this is for them and what they can do.

**Considerations.**
- Advocates enter mid-call under time pressure: zero navigation.
- Legal enters from an email between other work: a deep link to one item, with the count of what remains.
- Members may be unsure what to ask: suggested questions in their words, and a clarifying question instead of a dead end. On the phone, the menu accepts plain speech.
- A first-time explorer (a panelist after the talk) needs a first step: the "Try this" tip.

**By role.**
| Role | Great looks like |
|---|---|
| Member | The phone line asks one open question; the signed-in site opens on the estimator with their drugs listed and a text size control in the header; chat opens with topic chips |
| Advocate | The desktop opens on the active call with caller, verification status and suggested answers |
| Knowledge Ops author | My work is grouped by what needs them, most urgent first |
| Legal approver | "Start review" opens item 1 of N with the reason it came to them |
| Knowledge owner | Insights opens on the decision for the top gap |
| Channel and AI team | Quick start with a copyable request |

**Prototype today.** All of the above are built, including the larger-text control, and the member Explore view opens on the phone line. Gaps: TTY and interpreter paths are roadmap.

### 10.3 Engage

**Definition.** The core of the experience, where the value proposition is delivered.

**What great looks like.**
- The specific answer, with its approved wording and citation, in the form the person needs: a price with its disclaimer for a member, a read-aloud block for an advocate, a diff and a source for Legal.
- Every AI output is labeled, and every decision that changes what members hear is a human action with a recorded reason.
- When there is no approved answer, the person is told plainly and offered a next step; nothing is guessed.

**Considerations.**
- Numbers come from plan data and wording from approved units; the model never writes member-facing wording (D6, D66).
- A price is never shown without its approved disclaimer, and is withheld if the disclaimer is not approved.
- Unverified callers get no coverage details, and the screen says why.
- Spoken answers need wording that works aloud; long verbatim blocks may need an approved spoken variant.
- Required reasons start empty; the AI's suggestion is inserted only by a deliberate click.

**By role.**
| Role | Great looks like |
|---|---|
| Member | "Atorvastatin, 30-day supply: $0", then the disclaimer, then "anything else, or talk to a person" |
| Advocate | The read-aloud block, the member's price on the Prescriptions tab, and "Under Legal review" when a rule is in dispute |
| Knowledge Ops author | The draft editor shows the questions it must answer and the placeholders left |
| Legal approver | "If you approve this unit" shows who will see it, where, and what it replaces |
| Knowledge owner | Each gap shows demand, roles, a draft, and whether it is a search miss or a real content gap |
| Channel and AI team | Try it returns the cited unit or an explicit no-answer |

**Prototype today.** Built across all roles. Gaps: plan-specific answers by coverage stage (ROADMAP R3); spoken variants of verbatim units.

### 10.4 Exit

**Definition.** How the experience ends, and whether the person leaves better off and confident.

**What great looks like.**
- A clear end with a record of what happened, so the person knows they are done.
- The person leaves with what they need for the second moment of truth: the price and what could change it, a compliant call record, a decision on file.
- An easy way to reach a person if anything is unresolved.

**Considerations.**
- Advocates: the wrap-up is the compliance record; it should take seconds and carry call notes forward.
- Members: end with the answer restated, the disclaimer, and the phone number; never end on "no answer" without a hand-off.
- Legal: end on "all caught up" and what happens next.
- The panel: the demo ends on what changed, with skipped steps shown honestly.

**By role.**
| Role | Great looks like |
|---|---|
| Member | "Anything else? Press 0 for a person"; the chat offers "Did that help?" and a hand-off |
| Advocate | Wrap-up confirms the word-for-word read and the outcome, then "Take the next call" |
| Knowledge Ops author | After sending, a card says where the unit went and why |
| Legal approver | "All caught up" with the next digest date |
| Knowledge owner | The decision is saved with its reason and the gap leaves the open list |
| Channel and AI team | A working request to copy into their code |

**Prototype today.** Built, including the guided demo's closing screen. Gaps: chat hand-off does not yet pass the conversation to the advocate (roadmap).

### 10.5 Extend

**Definition.** What keeps the person connected after the experience, so they come back and rely on it.

**What great looks like.**
- People hear back when something they touched changes: a revised wording, a closed gap, an answer to a question they could not get answered.
- Trust grows because the second moment of truth keeps confirming the first.
- Each person sees the effect of their contribution.

**Considerations.**
- Advocates must confirm they read a revised wording before quoting it again; the confirmation is recorded.
- Members who got no answer should be followed up in the channel they chose, including a call back for those who prefer the phone.
- Authors and Legal should see impact: which of their units answered questions this week.
- Channel teams subscribe to change events so revisions arrive without code changes.

**By role.**
| Role | Great looks like |
|---|---|
| Member | A follow-up when an answer to their question is approved (ROADMAP R1) |
| Advocate | The change banner and the "New approved answer" notice for questions their role asked |
| Knowledge Ops author | A weekly note on how their units performed (ROADMAP R2) |
| Legal approver | The same impact note, plus which roles have read each revision |
| Knowledge owner | "Closed this week" and the call wrap-up summary in Insights |
| Channel and AI team | unit.revised, unit.retired and unit.flagged events |

**Prototype today.** Change banner with acknowledgement, closed-gap notices, Insights summaries, change events. Gaps: member follow-up and impact notes (ROADMAP R1, R2).
