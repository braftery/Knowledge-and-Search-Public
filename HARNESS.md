# The AI harness, and what I would change

How the model is used in this prototype: the six prompts, what goes into each one, what the code checks around them, and the specific changes I would make to the model's behavior, each backed by an evaluation result. Written on 9 November 2026, after the presentation. Illustrative data throughout.

## Design principle

The model proposes; code and people decide. Anything that can be guaranteed in code is enforced in code, and the model is used only for judgments code cannot make: reading a document, comparing two wordings, deciding whether an approved unit answers a question.

## The six prompts

All six use structured outputs (a JSON schema per task), adaptive thinking at medium effort, and server-side fallbacks on a refusal. The prompts are in `src/ai.py`.

| Prompt | Input | It decides | What the code checks afterwards |
|---|---|---|---|
| `extract_units` | One source document | How the document splits into units; type, audience, source span | The source span must be an exact substring of the document; a verbatim unit's text must equal its span (`check_unit`). Failures are flagged, never rewritten. |
| `judge_pair` | Two wordings | Exact, near-duplicate, conflict, or distinct; the phrases that differ | Only pairs that share content are sent. A conflict blocks both units until Legal decides. |
| `assess_sufficiency` | A redacted question and the approved units this role may read | Which unit fully answers, or none | Any unit ID outside the candidates is rejected. Role scope is applied before the model sees anything. |
| `draft_gap_unit` | Unanswered questions and nearby approved units | A draft with a bracketed placeholder for every unsourced fact | Any figure not in the questions or an approved unit is flagged (`invented_figures`). The draft cannot be sent until every placeholder is grounded in a source. |
| `propose_drift_fix` | The old and new source passage | Material or cosmetic; the proposed new wording | The approved version stays live; the fix goes to whoever approved the unit. |
| `label_clusters` | Groups of unanswered questions | A short label per group | Questions are redacted before they are sent. |

## What the model never decides

- **Who may see what.** Retrieval is filtered by role and knowledge base before any candidate reaches the model, so an answer from another role's content is impossible by construction (zero leaks in every run).
- **Who approves.** Routing is a rule in code, with a plain-language reason. It can raise a unit to Legal and never lowers a Legal gate.
- **Numbers.** Prices and costs come from the plan's systems of record, shown only after the approved disclaimer and withheld when the caller is not verified.
- **Whether wording is exact.** Verbatim text is compared character for character in code.
- **What is current.** Units past their review date, or in an open conflict, are withheld before search.

## Context engineering

- **In context:** only approved units the role may read, by title and text, and the question with member identifiers removed (`redact_query`).
- **Kept out:** member records, plan figures, and anything not approved. Figures join the answer after the model has chosen the unit.
- **Replay and limits:** saved model outputs are replayed by default, so the prototype and its tests are repeatable and cost nothing to run. Live calls are capped per session and time out after six seconds.
- **Why retrieval over approved units instead of fine-tuning:** approved wording must be reproduced exactly and revised the same day Legal changes it. Retrieval over approved units does both; a fine-tuned model can do neither reliably. Context length is not the constraint here; the candidate set is small.

## Cost and latency

Measured from the evaluation runs on the current Opus model: about $0.01 per search decision, $0.007 per duplicate judgment, and $0.09 per document extraction. Search is the only call on the live path of a conversation; extraction, duplicate checks, drift and gap drafts run when content changes, off the call path. At contact-center volume the search cost and latency are what matter, which is one reason to test a smaller model on the search task against the same keys (see below).

## What I would change, and why

Each change is tied to a result in `docs/eval-report.md` and would be re-measured against the same keys before it ships.

**1. The search prompt describes the wrong input.** The prompt says the model sees "up to three approved units". In Explore, retrieval sends up to 20 (`EXPLORE_CANDIDATE_LIMIT` in `src/finish.py`), and retries with the top three only when that call finds no answer. The prompt should describe what it actually receives, and the candidate count should be chosen by measurement: run the search set at 3, 5, 10 and 20 candidates and pick the smallest number that holds the right-answer rate.

**2. Acronyms and misspellings cause false no-answers, and the fix is in retrieval.** Acronym questions were right on 6 of 9 and misspellings on 7 of 9 ("PCP referral", "OON visit", "voicemial"). In one case the right unit never reached the shortlist at all. A looser prompt would not help that. The fix is a synonym and acronym layer in retrieval, built from the search log of unanswered questions, like the brand-name expansion that already exists for drug names. The sufficiency prompt stays strict.

**3. Partial answers need a product decision before a prompt change.** Asked a two-part question where only one part has an approved answer, the model declined 6 of 7 times, exactly as instructed ("the unit that fully answers"). Loosening "fully" silently would let the model answer half a question as if it were whole. The better change is to the output schema: return the unit, whether it covers the question fully or partly, and what is missing, so the desktop can show the approved part and flag the rest. That needs new keys for partial coverage before it ships.

**4. An ambiguous instruction shows up as inconsistency.** "Can I schedule a callback on a Saturday?" was answered with the weekday-hours unit on 3 of 5 runs and declined on 2. Whether an implication ("weekdays") answers a question is a judgment the prompt does not settle. Run-to-run disagreement on the same input is the signal: state the rule (a unit answers only when it states the fact asked; an implication does not count) and re-measure consistency.

**5. Extraction keeps definitions and pointer sentences.** It found every keyed unit (48 of 48) but left only 44 of 59 context passages alone. Most extra units were definitions ("In this SOP, intake means...") and pointers ("The fee is on the rate card. This SOP does not state that fee."). The prompt should say that definitions of common terms, purpose and scope statements, and pointers to other documents are not units unless they state a rule. Two audience errors in the guided demo (advocate-read lines labelled for members) point to a second clarification: audience means who reads the words aloud or on screen.

**6. Some disagreements call for a change to the evaluation.** All four lookalike pairs (for example "within 2 business days" against "within 2 days") were labelled conflict on every run, while the key said "different". By the app's own definition the model is right, and no lookalike was ever merged. The change is to the key taxonomy for the next set, recorded as a dated correction, with the prompt left as it is.

**7. Do not fix with a prompt what code can guarantee.** One gap draft invented a figure ("100") despite the instruction not to. The code check caught it. The instruction stays, but the guarantee is the check, and that pattern (a deterministic check behind every rule that can be checked) is the one to reuse.

**8. Try a smaller model on search, against the same keys.** Search is the highest-volume call. The evaluation harness makes the comparison cheap: run the same five-run set on a smaller, faster model and switch only if right-answer rate, wrong no-answer rate and consistency hold within the error budget.
