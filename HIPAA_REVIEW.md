# HIPAA and privacy review

> **Public copy:** this document refers to internal working files (such as the requirements check) that are not included in this public copy of the repository.

Reviewed on Nov 4, 2026, against the Streamlit prototype on main (merge of PR 28) and the plans for the web rebuild (`web/`, `api/`). Not legal advice. A privacy officer and counsel would own the real assessment.

## Short answer

- **The prototype holds no PHI.** All data is made up, as the case requires. Harbor Health is fictional. No real member, provider or claims data exists anywhere in the repo.
- **The knowledge itself is not PHI.** Scripts, policies, disclaimers and FAQs describe the plan, not a person. That is a useful point for the presentation: the governed knowledge layer can be built and approved without touching member data.
- **PHI enters at the edges.** It comes in through what people type: advocate searches during a live call, member chat messages, feedback notes, and the logs built from them. The design already treats those as sensitive (redaction before storage). The review found gaps in how complete that redaction is, and one live-mode path that sends unredacted text to the model provider.
- **For Friday**, nothing here blocks the demo. Three small changes are worth making (section 4). The rest belongs on the roadmap and in the Q&A answers (section 5).

## 1. Where PHI could enter in production

| Entry point | What a person might type | Where it goes today in the prototype |
|---|---|---|
| Advocate search in the agent desktop | "member H12345678 says her insulin copay went up" | Search uses the raw text. The activity log, gap queue and search count store a redacted copy. Live mode sends the raw text to the model. |
| Member chat, website, app, phone line | "I'm Mary Johnson, born 3/4/1950, what does my metformin cost?" | Same as above, through `member_answer` and `record_search`. The chat history in the browser session keeps the raw text. |
| Advocate "Flag this answer" note | "caller at 555-123-4567 was confused" | `record_feedback` redacts the question and the note before storing. |
| Feedback resolution note | Free text from an author | Redacted before storing. |
| Gap queue and insights | Example questions shown to Knowledge owners | Shown from the redacted copies. |
| Developer portal, change events | Unit content only | No member data. |
| Agent desktop caller profile | Name, member ID, plan, verification status | Fictional, hardcoded per scenario. In production this comes from the CRM, outside this platform. |

## 2. What the design already gets right

- **Redaction before storage.** `redact_query` runs before every write of a question or note: activity log, gap clustering, search counts, feedback, resolution notes (SPEC section 5, flow 8).
- **Minimum necessary.** Knowledge owners and the product backlog see clustered, redacted examples, never call records.
- **Member answers are general.** The member chat answers with approved plan-level wording. It never looks up a person's claims, eligibility or drug history, so it needs no member data to answer.
- **Role scoping.** Each role reads only its knowledge bases, enforced in the retrieval step, which is the same control pattern HIPAA access controls need.
- **Audit trail.** Every approval, send back, conflict decision, gap decision and drift action is logged with the actor's role and reason.
- **No training on user input.** Nothing typed by an advocate or member is used to train a model. Fixtures are written only by the offline script from the made-up corpus.

## 3. Findings

| # | Finding | Severity for production | Evidence |
|---|---|---|---|
| H1 | **Live mode sends the raw question to the model provider.** `search` and `member_answer` pass the original text to `assess_sufficiency`, which goes to the Anthropic API when Live AI is on. Redaction only happens before storage. | High | `src/corpus.py` `decide()` calls `sufficiency_user(question, ...)` with the unredacted question; `src/engine.py` redacts only `logged_query`. |
| H2 | **Redaction misses common identifiers.** Tested on Nov 4: it catches phone numbers, dates of birth, SSNs, labeled member IDs and nine-digit numbers. It misses Medicare Beneficiary Identifiers (`1EG4-TE5-MK73`), names, street addresses, ZIP codes, email addresses and long claim numbers. | High | `redact_query` patterns in `src/engine.py` lines 1489 to 1513. |
| H3 | **Health details pass through unredacted.** "She has diabetes and takes insulin" is stored as typed. On its own that is not PHI, but combined with any identifier that slipped through H2 it is. | Medium | Same function. The fix is a policy decision (section 5), not only a regex. |
| H4 | **The member chat does not warn people off sharing personal details.** The public website chat is unauthenticated and should say so. | Medium for production, low for the demo | `src/surfaces.py` member app and website pages. |
| H5 | **Raw chat history lives in the browser session.** Members see their own messages, which is expected, but nothing clears it on a shared computer. | Low | `st.session_state` chat history in `src/surfaces.py`. |
| H6 | **The demo host is a public cloud with no BAA.** Fine for made-up data. If someone types real details during Q&A with Live AI on, they reach Streamlit Community Cloud (or Render) and the model API. | Low for Friday | `DEPLOY.md`. |
| H7 | **No retention rule** for the activity log, gap queries or feedback. Each session database is temporary in the prototype; production needs a stated retention period. | Medium for production | `src/engine.py` schema. |

## 4. Changes worth making before Friday

These are small, and they make the privacy story demonstrable rather than only described.

1. **Redact before the model call, too** (H1). Pass `redact_query(question)` into the sufficiency prompt. Search ranking can keep using the raw text locally. Saved answers are keyed by input, so the redacted text must match the fixture inputs; the demo questions contain no identifiers, so they do not change.
2. **Widen the redaction patterns** (H2): MBI format, email addresses, ZIP codes, street address shapes, and claim or reference numbers of 10 or more digits. Add tests with each example from finding H2.
3. **Add one line under the member chat input** (H4): "Please don't include personal details like your member ID or date of birth. For questions about your own claims, sign in." In the web build, that line goes in the ChatPanel footer.

Owner: items 1 and 2 are engine changes (Cursor). Item 3 is UI (Claude for Streamlit, the web agent for `web/`). A ready prompt is in `REQUIREMENTS_CHECK.md`, section 6.

## 5. What production would need (roadmap and Q&A material)

- **Business associate agreements** with every vendor that touches typed input: the model provider (Anthropic offers a BAA and zero data retention for eligible customers; the same models are available through cloud providers under the insurer's existing BAA), hosting, logging and analytics.
- **Redaction as a service with two layers:** pattern rules plus a named-entity model for names and addresses, measured on a labeled test set like the golden set. Report its recall as a launch metric next to the retrieval metrics.
- **A decision on health details in queries.** Options: keep them (they help gap clustering), strip them, or keep them only in a restricted store. Recommend: keep the condition or drug name (it is what makes the gap actionable), strip every identifier, and restrict raw call-time text to the contact-center system of record.
- **Separate authenticated and unauthenticated member experiences.** The public chat answers general questions only. Anything personal hands off to signed-in channels or an advocate.
- **Access control and audit** on the feedback and gap stores, with role-based access and access logging (HIPAA Security Rule access control and audit controls).
- **Retention:** a stated period for search logs and feedback, aligned with the plan's records policy. Approved units and their versions are business records and are kept (the report notes a 6-year retention period for call recordings under the CY2027 rule, [4.7]).
- **De-identification before analytics or evaluation.** If real search logs are used to build the golden set or tune synonyms, de-identify them first (Safe Harbor's 18 identifiers, or expert determination).
- **Incident path:** if PHI is found in a stored query, a way to purge it and a breach assessment process.

## 6. How to say it in the presentation

"The knowledge layer contains no member data, so authors and Legal can build it without PHI access. PHI only enters through what people type: searches during calls, chat messages and feedback. We redact before anything is stored, the member chat answers general questions only, and in production every vendor that sees typed text sits under a BAA. The prototype's redaction is a first pass. Its coverage is a launch metric I would measure the same way we measure retrieval."
