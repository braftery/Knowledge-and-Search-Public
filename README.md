# Knowledge and Search

A working prototype of a governed knowledge and search platform for a Medicare Advantage contact center, with the research, design decisions and evaluations behind it. Built for a case interview, November 2026.

Harbor Health is a fictional health plan. Every document, member, price and figure in this repository is made up and illustrative.

**Live prototype:** https://harbor-knowledge.onrender.com
(The free host sleeps when idle, so the first load can take up to a minute.)

## In two minutes

- **The problem:** advocates search, find three documents that word the same rule three ways, and pick one. Every new AI channel copies the problem.
- **What the prototype shows working:**
  - one approved answer per question, served by reference to the advocate desktop, member chat, the website and the phone line;
  - a Legal wording change reaching every channel the same day, with the old version kept in the history;
  - an explicit "no approved answer" instead of a guess, routed back to the people who can fill the gap;
  - a person deciding at every point where a mistake would reach a member.
- **How it is measured:** five AI tasks tested against answer keys written before the model ran, five runs each, with every miss shown. Safety held in every run; search is the weak spot, with specific causes and fixes.
- **Look at:** the [live prototype](https://harbor-knowledge.onrender.com) (the business case is at [`/pilot`](https://harbor-knowledge.onrender.com/pilot), the evaluations at [`/evals`](https://harbor-knowledge.onrender.com/evals)).

## Key decisions

From [`DECISIONS.md`](DECISIONS.md), which records each one with the alternatives considered and why:

- **D2.** A knowledge unit is the smallest statement that can be approved on its own, plus the contexts it is approved for.
- **D4, D5.** Channels render a unit by reference and hold no copy, and answers are extractive: search returns an approved unit's text, never generated prose.
- **D6.** The model may only choose among approved units the role may read, or say there is no answer.
- **D8, D53.** Approval is routed by risk: Legal for verbatim, policy, clinical and cost wording; Knowledge Ops for procedures and FAQs. The rule can raise a gate and never lowers one.
- **D10.** When a source document changes, the approved version stays live until a person approves the fix.
- **D71.** A quoted price is returned only with its approved disclaimer, and withheld until the caller is verified.
- **D14, D208 to D210.** Measure before trusting: answer keys written before any model run, never edited after, and every result reported with its misses.

## Five more minutes

- [`EVAL_PLAYBOOK.md`](EVAL_PLAYBOOK.md): the evaluation method as a standard another team could adopt, with launch gates and error budgets.
- [`HARNESS.md`](HARNESS.md): the six prompts, what the code checks around them, and eight specific changes to the model's behavior, each backed by an evaluation result.
- [`PORTFOLIO.md`](PORTFOLIO.md): the prototype as a shared capability, with a sequenced slate of use cases, investment decision points and governance at scale.

## What it does

Contact-center knowledge usually lives in many documents that say the same thing in different words. Advocates search, find three versions, and pick one. This prototype turns source documents into small approved **knowledge units**, routes each unit to the right approver (Knowledge Ops for procedures, Legal for regulated wording), and serves one approved answer to every channel: the advocate desktop, member chat, the website and the phone line. When no approved answer exists, it says so instead of guessing.

The prototype has two parts:
- **The guided demo** (about 8 or 11 minutes): one scenario from today's messy search to a governed answer, a Legal change reaching every channel, and the evaluation.
- **Explore as one person:** each role in its own workspace. Knowledge Ops reviews extracted units and works unanswered questions; Legal approves, sends back and decides source changes; advocates see the member's question and the approved answer front and center; the Knowledge owner sees gaps and quality; members use chat, the website and the phone line.

## Ten-minute reading path

1. **The live prototype:** start the short demo from the home page, then open **Explore** as the Pharmacy advocate and press **Member asks a question**.
2. [`SPEC.md`](SPEC.md): the knowledge unit, the roles, the flows and how it is evaluated.
3. [`DECISIONS.md`](DECISIONS.md): every product, design and build decision, with what was considered and why. The best view of the reasoning.
4. [`docs/eval-report.md`](docs/eval-report.md) and [`EVAL_PLAYBOOK.md`](EVAL_PLAYBOOK.md): the model evaluations, and the method behind them.
5. [`humana-knowledge-search/final-report.md`](humana-knowledge-search/final-report.md): the desk research that shaped the design.
6. [`HUMAN_IN_THE_LOOP.md`](HUMAN_IN_THE_LOOP.md) and [`HIPAA_REVIEW.md`](HIPAA_REVIEW.md): where people decide, and how member data is handled.

## Evaluations

Five AI tasks are tested against answer keys and test sets that were written before the model ran, on made-up documents. Every input ran five times, so the results show both accuracy and consistency. Headline results (illustrative data, small sets with wide intervals):

| Task | Result |
|---|---|
| Extraction: expected units found | 48 of 48 |
| Extraction: Legal wording copied character for character | 3 of 3 |
| Search: unanswerable questions correctly given no answer | 17 of 18 |
| Search: answerable questions given the right unit | 28 of 41 |
| Search: answers from another role's knowledge | 0 |
| Duplicate and conflict judgment | 39 of 44 (no lookalike ever merged) |
| Source-change classification | 10 of 10 |
| Drafts for unanswered questions with no invented facts | 11 of 11 |

The full report, every miss, and the two results that are judgment calls are in [`docs/eval-report.md`](docs/eval-report.md). The runner is [`scripts/run_evals.py`](scripts/run_evals.py); the data is in [`data/eval/`](data/eval/).

## Repository map

| Path | What it holds |
|---|---|
| `SPEC.md`, `APP_SPEC.md`, `EXPERIENCE_SPEC.md` | What the prototype is and how each screen behaves |
| `DECISIONS.md` | Decision log |
| `EVAL_PLAYBOOK.md`, `HARNESS.md`, `PORTFOLIO.md` | The evaluation standard, the AI harness and what to change in it, and the portfolio view (written after the presentation) |
| `SERVICE_DESIGN.md`, `PLATFORM.md`, `ROADMAP.md` | Service design, platform view, and what comes after the pilot |
| `HUMAN_IN_THE_LOOP.md`, `HIPAA_REVIEW.md` | Human decision points; privacy review |
| `DEMO.md` | The click-by-click talk track |
| `humana-knowledge-search/` | The research report and its source list |
| `web/` | The web app (React and TypeScript) |
| `api/`, `src/` | The API (FastAPI) and the knowledge engine |
| `data/` | Made-up source documents, roles, plan data, and the eval corpus |
| `fixtures/` | Saved model outputs. The app replays them, so it runs without an API key |
| `tests/`, `api/tests/` | Tests |
| `scripts/`, `.github/workflows/evals.yml` | The eval runner and the workflow that runs it |

## Run it locally

Python 3.12 or later and Node 22 or later.

```bash
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
PORT=8000 python3 -m api
```

Then open http://localhost:8000. No API key is needed: the app replays the saved model outputs in `fixtures/`. Tests: `python3 -m pytest tests api/tests --ignore=tests/e2e`.

## About this copy

This is a curated copy of the working repository, published as a single commit. Internal working files are not included: build logs, self-critiques, audits, agent prompts, research notes, and copies of third-party source documents. Some documents, mainly `DECISIONS.md` and the research report, still refer to those files by name. The research sources are listed with links in [`humana-knowledge-search/sources.md`](humana-knowledge-search/sources.md).

The prototype was built by directing AI coding agents (Claude Code and Cursor), with every change specified, reviewed and tested by the author. Separate agents built the front end and the back end; one wrote the evaluation documents and their answer keys, and another wrote the test questions without seeing those keys. The specifications and the decision log were the control layer, and nothing was merged until the guided demo and every role passed their checks. `EVAL_PLAYBOOK.md`, `HARNESS.md` and `PORTFOLIO.md` were written on 9 November 2026, after the presentation.

## Copyright

Copyright 2026 the owner of this repository (GitHub: braftery). All rights reserved.

This work is shared for interview evaluation only. No license is granted to copy, modify, distribute, or use any part of it.
