# Knowledge and Search: Prototype Spec

One page, and the build context file for Claude Code or Cursor. Read this before writing code. If the code and this spec disagree, change one of them on purpose.

Case: Humana Use Case 3, Knowledge & Search. Made-up data only. Figures shown in the demo are illustrative and must be labeled that way. Research behind each decision: `humana-knowledge-search/final-report.md`, cited below as "report sN".

## 0. Main user

The brief asks us to pick one. The main user is **Knowledge Ops authors and Legal / Compliance approvers**, because the case is testing structure, governance and single-source reuse. Advocates and the member chat are the consumers that prove the reuse. Knowledge owners use the gap queue.

## 1. What the demo must show

| ID | What the brief requires | Status |
|---|---|---|
| a | A messy document turned into structured, tagged, cited knowledge units, with a duplicate detected | Required |
| b | Authoring plus a governance and approval step | Required |
| c | A consumer searching or asking and getting an answer back with a citation to the unit, scoped to the knowledge bases its role may read. The same question from two roles returns different scoped results. | Required |
| d | An unanswerable question says so and lands in the author's queue as a proposed unit | Optional; build it |
| e | A unit flagged stale when its source document changes | In the brief's "great" list; build it |
| s1 | The same published unit grounding two channels at once (advocate guidance and member chat) | Stretch; build it |
| s2 | A drift alert that proposes the fix | Stretch; build it |
| s3 | A search-analytics view that finds a blind spot and proposes the unit that would close it | Stretch; build only if time remains |
| f | The brief's scenario as a before and after: "Rx pricing disclaimer" today returns three documents with three wordings (labeled as today's state, not the product); on the platform it returns one approved unit with its citation and the channels that use it. When Legal revises the wording, each channel picks up the new version at once. | Required for the story |

Out of scope: search over raw files, drives or mailboxes; real member, provider or claims data; production authentication.

## 2. Users and roles

| Role | Can do | Reads knowledge bases |
|---|---|---|
| Knowledge Ops author | Ingest documents, edit proposed units, write units from gaps | All, read and write |
| Legal / Compliance approver | Approve, reject or retire legal and clinical units; resolve conflicts of authority | All |
| Pharmacy advocate | Search and ask | `pharmacy`, `shared-legal` |
| Insurance advocate | Search and ask | `benefits`, `shared-legal` |
| Member chat (persona) | Ask | Units marked `audience: member`, in `pharmacy` or `benefits` |
| Knowledge owner | View gaps and search analytics | All analytics |

## 3. The knowledge unit (core decision)

A unit is the smallest statement that can be approved on its own, plus the contexts it is approved for (report s4). Every channel renders a unit by reference, so one edit reaches all channels.

| Field | Notes |
|---|---|
| `unit_id` | Stable across versions (FDA SPL set ID pattern, report s2) |
| `version`, `effective_date` | Version is an increasing integer. A published version is never edited: a change creates a new version, and old versions are kept for audit ("which wording was in effect on date X"). |
| `type` | `verbatim`, `policy`, `procedure`, `faq` |
| `text` | For `verbatim`, the exact approved wording |
| `title`, `tags`, `domain` | AI-suggested, human-confirmed |
| `kb_scope` | One or more knowledge bases (`pharmacy`, `benefits`, `shared-legal`). This is the permission boundary. |
| `audience` | `advocate`, `member`, or both |
| `applicability` | Plans, products or call types the approval covers (report s4, Carestream lesson) |
| `source` | Document ID, version, character span, and a hash of the span text (used for drift) |
| `owner`, `approver` | Named roles |
| `status` | `proposed`, `in_review`, `approved`, `superseded`, `retired` |
| `review_by` | Expiry or review date. A unit past this date is flagged (the brief lists "flag drift / expiry" as AI-decides). |
| `requires_legal_gate` | True for `verbatim`, `policy`, and anything clinical or cost-related |
| `channels` | Where the unit is used: `advocate_guidance`, `member_chat`, `voice_bot`, `website` |
| `duplicate_of` / `conflicts_with` | Set by dedup; resolved by a human |

Other objects: `SourceDocument` (versioned text), `ApprovalEvent` (who, when, what, decision), `SearchEvent` (query, role, results, abstained or not), `GapItem` (clustered unanswered queries with an AI-drafted proposed unit), `DriftFlag` (unit, old span hash, new span text, proposed fix), `Feedback` (source `advocate` or `channel`, kind, redacted question and note, optional signals, a route to the Knowledge Ops author or the product backlog, and a resolution note).

## 4. Who decides what (mirrors the brief's table)

- **AI decides:** extract candidate units; classify type; detect duplicates and conflicts; embed; rank; apply role scope; abstain when evidence is insufficient; cluster unanswered questions; flag drift.
- **AI recommends, a human confirms:** tags and domain; merge or split; wording updates and drift fixes; proposed units from gaps; synonyms and acronyms learned from the search log.
- **Human only:** approve or publish legal or clinical content; retire a source of record; resolve a conflict of authority; grant a role access to a knowledge base; approve a unit written to close a gap.

## 5. Flows

1. **Ingest.** The author uploads a script. The AI extracts candidate units, marks lines tagged "Verbatim (Legal)" as `verbatim`, and records the source span.
2. **Deduplicate.** Each candidate is compared with existing units at three levels: exact match after normalization, near-duplicate similarity, and a semantic conflict check. The second script's disclaimer shows up as a near-duplicate of the first, with a word-level diff. A human chooses one of four actions: merge, keep the canonical version, keep both, or escalate a conflict of authority.
3. **Approve.** `requires_legal_gate` units go to the Legal queue. Nothing reaches search until a human approves it.
4. **Search and ask.**
   - Query expansion uses the synonym and acronym map.
   - Results are filtered by the caller's `kb_scope` before ranking. Only `approved` units are searched.
   - Ranking is hybrid: lexical plus embedding.
   - If the top score clears the threshold, the answer returns the unit text word for word with a citation (unit ID, version, source document and span) and lists the channels that use the unit.
   - When the best lexical match is blocked by an open Legal conflict, the result status is `blocked_conflict`, with the note "Under Legal review. Use the currently approved rule until Legal decides." `fallback_unit` is the approved rule it conflicts with, when one is live. The blocked wording is not the answer, and the question is not logged as a gap.
   - Otherwise the answer is "No approved answer", and a `SearchEvent` and `GapItem` are logged.
   - On the guided path, a cache miss calls the model live when an API key is set, with the same 20-call visit cap Explore uses. No key, or a failed call, returns an abstention with `ai_source` `missing`.
5. **Gaps.** Unanswered queries are clustered. The AI drafts a proposed unit for each cluster and sends it to the author queue. The knowledge owner decides one of three actions: write the unit, fix the process that causes the question, or dismiss. A unit written to close a gap still goes through approval.
6. **Drift.** Editing a source document recomputes span hashes. A changed span flags its unit as stale, and the AI proposes the updated wording for approval. Until a human approves the change, the old version stays live, marked "source changed".
7. **Channels.** The advocate guidance view and the member chat view render the same unit by reference. Approving a new version updates both.
8. **Feedback.** An advocate or a channel can flag a question. Content kinds (`couldnt_find`, `confusing_wording`, `wrong_or_outdated`, `no_answer`, `not_helpful`) go to the Knowledge Ops author. Findability and product kinds (`hard_to_find`, `rephrased`, `clarified`, `handed_off`, `slow`) go to a product backlog. The question and the note are redacted before they are stored. Closing an item requires a resolution note. The report and the resolution are both logged.
9. **Call wrap-up.** A Pharmacy or Insurance advocate records how the call ended. When an approved verbatim unit was on the call, they confirm whether they read that wording word for word. The note and the other free-text fields are redacted before they are stored.
10. **Change acknowledgement.** When Legal publishes a new version of wording an advocate can search, that role sees the change and confirms the version. A second confirmation of the same version does not add another activity line.

Prices, copays, and the other plan figures come from a mock plan-data service. The wording shown with a number is an approved unit, attached by reference, and the number is withheld when that disclaimer is not approved and search-visible.

### Engine functions added on Nov 5

These live in `src/engine.py`. An empty string means the action was saved. Any other string is a refusal in plain language. Each successful action writes an activity row with the actor's role. `redact_query` still runs before a typed question is stored or placed in a model prompt. Local ranking keeps the original text.

`bracketed_placeholders(text) -> list[str]`
Square-bracket tokens such as `[clinic hours]`, in order, without duplicates.

`edit_gap_draft(conn, gap_id, text, member_text="", role="Knowledge Ops author") -> str`
The Knowledge Ops author rewrites the advocate text and the member text of a gap draft whose status is `proposed` or `in_review`. Placeholders may stay during the edit. An empty advocate text is refused. A draft already sent, or one whose unit is approved, is refused. An approved unit cannot be edited here. A change publishes a new version. The author's edit list shows a gap only after the owner sends it: status `in_review` and no unit id yet. A `proposed` gap stays on the owner's list.

`edit_returned_unit(conn, unit_id, text, member_text="", role="Knowledge Ops author") -> str`
The same edit for version 1 of a unit whose status is `returned`. Any other status is refused, including `approved`.

`send_gap_to_approval(conn, gap_id, role="Knowledge Ops author") -> str`
Turns the draft into proposed unit `U-GAP-{gap_id}` with `origin` `gap:{gap_id}`. A remaining bracketed placeholder blocks the send. The refusal names the open placeholders. The gap status becomes `in_review` and stores `unit_id`. Sending the unclustered bucket `new-unclustered` is refused until those questions are grouped into a topic.

`send_returned_to_approval(conn, unit_id, role="Knowledge Ops author") -> str`
Sets a `returned` unit back to `proposed`. The same placeholder block applies.

Both sends set `requires_legal` to 1, and place the unit in the Legal queue (`waiting_units`), when the type is policy or verbatim, when the advocate text or member text contains the normalized text of an approved verbatim or legally gated unit (a full sentence or longer, after whitespace and straight-versus-curly quotes are normalized), or when that text mentions a dollar amount or a whole cost word; otherwise a procedure or FAQ goes to Knowledge Ops approvals (`author_queue`), and that plain-language reason is stored on `routing_reason` and written to the activity log. A returned unit that needed Legal before it was sent back always returns to Legal; the rule never lowers a gate.

Approval uses the existing `approve_one` and `approve_by_author`. On approval the unit becomes searchable, the matching gap is marked `closed`, and `search` and `member_answer` return that unit for each of the gap's original questions when the caller's knowledge bases overlap the unit. `member_answer` returns member text and a citation, and does not include a `unit` key. The result's `ai_source` is `closed_gap`. Other questions keep the cached candidate list.

`legal_drift_items(conn) -> list[dict]`
Material drift rows with status `sent`. Each item has `id`, `unit_id`, `version`, `old_wording` (the live approved text), `new_wording` (the proposed text), `source_before`, `source_after`, `summary`, and `member_text`. These items stay out of `waiting_units`.

`approve_drift_fix(conn, role="Legal approver") -> str`
Only a Legal approver. Publishes the proposal as the next approved version, the same way `publish_revision` does: the previous version is superseded, the new version is searchable, channels and knowledge bases are copied, and the old source span is replaced once in the member text and the source quote when it is present. The activity line says every channel now shows that version.

`return_drift_fix(conn, reason, role="Legal approver") -> str`
Only a Legal approver, and the reason must be non-empty. The approved version stays live and stays marked stale.

`resolve_returned_drift(conn, note, role="Knowledge Ops author") -> str`
Only a Knowledge Ops author, and the note must be non-empty. Clears the stale flag on the approved version Legal sent back. The live text stays the current version.

`search(conn, role, query, record=False)` and `record_search(conn, role, query, result)`
When Live AI is on and a recorded abstention matches no existing gap cluster, the existing gap-drafting task writes a proposed unit and stores it as its own cluster. The cluster id is `live-` plus the first 8 hex characters of the sha256 of the redacted question. The label is that redacted question. Placeholders and the invented-figures check are stored on the gap. A saved fixture wins. A missing, capped, or failed draft, including live mode with no API key, keeps the unclustered bucket `new-unclustered` ("New, not yet clustered"). Cached mode always uses that bucket. `search` with `record=False` does not draft. A question that already belongs to a cluster only increments that cluster. A member question that matches a drug price or a visit cost is answered from plan data before this search, with no model call. A member question with no plan vocabulary is out of scope and is not recorded as a search, a gap, or feedback.

`override_channels(override, audience) -> list[str]` in `src/ai.py`
Channels recorded on an audience override, or the audience default from `channels_for`. `confirm_tags` and `with_audience_override` both use it. The pricing unit records `advocate_guidance`, `member_chat`, `voice_bot`, and `website`. The closing unit has no recorded list, so it stays on advocate guidance.

## 6. Key tradeoff (v1)

Answers are extractive only: a returned unit's approved text, never generated prose. This gives up fluency and some coverage in exchange for compliance, auditability and exact verbatim (report s4: CMS standardized content allows no alteration; models adopt wrong retrieved text over 60% of the time; generated citations are often unsupported). Generated summaries of `policy` units, always citing the unit, are a phase 2 option.

## 7. Evaluation (shown in the demo)

- **Golden set:** 10 questions, each with its expected unit or an expected abstention. Include answerable, unanswerable, misspelled and acronym questions, plus cross-role questions that must not leak.
- **Metrics:**
  - hit@1 and hit@3;
  - verbatim exact match (target 100%);
  - correct-abstention rate;
  - over-abstention rate;
  - cross-scope leaks (target 0).
- Insights and the quality screen use this same golden set and the same expected unit on every database. A row with no saved answer is not scored: it is not a pass and not a miss. Among the scored answerable rows, right answers, wrong units, and wrong no-answers sum to the scored total.
- **Dedup check:** 10 to 20 synthetic disclaimer variants, some true duplicates and some meaningfully different, scored for precision and recall. This fills a gap the research could not.
- **Labels:** all numbers are from made-up data and are labeled illustrative.

## 8. Sample data (made-up, under `data/`)

- `rx_education_script.md`: greeting, pricing disclaimer and closing, with "Verbatim (Legal)" lines.
- `rx_education_script_v2.md`: the near-duplicate, whose disclaimer wording differs slightly.
- `search_log.csv`: about 20 queries with Humana-speak, acronyms and misspellings. Several of them cannot be answered by either script.
- `roles.json`: the role-to-knowledge-base map from section 2.
- `golden_set.csv`: question, role, expected unit ID or `ABSTAIN`.

## 9. Build guidance

- Keep it small: one app, a local store (SQLite or JSON), and a single page with tabs for Author, Approve, Search, Gaps, Drift, Channels and Evals.
- Use real LLM calls for extraction, classification, near-duplicate judgment, gap drafting and drift fixes. Cache every LLM output to `fixtures/` and run the live demo from the cache, with a toggle to call the model live.
- Implement the permission filter in the retrieval query itself, never as a post-processing step in the UI.
- Make every screen show the unit ID, version and status, so governance is visible.

## 10. Demo requirements (the presenter is not an engineer)

- **No terminal on demo day.** The app runs at a hosted web address, deployed from GitHub with point-and-click setup (Streamlit Community Cloud is the default). Opening the link is the only step.
- **Cached mode is the default.** Every AI step replays its saved output, so the demo works without an API key, internet hiccups, or model changes. A clearly labeled toggle can switch to live calls.
- **A "Reset demo" button** restores the seeded starting state, so the demo can be rehearsed and rerun.
- **A guided path.** The tabs follow the demo order, and each screen has one obvious next action.
- **`DEMO.md`:** a click-by-click script with what to say at each step. Timing: the slot is 30 minutes of presentation plus 15 minutes of Q&A, so the live demo gets about 10 minutes and must still work if cut to 5. Mark which steps to skip when short on time.
- **Hybrid audience** (two people in the room, one remote): run the demo from one laptop that is both shared into the video call and mirrored to the room screen. Use large text and high contrast so it reads on a shared screen, keep the full flow on one browser tab, and avoid hover-only details.
- **Backup:** a recorded walkthrough video in case the network fails during the call.
- **Access:** the API key, if used, lives in the hosting platform's secrets settings, never in the repository.

## 11. Not building, and why

- Search over raw documents as the product, which the brief scores as weak. (It appears only as the labeled "today" baseline in item f.)
- Generated answers, deferred by the tradeoff in section 6.
- Mirrored source-system permissions. Scope lives on the unit (report s4: sync lag and oversharing risks).
- Multi-step approval routing beyond one Legal gate. That would be phase 2.

## 12. Deliverables outside the prototype

The brief asks for five deliverables. This spec covers the prototype and the tradeoff. The rest are produced separately, and the deck carries all of them.

| Deliverable | Where | Inputs |
|---|---|---|
| Problem Brief | Deck section 1 | Report sections 1, 2 (LG1, LG4) |
| Service Design: current and future authoring journey, current and future finding journey | Deck section 2 (journey diagrams) | Report LG1, LG4; the case scenario |
| Working Prototype | This spec and the hosted app | Sections 1 to 10 |
| Product Roadmap, including when search goes live relative to the knowledge it runs on, and which other AI use cases wait on this platform | Deck section 4 | Report section 4 ("Order of search go-live") |
| Key Tradeoff | Deck section 5 | Section 6 |
| Show your thinking: decisions and paths not taken, assumptions, how past experience shaped it, what to do next | Deck appendix and the follow-up conversation | Section 11, report sections 7 and 8 |
