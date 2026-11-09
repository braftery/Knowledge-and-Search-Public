# Product roadmap candidates

> **Public copy:** this document refers to internal working files (such as the critique) that are not included in this public copy of the repository.

A running list of what the prototype deliberately does not build, with where each item came from. It feeds the roadmap section of the deck (SPEC section 12, deck section 4). Sequencing and phasing are decided in the presentation work, not here.

Add items at the bottom. When an item is built, mark it built and name the pull request; do not delete it.

| # | Item | Why it matters | Source | 5E stage | Status |
|---|---|---|---|---|---|
| R1 | Member follow-up when there is no approved answer. When the bot or an advocate cannot answer, the member chooses how to hear back (message, email or call). When the gap closes, the member gets the approved answer through that channel. | Today the advocate's script says "tell the member you will follow up", and nothing makes it happen. The person who asked never benefits from the gap they exposed. | 5E critique, Nov 4 | Extend | Not built |
| R2 | Weekly impact note to authors and Legal approvers: which of their units answered questions this week, how many, in which channels, and which were flagged. | People who write and approve knowledge never see its effect. Visible impact keeps them engaged in a loop that depends on their time. | 5E critique, Nov 4 | Extend | Not built |
| R3 | Plan-aware member answers: scope retrieval by the member's plan and coverage stage using each unit's `applicability`, with golden-set questions per plan. | Members get correct general wording today, not wording for their plan. The `applicability` field exists, and search does not use it yet. | 5E critique, Nov 4 (Engage) | Engage | Not built. Recommended after launch, because it changes retrieval and the golden set |
| R4 | Grant a role access to a knowledge base, recorded with the unit's scope and denied by default. | The case lists access grants as human only. Roles are fixed in `data/roles.json`. | HUMAN_IN_THE_LOOP.md G4 (H14) | Engage | Not built |
| R5 | Retire a whole source document, and with it every unit extracted from it, after a person confirms. | Units are retired on conflict resolution; documents are not. | HUMAN_IN_THE_LOOP.md G5 (H15) | Engage | Not built |
| R6 | Learn synonyms and acronyms from search logs; the AI proposes, an author confirms. | The synonym map is static. | HUMAN_IN_THE_LOOP.md G6 (H16) | Engage | Not built |
| R7 | Pinned answers for top questions; the AI proposes, the knowledge owner confirms. | Fastest path for the most-asked questions. | HUMAN_IN_THE_LOOP.md G6 (H17) | Engage | Not built |
| R8 | Named, authenticated approvers through single sign-on. | Approvals are recorded by role. An audit trail needs a named individual. | CRITIQUE.md H1 | Engage | Not built |
| R9 | Release sign-off: Compliance accepts golden-set and held-out results before launch, against proposed gates (100% verbatim match, zero cross-role leaks). | Step 8 shows the scores; the sign-off itself is not recorded. | HUMAN_IN_THE_LOOP.md G7 (H18) | Exit | Shown as a line on the closing screen; the sign-off record is not built |
| R10 | A classifier that routes clinical and cost content to Legal, with a human override, in place of the keyword rule. | The current rule is simple and explainable but will miss paraphrased cost or clinical wording. | DECISIONS.md D53 | Engage | Not built |
| R11 | A redaction service with measured recall, including person names. | Redaction covers member IDs, email, ZIP, address and claim numbers; names are not redacted yet. | HIPAA_REVIEW.md section 5 | Engage | Not built |
