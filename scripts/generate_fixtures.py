"""Call the model once and save fixtures/ai/.

Run from the repository root:

    ANTHROPIC_API_KEY=... python scripts/generate_fixtures.py

The key stays in the environment. This script never writes it to disk.
Re-running skips inputs that already have a fixture. Pass --force to call again.
Saved model outputs are not edited, even when the checks below find a miss.

    python scripts/generate_fixtures.py --demo-paths

--demo-paths walks the jump, full, and short demo states and calls the model
only for sufficiency inputs that do not have a fixture yet. It does not rebuild
the extraction and pair fixtures. It also records the Explore surface questions.

--explore-surfaces records only those Explore questions: fresh, after the
version 2 publish, after Legal approves U-GAP-c0, and after both.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ai import (  # noqa: E402
    DEMO_QUERIES,
    assign_ids,
    candidate_pairs,
    drift_user,
    extract_user,
    find_fixture,
    gap_user,
    invented_figures,
    jaccard,
    judge_user,
    label_user,
    prepared_drift_edits,
    pricing_sentence,
    search_pool,
    sufficiency_user,
    write_fixture,
)
from src.engine import DATA, DOCUMENTS, ROLE_KB, STOP, _score_unit  # noqa: E402

CLUSTER_THRESHOLD = 0.5


def _call(task: str, user_content: str, input_ref: str, force: bool):
    existing = find_fixture(task, user_content)
    if existing and not force:
        print(f"skip {task} {input_ref} {existing['input_sha256'][:12]}", flush=True)
        return existing["output"]
    print(f"call {task} {input_ref}", flush=True)
    import anthropic

    from src.ai import call_model

    delays = [4, 8, 16, 32]
    last_error = None
    for attempt, delay in enumerate([0, *delays]):
        if delay:
            time.sleep(delay)
        try:

            output, provenance = call_model(task, user_content, input_ref)
            break
        except anthropic.RateLimitError as error:
            last_error = error
            print(f"rate limit on {task}, retry {attempt + 1}", flush=True)
            continue
        except anthropic.APIConnectionError as error:
            last_error = error
            print(f"connection error on {task}, retry {attempt + 1}", flush=True)
            continue
        except anthropic.APIStatusError:
            raise
    else:
        raise last_error
    path = write_fixture(task, user_content, output, input_ref, provenance=provenance)
    print(f"wrote {path.name}", flush=True)
    print(json.dumps(output, indent=2, ensure_ascii=False), flush=True)
    return output


def _load_docs():
    loaded = []
    for index, (doc_id, _title, filename, _legal, kb) in enumerate(DOCUMENTS):
        text = (DATA / filename).read_text()
        loaded.append({"doc_id": doc_id, "filename": filename, "kb": kb, "index": index, "text": text})
    return loaded


def _extract_all(docs, force: bool, misses: list[str]):
    units = []
    for doc in docs:
        user = extract_user(doc["doc_id"], doc["text"])
        output = _call("extract_units", user, f"data/{doc['filename']}", force)
        raw = output.get("units") if isinstance(output, dict) else None
        if not isinstance(raw, list):
            misses.append(f"T1 {doc['doc_id']} returned no units array.")
            raw = []
        assigned = assign_ids(doc["doc_id"], doc["text"], doc["kb"], doc["index"], raw)
        for unit in assigned:
            if unit["source_mismatch"]:
                misses.append(
                    f"T1 {unit['unit_id']} source span is not in {doc['doc_id']}. Badge: Source mismatch."
                )
            if unit["verbatim_altered"]:
                misses.append(
                    f"T1 {unit['unit_id']} verbatim text differs from its source span. Badge: Verbatim altered by AI."
                )
            if unit["type"] == "verbatim" and "advocate note" in unit["text"].lower():
                misses.append(f"T1 {unit['unit_id']} verbatim unit contains an advocate note.")
        _report_mixed_paragraph(doc, assigned, misses)
        units.extend(assigned)
    return units


def _report_mixed_paragraph(doc, units, misses):
    if doc["doc_id"] != "SRC-RX-EDU-001":
        return
    mixed = [
        unit
        for unit in units
        if "verify the member with two of these" in unit["text"].lower()
        and "do not quote a copay" in unit["text"].lower()
    ]
    if mixed:
        misses.append(
            "T1 the verification paragraph in script v1 stayed in one unit. It mixes a procedure with a policy."
        )


def _pair_units(units, force: bool):
    judgments = []
    for earlier, later in candidate_pairs(units):
        user = judge_user(earlier["title"], earlier["text"], later["title"], later["text"])
        ref = f"{earlier['unit_id']} vs {later['unit_id']}"
        output = _call("judge_pair", user, ref, force)
        judgments.append({"a_id": earlier["unit_id"], "b_id": later["unit_id"], "output": output})
    return judgments


def _score_variants(force: bool, sentence: str, misses: list[str]):
    rows = list(csv.DictReader((DATA / "dedup_variants.csv").open()))
    results = []
    for index, row in enumerate(rows, start=1):
        user = judge_user("Canonical pricing disclaimer", sentence, "Variant", row["variant_text"])
        output = _call("judge_pair", user, f"dedup_variants.csv row {index}", force)
        relation = output.get("relation", "")
        guess = "duplicate" if relation in {"exact", "near_duplicate"} else "meaningfully_different"
        label = row["label"]
        passed = guess == label
        if not passed:
            misses.append(
                f"T2 variant {index} labeled {label}, model said {relation}. Reason: {output.get('reason', '')}"
            )
        results.append({**row, "relation": relation, "guess": guess, "pass": passed, "reason": output.get("reason", "")})
    return results


def _top_candidates(query: str, role: str, pool: list[dict]):
    kbs = set(ROLE_KB.get(role, []))
    if not kbs:
        return []
    allowed = []
    for unit in pool:
        if not set(unit["kb_scope"]) & kbs:
            continue
        if role == "Member" and "member" not in unit["audience_list"]:
            continue
        allowed.append(unit)
    scored = []
    for unit in allowed:
        tags = ", ".join(unit.get("tags") or [])
        score, weight, _overlap, _notes = _score_unit(
            query, unit["title"], tags, unit["text"], unit["domain"], unit["type"]
        )
        scored.append((score, weight, unit["unit_id"], unit))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [item[3] for item in scored[:3]]


def _questions():
    seen = set()
    ordered = []

    def add(question, role):
        key = (question, role)
        if key in seen:
            return
        seen.add(key)
        ordered.append(key)

    for row in csv.DictReader((DATA / "golden_set.csv").open()):
        add(row["question"], row["role"])
    for row in csv.DictReader((DATA / "search_log.csv").open()):
        add(row["query"], row["role"])
    for question, role in DEMO_QUERIES:
        add(question, role)
    return ordered


def _sufficiency(pool, force: bool, misses: list[str]):
    decisions = {}
    for question, role in _questions():
        candidates = _top_candidates(question, role, pool)
        key = (question, role)
        if not candidates:
            decisions[key] = {"answer_unit_id": None, "reason": "No approved unit matched", "source": "no_candidates"}
            continue
        user = sufficiency_user(question, role, candidates)
        output = _call("assess_sufficiency", user, f"{role}: {question}", force)
        allowed = {unit["unit_id"] for unit in candidates}
        answer = output.get("answer_unit_id")
        if answer and answer not in allowed:
            misses.append(
                f"T3 returned {answer} for '{question}' ({role}), which was not one of the units it was shown."
            )
            answer = None
        decisions[key] = {
            "answer_unit_id": answer,
            "reason": output.get("reason", ""),
            "candidates": [unit["unit_id"] for unit in candidates],
        }
    return decisions


def _normalize(query: str) -> set[str]:
    from src.engine import CATALOG, _tokenize

    tokens, _notes = _tokenize(query)
    synonyms = CATALOG["synonyms"]
    mapped = []
    for token in tokens:
        word = synonyms.get(token, token)
        if word not in STOP and len(word) > 2:
            mapped.append(word)
    return set(mapped)


def _cluster_abstentions(decisions):
    rows = list(csv.DictReader((DATA / "search_log.csv").open()))
    items = []
    for row in rows:
        key = (row["query"], row["role"])
        decision = decisions.get(key)
        if decision is None:
            continue
        if decision.get("answer_unit_id"):
            continue
        items.append({"query": row["query"], "role": row["role"], "tokens": _normalize(row["query"])})
    groups = []
    for item in items:
        placed = False
        for group in groups:
            if jaccard(" ".join(item["tokens"]), " ".join(group["tokens"])) >= CLUSTER_THRESHOLD or item["tokens"] == group["tokens"]:
                group["items"].append(item)
                group["tokens"] = group["tokens"] | item["tokens"]
                placed = True
                break
        if not placed:
            groups.append({"tokens": set(item["tokens"]), "items": [item]})
    # Merge groups that became close after growth.
    merged = True
    while merged:
        merged = False
        for left_index, left in enumerate(groups):
            for right in groups[left_index + 1 :]:
                if jaccard(" ".join(left["tokens"]), " ".join(right["tokens"])) >= CLUSTER_THRESHOLD:
                    left["items"].extend(right["items"])
                    left["tokens"] |= right["tokens"]
                    groups.remove(right)
                    merged = True
                    break
            if merged:
                break
    clusters = []
    for index, group in enumerate(groups):
        unique = []
        seen = set()
        for item in group["items"]:
            key = (item["query"], item["role"])
            if key in seen:
                continue
            seen.add(key)
            unique.append({"query": item["query"], "role": item["role"]})
        clusters.append({"id": f"c{index}", "queries": unique, "count": len(group["items"])})
    return clusters


def _draft_gaps(clusters, pool, force: bool, misses: list[str]):
    if not clusters:
        misses.append("T4 found no abstained search-log clusters.")
        return
    label_output = _call("label_clusters", label_user(clusters), "search_log abstentions", force)
    labels = {item.get("id"): item.get("label", "") for item in label_output.get("clusters", [])}
    for cluster in clusters:
        label = labels.get(cluster["id"]) or cluster["queries"][0]["query"]
        example = cluster["queries"][0]["query"]
        nearby = _top_candidates(example, cluster["queries"][0]["role"], pool)
        user = gap_user(label, cluster["queries"], nearby)
        output = _call("draft_gap_unit", user, cluster["id"], force)
        draft = output.get("draft_text", "")
        if "[" not in draft or "]" not in draft:
            misses.append(f"T4 {cluster['id']} draft has no square-bracket placeholder.")
        query_texts = [item["query"] for item in cluster["queries"]]
        approved_texts = [unit.get("text") or "" for unit in pool]
        for figure in invented_figures(draft, query_texts, approved_texts):
            misses.append(
                f"T4 {cluster['id']} draft contains a figure not in the questions or an approved unit: {figure}."
            )


def _drift(units, docs, force: bool, misses: list[str]):
    script = next(doc for doc in docs if doc["doc_id"] == "SRC-RX-EDU-001")
    sentence = pricing_sentence(script["text"])
    if not sentence:
        misses.append("T5 could not find the 30-day pricing sentence in script v1.")
        return
    match = [
        unit
        for unit in units
        if unit["source_doc"] == "SRC-RX-EDU-001" and sentence in (unit.get("source_span") or "")
    ]
    unit_text = match[0]["text"] if match else sentence
    if not match:
        misses.append("T5 no extracted unit contains the script v1 pricing sentence. The drift call uses that sentence as the unit text.")
    for edit in prepared_drift_edits(unit_text, sentence):
        user = drift_user(edit["unit_text"], edit["old_span"], edit["new_span"])
        output = _call("propose_drift_fix", user, edit["name"], force)
        if edit["name"] == "material" and output.get("change") != "material":
            misses.append(f"T5 material edit was judged {output.get('change')}.")
        if edit["name"] == "cosmetic" and output.get("change") != "cosmetic":
            misses.append(f"T5 cosmetic edit was judged {output.get('change')}.")


def _with_resolved_conflict(pool, units):
    """Pool after Legal keeps the chosen blocked unit. Used only to cache that state's questions."""
    from src.ai import load_human_decisions

    chosen = (load_human_decisions().get("conflict_resolution") or {}).get("chosen_unit_id") or ""
    ids = {unit["unit_id"] for unit in pool}
    if not chosen or chosen in ids:
        return pool
    extra = next((unit for unit in units if unit["unit_id"] == chosen), None)
    if extra is None or extra.get("source_mismatch") or extra.get("verbatim_altered"):
        return pool
    return [*pool, extra]


def _golden_notes(decisions, misses: list[str]):
    for row in csv.DictReader((DATA / "golden_set.csv").open()):
        decision = decisions.get((row["question"], row["role"]))
        if decision is None:
            continue
        expected = row.get("expected_before_resolution") or row["expected_unit"]
        got = decision.get("answer_unit_id")
        if expected == "ABSTAIN" and got:
            misses.append(
                f"T3 answered '{row['question']}' for {row['role']} with {got}. The golden set expects an abstention."
            )
        if expected != "ABSTAIN" and not got:
            misses.append(
                f"T3 abstained on '{row['question']}' for {row['role']}. The golden set expects {expected}. New unit ids are U-<document>-<number>, so this expected id is the pre-extraction name."
            )


def _cache_explore_surfaces(force: bool) -> None:
    """Saved sufficiency answers for the Explore desktop and member topic questions.

    States: fresh, after the version 2 publish, after Legal approves U-GAP-c0, and after both.
    """
    from src.corpus import top_candidates
    from src.demo_paths import explore_surface_queries, walk_explore_surface_states
    from src.engine import approved_search_pool, member_candidate_units

    queries = explore_surface_queries()
    for name, conn in walk_explore_surface_states():
        print(f"explore surface {name} queries {len(queries)}", flush=True)
        for role, question in queries:
            pool = member_candidate_units(conn) if role == "Member" else approved_search_pool(conn)
            candidates = top_candidates(question, role, pool)
            if not candidates:
                print(f"skip assess_sufficiency {name} | {role}: {question} no candidates", flush=True)
                continue
            user = sufficiency_user(question, role, candidates)
            _call("assess_sufficiency", user, f"{name} | {role}: {question}", force)


def _cache_demo_paths(force: bool) -> None:
    from src.corpus import top_candidates
    from src.demo_paths import walk_demo_paths
    from src.engine import approved_search_pool

    for name, conn, queries in walk_demo_paths():
        pool = approved_search_pool(conn)
        print(f"demo {name} pool {len(pool)} queries {len(queries)}", flush=True)
        for role, question in queries:
            candidates = top_candidates(question, role, pool)
            if not candidates:
                print(f"skip assess_sufficiency {role}: {question} no candidates", flush=True)
                continue
            user = sufficiency_user(question, role, candidates)
            _call("assess_sufficiency", user, f"{name} | {role}: {question}", force)
            if name == "explore" and role == "Member":
                _cache_member_answer(name, conn, question, force)
        _cache_pending_drift(name, conn, force)


def _cache_member_answer(name: str, conn, question: str, force: bool) -> None:
    """Saved member-wording answer. The model sees member text only."""
    from src.corpus import top_candidates
    from src.engine import member_candidate_units

    pool = member_candidate_units(conn)
    candidates = top_candidates(question, "Member", pool)
    if not candidates:
        print(f"skip assess_sufficiency {name} member: {question} no member wording", flush=True)
        return
    user = sufficiency_user(question, "Member", candidates)
    _call("assess_sufficiency", user, f"{name} member | Member: {question}", force)


def _cache_pending_drift(name: str, conn, force: bool) -> None:
    """Cache the drift call the walk is about to make from this source sentence."""
    from src.demo_paths import PENDING_DRIFT
    from src.engine import flag, prepared_drift_request

    kind = PENDING_DRIFT.get(name)
    if kind is None and flag(conn, "revised") and not flag(conn, "drift") and not flag(conn, "drift_cosmetic"):
        kind = "material"
    if not kind:
        return
    user, _edit = prepared_drift_request(conn, kind)
    if not user:
        print(f"skip propose_drift_fix {name} no source sentence for {kind}", flush=True)
        return
    _call("propose_drift_fix", user, f"{name} | {kind} drift", force)


def _cache_pool(name: str, conn, queries, force: bool) -> None:
    from src.corpus import top_candidates
    from src.engine import approved_search_pool

    pool = approved_search_pool(conn)
    print(f"cache {name} pool {len(pool)} queries {len(queries)}", flush=True)
    for role, question in queries:
        candidates = top_candidates(question, role, pool)
        if not candidates:
            print(f"skip assess_sufficiency {name} | {role}: {question} no candidates", flush=True)
            continue
        user = sufficiency_user(question, role, candidates)
        _call("assess_sufficiency", user, f"{name} | {role}: {question}", force)


def _step4_questions():
    from src.engine import ABSTAIN_QUERY, COST_QUERY, MISSPELL_QUERY

    leak = "do specialty drugs stay at the specialty pharmacy"
    roles = ("Pharmacy advocate", "Insurance advocate")
    questions = (COST_QUERY, ABSTAIN_QUERY, MISSPELL_QUERY, leak)
    return [(role, question) for question in questions for role in roles]


def _cache_guided_step4(force: bool) -> None:
    """Saved answers for step 4 when the approved set is not the full demo path.

    Three guided states: only the pricing disclaimer; the three short-path units;
    and Approve all remaining with no Knowledge Ops approvals and no conflict resolved.
    """
    import tempfile

    from src.engine import (
        apply_website_merge,
        approve_one,
        approve_remaining,
        build_database,
        confirm_tags,
        connect,
        escalate_conflict,
        extract_units,
        keep_canonical,
        presenter_unit_ids,
    )

    questions = _step4_questions()

    def fresh(mode: str):
        folder = tempfile.mkdtemp()
        path = str(Path(folder) / f"{mode}.sqlite")
        build_database(path, mode=mode)
        return connect(path)

    conn = fresh("start")
    try:
        extract_units(conn)
        confirm_tags(conn)
        apply_website_merge(conn)
        keep_canonical(conn)
        escalate_conflict(conn)
        approve_one(conn, "U-RX-EDU-001-09")
        _cache_pool("step4-pricing-only", conn, questions, force)
    finally:
        conn.close()

    conn = fresh("short")
    try:
        for unit_id in presenter_unit_ids(conn):
            approve_one(conn, unit_id)
        _cache_pool("step4-short-three", conn, questions, force)
    finally:
        conn.close()

    conn = fresh("start")
    try:
        extract_units(conn)
        confirm_tags(conn)
        apply_website_merge(conn)
        keep_canonical(conn)
        escalate_conflict(conn)
        approve_remaining(conn)
        _cache_pool("step4-legal-remaining", conn, questions, force)
    finally:
        conn.close()


def _cache_explore_golden(force: bool) -> None:
    """Golden questions against the Explore pool after desk copies are merged."""
    import tempfile

    from src.demo_paths import SEARCH_QUERIES, golden_queries
    from src.engine import build_database, connect

    folder = tempfile.mkdtemp()
    path = str(Path(folder) / "explore.sqlite")
    build_database(path, mode="explore")
    conn = connect(path)
    try:
        seen = set()
        queries = []
        for item in [*golden_queries(), *SEARCH_QUERIES, *_step4_questions()]:
            if item in seen:
                continue
            seen.add(item)
            queries.append(item)
        _cache_pool("explore-golden", conn, queries, force)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--demo-paths", action="store_true")
    parser.add_argument("--explore-surfaces", action="store_true")
    args = parser.parse_args()
    if args.explore_surfaces:
        _cache_explore_surfaces(args.force)
        _cache_explore_golden(args.force)
        _cache_guided_step4(args.force)
        return
    if args.demo_paths:
        _cache_demo_paths(args.force)
        _cache_explore_surfaces(args.force)
        _cache_explore_golden(args.force)
        _cache_guided_step4(args.force)
        return
    misses = []
    docs = _load_docs()
    units = _extract_all(docs, args.force, misses)
    print(f"extracted {len(units)} units", flush=True)
    judgments = _pair_units(units, args.force)
    sentence = pricing_sentence(docs[0]["text"])
    variants = _score_variants(args.force, sentence, misses)
    pool = search_pool(units, judgments)
    print(f"search pool {len(pool)} of {len(units)} units", flush=True)
    decisions = _sufficiency(pool, args.force, misses)
    expanded = _with_resolved_conflict(pool, units)
    if len(expanded) != len(pool):
        print(f"post-resolution pool {len(expanded)}", flush=True)
        _sufficiency(expanded, args.force, misses)
    _golden_notes(decisions, misses)
    clusters = _cluster_abstentions(decisions)
    print(f"gap clusters {len(clusters)}", flush=True)
    _draft_gaps(clusters, pool, args.force, misses)
    _drift(units, docs, args.force, misses)
    _cache_explore_surfaces(args.force)
    _cache_explore_golden(args.force)
    _cache_guided_step4(args.force)
    duplicate_hits = sum(1 for row in variants if row["label"] == "duplicate" and row["pass"])
    duplicate_labels = sum(1 for row in variants if row["label"] == "duplicate")
    different_hits = sum(1 for row in variants if row["label"] != "duplicate" and row["pass"])
    different_labels = sum(1 for row in variants if row["label"] != "duplicate")
    print("", flush=True)
    print("Summary", flush=True)
    print(f"Units extracted: {len(units)}", flush=True)
    print(f"Pair judgments sent to the model: {len(judgments)}", flush=True)
    print(
        f"Dedup variants matching the label: {sum(1 for row in variants if row['pass'])} of {len(variants)}",
        flush=True,
    )
    print(f"Duplicate rows recalled: {duplicate_hits} of {duplicate_labels}", flush=True)
    print(f"Meaningfully different rows kept apart: {different_hits} of {different_labels}", flush=True)
    if misses:
        print("Misses:", flush=True)
        for miss in misses:
            print(f"- {miss}", flush=True)
    else:
        print("No misses recorded by the checks in this script.", flush=True)


if __name__ == "__main__":
    main()
