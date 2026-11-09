# One platform, many AI use cases

How the parts of this prototype carry over to other AI solutions, and why that matters for managing a portfolio of them. Illustrative; written for the presentation and Q&A.

## The portfolio argument in one paragraph

Every AI channel a health plan launches (voice bot, member chat, agent assist, outbound messages) needs the same three things: content someone accountable has approved, a way to keep it current, and proof that the AI uses it correctly. If each team builds those for itself, the plan pays for them many times and gets inconsistent answers across channels, which is the problem this case starts from. Treating governed knowledge, risk-tiered approval and evaluation as shared infrastructure lowers the cost and risk of each new use case. It also gives the portfolio one risk framework and one launch standard, so use cases can be compared, sequenced, scaled or stopped on the same evidence.

## What is reusable, and what each new use case configures

| Component | Reusable as is | Configured per use case | Where it is in the prototype |
|---|---|---|---|
| Knowledge unit | Schema: type, advocate and member wording, scope, approver, version, effective and review dates, source span | Types and knowledge bases for the domain | `src/engine.py` units table; Studio Library |
| Risk-tiered approval routing | Rule engine with a plain-language reason; can raise a gate, never lowers one | Which content needs which approver (Legal, clinical, compliance) | D53; routing reason on every send |
| AI proposes, a person confirms | Extraction, duplicate and conflict detection, drift detection, gap drafts with placeholders | Prompts and source documents | Guided steps 1, 2, 6, 7 |
| Scoped retrieval with abstention | Role-scoped search, citations, explicit no-answer | Roles and knowledge bases | Guided step 4; `GET /v1/answers` |
| Data plus approved wording | A number from a system of record is shown only with its approved wording, and withheld without it | Which systems of record (pricing, benefits, network, claims) | Member estimators; agent desktop tabs |
| Evaluation harness | Golden and held-out sets; right answer first, wrong no-answers, cross-role leaks; launch gates; saved-answer replay for repeatable regression tests | The golden questions for the domain | Guided step 8; Insights |
| Feedback and gap loop | Flags, unanswered-question clusters, owner decisions, closed-gap notices | None | Studio, Insights, agent desktop |
| Change events | unit.revised, unit.retired, unit.flagged for every downstream channel | Subscribers | Developer docs |
| Human-in-the-loop map | The method: list every decision, who makes it, and what holds until they do | The decisions for the domain | `HUMAN_IN_THE_LOOP.md` |

## Where else it applies (examples, not built)

| Use case | What changes | What stays |
|---|---|---|
| Provider and pharmacy directory answers | Systems of record are network data; approver is network operations; the Aetna penalty came from exactly this kind of data reaching the website and call center [4.9] | Units, routing, evaluation, change events |
| Clinical program scripts (care management outreach) | Approver is a clinical reviewer; knowledge bases are clinical programs | Everything else |
| Prior authorization explanations to members | Joins authorization status data; approver is utilization management and Legal | Data plus approved wording, abstention, evaluation |
| Sales and third-party marketing scripts | Recording and retention rules differ [4.4]; approver is compliance | Version history to prove what was in effect on a date |
| Internal policy assistants (HR, IT) | Lower risk tier: a single approver, no member wording | The same platform at a lighter gate |

## How this shows up as portfolio management

1. **Sequence by dependency.** The governed knowledge layer comes before the channels that consume it: advocate guidance first (a person still in the loop), then member chat and voice on the same units.
2. **One risk framework.** Tier use cases by potential harm (member-facing regulated wording, member-facing general, internal), and set the approval gate and launch thresholds by tier, not by team.
3. **One launch standard.** Every AI feature passes the same evaluation before launch and is monitored on the same measures after it, so results are comparable across the portfolio.
4. **Measure reuse.** Track channels consuming approved units, the share of AI answers grounded in an approved unit, and time to launch a new channel. These show whether the platform lowers the marginal cost of the next use case.
5. **Scale or stop on evidence.** Gaps, flags and wrap-up records show where a use case is not delivering, using the same signals for every use case.

## What the prototype proves, and what it does not

- **Proves:** one unit serves four channels (agent desktop, website, app chat, phone line) and a public API, with a single revision reaching all of them; the routing rule, evaluation harness and feedback loop run without channel-specific code.
- **Does not prove:** a second domain. The fastest test would be the provider directory case above, because it reuses the most and carries a documented regulatory cost.
