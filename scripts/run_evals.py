"""Eval runner for the six model tasks, against blind answer keys. Illustrative data only.

Run from the repository root.

    ANTHROPIC_API_KEY=... python scripts/run_evals.py --record --runs 5
        Calls the model for every eval input that has no saved output yet, once per run, and saves
        each output under fixtures/eval/run<n>/. Saved outputs are never edited.

    python scripts/run_evals.py --score
        Scores the saved outputs against the keys and test sets. Writes data/eval/results.json
        (read by the app) and docs/eval-report.md. Needs no key.

    ANTHROPIC_API_KEY=... python scripts/run_evals.py --app-fixtures
        Walks Explore Insights and the Explore searches, and saves a model answer for every input
        the app would otherwise call live. Writes to fixtures/ai/ like scripts/generate_fixtures.py.

Inputs, all optional (a missing file skips that eval):
    data/eval/*.md                      eval documents (extraction)
    data/eval/keys/*_key.csv            answer keys (extraction, search pool)
    data/eval/keys/traps.csv            planted traps (duplicates, near misses)
    data/eval/sets/questions.csv        search questions
    data/eval/sets/dedup_pairs.csv      duplicate and conflict pairs
    data/eval/sets/drift_cases.csv      source edits
    data/eval/sets/gap_cases.csv        unanswered questions
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai import (  # noqa: E402
    MODEL,
    drift_user,
    extract_user,
    find_fixture,
    gap_user,
    invented_figures,
    judge_user,
    sufficiency_user,
    write_fixture,
)

import os  # noqa: E402

# Overridable so the scorer can be tested on a small fake corpus without touching the real one.
EVAL = Path(os.environ.get("HARBOR_EVAL_DIR", ROOT / "data" / "eval"))
KEYS = EVAL / "keys"
SETS = EVAL / "sets"
RUNS_DIR = Path(os.environ.get("HARBOR_EVAL_RUNS", ROOT / "fixtures" / "eval"))
RESULTS = EVAL / "results.json"
REPORT = Path(os.environ.get("HARBOR_EVAL_REPORT", ROOT / "docs" / "eval-report.md"))
SEARCH_LIMIT = 20

ROLE_KB = {
    "Pharmacy advocate": ["pharmacy", "shared-legal"],
    "Insurance advocate": ["benefits", "shared-legal"],
    "Member": ["pharmacy", "benefits"],
}


# ---------- small helpers ----------


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(line for line in handle if not line.startswith("#"))]
    return [{(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in rows]


def norm(text: str) -> str:
    text = (text or "").lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9$%.' ]+", " ", text)).strip()


def tokens(text: str) -> set[str]:
    return {word for word in norm(text).replace(".", " ").split() if len(word) > 2}


def overlap(left: str, right: str) -> float:
    a, b = tokens(left), tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def same_passage(left: str, right: str, threshold: float = 0.6) -> bool:
    a, b = norm(left), norm(right)
    if not a or not b:
        return False
    if a in b or b in a:
        return min(len(a), len(b)) / max(len(a), len(b)) >= 0.5
    return overlap(left, right) >= threshold


def wilson(successes: int, total: int) -> tuple[float, float]:
    if not total:
        return (0.0, 0.0)
    z = 1.96
    p = successes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return (round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3))


def run_dirs() -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    return sorted((path for path in RUNS_DIR.iterdir() if path.is_dir() and path.name.startswith("run")), key=lambda p: int(p.name[3:]))


# ---------- the eval corpus ----------


def eval_documents() -> dict[str, dict]:
    docs = {}
    for path in sorted(EVAL.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        match = re.search(r"Document ID:\s*(\S+)", body)
        doc_id = match.group(1) if match else path.stem
        docs[path.stem] = {"doc_id": doc_id, "file": path.name, "body": body, "key": read_csv(KEYS / f"{path.stem}_key.csv")}
    return docs


def demo_documents() -> dict[str, str]:
    out = {}
    for path in sorted((ROOT / "data").glob("*.md")):
        if path.name == "README.md":
            continue
        body = path.read_text(encoding="utf-8")
        match = re.search(r"Document ID:\s*(\S+)", body)
        out[match.group(1) if match else path.stem] = body
        out[path.name] = body
        out[path.stem] = body
    return out


def search_pool() -> list[dict]:
    """Approved demo units plus every key unit, treated as approved. The search eval assumes extraction was right."""
    from src.corpus import load_corpus

    pool = []
    for unit in load_corpus()["pool"]:
        pool.append(dict(unit, origin="demo"))
    for stem, doc in eval_documents().items():
        for row in doc["key"]:
            if row.get("is_unit", "").lower() != "yes":
                continue
            roles = {role.strip() for role in row.get("roles", "").split(";") if role.strip()}
            kbs = [kb.strip() for kb in row.get("knowledge_base", "").replace(",", ";").split(";") if kb.strip()]
            if {"Pharmacy advocate", "Insurance advocate"} <= roles and "shared-legal" not in kbs:
                kbs.append("shared-legal")
            audience = row.get("audience", "advocate")
            audience_list = ["advocate", "member"] if audience == "both" else [audience]
            span = row["span_text"]
            pool.append({
                "unit_id": row.get("expected_unit_id") or f"E-{stem}-{len(pool)}",
                "title": " ".join(span.split()[:8]),
                "text": span,
                "source_span": span,
                "type": row.get("type") or "policy",
                "tags": [],
                "domain": row.get("section", ""),
                "audience_list": audience_list,
                "kb_scope": kbs or ["pharmacy"],
                "member_text": span if "member" in audience_list else "",
                "source_doc": doc["doc_id"],
                "origin": "eval",
            })
    return pool


def candidates_for(question: str, role: str, pool: list[dict]) -> list[dict]:
    from src.corpus import top_candidates
    from src.finish import expand_explore_query

    return top_candidates(expand_explore_query(question), role, pool, limit=SEARCH_LIMIT)


# ---------- inputs, shared by record and score ----------


def build_inputs() -> list[dict]:
    items: list[dict] = []
    for stem, doc in eval_documents().items():
        items.append({"eval": "extraction", "id": stem, "task": "extract_units", "content": extract_user(doc["doc_id"], doc["body"])})

    questions = read_csv(SETS / "questions.csv")
    # Near-miss traps from the answer keys are questions that should get no answer. Add any the test set lacks.
    seen = {norm(row.get("question", "")) for row in questions}
    for trap in read_csv(KEYS / "traps.csv"):
        if trap.get("kind") == "near_miss" and trap.get("question") and norm(trap["question"]) not in seen:
            questions.append({
                "question_id": trap.get("trap_id"),
                "question": trap["question"],
                "role": "Pharmacy advocate",
                "trap_kind": "near_miss",
                "expected_doc": trap.get("passage_a_doc", ""),
                "expected_span": "",
                "notes": "From the near-miss traps in the answer keys.",
            })
    if questions:
        pool = search_pool()
        for row in questions:
            role = row.get("role") or "Pharmacy advocate"
            cands = candidates_for(row["question"], role, pool)
            item = {"eval": "search", "id": row.get("question_id") or row["question"], "row": row, "candidates": [c["unit_id"] for c in cands]}
            if cands:
                item.update(task="assess_sufficiency", content=sufficiency_user(row["question"], role, cands))
            items.append(item)

    pairs = read_csv(SETS / "dedup_pairs.csv")
    for row in read_csv(KEYS / "traps.csv"):
        if row.get("kind") in {"near_duplicate", "conflict", "lookalike"} and row.get("passage_b_text"):
            pairs.append({
                "pair_id": row.get("trap_id"),
                "text_a": row.get("passage_a_text"),
                "text_b": row.get("passage_b_text"),
                "expected_label": row.get("expected_label"),
                "kind": row.get("kind"),
                "notes": "planted trap",
            })
    for row in pairs:
        items.append({
            "eval": "duplicates",
            "id": row.get("pair_id") or row["text_a"][:30],
            "row": row,
            "task": "judge_pair",
            "content": judge_user("Statement A", row["text_a"], "Statement B", row["text_b"]),
        })

    for row in read_csv(SETS / "drift_cases.csv"):
        items.append({
            "eval": "drift",
            "id": row.get("case_id"),
            "row": row,
            "task": "propose_drift_fix",
            "content": drift_user(row["old_text"], row["old_text"], row["new_text"]),
        })

    for row in read_csv(SETS / "gap_cases.csv"):
        nearby = [{"unit_id": "U-KNOWN-FACT", "title": "Approved source", "text": row["known_fact"]}] if row.get("known_fact") else []
        items.append({
            "eval": "gaps",
            "id": row.get("case_id"),
            "row": row,
            "task": "draft_gap_unit",
            "content": gap_user(row["question"], [{"query": row["question"], "role": row.get("role") or "Pharmacy advocate"}], nearby),
        })
    return items


# ---------- record ----------


def _call_with_retry(task: str, content: str, ref: str):
    import anthropic

    from src.ai import call_model

    last = None
    for delay in (0, 4, 8, 16, 32, 64):
        if delay:
            time.sleep(delay)
        try:
            return call_model(task, content, ref)
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError) as error:
            last = error
            continue
    raise RuntimeError(f"{task} {ref} failed after retries: {last}")


def record(runs: int, workers: int) -> None:
    items = [item for item in build_inputs() if item.get("task")]
    jobs = []
    for run in range(1, runs + 1):
        folder = RUNS_DIR / f"run{run}"
        for item in items:
            if find_fixture(item["task"], item["content"], folder) is None:
                jobs.append((folder, item, run))
    print(f"{len(items)} inputs, {runs} runs, {len(jobs)} calls to make", flush=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_call_with_retry, item["task"], item["content"], f"{item['eval']}:{item['id']}"): (folder, item, run) for folder, item, run in jobs}
        for done, future in enumerate(as_completed(futures), 1):
            folder, item, run = futures[future]
            try:
                output, provenance = future.result()
            except Exception as error:  # noqa: BLE001
                failures += 1
                print(f"FAIL run{run} {item['eval']} {item['id']}: {error}", flush=True)
                continue
            write_fixture(item["task"], item["content"], output, f"{item['eval']}:{item['id']}", directory=folder, provenance=provenance)
            if done % 25 == 0:
                print(f"{done}/{len(jobs)} saved", flush=True)
    print(f"done, {failures} failed", flush=True)
    if failures:
        sys.exit(1)


# ---------- score ----------


def _outputs(item: dict, dirs: list[Path]) -> list[dict | None]:
    if not item.get("task"):
        return [None for _ in dirs]
    out = []
    for folder in dirs:
        found = find_fixture(item["task"], item["content"], folder)
        out.append(found["output"] if found else None)
    return out


def _consistency(per_item: list[list]) -> dict:
    complete = [decisions for decisions in per_item if decisions and all(d is not None for d in decisions)]
    same = sum(1 for decisions in complete if len({json.dumps(d, sort_keys=True) for d in decisions}) == 1)
    return {"items": len(complete), "same_every_run": same, "share": round(same / len(complete), 3) if complete else None}


def _summary(name: str, item_results: list[dict], runs: int) -> dict:
    """item_results: each has 'correct' (list per run) and 'decisions' (list per run)."""
    scored = [r for r in item_results if r["correct"] and all(c is not None for c in r["correct"])]
    n = len(scored)
    per_run = []
    for index in range(runs):
        hits = sum(1 for r in scored if r["correct"][index])
        per_run.append(hits)
    majority = sum(1 for r in scored if sum(r["correct"]) * 2 > len(r["correct"]))
    every = sum(1 for r in scored if all(r["correct"]))
    low, high = wilson(majority, n)
    return {
        "name": name,
        "items": n,
        "runs": runs,
        "majority_correct": majority,
        "majority_rate": round(majority / n, 3) if n else None,
        "interval_95": [low, high],
        "correct_every_run": every,
        "per_run_correct": per_run,
        "consistency": _consistency([r["decisions"] for r in scored]),
    }


def score_extraction(items: list[dict], dirs: list[Path]) -> dict:
    docs = eval_documents()
    report = {"documents": [], "misses": []}
    unit_rows, verbatim_rows, selectivity_rows, type_rows = [], [], [], []
    for item in items:
        doc = docs[item["id"]]
        key_units = [row for row in doc["key"] if row.get("is_unit", "").lower() == "yes"]
        leave_alone = [row for row in doc["key"] if row.get("is_unit", "").lower() == "no"]
        outputs = _outputs(item, dirs)
        found_by_unit = {row["span_text"]: [] for row in key_units}
        exact_by_unit = {row["span_text"]: [] for row in key_units if row.get("verbatim", "").lower() == "yes"}
        type_by_unit = {row["span_text"]: [] for row in key_units}
        touched_by_passage = {row["span_text"]: [] for row in leave_alone}
        extra_counts = []
        for output in outputs:
            if output is None:
                for collection in (found_by_unit, exact_by_unit, type_by_unit, touched_by_passage):
                    for key in collection:
                        collection[key].append(None)
                extra_counts.append(None)
                continue
            extracted = output.get("units", [])
            used = set()
            for row in key_units:
                best, best_score = None, 0.0
                for index, unit in enumerate(extracted):
                    if index in used:
                        continue
                    span = unit.get("source_span") or unit.get("text") or ""
                    if same_passage(span, row["span_text"]):
                        score = overlap(span, row["span_text"]) + (1 if norm(row["span_text"]) in norm(span) else 0)
                        if score > best_score:
                            best, best_score = index, score
                if best is not None:
                    used.add(best)
                found_by_unit[row["span_text"]].append(best is not None)
                unit = extracted[best] if best is not None else None
                type_by_unit[row["span_text"]].append(bool(unit) and unit.get("type") == row.get("type"))
                if row["span_text"] in exact_by_unit:
                    exact_by_unit[row["span_text"]].append(bool(unit) and (unit.get("text") or "").strip() == row["span_text"].strip())
            for row in leave_alone:
                hit = any(
                    index not in used and same_passage(unit.get("source_span") or unit.get("text") or "", row["span_text"], 0.5)
                    for index, unit in enumerate(extracted)
                )
                touched_by_passage[row["span_text"]].append(not hit)
            extra_counts.append(len(extracted) - len(used))
        for span, results in found_by_unit.items():
            unit_rows.append({"correct": results, "decisions": results, "label": span})
            if results and not all(r for r in results if r is not None):
                report["misses"].append({"eval": "extraction", "document": doc["file"], "kind": "unit not found", "text": span, "runs_found": sum(1 for r in results if r)})
        for span, results in exact_by_unit.items():
            verbatim_rows.append({"correct": results, "decisions": results, "label": span})
            if results and not all(r for r in results if r is not None):
                report["misses"].append({"eval": "extraction", "document": doc["file"], "kind": "verbatim not exact", "text": span, "runs_exact": sum(1 for r in results if r)})
        for span, results in type_by_unit.items():
            type_rows.append({"correct": results, "decisions": results, "label": span})
        for span, results in touched_by_passage.items():
            selectivity_rows.append({"correct": results, "decisions": results, "label": span})
            if results and not all(r for r in results if r is not None):
                report["misses"].append({"eval": "extraction", "document": doc["file"], "kind": "extracted text that should be left alone", "text": span, "runs_extracted": sum(1 for r in results if r is False)})
        report["documents"].append({"file": doc["file"], "key_units": len(key_units), "leave_alone": len(leave_alone), "extra_units_per_run": extra_counts})
    runs = len(dirs)
    report["units_found"] = _summary("Expected units found", unit_rows, runs)
    report["verbatim_exact"] = _summary("Verbatim copied character for character", verbatim_rows, runs)
    report["type_correct"] = _summary("Unit type correct", type_rows, runs)
    report["left_alone"] = _summary("Context left alone (purpose, scope, history)", selectivity_rows, runs)
    return report


def _search_hit(unit_id: str | None, row: dict, pool_by_id: dict) -> bool:
    expected = row.get("expected_span", "")
    if not expected:
        return unit_id is None
    if not unit_id:
        return False
    unit = pool_by_id.get(unit_id) or {}
    for text in (unit.get("source_span", ""), unit.get("text", ""), unit.get("member_text", "")):
        # A unit that contains the whole expected sentence is the right unit, however long the unit is.
        if text and (norm(expected) in norm(text) or same_passage(text, expected, 0.55)):
            return True
    return False


def score_search(items: list[dict], dirs: list[Path]) -> dict:
    pool_by_id = {unit["unit_id"]: unit for unit in search_pool()}
    rows, misses, by_kind, leaks = [], [], {}, 0
    for item in items:
        row = item["row"]
        outputs = _outputs(item, dirs) if item.get("task") else [{"answer_unit_id": None} for _ in dirs]
        decisions, correct = [], []
        for output in outputs:
            if output is None:
                decisions.append(None)
                correct.append(None)
                continue
            answer = output.get("answer_unit_id")
            if answer and answer not in item["candidates"]:
                answer = None  # the app rejects an ID outside the candidates
            if answer:
                kbs = set(pool_by_id.get(answer, {}).get("kb_scope", []))
                if not kbs & set(ROLE_KB.get(row.get("role", ""), [])):
                    leaks += 1
            decisions.append(answer or "NO_ANSWER")
            correct.append(_search_hit(answer, row, pool_by_id))
        result = {"correct": correct, "decisions": decisions, "label": row["question"]}
        rows.append(result)
        kind = row.get("trap_kind") or "plain"
        by_kind.setdefault(kind, []).append(result)
        if any(c is False for c in correct):
            retrieved = any(_search_hit(cid, row, pool_by_id) for cid in item["candidates"]) if row.get("expected_span") else None
            misses.append({
                "eval": "search",
                "runs_right": f"{sum(1 for c in correct if c)} of {sum(1 for c in correct if c is not None)}",
                "question": row["question"],
                "role": row.get("role"),
                "trap_kind": kind,
                "expected": row.get("expected_span") or "no approved answer",
                "answers": decisions,
                "right_unit_was_a_candidate": retrieved,
            })
    runs = len(dirs)
    answerable = [r for r, item in zip(rows, items) if item["row"].get("expected_span")]
    abstain = [r for r, item in zip(rows, items) if not item["row"].get("expected_span")]
    return {
        "overall": _summary("Right answer, or right no-answer", rows, runs),
        "answerable": _summary("Answerable questions answered with the right unit", answerable, runs),
        "abstain": _summary("Unanswerable questions answered no-answer", abstain, runs),
        "by_trap_kind": {kind: _summary(kind, results, runs) for kind, results in sorted(by_kind.items())},
        "leaks": leaks,
        "misses": misses,
    }


DEDUP_LABEL = {"exact": "duplicate", "near_duplicate": "duplicate", "conflict": "conflict", "distinct": "different"}


def score_duplicates(items: list[dict], dirs: list[Path]) -> dict:
    rows, misses, by_kind = [], [], {}
    confusion = Counter()
    lookalike_rows = []
    for item in items:
        row = item["row"]
        expected = (row.get("expected_label") or "").lower()
        decisions, correct = [], []
        for output in _outputs(item, dirs):
            if output is None:
                decisions.append(None)
                correct.append(None)
                continue
            label = DEDUP_LABEL.get(output.get("relation"), "different")
            decisions.append(label)
            correct.append(label == expected)
            confusion[(expected, label)] += 1
        result = {"correct": correct, "decisions": decisions, "label": row.get("pair_id")}
        rows.append(result)
        by_kind.setdefault(row.get("kind") or "other", []).append(result)
        if row.get("kind") == "lookalike":
            # The key's stated intent for lookalikes: never merged as duplicates. Scored alongside the exact label.
            lookalike_rows.append({"correct": [None if d is None else d != "duplicate" for d in decisions], "decisions": decisions, "label": row.get("pair_id")})
        if any(c is False for c in correct):
            misses.append({"eval": "duplicates", "runs_right": f"{sum(1 for c in correct if c)} of {sum(1 for c in correct if c is not None)}", "pair": row.get("pair_id"), "kind": row.get("kind"), "expected": expected, "got": decisions, "a": row.get("text_a"), "b": row.get("text_b")})
    runs = len(dirs)
    false_merges = sum(count for (exp, got), count in confusion.items() if exp == "different" and got == "duplicate")
    return {
        "overall": _summary("Pairs labelled correctly", rows, runs),
        "by_kind": {kind: _summary(kind, results, runs) for kind, results in sorted(by_kind.items())},
        "confusion": [{"expected": exp, "got": got, "count": count} for (exp, got), count in sorted(confusion.items())],
        "false_merges_across_runs": false_merges,
        "lookalikes_not_merged": _summary("Lookalikes never merged as duplicates", lookalike_rows, runs),
        "misses": misses,
    }


def score_drift(items: list[dict], dirs: list[Path]) -> dict:
    rows, misses, exact_fix = [], [], 0
    total_fix = 0
    for item in items:
        row = item["row"]
        expected = (row.get("expected_change") or "").lower()
        decisions, correct = [], []
        for output in _outputs(item, dirs):
            if output is None:
                decisions.append(None)
                correct.append(None)
                continue
            change = output.get("change")
            decisions.append(change)
            correct.append(change == expected)
            if expected == "material":
                total_fix += 1
                exact_fix += int(norm(output.get("proposed_text", "")) == norm(row["new_text"]))
        rows.append({"correct": correct, "decisions": decisions, "label": row.get("case_id")})
        if any(c is False for c in correct):
            misses.append({"eval": "drift", "runs_right": f"{sum(1 for c in correct if c)} of {sum(1 for c in correct if c is not None)}", "case": row.get("case_id"), "expected": expected, "got": decisions, "old": row["old_text"], "new": row["new_text"]})
    return {
        "overall": _summary("Source edits classified correctly", rows, len(dirs)),
        "material_fix_matches_new_source": {"matches": exact_fix, "total": total_fix},
        "misses": misses,
    }


def score_gaps(items: list[dict], dirs: list[Path]) -> dict:
    rows, misses = [], []
    for item in items:
        row = item["row"]
        decisions, correct = [], []
        for output in _outputs(item, dirs):
            if output is None:
                decisions.append(None)
                correct.append(None)
                continue
            draft = output.get("draft_text", "")
            invented = invented_figures(draft, [row["question"]], [row["known_fact"]] if row.get("known_fact") else [])
            needs_placeholder = not row.get("known_fact")
            has_placeholder = bool(output.get("placeholders")) or "[" in draft
            ok = not invented and (has_placeholder or not needs_placeholder)
            decisions.append({"invented": invented, "placeholder": has_placeholder})
            correct.append(ok)
        rows.append({"correct": correct, "decisions": decisions, "label": row.get("case_id")})
        if any(c is False for c in correct):
            misses.append({"eval": "gaps", "runs_right": f"{sum(1 for c in correct if c)} of {sum(1 for c in correct if c is not None)}", "case": row.get("case_id"), "question": row["question"], "got": decisions})
    return {"overall": _summary("Drafts with no invented facts and a placeholder where a source is needed", rows, len(dirs)), "misses": misses}


def score() -> dict:
    dirs = run_dirs()
    items = build_inputs()
    groups = {name: [item for item in items if item["eval"] == name] for name in ("extraction", "search", "duplicates", "drift", "gaps")}
    results = {
        "generated_at": datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="minutes"),
        "model": MODEL,
        "runs": len(dirs),
        "illustrative": True,
        "note": "Illustrative, made-up data. Keys and test sets were written before any model run.",
        "sets": {name: len(group) for name, group in groups.items()},
    }
    if groups["extraction"]:
        results["extraction"] = score_extraction(groups["extraction"], dirs)
    if groups["search"]:
        results["search"] = score_search(groups["search"], dirs)
    if groups["duplicates"]:
        results["duplicates"] = score_duplicates(groups["duplicates"], dirs)
    if groups["drift"]:
        results["drift"] = score_drift(groups["drift"], dirs)
    if groups["gaps"]:
        results["gaps"] = score_gaps(groups["gaps"], dirs)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(markdown(results), encoding="utf-8")
    return results


def _line(summary: dict | None) -> str:
    if not summary or not summary.get("items"):
        return "not run"
    low, high = summary["interval_95"]
    consistency = summary["consistency"]
    same = f"{consistency['same_every_run']} of {consistency['items']} gave the same result every run" if consistency["items"] else ""
    return (
        f"{summary['majority_correct']} of {summary['items']} (95% interval {round(low * 100)} to {round(high * 100)} percent); "
        f"right every run on {summary['correct_every_run']}; {same}"
    )


def markdown(results: dict) -> str:
    lines = [
        "# Eval report",
        "",
        f"Illustrative, made-up data. Generated {results['generated_at']} from {results['runs']} runs of {results['model']}.",
        "Keys and test sets were committed before any model output existed. Scores count an item right when most runs got it right.",
        "",
    ]
    if "extraction" in results:
        ext = results["extraction"]
        lines += ["## Extraction", ""]
        for key in ("units_found", "verbatim_exact", "type_correct", "left_alone"):
            lines.append(f"- {ext[key]['name']}: {_line(ext[key])}")
        lines.append("")
    if "search" in results:
        s = results["search"]
        lines += ["## Search answer", ""]
        for key in ("overall", "answerable", "abstain"):
            lines.append(f"- {s[key]['name']}: {_line(s[key])}")
        for kind, summary in s["by_trap_kind"].items():
            lines.append(f"- Trap kind {kind}: {_line(summary)}")
        lines.append(f"- Cross-role leaks: {s['leaks']}")
        lines.append("")
    for key, title in (("duplicates", "Duplicate and conflict judgment"), ("drift", "Drift classification"), ("gaps", "Gap drafts")):
        if key in results:
            lines += [f"## {title}", "", f"- {results[key]['overall']['name']}: {_line(results[key]['overall'])}"]
            if key == "duplicates":
                for kind, summary in results[key]["by_kind"].items():
                    lines.append(f"- {kind}: {_line(summary)}")
                lines.append(f"- Lookalikes wrongly merged, across all runs: {results[key]['false_merges_across_runs']}")
                lines.append(f"- {results[key]['lookalikes_not_merged']['name']}: {_line(results[key]['lookalikes_not_merged'])}")
            lines.append("")
    lines += ["## Every miss", ""]
    for key in ("extraction", "search", "duplicates", "drift", "gaps"):
        for miss in (results.get(key) or {}).get("misses", []):
            lines.append(f"- {json.dumps(miss, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


# ---------- app fixtures ----------


def app_fixtures() -> None:
    """Record a saved answer for every input Explore would otherwise send to the model live."""
    import src.ai as ai
    import src.corpus as corpus
    from fastapi.testclient import TestClient

    from api.main import app

    original = ai.replay
    recorded = []

    def recording(task, user_content, live=False, directory=None):
        output, source = original(task, user_content, False, directory)
        if output is not None or not live:
            # Only inputs the app would send to the model live are recorded. Cached-only lookups stay as they are,
            # so the guided demo and its scores cannot change.
            return output, source
        output, provenance = _call_with_retry(task, user_content, "app-fixture")
        write_fixture(task, user_content, output, "explore-surface", provenance=provenance)
        recorded.append(task)
        return output, "cached"

    corpus.replay = recording
    client = TestClient(app)
    client.post("/api/explore/open", json={"role": "Knowledge owner"})
    client.get("/api/explore/insights")
    questions = read_csv(ROOT / "data" / "golden_set.csv")
    for role in ("Pharmacy advocate", "Insurance advocate"):
        client.post("/api/explore/open", json={"role": role})
        for row in questions:
            client.post("/api/search", json={"world": "explore", "query": row.get("question", ""), "role": role})
        for query in ("What do I say before I quote a drug price?", "what do I say before I quote a cost", "Can I get a 90-day insulin supply by mail?"):
            client.post("/api/search", json={"world": "explore", "query": query, "role": role})
    # The member questions scripted on each advocate call, asked the way the desktop asks them: caller verified first.
    import re

    scenarios = (ROOT / "web" / "src" / "pages" / "advocate" / "scenarios.ts").read_text(encoding="utf-8")
    blocks = re.split(r"\n      \{\n        id: ", scenarios)
    for block in blocks[1:]:
        member = re.search(r'memberId: "([^"]+)"', block)
        birth = re.search(r'dateOfBirth: "([^"]+)"', block)
        verified = "verified: true" in block
        role = "Insurance advocate" if "HBR-25" in block or "HBR-26" in block or "HBR-27" in block else "Pharmacy advocate"
        for query in re.findall(r'query: "([^"]+)"', block):
            client.post("/api/explore/open", json={"role": role})
            if verified and member and birth:
                client.post("/api/explore/verify", json={"member_id": member.group(1), "date_of_birth": birth.group(1)})
            client.post("/api/explore/ask", json={"role": role, "query": query, "member_id": member.group(1) if member else "", "verified": verified})
            if not verified and member and birth:
                # The advocate verifies the caller during the call, then asks again.
                client.post("/api/explore/verify", json={"member_id": member.group(1), "date_of_birth": birth.group(1)})
                client.post("/api/explore/ask", json={"role": role, "query": query, "member_id": member.group(1), "verified": True})
    print(f"recorded {len(recorded)} app fixtures", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--app-fixtures", action="store_true")
    parser.add_argument("--list", action="store_true", help="Print how many inputs each eval has.")
    args = parser.parse_args()
    if args.list:
        print(Counter(item["eval"] for item in build_inputs() if item.get("task")))
    if args.app_fixtures:
        app_fixtures()
    if args.record:
        record(args.runs, args.workers)
    if args.score:
        results = score()
        print(markdown(results))


if __name__ == "__main__":
    main()
