# Service Design Spec: Knowledge and Search

> **Public copy:** this document refers to internal working files (such as the build plan and audit) that are not included in this public copy of the repository.

The user-centered definition of the concept: who it serves, the jobs they are trying to get done, where today fails them, what the concept promises each of them, and what must be true for it to work. Use it to evaluate what gets built (APP_SPEC.md, APP_PLAN.md) and to decide what to improve.

**Evidence labels.**
- Bracketed IDs such as [4.9] refer to the references in `humana-knowledge-search/final-report.md`.
- Statements marked *(assumption)* come from the case brief or from judgment, not from a source. No primary research with users was done, so every job step and pain point needs validation with real authors, approvers and advocates.
- All figures are illustrative or come from the cited source.

---

## 1. The end users

| User | Role in the system | Priority |
|---|---|---|
| Knowledge Ops author | Turns source documents into units and keeps them current | Main user (with the approver) |
| Legal / Compliance approver | Approves legal and clinical content; decides which wording is authoritative | Main user (with the author) |
| Advocate (Pharmacy, Insurance) | Finds and uses the right answer during a live member call | Core consumer |
| Channel and AI feature teams (voice bot, member chat, website, agent assist) | Build channels that must show approved, current answers | Core consumer |
| Knowledge owner | Reads what people searched for and could not find, and decides what to write | Core user of the gap loop |
| Member (Medicare Advantage enrollee) | Receives the answer through a person or a channel; never uses the platform directly | Ultimate beneficiary |

---

## 2. Jobs, job steps, pains and unmet needs

### 2.1 Knowledge Ops author

**Job to be done.** Get accurate, approved knowledge to every place it is needed, and keep it accurate as the business changes.

**Job steps (today, assumption from the brief).**
1. Receive a change: a new policy, a benefit update, or a Legal revision.
2. Find every document, script and channel copy that holds the affected content.
3. Edit each copy.
4. Route each edited document for review.
5. Publish to each channel separately.
6. Notice when something drifts, usually from a complaint or an escalation.

**Pain points.**
- Copies of the same content live in many documents with slightly different wording, and there is no way to find them all. The brief's scenario: three wordings of one disclaimer. Duplicate content is a top-ranked knowledge base problem [1.8].
- Updates are hard and slow. In the same survey, 37.0% named difficulty updating and 32.7% out-of-date information [1.8]. Approval steps have delayed content "by weeks" at named adopters [1.7].
- Content is written as long documents, not reusable pieces, so every channel needs its own rewrite *(assumption from the brief)*.

**Unmet needs.**
- One place to change a statement, with confidence that every channel picks it up.
- Automated discovery of existing copies and conflicts, with a human deciding which one wins.
- A signal of what advocates need but cannot find, to drive what to write next.

### 2.2 Legal / Compliance approver

**Job to be done.** Make sure the organization says only what Legal has approved, and be able to prove it later.

**Job steps (today, assumption).**
1. Review a document or script containing regulated language.
2. Sign off on the whole document.
3. Answer questions when channels ask which wording to use.
4. Revise wording when rules or policy change.
5. Respond to audits and complaints by reconstructing what was said and when.

**Pain points.**
- Approval sits on whole documents, so later edits by others are not re-signed. The sample script shows an advocate note added after Legal last signed *(sample data)*. Approval tied to a deliverable limited safe reuse in an FDA-regulated firm [2.6].
- A revision does not reach every copy. CMS's 2025 audit report found required notice updates "not implemented consistently across multiple systems and delegated entities" [4.11].
- Proving which version was in use on a date requires manual reconstruction. No rule we read prescribes how, but auditors and regulators can examine a plan's records [4.5].

**Unmet needs.**
- Approval at the level of the statement, with the contexts it is approved for.
- Every channel reflecting a revision at once.
- A version history that answers "what did we say, where, on what date".
- Final say on any conflict of authority (human-only in the brief).

### 2.3 Advocate (Pharmacy and Insurance)

**Job to be done.** Give the member a correct, compliant answer quickly, without putting the member or the plan at risk.

**Job steps (today, assumption from the brief).**
1. Hear the member's question.
2. Search one or more tools.
3. Open the returned documents and scan for the relevant section.
4. Judge which document is current.
5. Read any mandatory verbatim word for word.
6. Answer, or escalate if they cannot find it.

**Pain points.**
- Searches return documents, not answers, and different tools return different documents. Finding information quickly was the top-ranked challenge (58.6%) [1.8].
- Advocates cannot tell which wording Legal approved or which document is current *(brief)*.
- Mandatory verbatim is buried in long documents they follow by hand *(brief)*.
- When nothing is found, the gap is invisible to anyone who could fix it *(brief)*.

**Unmet needs.**
- One answer with a citation they can trust.
- The exact verbatim, marked as such.
- Results limited to what their role may use.
- An explicit "no approved answer" instead of a guess, so they know to escalate.

### 2.4 Channel and AI feature teams

**Job to be done.** Ship a channel (voice bot, member chat, website, agent assist) whose answers are grounded, current and compliant.

**Job steps (today, assumption).**
1. Gather source content for the channel.
2. Adapt or rewrite it for the channel.
3. Get it reviewed.
4. Ground the AI or page on it.
5. Maintain it when the source changes, often without being told.

**Pain points.**
- Each team writes its own version, so channels disagree *(brief)*.
- Retrieval over raw documents produces inconsistent and sometimes non-compliant answers *(brief)*. Models adopt incorrect retrieved content over 60% of the time [3.6], and liability for a chatbot's answer sits with the company [3.1].
- Payers are deploying AI to large advocate populations, for example Humana's Agent Assist for more than 20,000 advocates (company-stated) [5.31a]. Each deployment needs a grounded knowledge source.

**Unmet needs.**
- A governed source to retrieve from: approved units with IDs, versions and scopes.
- Change notifications or automatic updates when a unit is revised.
- A way to show its citation in the channel.

### 2.5 Knowledge owner

**Job to be done.** Know what people need and do not have, and close the most important gaps first.

**Job steps (today, assumption).**
1. Collect anecdotal requests from supervisors and escalations.
2. Guess at priorities.
3. Assign authoring work.
4. Have no reliable way to tell whether the gap closed.

**Pain points.** No tool logs empty searches *(brief)*. KCS treats "no match found" queries as a primary demand signal [1.1], and a named adopter used search strings and abandoned solutions as its backlog [1.5], so the signal exists in principle but is not captured here.

**Unmet needs.**
- Clustered, counted unanswered questions, each with a draft proposed answer.
- The choice between writing content and fixing the process that generates the question.

### 2.6 Member (ultimate beneficiary)

**Job to be done.** Understand what their prescription or service will cost and what the plan covers, and trust the answer.

**Pain points.** Different answers from the website, the bot and an advocate *(brief scenario)*. Wrong information has led to real harm and penalties: Aetna members were told 6,887 out-of-network pharmacies were in network, through the website and call center representatives, and CMS granted a special enrollment period [4.9].

**Unmet need.** The same correct answer in every channel, with the right disclaimers.

**Who members are, and what that means for the design.**
- Most Medicare Advantage members are 65 or older. A real minority are younger people who qualify through a disability: in 2019, about 7 million of 53.6 million Medicare beneficiaries were under 65 because of a long-term disability ([KFF](https://files.kff.org/attachment/issue-brief-Medicares-Role-for-People-Under-Age-65-with-Disabilities), [Health Payer Intelligence](https://healthpayerintelligence.com/news/younger-medicare-beneficiaries-report-more-issues-with-care-access-costs)). These sources are outside the research report.
- Channel preference is mixed, so no channel can be treated as the fallback. Several surveys find the phone is the preferred way for older plan members to reach their plan: 48% of Medicare plan members preferred the phone, against 10% of members 64 and under ([HealthMine via Health Payer Intelligence](https://healthpayerintelligence.com/news/medicare-consumers-prefer-phone-calls-from-health-plans); [Media Logic 2025](https://www.medialogic.com/blog/healthcare-marketing/2025-media-preferences-of-older-adults/)). Others find email at the top ([Welltok and Ipsos](https://www.ipsos.com/sites/default/files/ct/news/documents/2019-01/welltok-2018-senior-survey-pr-01-16-2019.pdf); [Phreesia](https://www.phreesia.com/wp-content/uploads/2023/10/PAYER-Short-report-MemberInsights-2.pdf)). Most are vendor surveys; treat them as directional.
- Many members are helped by someone else: a daughter, a spouse, a caregiver. They call on the member's behalf and need an authorization on file *(assumption, consistent with the caregiver rule in the source scripts)*.
- Part D call centers must give callers cost-sharing and formulary information that is "complete, accurate, timely, clinically appropriate, patient-specific" [4.16]. The phone is a regulated channel, and for many members it is the main one.

Design consequences, carried into `EXPERIENCE_SPEC.md` section 5 and section 10:
1. **The phone line and the advocate are first-class member channels.** Most members who call reach an advocate or the automated line. The same approved wording must work when it is heard, not only when it is read.
2. **Wording that works aloud.** Numbers first, short sentences, one idea per sentence, and an offer to repeat. Long verbatim blocks need a spoken variant that Legal approves as part of the same unit *(roadmap)*.
3. **Caregivers are users.** The authorized-caller rule appears in every channel, and adding an authorized caller is a task on the website.
4. **No channel is forced.** Every answer offers the phone number and a person. Nothing requires an app.
5. **Readable and operable for older eyes and hands.** Text of at least 16 px with a larger option (built: "Text size" on the member site), high contrast, large targets, plain language at about a sixth to eighth grade reading level *(assumption, common plain-language practice)*, and TTY and interpreter access on the phone line *(roadmap)*.

---

## 3. Concept statements

**Concept name (working): Single Source.**

**Overall.** Single Source does four things:
- turns unstructured documents into governed knowledge units with AI, with humans approving;
- serves the same approved unit to every channel and search by reference;
- scopes and cites every answer, and says so when no approved answer exists;
- flags drift and gaps for humans to act on.

This is all to help authors, approvers and advocates know that what they say is correct, current and approved, and to change it once when it needs to change. To ultimately give every member the same correct, compliant answer, wherever they ask.

**Knowledge Ops author.** Single Source:
- extracts candidate units from source documents;
- finds duplicates and conflicts;
- links each unit to its source span;
- flags units when their source changes.

This is all to help the author change content once and stop hunting for copies, and see what to write next. To ultimately keep accurate, approved knowledge in every place it is needed.

**Legal / Compliance approver.** Single Source:
- gates every legal and clinical unit behind an explicit approval;
- records the version, effective date and approver of every unit;
- propagates a revision to every channel at once.

This is all to help the approver approve statements instead of whole documents, resolve conflicts of authority, and answer "what did we say on this date" from the record. To ultimately ensure the organization says only what Legal approved, and can prove it.

**Advocate.** Single Source:
- returns one cited answer instead of a list of documents;
- shows mandatory verbatim marked "read exactly";
- limits results to the advocate's knowledge bases;
- says when no approved answer exists.

This is all to help the advocate answer faster, read the right wording, and know when to escalate. To ultimately give the member a correct, compliant answer on the call.

**Channel and AI feature teams.** Single Source:
- provides an API of approved, versioned, scoped units with citations;
- pushes new versions when Legal revises.

This is all to help those teams ground their channel without writing or maintaining their own content. To ultimately ship channels that agree with each other and stay compliant.

**Knowledge owner.** Single Source:
- logs every unanswered question;
- clusters the questions by topic;
- drafts the unit that would close each cluster.

This is all to help the owner see real demand and choose between writing content and fixing a process. To ultimately close the gaps that matter most first.

---

## 4. Core features and differentiation

| Feature | Value | How it differs from today and from alternatives |
|---|---|---|
| AI extraction into typed units with source spans | Turns documents into reusable, traceable statements | Enterprise search tools index documents and inherit their governance [5.15][5.18]. Contact center KM tools manage articles; statement-level units with source spans are not documented in the vendor sources read |
| Duplicate and conflict detection with human resolution | Finds every copy of the "same" disclaimer | Shelf documents similar checks [5.28]. Here detection feeds a unit-level approval and propagation model |
| Unit-level Legal gate with version and effective date | Approval at the right granularity; provable history | Follows FDA SPL's set ID, version and effective date pattern [2.12]; vendors claim "versioned, approved" (company-stated) without documenting how [5.23] |
| Render by reference to every channel | One change reaches all channels | The DITA reuse model [2.3] applied to contact center channels and AI features |
| Scoped, cited, extractive answers with abstention | Advocates get approved wording only, within their scope | Generic RAG generates text and cites inconsistently [3.8][3.9]; permission-aware search tools govern access, not approval [5.15] |
| Gap queue from unanswered searches | Demand-driven authoring backlog | The KCS practice [1.1] built into the product rather than run as a manual analysis |
| Drift flags from source changes | Catches silent divergence | The closest documented analog is dataset staleness in Palantir lineage [5.6], applied here to prose units |

**The differentiator in one sentence.** Alternatives make documents searchable. Single Source makes approved statements the thing every channel and search consumes.

---

## 5. Value proposition

| User | Specific benefit | What it saves, enables, or makes easier |
|---|---|---|
| Knowledge Ops author | Change a statement once; see every copy and conflict found for them | Saves the hunt for copies and per-channel rewrites. Enables authoring from demand. Makes updates a single edit plus approval |
| Legal / Compliance approver | Approves statements, not documents; sees exactly what will go live and where | Saves re-reviewing unchanged content. HORIBA reported eliminating "redundant review of already reviewed content" after moving to structured content (company-stated) [2.4]. Enables a provable version history. Makes revisions reach every channel |
| Advocate | One cited answer with exact verbatim, limited to their role | Saves opening and scanning long documents and guessing which is current. Enables confident escalation when no answer exists. Illustrative: an AI assistant linking to documentation raised productivity 14% overall and 34% for novices in one study [1.9], a related but different intervention |
| Channel and AI feature teams | A governed, versioned source to ground on | Saves building and maintaining a separate content set. Enables consistent answers across channels. Makes compliance review a property of the source |
| Knowledge owner | A ranked list of real unanswered questions with drafted answers | Saves anecdote-driven prioritization. Enables closing the most-asked gaps first |
| Member | The same correct answer in every channel | Avoids being misled on costs or coverage, as in the Aetna case [4.9] |
| The plan (business) | Lower compliance exposure, plus a dependency every AI use case can build on | Reduces the risk of CMS penalties for inaccurate information [4.9][4.10]. Enables faster, safer AI channel launches *(assumption: no source measures this)* |

---

## 6. Paradigm shift: why now

| Shift | What is changing | Why it makes the old way untenable or creates the opportunity |
|---|---|---|
| Technology | Generative AI can extract structure from documents, detect near-duplicates and retrieve answers well enough to assist humans *(brief)*. Hybrid retrieval and reranking cut missed retrievals sharply in vendor tests [3.12] | The cost of turning documents into units has dropped. But retrieval over raw documents amplifies inconsistency: models follow wrong context [3.6] and rarely abstain [3.10] |
| Behavior and operations | Payers are moving advocates and members onto AI channels at scale. Examples: Humana's Agent Assist for more than 20,000 advocates handling up to 80 million calls a year; UnitedHealthcare's Avery for Medicare Advantage members (company-stated) [5.31a][5.32] | Each new channel multiplies the copies of every answer unless the channels share one source |
| Regulation and liability | Organizations are held responsible for what their chatbots say [3.1]. CMS penalizes inaccurate member information, including information from call center representatives [4.9]. The CY2027 rule changes marketing rules from October 2026 [4.7]. No CMS guidance on AI in member communications was found [4.13a][4.7] | Inconsistency is already a compliance risk with humans, and AI channels increase the volume of statements made. Rules for AI communications may come later, so governed provenance is a hedge |
| Economics | UnitedHealth Group plans $1.6 billion of AI investment and runs more than 1,000 AI solutions (company-stated) [5.32]. Gartner published its first Magic Quadrant for customer service knowledge management in 2026 [5.30] | Knowledge infrastructure is becoming a recognized category and a shared dependency, so building the layer once is cheaper than every AI team curating its own |

---

## 7. Hypotheses and leap of faith assumptions

**H1, extraction feasibility.** AI can extract units from contact center scripts and policies, classify their type, and mark verbatim accurately enough that human review is faster than writing units by hand.
- **Leap of faith:** reviewers can spot extraction errors reliably, and errors in verbatim boundaries are rare enough not to erode trust. *(No source measures extraction accuracy on legal wording.)*

**H2, duplicate detection.** Near-duplicate and conflict detection finds the large majority of copies of a disclaimer with few false alarms.
- **Leap of faith:** slightly different wordings of the same disclaimer are similar enough to detect, without flagging meaningfully different statements. Shelf's near-duplicate rule triggers only at 99% similarity [5.28]. The prototype's 15-variant test is the first evidence.

**H3, approval at unit level.** Legal will approve individual units with an applicability scope instead of whole documents.
- **Leap of faith:** Legal trusts unit-level approval despite reuse risk. Carestream's experience is that approval holds only "in context of the entire deliverable" [2.6], so applicability scope must be enough to satisfy Legal.

**H4, approval capacity.** Approvers can keep pace with the volume of units without becoming the bottleneck.
- **Leap of faith:** volume is manageable once duplicates collapse, and lower-risk unit types can use lighter review. A QA gate at Progress released only 25 of every 100 solutions [1.5].

**H5, advocate adoption.** Advocates prefer a single cited unit, and accept "no approved answer" over a generated guess.
- **Leap of faith:** abstention does not frustrate advocates into working around the tool. Over-abstention is a documented risk [3.11].

**H6, gaps as backlog.** Unanswered searches are a useful signal of missing content.
- **Leap of faith:** enough advocates search, rather than ask a colleague, for the log to be representative. Clustering separates true gaps from findability problems, which KCS treats as different issues [1.1].

**H7, channel adoption.** Channel and AI teams will consume units by reference instead of maintaining their own content.
- **Leap of faith:** the unit API meets their latency, format and tone needs, and leadership requires it.

**H8, drift detection.** Source-change flags catch meaningful drift without overwhelming owners with trivial flags.
- **Leap of faith:** source documents keep stable enough structure for span tracking to work across edits.

**H9, business value.** Fewer inconsistent answers and faster updates reduce compliance exposure and handle time enough to justify the platform.
- **Leap of faith:** the improvement can be measured. No source links knowledge governance directly to compliance outcomes, beyond enforcement cases like Aetna [4.9].

---

## 8. What could go wrong

Mitigation types:
- **Design** means it can be built into the concept itself.
- **Operational** means it needs process, staffing or organizational action.

**R1. A wrong approved unit spreads everywhere at once.**
- **The risk:** single-sourcing means an error approved once appears in every channel and search simultaneously.
- **Who is affected:** members, advocates, the plan.
- **If it materializes:** members across voice, chat, web and calls receive the same wrong cost or coverage statement. This could lead to complaints, a CMS finding, or a special enrollment period, as in the Aetna case [4.9].
- **Mitigation:**
  - *Design:* a preview of every channel and search where the unit appears before approval; rollback to the prior version; channel lists on every unit.
  - *Operational:* a second approver for high-impact units; monitoring of complaints by unit ID.

**R2. Over-abstention makes the tool useless.**
- **The risk:** a strict threshold or thin coverage leaves too many questions with "no approved answer".
- **Who is affected:** advocates, members, the knowledge team.
- **If it materializes:** advocates stop using search and revert to old documents or colleagues. The platform loses its single-source role, and handle time rises.
- **Mitigation:**
  - *Design:* measure over-abstention in the golden set; show the nearest approved units with a clear label; route every abstention to the gap queue.
  - *Operational:* launch per knowledge base only when coverage of top questions is adequate, and staff gap closure.

**R3. The approval gate becomes a bottleneck.**
- **The risk:** Legal cannot keep up with unit volume.
- **Who is affected:** authors, channel teams, advocates.
- **If it materializes:** a backlog of unapproved units means search cannot answer, so teams revert to ungoverned content. A review gate throttled publishing at Progress [1.5].
- **Mitigation:**
  - *Design:* collapse duplicates before review; route only legal and clinical types to Legal; show a reviewed diff instead of the whole document.
  - *Operational:* service levels for approvals; Legal staffing tied to change volume; tiered review, as pharma MLR teams use [2.10].

**R4. Permission misconfiguration leaks restricted content.**
- **The risk:** a unit is scoped to the wrong knowledge base, or a role is granted too broadly.
- **Who is affected:** advocates, members, the plan.
- **If it materializes:** an Insurance advocate quotes pharmacy-only guidance, or member chat shows advocate-only content. Cross-group retrieval leakage is a documented risk [3.18].
- **Mitigation:**
  - *Design:* scope enforced in the retrieval query; deny by default when scope is unknown [5.21]; leak tests in the golden set; retrieval logs.
  - *Operational:* human-only role grants (per the brief); periodic access reviews.

**R5. Extraction or editing changes verbatim wording.**
- **The risk:** the AI paraphrases or truncates a verbatim block, or splits it at the wrong boundary.
- **Who is affected:** members, Legal, the plan.
- **If it materializes:** non-compliant wording is approved because the reviewer missed a small change. Models adopt subtly wrong text more readily than obviously wrong text [3.6].
- **Mitigation:**
  - *Design:* verbatim units are copied from the source span and compared character by character, never generated; any difference from the source is highlighted; verbatim cannot be edited outside a new version.
  - *Operational:* Legal approves verbatim against the source side by side.

**R6. Drift or expiry alerts are ignored.**
- **The risk:** too many trivial flags, so owners tune them out.
- **Who is affected:** authors, owners, members.
- **If it materializes:** a meaningful source change goes unreviewed and the stale unit keeps serving every channel.
- **Mitigation:**
  - *Design:* rank flags by unit type and channel reach; collapse whitespace-only changes; escalate stale legal units.
  - *Operational:* named owners per knowledge base with review service levels.

**R7. Conflicts of authority stall or get resolved by default.**
- **The risk:** two approved sources disagree (for example, the mail-order rule) and nobody decides, or the system silently picks one.
- **Who is affected:** advocates, members, Legal.
- **If it materializes:** advocates give contradictory answers, or the wrong rule wins without anyone deciding.
- **Mitigation:**
  - *Design:* conflicts block publication of both units until resolved; resolution is human-only and recorded.
  - *Operational:* a defined decision owner per domain, as with Progress's Knowledge Domain Manager acting as "arbiter when solutions collide" [1.5].

**R8. Over-trust in the citation.**
- **The risk:** advocates assume any cited answer is right for this member's situation.
- **Who is affected:** members, advocates.
- **If it materializes:** a correct unit is applied to the wrong plan or product. Applicability varies, as Carestream found [2.6].
- **Mitigation:**
  - *Design:* show applicability scope on the answer; plan-variant selection (Oscar does this, company-stated [5.35]).
  - *Operational:* advocate training on applicability.

**R9. Search logs capture member information.**
- **The risk:** advocates type member names or IDs into search, and the gap log stores them.
- **Who is affected:** members, the plan.
- **If it materializes:** protected health information sits in analytics data and reaches authors who should not see it.
- **Mitigation:**
  - *Design:* redact identifiers before logging; keep the analytics view at cluster level.
  - *Operational:* privacy review of logging; retention limits.

**R10. Metrics get gamed or mistaken for quality.**
- **The risk:** teams optimize unit counts or answer rates instead of correctness.
- **Who is affected:** the knowledge team, leadership.
- **If it materializes:** the knowledge base fills with low-value units, or the threshold is loosened to raise the answer rate. KCS warns "DO NOT PUT GOALS ON ACTIVITIES!" [1.2], and a quality index was gamed as a target [1.4].
- **Mitigation:**
  - *Design:* report correctness (golden set), abstention accuracy and leaks alongside volume.
  - *Operational:* set goals on outcomes, not activity counts.

**R11. Authors and channel teams lose ownership or roles change.**
- **The risk:** centralizing content removes work channel teams did and shifts authority to a central team.
- **Who is affected:** channel content writers, authors.
- **If it materializes:** resistance, workarounds, or loss of channel-specific expertise.
- **Mitigation:**
  - *Design:* channel teams keep channel presentation, while the approved text is shared.
  - *Operational:* involve channel teams in governance; a clear RACI; change management.

**R12. Migration stalls on legacy content.**
- **The risk:** trying to convert every legacy document before launch.
- **Who is affected:** the program, leadership.
- **If it materializes:** months of conversion with no value delivered. KCS has "never seen a mass migration of legacy content work" [1.1].
- **Mitigation:**
  - *Design:* start with the highest-risk verbatim and the top searched questions; keep legacy read-only outside the answer path.
  - *Operational:* phase the roadmap by knowledge base and demand.

**R13. Regulatory expectations change.**
- **The risk:** CMS or HHS issues rules on AI in member communications that the design does not meet.
- **Who is affected:** the plan.
- **If it materializes:** rework, or channels paused pending compliance.
- **Mitigation:**
  - *Design:* full provenance (unit, version, approver, effective date, channel) for every answer, which is the record most rules would require.
  - *Operational:* regulatory monitoring by Compliance.

---

## 9. Using this spec to evaluate the build

Score each screen in APP_PLAN.md against three questions:
1. Does it serve a job step in section 2?
2. Does it remove a named pain?
3. Does it deliver a value in section 5?

Check that the demo makes hypotheses H1, H2, H5 and H6 visible with evidence (extraction, dedup precision and recall, abstention behavior, gap clusters). Check that the risks with design mitigations R1, R4, R5 and R7 show their mitigations on screen.

---

## 10. Touchpoints and time to value

Most users never open "the knowledge system". Only Knowledge Ops authors and Legal approvers work inside it. Everyone else meets its output inside a tool they already use. Each user's experience is designed for the touchpoint they actually have.

**Time to value** is the time from the moment a user needs something to the moment the product relieves their most important pain (section 2) and delivers their value proposition (section 5). Every target below is an *(assumption)* to validate with real users. No source we read measures these for this setting.

| User | Touchpoint (where and when) | First value moment | Time to value target *(assumption)* |
|---|---|---|---|
| Knowledge Ops author | A dedicated desktop web workspace, all day, as their main job | Opening the workspace shows what needs them now: new extractions, copies to settle, drift flags, assigned gaps | Under 1 minute from sign-in to working the first item. Under 5 minutes from uploading a document to reviewing its proposed units |
| Legal / Compliance approver | An email or Teams notification that deep-links to a single review page. A few times a week, between other work | One page shows the wording, its source, the verbatim check, where it will appear, and what it replaces | Under 2 minutes from opening the notification to a recorded decision on one unit |
| Advocate (Pharmacy, Insurance) | A knowledge panel inside the existing agent desktop, during a live call. Humana's Agent Assist is the kind of tool this sits in (company-stated) [5.31a] | The approved line to read, marked "read exactly", with its citation, or a clear "no approved answer" with how to escalate | Under 10 seconds and at most one action from the member's question to reading the wording |
| Member | The plan's website, mobile app chat, and phone line. Never the platform itself | A plain-language answer with the right disclaimer, the same in every channel | One turn: the first reply answers the question, or hands off to a person with context |
| Knowledge owner | A weekly insights view in the workspace, or a weekly digest | The top unanswered questions, ranked by demand, each with a drafted unit and a one-step decision | Under 5 minutes from opening the digest to assigning the top gaps |
| Channel and AI feature teams | A developer portal: API reference, change events, changelog | A first successful API call that returns an approved unit with its version and citation | Under 15 minutes from opening the portal to the first successful call |

The detailed experience for each touchpoint, with what the first screen must show and how to test it, is in `EXPERIENCE_SPEC.md`.


---

## 11. Moments of truth: where the value proposition becomes real

A moment of truth is the point where a person forms or changes their judgment of the service, because the value proposition (section 5) either shows up for them or does not. Each user has three:

- **Zero moment:** when the need arises and they go looking. The promise is tested on whether they reach the answer at all.
- **First moment:** when they get the answer. The promise is tested on whether it is right, clear and trusted.
- **Second moment:** later, when the answer meets reality: at the pharmacy counter, in an audit, on the next call. The promise is tested on whether it held.

Today's failure mode lives in the second moment: an answer that sounded right turns out wrong later, as in the Aetna case [4.9]. Single Source is designed so the second moment confirms the first.

| User | Value proposition (section 5) | Zero moment | First moment | Second moment | Where the prototype shows it |
|---|---|---|---|---|---|
| Member | The same correct answer in every channel | Wondering what a refill will cost, then calling, opening chat, or asking a family member to call | Hearing or reading a specific price for their drug, with the disclaimer that explains what could change it | At the pharmacy counter the price matches, or the disclaimer already told them why it differs; a call to the plan later gives the same answer | Member website estimator and chat quote; phone line exchange; guided step 5 |
| Advocate | One cited answer with exact verbatim, limited to their role | The member asks "what will this cost?" mid-call | Within seconds the approved line appears, marked read word for word, with the member's price on the Prescriptions tab | A QA review or a callback finds the call compliant and consistent; the advocate stops keeping a private copy of the script | Agent desktop suggested answer, Prescriptions tab, wrap-up confirmation |
| Knowledge Ops author | Change a statement once; every copy and conflict found for them | A source document changes, or a gap is assigned | Opening Studio shows the extracted units, the copies and the routing reason for each draft | Weeks later no stale copy surfaces in another channel, because none exists | Guided steps 1, 2 and 7; Studio My work and Library |
| Legal approver | Approve statements, not documents; see exactly what goes live and where | An email says items are waiting, and why each came to Legal | One review page shows the wording, its source, the verbatim check and who will see it | An audit or a CMS inquiry asks what was said on a date, and the version history answers it in minutes | Legal inbox and review page; "If you approve this unit"; version history |
| Knowledge owner | A ranked list of real unanswered questions with drafted answers | The weekly digest arrives | The top gap is named with its demand and a draft, and the decision takes one step | The gap appears under "Closed this week", and the people who asked are told | Insights; closed-gap notice on the agent desktop |
| Channel and AI team | A governed, versioned source to ground on | A new channel needs approved answers | The first API call returns an approved unit with its citation | Legal publishes a revision and the channel updates through a change event with no code change | Developer docs, Try it, Change events |
| The plan | Lower compliance exposure and a shared dependency for AI channels | Planning a new AI channel or preparing for an audit | The channel launches on approved content without its own content set | Monitoring finds accurate answers; CMS secret-shops the accuracy of plan information on prospective-member lines [4.12][4.14] | Guided step 8 quality gates; closing screen |

**What this asks of the build.**
- Every first moment shows the specific answer and its citation together, never the disclaimer alone. The audit found the opposite on the member pages (AUDIT.md A1 to A4), which is why plan data was added.
- Every second moment needs evidence: version history, the wrap-up's word-for-word record, change events and closed gaps.
- The time-to-value targets in section 10 are the first moment, measured.
