# Portfolio memo: governed answers as a shared capability

How the prototype becomes a portfolio: what to measure across it, which use cases to build on it and in what order, where the investment decisions sit, and how governance scales. Written on 9 November 2026, after the presentation. No figure here is a forecast; every value is a hypothesis for a pilot to measure, and the data in this repository is made up.

## The portfolio problem

Every AI channel a health plan launches (agent assist, member chat, the website, the phone line, outbound messages) needs the same three things: content someone accountable has approved, a way to keep it current, and proof the AI uses it correctly. Built separately by each team, they are paid for many times over and the answers drift apart across channels, which is the problem this case starts from. Built once, as shared infrastructure, they lower the cost and risk of every later use case. `PLATFORM.md` sets out which parts are reusable as they are and what each new use case configures.

## North star and guardrails

- **North star:** the share of answers, across advocates and member channels, grounded in a current approved unit.
- **Guardrails:** zero unapproved wording reaching a member; zero answers from content a role may not read; time from an approved change to every channel (target: the same day); the wrong no-answer rate, so advocates keep trusting the tool.
- **Reuse:** channels and use cases consuming approved units, and the time to launch the next one. If the platform works, each use case should cost less than the one before.

## The slate

| Horizon | Use case | Value hypothesis (to measure) | Risk tier | Approver | Builds on |
|---|---|---|---|---|---|
| 1 (pilot) | Pharmacy price answers for advocates | Shorter price calls; fewer quality findings on disclaimer wording | Member-facing, regulated (read by a person) | Legal, Knowledge Ops | Built in this prototype |
| 1 | Knowledge Ops workbench: extraction, review, unanswered questions, source changes | Less time per approved unit; changes reach every copy at once | Internal | Knowledge Ops | Built in this prototype |
| 2 | Member chat and website price answers on the same units | Calls avoided for price questions, with the same approved wording | Member-facing, regulated (no person in the loop) | Legal | Horizon 1 units, unchanged |
| 2 | Benefits knowledge for the Insurance queue | The same gains on medical cost questions | Member-facing, regulated (read by a person) | Legal, Knowledge Ops | Platform; new golden set |
| 2 | Provider and pharmacy directory answers | Fewer wrong-directory answers, a documented source of regulatory penalties | Member-facing, regulated | Network operations | Platform; new system of record |
| 3 | Phone line answers | The same answers by voice | Member-facing, regulated (no person in the loop) | Legal | Horizon 2 member channels; caller authentication |
| 3 | Prior authorization status explanations | Fewer repeat calls about pending requests | Member-facing, clinical | Utilization management, Legal | Platform; authorization data |
| 3 | Clinical program scripts and internal policy assistants | Consistent outreach; a quick, lower-risk reuse win | Clinical; internal | Clinical reviewers; policy owners | Platform at the matching gate |

## How the slate is sequenced

1. **Dependencies first.** The governed knowledge layer and the workbench come before the channels that consume them.
2. **A person in the loop before none.** Advocate assist proves the content and the evaluation while a person still reads every answer; member channels follow on the same units.
3. **Prove a second domain before adding breadth.** The directory case reuses the most and has a documented regulatory cost, so it is the fastest test of whether the platform generalizes. Until it passes, the portfolio has one product.
4. **Scale or stop on evidence.** Every use case is judged on the same measures, so they can be compared, sequenced and stopped on the same evidence.

## Where the investment decisions sit

Each business case uses the same arithmetic as the prototype's pilot page (`/pilot`): time saved, quality findings avoided, and Legal change effort saved, less the run cost, with every input a baseline the pilot measures first.

1. **Pilot, week 8:** continue only if quality findings on price wording fall, handle time does not rise, and Legal changes reach every copy the same day.
2. **Before the first member-facing channel:** about 150 human-labelled questions, the lower end of the 95% interval above the agreed bar, and compliance sign-off.
3. **Before voice:** caller authentication and spoken wording approved, with a channel-specific evaluation.
4. **Before scaling to a second domain:** the directory case passes its own gates with no channel-specific code.

## Governance at portfolio scale

- **Tier by potential harm, whatever the team:** member-facing regulated wording, member-facing general, and internal. The tier sets the approver, the evaluation gate and the monitoring, so two teams at the same tier meet the same bar.
- **One review packet per use case,** reusing what this repository already produces: the use-case brief (`SPEC.md`), the human-in-the-loop map (`HUMAN_IN_THE_LOOP.md`), the privacy review (`HIPAA_REVIEW.md`), the evaluation report and method (`docs/eval-report.md`, `EVAL_PLAYBOOK.md`), the harness and its safeguards (`HARNESS.md`), and a monitoring plan. Offered as a template an enterprise AI review board could adopt and adapt.
- **Shared standards,** so each team does not reinvent them: the knowledge unit schema, the routing rule (which can raise a gate and never lowers one), the evaluation playbook, and the harness pattern of putting a deterministic check behind every rule that can be checked.

## What would change the plan

- Advocates stop using the tool, or the wrong no-answer rate rises: fix retrieval before adding channels (`HARNESS.md`, changes 1 and 2).
- Knowledge Ops cannot keep up with review: invest in the workbench and extraction quality before new content domains.
- The directory case needs channel-specific code: the platform is narrower than assumed, and the slate shrinks to pricing and benefits.
- Any unapproved wording reaches a member: stop, as the pilot plan requires.

## The first 90 days

1. Measure the pilot baselines and build the 150-question human-labelled set for pharmacy pricing with Knowledge Ops and Legal.
2. Run the pilot against the week-8 gates, with weekly evaluation readouts.
3. Run discovery with network operations for the directory case and write its business case.
4. Publish the evaluation playbook and harness patterns as the team standard, and agree the risk tiers with the AI governance board.
