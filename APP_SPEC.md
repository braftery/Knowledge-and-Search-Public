# Demo App Spec: Knowledge and Search

The front end shown live on Friday. It sits under `SPEC.md`, which defines the knowledge unit, roles and flows; this file defines what the presenter sees and clicks. Every screen exists to resolve a pain named in the problem brief, and the order of screens is the future-state service journey. Made-up data only (fictional plan: Harbor Health). Every number on screen is labeled illustrative.

## 1. The story the app tells

**Problem (from the brief).** Five pains drive the design:

| ID | Pain |
|---|---|
| P1 | The same legal verbatim lives in several documents with slightly different wording, and it drifts. |
| P2 | Each channel team writes its own answer, so the voice bot, advocate and website disagree. |
| P3 | Search returns documents rather than answers, and cannot say which is current or which wording Legal approved. |
| P4 | Mandatory verbatim is buried in long documents a human opens and follows by hand. |
| P5 | Empty searches are not logged, so owners cannot see what advocates need. |

**Promise.** Author once. Every channel and every search returns the same approved, cited, current unit, scoped to the role asking. When there is no approved answer, the system says so and the question becomes an author's task.

**Arc of the demo.** Show today's failure, then walk the future journey from document to answer, then show the system staying correct: a Legal revision, drift, gaps, and measured quality.

## 2. Service design, mapped to screens

### Authoring journey

| Today (pain) | Future (screen) |
|---|---|
| Legal signs verbatim inside a script; copies are pasted into other scripts, the website and the bot (P1, P2) | **Ingest** (screen 1): the AI extracts typed units from the document, with verbatim marked |
| No one knows which copies exist or which is current (P1, P3) | **Duplicates** (screen 2): the AI pairs near-duplicates and conflicts; a human decides |
| Approval happens on whole documents, if at all; advocate notes are added after Legal signs (P1) | **Approve** (screen 3): the Legal gate on each unit, with an audit trail |
| Each channel team rewrites the content (P2) | **Channels** (screen 5): every channel renders the same unit by reference |
| When Legal revises, someone hunts for every copy (P1) | **Channels** (screen 5): approving a new version updates every channel at once |
| A source document changes and nobody notices (P1) | **Drift** (screen 7): the unit is flagged stale and a fix is proposed |

### Finding journey

| Today (pain) | Future (screen) |
|---|---|
| The advocate searches several tools and gets documents (P3) | **Search** (screen 4): one search returns an answer: the unit, its citation, and the channels using it |
| The advocate opens a long script to find the line to read (P4) | **Search** (screen 4): the verbatim is returned word for word, marked "read exactly" |
| Results ignore who is asking | **Search** (screen 4): results are scoped to the role's knowledge bases |
| Empty searches vanish (P5) | **Search**, then **Gaps** (screens 4 and 6): "No approved answer" is logged, clustered, and drafted into a proposed unit |

## 3. Layout

- **A single browser tab.** A sidebar lists the story in order. Each step is a number and a plain label. The current step is filled. Earlier steps say Done. Later steps are upcoming. Any step can be opened.
  - 0 Today's problem
  - 1 Extract units
  - 2 Find copies
  - 3 Legal approves
  - 4 Search
  - 5 Every channel
  - 6 Gaps
  - 7 Drift
  - 8 Quality
- **A top strip in one row:**
  - "You are: <role>", set by the step, with a Switch role popover for questions;
  - "Step N of 8";
  - a Cached AI or Live AI mode label;
  - Reset demo.
- **The sidebar header** says Harbor Health Knowledge (demo) and "Illustrative, made-up data".
- **Jump to short demo** is in the sidebar. It preloads extraction and the duplicate decisions, approves the other reviewed units, and leaves three units for Legal: the pricing disclaimer, the verification rule, and the benefits cost disclaimer. It lands on step 0.
- **Settings** (the Live AI toggle) is an expander at the bottom of the sidebar.
- **Next** sits at the bottom of each step and moves in order from 0 to 8.
- **Latest activity** is one line under the step, with the full log in an expander.
- **A reusable unit card,** identical everywhere a unit appears. It shows:
  - the title;
  - the unit ID and version;
  - a type badge (Verbatim, Policy, Procedure, FAQ);
  - suggested or confirmed tags, and the domain;
  - a status badge (Proposed, In review, Approved, Superseded, Stale);
  - the knowledge base scope;
  - the channels using the unit;
  - "Approved by [role] on [date]";
  - a "Source" link that opens the source document with the span highlighted.

  Verbatim text sits in a bordered block labeled "Read exactly".
- **An activity log drawer** at the bottom shows every approval, version change and gap action, with the role and time. This makes governance visible.
- **Readability:**
  - body text 18px or larger, headings 28px or larger;
  - high contrast;
  - status shown by text label as well as color;
  - nothing that appears only on hover;
  - laid out for a 1280px-wide shared screen.

## 4. Screens

Each screen has a purpose, the pain it answers, what is on it, the one primary action, a talking point, and a time budget. Screens marked [5-min] form the short path (section 5).

### 0 Today [5-min], 1 minute
- **Pain:** P1, P3.
- **On screen:** a plain search box labeled "Today's document search (illustration of the current state)". The query "Rx pricing disclaimer" is prefilled.
- **Primary action:** run the search. It returns three documents (script v1, script v2, website FAQ) with the three disclaimer wordings side by side and the differing words highlighted. Below each, the document's own header: "Legal last signed: 2025-11-02", "not recorded", and the FAQ's date. A callout reads "Which wording is current? The tool cannot say."
- **Talking point:** this is the brief's scenario, and the brief calls a search box over raw files weak, which is why this screen is labeled as today.

### 1 Ingest [5-min], 1 minute
- **Pain:** P4.
- **On screen:** the source document on the left. On the right, the extracted unit cards, each linked to a highlighted span on the left.
- **Primary action:** "Extract units" on script v1. Cards appear: greeting (procedure), verification steps (procedure), verification rule (policy), pricing disclaimer (verbatim), mail-order rule (policy), specialty rule (policy), closing (verbatim). The mixed paragraph is split into two units. Each card shows suggested tags. The next filled button is "Confirm tags". Advocate notes are tagged as guidance, kept separate from verbatim.
- **Talking point:** the AI decides extraction and type; tags are suggestions a human confirms.

### 2 Duplicates, 1 minute
- **Pain:** P1.
- **On screen:** script v2 and the website FAQ are ingested. Pairs are listed under three headings:
  - Exact match: the closing;
  - Near-duplicate: the pricing disclaimer, with a word-level diff;
  - Conflict: the mail-order rule, side by side.
- **Primary action:** on the near-duplicate, choose "Keep v1 wording as canonical". On the conflict, the only action is "Escalate to Legal". Resolving a conflict of authority is human-only.
- **Talking point:** the AI finds and pairs; the human decides which wording is authoritative.

### 3 Approve [5-min], 45 seconds
- **Pain:** P1.
- **On screen:** the role is switched to Legal approver. The queue lists units needing the legal gate. Each shows its proposed text, source span, duplicates merged into it, and a "Search can see this unit: No" indicator.
- **Primary action:** approve the pricing disclaimer and the closing. The indicator flips to "Yes", and the activity log records the approval.
- **Talking point:** nothing reaches search or any channel until a human approves it.

### 4 Search [5-min], 2 minutes
- **Pain:** P3, P4, P5.
- **On screen:** a search box, plus a split view showing the same query answered for two roles side by side.
- **Primary action:** search "what do I say before I quote a cost". The two sides return:
  - Pharmacy advocate: the Rx pricing disclaimer unit, read exactly, with its citation and channels;
  - Insurance advocate: the benefits cost-estimate unit (see section 6), with its citation;
  - each side shows a line "Searched: pharmacy, shared-legal" or "Searched: benefits, shared-legal".
- **Then:** search "how long does a part d prior auth take". It returns "No approved answer. Your question was logged for the knowledge team." There is no generated guess.
- **Then (optional):** show a misspelled query, "rx price disclamer", resolving through the learned synonym map, with a note "matched via: disclamer -> disclaimer".
- **Talking point:** the answer is the approved unit itself, cited, scoped and current. When there is none, the system says so.

### 5 Channels [5-min], 1 minute
- **Pain:** P1, P2.
- **On screen:** two panels side by side, the advocate guidance view and the member chat. Both render the pricing disclaimer unit by reference, each with the same unit ID and version.
- **Primary action:** as Legal, "Revise wording", which creates version 2 with an edited sentence, then approve it. Both panels update at once and show version 2, and the Search screen now returns version 2. Version 1 stays in the audit history as "Superseded on [date]".
- **Talking point:** this closes the brief's scenario. When Legal revises, every channel picks up the new unit, and you can prove which version was live on any date.

### 6 Gaps, 1 minute
- **Pain:** P5.
- **On screen:** the Knowledge owner view. Unanswered queries are clustered with counts, for example "prior authorization turnaround: 3 searches, both roles" and "plan MOOP: 2 searches".
- **Primary action:** open a cluster to see the AI-drafted proposed unit, then choose one of three actions: write the unit (it enters review), fix the process, or dismiss.
- **Talking point:** the search log is the authoring backlog. Questions people could not answer become the next units to write, before anyone tunes ranking.

### 7 Drift, 45 seconds
- **Pain:** P1.
- **On screen:** the source document editor for script v1, simplified to an editable text block.
- **Primary action:** change "30-day supply" to "31-day supply" in the source. The pricing disclaimer unit is flagged "Stale: source changed", with a diff and an AI-proposed updated wording that waits for approval. The approved version stays live, marked "source changed, review pending".
- **Talking point:** the system notices when a source moves away from what was approved, and a human decides whether the unit should change.

### 8 Quality, 1 minute
- **Pain:** trust in all of the above.
- **On screen:**
  - **Golden-set table:** each question, its role, the expected unit or ABSTAIN, the result, and pass or fail.
  - **Metric tiles**, each labeled "Illustrative, made-up data":
    - hit@1;
    - verbatim exact match;
    - correct abstentions;
    - over-abstentions;
    - cross-role leaks.
  - **Dedup check:** precision and recall on the 15 disclaimer variants.
- **Talking point:** we measure retrieval before we trust it. Point to which failures remain and what is next.

## 5. Timing

- **Full path:** screens 0 to 8, about 11 minutes. Next moves in that order.
- **Short demo:** screens 0, 1, 3, 4, and 5. That covers a document turned into units, human approval, and a scoped cited answer, plus the Legal revision on every channel. "Jump to short demo" preloads extraction and the duplicate decisions, approves the other reviewed units, and leaves the pricing disclaimer, the verification rule, and the benefits cost disclaimer for Legal. It lands on step 0. Search answers from approved units as soon as any exist. Find copies, Gaps, Drift, and Quality stay on the full path.
- **Slot:** the presentation is 30 minutes and the demo should run about 10, so start with the full path and cut to the short demo if time runs over.

## 6. Data additions needed before building

- **`data/benefits_cost_guide.md`,** in the `benefits` knowledge base. A short made-up guide for Insurance advocates with:
  - a verbatim cost-estimate disclaimer for medical services;
  - one benefits policy.

  Without it, the Insurance advocate can only abstain, and the brief asks that the same question from two roles return answers scoped to each role.
- **Knowledge base assignments:**
  - the pricing disclaimer, verification rule, mail-order rule and specialty rule go in `pharmacy`;
  - the closing goes in `shared-legal`, so both roles can retrieve the same single unit;
  - the website FAQ disclaimer is merged into the canonical pharmacy disclaimer, with `audience` set to both advocate and member.
- **Golden set:** add one Insurance-answerable question (the benefits cost-estimate disclaimer) and one shared-legal question both roles should get (the closing).

## 7. Behavior rules

- **Cached AI by default:** extraction, duplicate judgment, gap drafts and drift fixes replay saved outputs. The "Live AI" switch is hidden behind a settings toggle.
- **"Reset demo"** restores the seeded state and keeps one-at-a-time approval, with a shortcut to approve the remaining reviewed units. "Jump to short demo" preloads extraction and the duplicate decisions, approves the other reviewed units, lands on step 0, and leaves three units for the Legal step.
- **Retrieval reads approved units only,** and filters by the role's knowledge bases inside the query.
- **No screen ever shows generated prose as an answer.** Answers are unit text only (SPEC.md section 6).
- **Every number on screen** carries an "Illustrative" label.

## 8. Acceptance checklist for Friday

- [ ] Opens from one link in a browser, with no install and no terminal.
- [ ] Works with no API key (cached mode).
- [ ] The full path runs in 11 minutes or less, and the short path in 5 or less.
- [ ] Reset returns to the start state every time.
- [ ] Readable on a shared screen at the stated font sizes.
- [ ] Every brief requirement is visible:
  - a document becomes units (screen 1);
  - approval (screen 3);
  - a scoped, cited answer (screen 4);
  - a gap becomes a proposed unit (screen 6);
  - a stale flag (screen 7);
  - two channels share one unit (screen 5);
  - a measured golden set (screen 8).
- [ ] A recorded video of the full path exists as a backup.
