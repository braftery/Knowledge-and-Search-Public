# Evaluation playbook for governed AI answers

A standard any team can adopt to decide whether an AI feature that answers from approved content is good enough to launch, and to keep it that way after launch. It generalizes how this prototype was evaluated. Written on 9 November 2026, after the presentation, from the work in this repository. All data is made up and illustrative.

The reusable parts are already here: the runner (`scripts/run_evals.py`), the workflow that calls the model (`.github/workflows/evals.yml`), the key and test-set formats (`data/eval/`), and the report (`docs/eval-report.md`, also at `/evals` in the prototype).

## The rules

1. **Define "correct" per task before writing a single test.** Each model task makes a different decision, so each needs its own definition of right and its own metric. See the task table below.
2. **Write the answer key before any model output exists, and never edit it after.** Commit the keys and test sets first; the git history is the proof. If a key row turns out wrong, add a dated correction row. In this repository the documents and keys were committed by one agent, and the test sets by a second agent working in a separate session without access to the keys.
3. **Separate the authors.** Whoever writes the keys should not write the test questions, and neither should be the system under test. Human-written sets are stronger still; the next step for this work is about 150 questions labelled by Harbor staff.
4. **Test the traps as well as the happy path.** Every set includes the cases that cause real harm: lookalikes that differ by one number, near-misses that sound answerable, misspellings and acronyms, partial answers, questions another role may not see, and unverified callers.
5. **Run every input several times.** Models are not deterministic. Five runs per input show both accuracy and consistency. Report three numbers: right on most runs, right on every run, and the same result on every run.
6. **Report denominators and intervals.** Write "28 of 41, 95% interval 53 to 80 percent", so the reader sees how much the result could move. Small sets give wide intervals, and a launch gate uses the lower end of the interval.
7. **Measure components separately, then end to end.** The search evaluation here treats every keyed unit as approved, so it measures search on its own; extraction is measured against the same keys separately. A miss can then be traced to the stage that caused it.
8. **Report judgment calls both ways, and say when a metric was added.** When the model and the key disagree for a defensible reason, show the exact-label score and the intent score side by side, and never relabel the key after seeing results (decision D210).
9. **Split safety from quality.** Safety measures have zero tolerance and block launch on a single failure. Quality measures have an error budget the business sets.
10. **Replay saved outputs for regression, run live for variance.** Saved model outputs make every test run repeatable and free; scheduled live runs show drift and run-to-run variation.

## What "correct" means for each task

| Task | The decision | Correct means | Metric | Type |
|---|---|---|---|---|
| Extraction | How a document splits into units | Every keyed unit found; Legal wording copied character for character; context left alone | Recall of keyed units; exact-match rate on verbatim; share of context passages left alone | Verbatim exactness is safety; the rest is quality |
| Search answer | Which approved unit answers, or none | The right unit first; no answer when none exists; never another role's unit | Right-unit rate on answerable questions; correct no-answer rate on unanswerable ones; cross-role leaks | Leaks are safety; the rest is quality |
| Duplicate and conflict | How two wordings relate | Duplicates merged, conflicts blocked for Legal, lookalikes never merged | Accuracy by kind; false merges (precision of the merge decision) | False merges are safety |
| Source change | Whether an edit matters | Material changes flagged; cosmetic ones logged | Classification accuracy; fix matches the new source | Missed material change is safety |
| Gap draft | A proposed unit for an unanswered question | No invented fact; a placeholder wherever a source is needed | Drafts with no invented figure (checked in code) | Safety |

Precision and recall matter differently by task. For duplicate detection, a false merge can remove Legal-approved wording, so precision of the merge decision comes first. For search, a wrong answer is worse than a wrong no-answer, so the prompt is strict and the gate watches both the right-answer rate and the wrong no-answer rate.

## Error budgets and launch gates

Safety measures (zero tolerance, any single failure blocks launch or stops the pilot):
- Approved wording copied character for character: 100 percent.
- Answers from content the role may not read: zero.
- Unapproved wording reaching a member: zero.
- Invented facts in a draft that reaches an approver unflagged: zero.

Quality measures (the business sets each bar; the gate uses the lower end of the 95% interval):
- Right unit on answerable questions.
- Wrong no-answers as a share of questions. This is the budget that protects advocates from a tool they stop trusting.
- Consistency: the share of items that give the same result on every run.

These map to the gates in the prototype's pilot plan (`/pilot`): before launch, 100% verbatim match, zero cross-role leaks, about 150 labelled questions with the lower end of the interval above the agreed bar, and compliance sign-off; continue at week 8 only if quality-assurance findings fall and handle time does not rise; stop at once on any leak or unapproved wording.

## LLM-as-judge: where it fits, and how to earn it

This work did not use an LLM as a judge. Every score is computed against keys or by deterministic checks, because the facts that matter here (exact wording, figures, which unit) can be checked exactly. An LLM judge earns a place where the quality is a matter of degree: whether a member-facing paraphrase keeps the meaning, or whether a gap draft is clear enough for an author to finish.

Before trusting one: have people label 50 to 100 items, run the judge on the same items, and measure agreement (for example Cohen's kappa) for each criterion separately. Use the judge only for criteria where agreement holds, keep a person on a sample of its decisions, and never let it replace a deterministic check that exists.

## After launch: live evaluation

The prototype already captures most of the signals a live evaluation needs:
- the version of each unit shown on every call, and whether the advocate read it word for word (wrap-up);
- advocate and channel flags, and questions with no approved answer, clustered for the Knowledge owner.

In production, add two rates computed from those logs: the no-answer rate and the share of answers grounded in an approved unit, each by role and channel.

Each week: sample answered and unanswered questions for human review, re-run the offline set on the live configuration, and compare against the launch baseline. A drop below a quality bar triggers a fix; any safety failure triggers the stop rule.

## The leadership readout

One page: the table of measures with denominators and intervals; which gates pass; the misses that matter, each with its cause and fix; the judgment calls stated both ways; and a recommendation (launch, hold, or stop). `docs/eval-report.md` follows this shape.

## What this run showed, and what it changed

Five runs of every input, scored against blind keys (`docs/eval-report.md`):
- Safety held: zero cross-role leaks, Legal wording exact in 3 of 3, no invented facts in 11 of 11 drafts, and no lookalike merged in any of 20 runs.
- Search was the weak point: 28 of 41 answerable questions got the right unit. The misses had specific causes (acronyms, misspellings, one retrieval miss, partial answers), each with a different fix. `HARNESS.md` sets out the changes.
- Two results were judgment calls, reported both ways: lookalikes labelled "conflict" where the key says "different", and partial answers declined as the prompt instructs.
