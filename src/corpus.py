"""Rebuild the cached corpus from fixtures/ai. This module never calls the model."""

from __future__ import annotations

import csv

from src.ai import (
    DEMO_QUERIES,
    MISSING_CAPTION,
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
    load_human_decisions,
    prepared_drift_edits,
    pricing_sentence,
    replay,
    search_pool,
    sufficiency_user,
)

CLUSTER_THRESHOLD = 0.5

_CACHE = None


def load_corpus() -> dict:
    """The rebuilt corpus, cached for the life of the process.

    Streamlit reruns the script on each click and reuses this object.
    The first build reads the fixture index once instead of scanning the
    directory on every saved answer.
    """
    global _CACHE
    if _CACHE is None:
        _CACHE = _build()
    return _CACHE


def decide(question: str, role: str, pool: list[dict], live: bool = False, limit: int = 3, rank_query: str | None = None) -> dict:
    """T3 for this question, role, and approved pool.

    A saved fixture wins even when live is on. source is cached, live, missing,
    live_failed, capped, no_candidates, or invalid.
    """
    candidates = top_candidates(rank_query or question, role, pool, limit=limit)
    ids = [unit["unit_id"] for unit in candidates]
    if not candidates:
        return {
            "answer_unit_id": None,
            "reason": "No approved unit matched",
            "source": "no_candidates",
            "candidates": [],
        }
    output, source = replay("assess_sufficiency", sufficiency_user(question, role, candidates), live=live)
    if len(candidates) > 3 and (output is None or not output.get("answer_unit_id")):
        # Saved answers were recorded for three candidates. Explore still retrieves 20.
        narrow = candidates[:3]
        narrowed, narrowed_source = replay(
            "assess_sufficiency",
            sufficiency_user(question, role, narrow),
            live=False,
        )
        if narrowed is not None:
            output, source = narrowed, narrowed_source
    if output is None:
        from src.engine import CAP_MESSAGE

        reason = CAP_MESSAGE if source == "capped" else MISSING_CAPTION
        return {
            "answer_unit_id": None,
            "reason": reason,
            "source": source if source in {"missing", "live_failed", "capped"} else "missing",
            "candidates": ids,
        }
    answer = output.get("answer_unit_id")
    allowed = set(ids)
    if answer and answer not in allowed:
        return {
            "answer_unit_id": None,
            "reason": output.get("reason", ""),
            "source": "invalid",
            "candidates": ids,
            "rejected_id": answer,
            "call_source": source,
        }
    return {
        "answer_unit_id": answer,
        "reason": output.get("reason", ""),
        "source": source,
        "candidates": ids,
    }


def top_candidates(query: str, role: str, pool: list[dict], limit: int = 3) -> list[dict]:
    from src.engine import ROLE_KB, _score_unit

    kbs = set(ROLE_KB.get(role, []))
    if not kbs:
        return []
    allowed = []
    for unit in pool:
        if not set(unit["kb_scope"]) & kbs:
            continue
        audience = unit.get("audience_list") or []
        member_wording = (unit.get("member_text") or "").strip()
        if role == "Member" and "member" not in audience and not member_wording:
            continue
        allowed.append(unit)
    scored = []
    for unit in allowed:
        tags = ", ".join(unit.get("tags") or [])
        score, weight, _overlap, _notes = _score_unit(
            query, unit["title"], tags, unit["text"], unit["domain"], unit["type"]
        )
        if unit.get("sandbox") and score <= 0:
            continue
        scored.append((score, weight, unit["unit_id"], unit))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [item[3] for item in scored[:limit]]


def _requires_legal(unit: dict) -> bool:
    """Verbatim, policy, and units a person marked cost-related or clinical."""
    if unit.get("type") in {"verbatim", "policy"}:
        return True
    marked = set(load_human_decisions().get("cost_or_clinical_units") or [])
    return unit.get("unit_id") in marked


def _field_for(unit: dict, key: str) -> str:
    table = load_human_decisions().get(key) or {}
    if isinstance(table, dict):
        return table.get(unit.get("unit_id"), "") or ""
    return ""


def as_spec(unit: dict) -> dict:
    notes = ["AI extracted."]
    if unit["source_mismatch"]:
        notes.append("Source mismatch.")
    if unit["verbatim_altered"]:
        notes.append("Verbatim altered by AI.")
    return {
        "unit_id": unit["unit_id"],
        "title": unit["title"],
        "type": unit["type"],
        "text": unit["text"],
        "tags": list(unit.get("tags") or []),
        "domain": unit["domain"],
        "kb_scope": list(unit["kb_scope"]),
        "audience": list(unit["audience_list"]),
        "channels": list(unit["channels"]),
        "source_doc": unit["source_doc"],
        "source_quote": unit.get("source_span") or "",
        "requires_legal": 1 if _requires_legal(unit) else 0,
        "applicability": _field_for(unit, "applicability"),
        "review_by": _field_for(unit, "review_by") or "2027-11-06",
        "conflicts_with": "",
        "notes": " ".join(notes),
        "source_mismatch": 1 if unit["source_mismatch"] else 0,
        "verbatim_altered": 1 if unit["verbatim_altered"] else 0,
    }


def legacy_target(name: str) -> str:
    """Map a golden-set id from the hand-written catalog onto an extracted unit."""
    anchors = load_corpus()["anchors"]
    mapping = {
        "U-RX-PRICING-DISCLAIMER": "pricing",
        "U-RX-VERIFY-BEFORE-QUOTE": "verify",
        "U-RX-MAIL-ORDER-TWO-RETAIL-FILLS": "mail_v1",
        "U-RX-SPECIALTY-PHARMACY": "specialty",
        "U-RX-CLOSING": "closing",
        "U-BEN-COST-DISCLAIMER": "benefits",
        "U-BEN-SPECIALIST-REFERRAL": "referral",
        "U-RX-CAREGIVER-AUTH": "caregiver",
    }
    key = mapping.get(name)
    if key is None:
        return name
    unit = anchors.get(key)
    return unit["unit_id"] if unit else ""


def _build() -> dict:
    from src.engine import DATA, DOCUMENTS

    misses = []
    docs = []
    for index, (doc_id, _title, filename, _legal, kb) in enumerate(DOCUMENTS):
        text = (DATA / filename).read_text()
        docs.append({"doc_id": doc_id, "filename": filename, "kb": kb, "index": index, "text": text})
    units = _extract_all(docs, misses)
    judgments = _pair_units(units, misses)
    sentence = pricing_sentence(docs[0]["text"])
    variants = _score_variants(sentence, misses)
    pool = search_pool(units, judgments)
    decisions = _sufficiency(pool, misses)
    anchors = _anchors(units)
    _golden_notes(decisions, anchors, misses, pool)
    clusters = _cluster_abstentions(decisions)
    drafts = _draft_gaps(clusters, pool, misses)
    drift = _drift(units, docs, misses)
    _extra_misses(units, judgments, anchors, misses)
    return {
        "units": units,
        "by_id": {unit["unit_id"]: unit for unit in units},
        "judgments": judgments,
        "variants": variants,
        "pool": pool,
        "pool_ids": {unit["unit_id"] for unit in pool},
        "anchors": anchors,
        "drafts": drafts,
        "drift": drift,
        "misses": misses,
        "decisions": decisions,
    }


def _extract_all(docs, misses):
    units = []
    for doc in docs:
        user = extract_user(doc["doc_id"], doc["text"])
        found = find_fixture("extract_units", user)
        if found is None:
            misses.append(f"T1 fixture missing for {doc['doc_id']}.")
            continue
        raw = found["output"].get("units") if isinstance(found["output"], dict) else None
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


def _pair_units(units, misses):
    judgments = []
    for earlier, later in candidate_pairs(units):
        user = judge_user(earlier["title"], earlier["text"], later["title"], later["text"])
        found = find_fixture("judge_pair", user)
        ref = f"{earlier['unit_id']} vs {later['unit_id']}"
        if found is None:
            misses.append(f"T2 fixture missing for {ref}.")
            continue
        judgments.append(
            {
                "a_id": earlier["unit_id"],
                "b_id": later["unit_id"],
                "output": found["output"],
            }
        )
    return judgments


def _score_variants(sentence, misses):
    from src.engine import DATA

    if not sentence:
        misses.append("T2 could not find the script v1 pricing sentence.")
        return []
    rows = list(csv.DictReader((DATA / "dedup_variants.csv").open()))
    results = []
    for index, row in enumerate(rows, start=1):
        user = judge_user("Canonical pricing disclaimer", sentence, "Variant", row["variant_text"])
        found = find_fixture("judge_pair", user)
        if found is None:
            misses.append(f"T2 fixture missing for dedup variant {index}.")
            results.append({**row, "relation": "", "guess": "missing", "pass": False, "reason": MISSING_CAPTION})
            continue
        output = found["output"]
        relation = output.get("relation", "")
        guess = "duplicate" if relation in {"exact", "near_duplicate"} else "meaningfully_different"
        passed = guess == row["label"]
        if not passed:
            misses.append(
                f"T2 variant {index} labeled {row['label']}, model said {relation}. Reason: {output.get('reason', '')}"
            )
        results.append(
            {
                **row,
                "relation": relation,
                "guess": guess,
                "pass": passed,
                "reason": output.get("reason", ""),
                "confidence": output.get("confidence", ""),
            }
        )
    return results


def _questions():
    from src.engine import DATA

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


def _sufficiency(pool, misses):
    decisions = {}
    for question, role in _questions():
        decision = decide(question, role, pool)
        if decision["source"] == "invalid":
            misses.append(
                f"T3 returned {decision.get('rejected_id')} for '{question}' ({role}), which was not one of the units it was shown."
            )
        elif decision["source"] == "missing":
            misses.append(f"T3 fixture missing for '{question}' ({role}).")
        decisions[(question, role)] = decision
    return decisions


def _visible_demo_pool(pool: list[dict]) -> list[dict]:
    """Drop units the demo has superseded or merged, so golden misses match search."""
    from src.ai import load_human_decisions

    decisions = load_human_decisions()
    dropped = set()
    for pair in (decisions.get("canonical_choices") or {}).get("pairs") or []:
        superseded = pair.get("superseded")
        if superseded:
            dropped.add(superseded)
    for merge in decisions.get("merges") or []:
        dropped.update(merge.get("unit_ids") or [])
    return [unit for unit in pool if unit["unit_id"] not in dropped]


def _golden_notes(decisions, anchors, misses, pool):
    from src.engine import DATA

    mapping = {
        "U-RX-PRICING-DISCLAIMER": "pricing",
        "U-RX-VERIFY-BEFORE-QUOTE": "verify",
        "U-RX-MAIL-ORDER-TWO-RETAIL-FILLS": "mail_v1",
        "U-RX-SPECIALTY-PHARMACY": "specialty",
        "U-RX-CLOSING": "closing",
        "U-BEN-COST-DISCLAIMER": "benefits",
        "U-BEN-SPECIALIST-REFERRAL": "referral",
        "U-RX-CAREGIVER-AUTH": "caregiver",
    }
    visible = _visible_demo_pool(pool)
    for row in csv.DictReader((DATA / "golden_set.csv").open()):
        fresh = decide(row["question"], row["role"], visible)
        if fresh["source"] == "missing":
            decision = decisions.get((row["question"], row["role"]))
        else:
            decision = fresh
        if decision is None:
            continue
        expected = row.get("expected_before_resolution") or row["expected_unit"]
        got = decision.get("answer_unit_id")
        if expected == "ABSTAIN" and got:
            misses.append(
                f"T3 answered '{row['question']}' for {row['role']} with {got}. The golden set expects an abstention."
            )
            continue
        if expected == "ABSTAIN":
            continue
        anchor = anchors.get(mapping.get(expected, ""))
        target = anchor["unit_id"] if anchor else ""
        if not target:
            misses.append(
                f"T1 did not extract a unit for golden id {expected} ('{row['question']}', {row['role']})."
            )
            continue
        if not got:
            misses.append(
                f"T3 abstained on '{row['question']}' for {row['role']}. The golden set expects {expected} ({target})."
            )
        elif got != target:
            misses.append(
                f"T3 chose {got} for '{row['question']}' ({row['role']}). The golden set expects {expected} ({target})."
            )


def _normalize(query: str) -> set[str]:
    from src.engine import CATALOG, STOP, _tokenize

    tokens, _notes = _tokenize(query)
    synonyms = CATALOG["synonyms"]
    mapped = []
    for token in tokens:
        word = synonyms.get(token, token)
        if word not in STOP and len(word) > 2:
            mapped.append(word)
    return set(mapped)


def _cluster_abstentions(decisions):
    from src.engine import DATA

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


def _draft_gaps(clusters, pool, misses):
    drafts = []
    if not clusters:
        misses.append("T4 found no abstained search-log clusters.")
        return drafts
    label_found = find_fixture("label_clusters", label_user(clusters))
    labels = {}
    if label_found is None:
        misses.append("T4 label fixture is missing.")
    else:
        labels = {item.get("id"): item.get("label", "") for item in label_found["output"].get("clusters", [])}
    for cluster in clusters:
        label = labels.get(cluster["id"]) or cluster["queries"][0]["query"]
        example = cluster["queries"][0]["query"]
        nearby = top_candidates(example, cluster["queries"][0]["role"], pool)
        user = gap_user(label, cluster["queries"], nearby)
        found = find_fixture("draft_gap_unit", user)
        if found is None:
            misses.append(f"T4 {cluster['id']} draft fixture is missing.")
            continue
        output = found["output"]
        draft = output.get("draft_text", "")
        if "[" not in draft or "]" not in draft:
            misses.append(f"T4 {cluster['id']} draft has no square-bracket placeholder.")
        query_texts = [item["query"] for item in cluster["queries"]]
        approved_texts = [unit.get("text") or "" for unit in pool]
        figures = invented_figures(draft, query_texts, approved_texts)
        for figure in figures:
            misses.append(
                f"T4 {cluster['id']} draft contains a figure not in the questions or an approved unit: {figure}."
            )
        roles = []
        for item in cluster["queries"]:
            if item["role"] not in roles:
                roles.append(item["role"])
        drafts.append(
            {
                "id": cluster["id"],
                "cluster": label,
                "query_example": example,
                "search_count": cluster["count"],
                "roles": ", ".join(roles),
                "queries": [item["query"] for item in cluster["queries"]],
                "output": output,
                "invented_figures": figures,
            }
        )
    return drafts


def _drift(units, docs, misses):
    script = next(doc for doc in docs if doc["doc_id"] == "SRC-RX-EDU-001")
    sentence = pricing_sentence(script["text"])
    result = {"sentence": sentence, "edits": {}}
    if not sentence:
        misses.append("T5 could not find the 30-day pricing sentence in script v1.")
        return result
    match = [
        unit
        for unit in units
        if unit["source_doc"] == "SRC-RX-EDU-001" and sentence in (unit.get("source_span") or "")
    ]
    unit_text = match[0]["text"] if match else sentence
    result["unit_id"] = match[0]["unit_id"] if match else ""
    if not match:
        misses.append(
            "T5 no extracted unit contains the script v1 pricing sentence. The drift call uses that sentence as the unit text."
        )
    for edit in prepared_drift_edits(unit_text, sentence):
        found = find_fixture("propose_drift_fix", drift_user(edit["unit_text"], edit["old_span"], edit["new_span"]))
        if found is None:
            misses.append(f"T5 fixture missing for the {edit['name']} edit.")
            continue
        output = found["output"]
        if edit["name"] == "material" and output.get("change") != "material":
            misses.append(f"T5 material edit was judged {output.get('change')}.")
        if edit["name"] == "cosmetic" and output.get("change") != "cosmetic":
            misses.append(f"T5 cosmetic edit was judged {output.get('change')}.")
        result["edits"][edit["name"]] = {"edit": edit, "output": output}
    return result


def _find_unit(units, source_doc, needle, type_=None):
    hits = []
    for unit in units:
        if unit["source_doc"] != source_doc:
            continue
        if type_ and unit["type"] != type_:
            continue
        if needle.lower() not in (unit.get("text") or "").lower():
            continue
        hits.append(unit)
    hits.sort(key=lambda unit: (len(unit["text"]), unit["unit_id"]))
    return hits[0] if hits else None


def _anchors(units):
    return {
        "pricing": _find_unit(units, "SRC-RX-EDU-001", "30-day supply at a preferred retail pharmacy", "verbatim"),
        "closing": _find_unit(units, "SRC-RX-EDU-001", "thank you for calling harbor health", "verbatim"),
        "verify": _find_unit(units, "SRC-RX-EDU-001", "do not quote a copay"),
        "mail_v1": _find_unit(units, "SRC-RX-EDU-001", "two times in the current calendar year"),
        "specialty": _find_unit(units, "SRC-RX-EDU-001", "harbor specialty pharmacy"),
        "mail_v2": _find_unit(units, "SRC-RX-EDU-002", "90-day mail-order supply on the first fill"),
        "pricing_v2": _find_unit(units, "SRC-RX-EDU-002", "30-day supply at a preferred retail pharmacy", "verbatim"),
        "benefits": _find_unit(units, "SRC-BEN-COST-001", "covered in-network medical visit", "verbatim"),
        "referral": _find_unit(units, "SRC-BEN-COST-001", "needs a referral from the primary care doctor"),
        "caregiver": _find_unit(units, "SRC-RX-EDU-001", "if a caregiver is on the line"),
    }


def _judgment_between(judgments, left_id, right_id):
    for judgment in judgments:
        ids = {judgment["a_id"], judgment["b_id"]}
        if ids == {left_id, right_id}:
            return judgment
    return None


def _extra_misses(units, judgments, anchors, misses):
    pricing = anchors.get("pricing")
    if pricing and pricing.get("audience") not in {"advocate", "both"}:
        misses.append(
            f"T1 {pricing['unit_id']} audience is {pricing.get('audience')}. The line is read by advocates."
        )
    closing = anchors.get("closing")
    if closing and closing.get("audience") not in {"advocate", "both"}:
        misses.append(
            f"T1 {closing['unit_id']} audience is {closing.get('audience')}. The closing is an advocate script."
        )
    watched = (load_human_decisions().get("watched_pairs") or [])
    selected = {(earlier["unit_id"], later["unit_id"]) for earlier, later in candidate_pairs(units)}
    mail_pairs = [item for item in watched if item.get("label") == "Mail-order rule"]
    for item in mail_pairs:
        pair = (item["a"], item["b"])
        if pair not in selected and (item["b"], item["a"]) not in selected:
            misses.append(f"T2 candidate rule did not select {item['a']} and {item['b']}.")
            continue
        judgment = _judgment_between(judgments, item["a"], item["b"])
        if judgment is None:
            continue
        relation = judgment["output"].get("relation", "")
        if relation != "conflict":
            misses.append(
                f"T2 judged {item['a']} and {item['b']} as {relation}. "
                "The mail-order rules disagree, so the expected relation is conflict."
            )
    website_units = [unit for unit in units if unit["source_doc"] == "SRC-WEB-FAQ"]
    full = "An estimate is not a guarantee of payment."
    if website_units and not any(
        full in (unit.get("text") or "") and "30-day supply" in (unit.get("text") or "") for unit in website_units
    ):
        misses.append("T1 split the website price disclaimer across more than one unit.")
