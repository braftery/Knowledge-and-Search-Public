"""Read models for every screen. Figures are illustrative."""

from __future__ import annotations

import json
import os

from src.ai import load_human_decisions, pricing_sentence, resolve_api_key
from src.corpus import load_corpus
from src.engine import (
    ABSTAIN_QUERY,
    COST_QUERY,
    MISSPELL_QUERY,
    ROLE_KB,
    acknowledgement_overview,
    activity,
    all_units,
    anchor,
    author_queue,
    conflict_plans,
    current_unit,
    document_body,
    drift_state,
    expired_units,
    feedback_for_author,
    feedback_summary,
    flag,
    gaps,
    has_approved,
    UNCLUSTERED_ID,
    legal_drift_items,
    list_wrapups,
    live_approved,
    live_enabled,
    mode_name,
    open_conflicts,
    product_backlog,
    previous_revision,
    proposed_queue,
    quality_report,
    step_done,
    units_as_of,
    revisions_for_role,
    waiting_units,
    wording_title,
    wrapup_summary,
    is_acknowledged,
)

from api.catalog import (
    CALLS,
    CAPTIONS,
    EXPLORE_LIVE_CAP,
    ILLUSTRATIVE,
    MEMBER_TOPICS,
    PHARMACY_ONLY_QUERY,
    QUESTION_BANK,
    ROLE_INTRO,
    ROLE_PAGES,
    SCREEN_ROLE,
    SEARCH_ROLES,
    SHORT_DEMO,
    STEP_NAMES,
    TITLES,
    TODAY_QUERY,
    _SAME,
    _STOP,
    doc_name,
    kind_label,
    plain_title,
)
from api.errors import APIError
from api.serialize import (
    activity_dict,
    approval_preview,
    as_dict,
    diff_parts,
    feedback_dict,
    gap_dict,
    placeholder_tokens,
    portal_unit,
    split_csv,
    unit_dict,
)


def _ok(payload: dict) -> dict:
    payload.setdefault("illustrative", True)
    payload.setdefault("note", ILLUSTRATIVE)
    return payload


def undo_payload(session, world: str) -> dict:
    info = session.undo_info(world)
    if not info:
        return {"available": False, "label": "", "world": world}
    return {
        "available": True,
        "label": info.get("label") or "",
        "world": world,
        "screen": info.get("screen"),
        "restore_screen": info.get("restore_screen"),
    }


def guided_view(session, conn) -> dict:
    meta = session.meta()
    step = int(meta.get("step") or 0)
    if step not in STEP_NAMES:
        step = 0
    mode = mode_name(conn) or "start"
    short = mode == "short"
    if short and step in SHORT_DEMO:
        index = SHORT_DEMO.index(step)
        nxt = SHORT_DEMO[index + 1] if index + 1 < len(SHORT_DEMO) else None
    else:
        nxt = step + 1 if step < 8 else None
    return _ok({
        "mode": mode,
        "step": step,
        "step_name": STEP_NAMES[step],
        "title": TITLES[step],
        "caption": CAPTIONS[step],
        "role": SCREEN_ROLE[step],
        "short_path": short,
        "steps": [
            {
                "number": number,
                "name": STEP_NAMES[number],
                "title": TITLES[number],
                "done": step_done(conn, number),
                "on_short_path": number in SHORT_DEMO,
            }
            for number in range(9)
        ],
        "next_step": nxt,
        "next_label": f"Next: {STEP_NAMES[nxt]}" if nxt is not None else None,
        "live_ai": live_enabled(conn),
        "has_api_key": bool(resolve_api_key()),
        "undo": undo_payload(session, "guided"),
    })


def explore_view(session) -> dict:
    meta = session.meta()
    role = meta.get("explore_role")
    ready = session.explore_ready()
    pages = list(ROLE_PAGES.get(role) or [])
    page = meta.get("explore_page")
    if page not in pages:
        page = pages[0] if pages else None
    used = int(meta.get("explore_live_calls") or 0)
    left = max(0, EXPLORE_LIVE_CAP - used)
    if left:
        live_note = "Saved model answers are used first. A new question calls the model live."
    else:
        live_note = "Saved answers only. The live call limit for this visit is reached."
    return _ok({
        "ready": ready,
        "role": role,
        "page": page,
        "pages": pages,
        "intro": ROLE_INTRO.get(role or "", ""),
        "live_calls_used": used,
        "live_calls_left": left,
        "live_calls_cap": EXPLORE_LIVE_CAP,
        "live_note": live_note,
        "undo": undo_payload(session, "explore"),
    })


def session_view(session, conn) -> dict:
    return _ok({
        "session_id": session.id,
        "guided": guided_view(session, conn),
        "explore": explore_view(session),
        "has_api_key": bool(resolve_api_key()),
    })


def today_view(conn) -> dict:
    ran = flag(conn, "today")
    payload = {
        "ran": ran,
        "query": TODAY_QUERY,
        "message": (
            "Which wording is current? Which one did Legal approve? The tool cannot say."
            if ran
            else "Run the search to see what an advocate gets today."
        ),
        "cards": [],
    }
    if not ran:
        return _ok(payload)
    v1 = pricing_sentence(document_body(conn, "SRC-RX-EDU-001"))
    v2 = pricing_sentence(document_body(conn, "SRC-RX-EDU-002"))
    merges = load_human_decisions().get("merges") or []
    website = merges[0].get("member_text", "") if merges else ""
    cards = [
        ("Rx education script v1", "Legal signed 2025-11-02", v1, v1),
        ("Rx education script v2 (desk copy)", "Legal signature not recorded", v2, v1),
        ("Website FAQ", "Page dated 2026-01-18", website, v1),
    ]
    payload["cards"] = [
        {"title": title, "signed": signed, "text": text, "diff": diff_parts(base, text)}
        for title, signed, text, base in cards
    ]
    return _ok(payload)


def _audience_corrections(conn, confirmed: bool) -> list[dict]:
    overrides = load_human_decisions().get("audience_overrides") or {}
    rows = []
    for unit_id, override in overrides.items():
        unit = current_unit(conn, unit_id)
        rows.append({
            "unit_id": unit_id,
            "title": unit["title"] if unit is not None else unit_id,
            "ai_audience": override.get("ai_audience") or "member",
            "audience": override.get("audience") or "advocate",
            "applied": confirmed,
        })
    return rows


def _apply_tag_edits(conn, units: list[dict]) -> None:
    """Show a per-unit tag decision on the extraction card.

    The guided unit row stays as confirmed, so the search pool does not move.
    An empty field on the decision means that field was left as stored.
    """
    if not units:
        return
    rows = conn.execute(
        "SELECT unit_id, audience, domain, tags, actor FROM unit_tag_edits"
    ).fetchall()
    edits = {row["unit_id"]: row for row in rows}
    for unit in units:
        edit = edits.get(unit.get("unit_id"))
        if edit is None:
            continue
        audience = (edit["audience"] or "").strip()
        domain = (edit["domain"] or "").strip()
        tags = (edit["tags"] or "").strip()
        if audience:
            unit["audience"] = split_csv(audience.replace(";", ","))
        if domain:
            unit["domain"] = domain
        if tags:
            unit["tags"] = split_csv(tags)
        unit["tags_edited_by"] = (edit["actor"] or "").strip() or "Knowledge Ops author"


def extraction_view(conn) -> dict:
    extracted = flag(conn, "extracted")
    confirmed = flag(conn, "tags_confirmed")
    units = []
    if extracted:
        units = [
            unit_dict(row)
            for row in all_units(conn)
            if row["source_doc"] == "SRC-RX-EDU-001" and row["version"] == 1
        ]
        for index, unit in enumerate(units, start=1):
            unit["number"] = index
        _apply_tag_edits(conn, units)
    verbatim = [unit for unit in units if unit.get("type") == "verbatim"]
    clean = [unit for unit in verbatim if not unit.get("source_mismatch") and not unit.get("verbatim_altered")]
    return _ok({
        "extracted": extracted,
        "tags_confirmed": confirmed,
        "document": {
            "doc_id": "SRC-RX-EDU-001",
            "title": doc_name("SRC-RX-EDU-001"),
            "body": document_body(conn, "SRC-RX-EDU-001"),
        },
        "units": units,
        "unit_count": len(units),
        "verbatim_matching_source": len(clean),
        "verbatim_total": len(verbatim),
        "audience_corrections": _audience_corrections(conn, confirmed),
        "message": (
            "AI decides units, types and spans. A person confirms tags and audience."
            if extracted
            else "AI reads the script and proposes units."
        ),
    })


def _human_line(decisions, a_id: str, b_id: str, statuses: dict) -> str:
    ids = {a_id, b_id}
    for pair in (decisions.get("canonical_choices") or {}).get("pairs") or []:
        if pair.get("superseded") in ids:
            return "Human decision: keep the script v1 wording. The v2 copy is superseded."
    for merge in decisions.get("merges") or []:
        if ids & set(merge.get("unit_ids") or []):
            return "Human decision: merged into the member wording of the pricing disclaimer."
    for plan in conflict_plans():
        plan_ids = {plan.get("chosen_unit_id"), *(plan.get("retire_unit_ids") or [])}
        if ids <= plan_ids:
            row = statuses.get(plan.get("chosen_unit_id"))
            if row is not None and row["status"] == "blocked_conflict":
                return "Both versions are blocked until Legal decides."
            return "Legal resolved this conflict."
    later = statuses.get(b_id)
    if later is not None and later["status"] == "proposed":
        return "The v2 copy is held back. One unit remains."
    return ""


def copies_view(conn) -> dict:
    extracted = flag(conn, "extracted")
    if not extracted:
        return _ok({
            "ready": False,
            "message": "No units to compare yet. Extract units from script v1 first.",
            "pairs": [],
            "counts": {"near_duplicate": 0, "exact": 0, "conflict": 0, "all": 0},
        })
    corpus = load_corpus()
    decisions = load_human_decisions()
    statuses = {row["unit_id"]: row for row in all_units(conn) if row["version"] == 1}
    watched = [{item.get("a"), item.get("b")} for item in (decisions.get("watched_pairs") or [])]

    def rank(item):
        ids = {item["a_id"], item["b_id"]}
        return watched.index(ids) if ids in watched else len(watched)

    pairs = []
    counts = {"near_duplicate": 0, "exact": 0, "conflict": 0, "all": len(corpus["judgments"])}
    ordered = sorted(corpus["judgments"], key=rank)
    for judgment in ordered:
        output = judgment.get("output") or {}
        relation = output.get("relation") or ""
        if relation in counts:
            counts[relation] += 1
        a_id, b_id = judgment["a_id"], judgment["b_id"]
        a = corpus["by_id"].get(a_id) or {}
        b = corpus["by_id"].get(b_id) or {}
        status_a = statuses.get(a_id)
        status_b = statuses.get(b_id)
        phrases = output.get("differing_phrases") or []
        human = _human_line(decisions, a_id, b_id, statuses)
        if human.startswith("Human decision") and not flag(conn, "canonical"):
            human = "Prepared decision: keep the script v1 wording. It applies when you press the button."
        pairs.append({
            "a_id": a_id,
            "b_id": b_id,
            "a_title": a.get("title") or a_id,
            "b_title": b.get("title") or b_id,
            "a_text": a.get("text") or "",
            "b_text": b.get("text") or "",
            "a_doc": doc_name(a.get("source_doc") or ""),
            "b_doc": doc_name(b.get("source_doc") or ""),
            "a_status": status_a["status"] if status_a is not None else "",
            "b_status": status_b["status"] if status_b is not None else "",
            "relation": relation,
            "confidence": output.get("confidence"),
            "reason": output.get("reason") or "",
            "differing_phrases": [{"a": item.get("a") or "", "b": item.get("b") or ""} for item in phrases],
            "diff": diff_parts(a.get("text") or "", b.get("text") or ""),
            "human_line": human,
        })
    merges = decisions.get("merges") or []
    website = None
    if merges:
        merge = merges[0]
        pieces = []
        for unit_id in merge.get("unit_ids") or []:
            unit = corpus["by_id"].get(unit_id) or {}
            status = statuses.get(unit_id)
            pieces.append({
                "unit_id": unit_id,
                "text": unit.get("text") or "",
                "status": status["status"] if status is not None else "",
            })
        website = {
            "into_unit_id": merge.get("into_unit_id") or "",
            "member_text": merge.get("member_text") or "",
            "units": pieces,
            "merged": flag(conn, "website_merged"),
        }
    return _ok({
        "ready": True,
        "canonical": flag(conn, "canonical"),
        "escalated": flag(conn, "escalated"),
        "website_merged": flag(conn, "website_merged"),
        "can_keep_canonical": not flag(conn, "canonical"),
        "can_escalate": flag(conn, "canonical") and not flag(conn, "escalated"),
        "counts": counts,
        "pairs": pairs,
        "website_merge": website,
        "message": "People decide what happens next.",
    })


def _queue_unit(conn, row) -> dict:
    return unit_dict(row, preview=approval_preview(conn, row))


def legal_queue_view(conn) -> dict:
    waiting = [_queue_unit(conn, row) for row in waiting_units(conn)]
    held = []
    for row in proposed_queue(conn):
        held.append({
            "unit_id": row["unit_id"],
            "title": row["title"],
            "notes": row["notes"] or "Held back as an exact copy.",
        })
    approved = conn.execute(
        "SELECT COUNT(*) AS n FROM units WHERE status = 'approved' AND search_visible = 1"
    ).fetchone()["n"]
    return _ok({
        "ready": flag(conn, "escalated"),
        "count": len(waiting),
        "waiting": waiting,
        "can_approve_all": mode_name(conn) != "short" and len(waiting) > 1,
        "held": held,
        "approved_count": approved,
        "message": "" if waiting else f"Queue is empty. {approved} units are approved and searchable.",
    })


def author_queue_view(conn) -> dict:
    rows = [_queue_unit(conn, row) for row in author_queue(conn)]
    return _ok({
        "count": len(rows),
        "waiting": rows,
        "can_approve_all": len(rows) > 1,
        "message": "" if rows else "Nothing waiting. Procedure and FAQ units are approved by Knowledge Ops.",
    })


def _editable_gap(row) -> bool:
    """A gap the owner has sent to the author, and that has not gone to approval yet."""
    if (row["status"] or "") != "in_review":
        return False
    return not (row["unit_id"] or "").strip()


def author_edits_view(conn) -> dict:
    """Gap drafts the owner sent to the author, and units Legal sent back."""
    drafts = []
    for row in gaps(conn):
        if row["id"] == UNCLUSTERED_ID:
            continue
        if not _editable_gap(row):
            continue
        item = gap_dict(row)
        open_tokens = placeholder_tokens(row["draft_text"], row["draft_member_text"])
        item["open_placeholders"] = open_tokens
        from src.sandbox import gap_ready, gap_sources_public

        item["can_send"] = gap_ready(conn, row)
        item["placeholder_sources"] = gap_sources_public(conn, row["id"])
        from src.sandbox import gap_candidate

        item["candidate"] = gap_candidate(conn, row["id"])
        drafts.append(item)
    returned = []
    rows = conn.execute(
        "SELECT * FROM units WHERE status = 'returned' AND version = 1 ORDER BY unit_id"
    ).fetchall()
    for row in rows:
        item = unit_dict(row)
        open_tokens = placeholder_tokens(row["text"], row["member_text"])
        item["placeholders"] = open_tokens
        item["can_send"] = bool((row["text"] or "").strip()) and not open_tokens
        returned.append(item)
    count = len(drafts) + len(returned)
    return _ok({
        "count": count,
        "gaps": drafts,
        "returned": returned,
        "message": "" if count else "Nothing is waiting for the author to edit.",
    })


def _conflict_row(conn, plan, statuses) -> dict:
    corpus = load_corpus()
    chosen = plan.get("chosen_unit_id") or ""
    kept = corpus["by_id"].get(chosen) or {}
    status = statuses.get(chosen)
    still_open = status is not None and status["status"] == "blocked_conflict"
    comparisons = []
    for other_id in plan.get("retire_unit_ids") or []:
        other = corpus["by_id"].get(other_id) or {}
        comparisons.append({
            "unit_id": other_id,
            "title": other.get("title") or other_id,
            "doc": doc_name(other.get("source_doc") or ""),
            "text": other.get("text") or "",
            "diff": diff_parts(kept.get("text") or "", other.get("text") or ""),
        })
    from src.engine import _meta_get

    recorded = ""
    reason_source = ""
    if not still_open:
        if plan.get("resolve_in_demo"):
            recorded = _meta_get(conn, "conflict_reason", "")
        else:
            recorded = plan.get("reason") or ""
        raw_sources = _meta_get(conn, "conflict_sources", "")
        try:
            sources = json.loads(raw_sources) if raw_sources else {}
        except json.JSONDecodeError:
            sources = {}
        if isinstance(sources, dict):
            reason_source = sources.get(plan.get("id") or "") or ""
    return {
        "id": plan.get("id") or "",
        "label": plan.get("label") or "Conflict",
        "open": still_open,
        "resolve_in_demo": bool(plan.get("resolve_in_demo")),
        "chosen_unit_id": chosen,
        "chosen_title": kept.get("title") or chosen,
        "chosen_text": kept.get("text") or "",
        "chosen_doc": doc_name(kept.get("source_doc") or ""),
        "retire_unit_ids": list(plan.get("retire_unit_ids") or []),
        "reason_suggestion": plan.get("reason") or "",
        "recorded_reason": recorded,
        "reason_source": reason_source,
        "comparisons": comparisons,
    }


def conflicts_view(conn) -> dict:
    statuses = {row["unit_id"]: row for row in all_units(conn) if row["version"] == 1}
    plans = [_conflict_row(conn, plan, statuses) for plan in conflict_plans()]
    return _ok({
        "count_open": sum(1 for plan in plans if plan["open"]),
        "plans": plans,
        "message": "Both versions stay blocked until Legal picks one and records a reason.",
    })


def inbox_view(conn) -> dict:
    items = []
    order = {"verbatim": 0, "policy": 1}
    waiting = sorted(waiting_units(conn), key=lambda unit: (order.get(unit["type"], 2), unit["unit_id"]))
    for row in waiting:
        shown = _queue_unit(conn, row)
        items.append({
            "kind": "approval",
            "id": row["unit_id"],
            "title": row["title"],
            "routing_reason": shown.get("routing_reason") or "",
            "unit": shown,
        })
    open_ids = {plan.get("id") for plan in open_conflicts(conn)}
    statuses = {row["unit_id"]: row for row in all_units(conn) if row["version"] == 1}
    for plan in conflict_plans():
        if plan.get("id") in open_ids:
            items.append({
                "kind": "conflict",
                "id": plan.get("id"),
                "title": f"Conflict: {plan.get('label')}",
                "conflict": _conflict_row(conn, plan, statuses),
            })
    return _ok({
        "count": len(items),
        "items": items,
        "message": "3 units await your review." if len(items) == 3 else f"{len(items)} items await your review.",
    })


def search_prompts() -> dict:
    return _ok({
        "cost": COST_QUERY,
        "abstain": ABSTAIN_QUERY,
        "misspell": MISSPELL_QUERY,
        "pharmacy_only": PHARMACY_ONLY_QUERY,
        "roles": list(SEARCH_ROLES),
    })


def _revision_change() -> dict:
    from src.engine import CATALOG

    return load_human_decisions().get("channels_revision") or CATALOG.get("channels_revision") or {}


def channels_view(conn) -> dict:
    unit_id = anchor(conn, "pricing")
    live = live_approved(conn, unit_id) if unit_id else None
    if live is None:
        return _ok({
            "ready": False,
            "message": "No channel has an approved pricing disclaimer yet. Legal must approve it first.",
            "live": None,
            "previous": None,
            "revised": flag(conn, "revised"),
        })
    previous = None
    if live["version"] > 1:
        row = conn.execute(
            "SELECT * FROM units WHERE unit_id = ? AND version = ?",
            (live["unit_id"], live["version"] - 1),
        ).fetchone()
        if row is not None:
            previous = unit_dict(row)
    change = _revision_change()
    advocate_next = (live["text"] or "").replace(change.get("find") or "", change.get("replace") or "")
    member_old = live["member_text"] or ""
    member_find = change.get("member_find") or ""
    member_next = member_old.replace(member_find, change.get("member_replace") or "") if member_find else member_old
    revision_ready = bool(change.get("find")) and change.get("find") in (live["text"] or "")
    return _ok({
        "ready": True,
        "revised": flag(conn, "revised"),
        "live": unit_dict(live),
        "previous": previous,
        "advocate_diff": diff_parts(previous["text"], live["text"]) if previous else [],
        "member_diff": diff_parts(previous["member_text"], live["member_text"]) if previous and previous.get("member_text") else [],
        "revision_ready": revision_ready,
        "revision_preview": {
            "find": change.get("find") or "",
            "replace": change.get("replace") or "",
            "advocate_text": advocate_next,
            "advocate_diff": diff_parts(live["text"] or "", advocate_next),
            "member_text": member_next,
            "member_diff": diff_parts(member_old, member_next),
            "next_version": live["version"] + 1,
        },
        "message": f"Live everywhere: {live['unit_id']} version {live['version']}",
    })


def versions_view(conn, unit_id: str) -> dict:
    rows = conn.execute(
        "SELECT * FROM units WHERE unit_id = ? ORDER BY version",
        (unit_id,),
    ).fetchall()
    if not rows:
        raise APIError(f"No unit {unit_id}.", 404)
    versions = []
    previous = None
    for row in rows:
        item = unit_dict(row)
        if previous is not None:
            item["diff_from_previous"] = {
                "advocate": diff_parts(previous["text"] or "", row["text"] or ""),
                "member": diff_parts(previous["member_text"] or "", row["member_text"] or ""),
            }
        else:
            item["diff_from_previous"] = {"advocate": [], "member": []}
        versions.append(item)
        previous = row
    moments = [row["effective_date"] for row in rows if row["effective_date"]]
    return _ok({"unit_id": unit_id, "versions": versions, "moments": moments})


def as_of_view(conn, unit_id: str, timestamp: str) -> dict:
    from src.compliance import parse_timestamp

    if not (timestamp or "").strip():
        raise APIError("A timestamp is required.")
    try:
        parse_timestamp(timestamp)
    except ValueError as exc:
        raise APIError(str(exc)) from exc
    found = units_as_of(conn, unit_id, timestamp)
    if found is None:
        raise APIError("No version was live at that time.", 404)
    return _ok(dict(found))


def expired_view(conn) -> dict:
    rows = [unit_dict(row) for row in expired_units(conn)]
    noun = "unit" if len(rows) == 1 else "units"
    message = f"{len(rows)} approved {noun} past the review date." if rows else "No approved unit is past its review date."
    return _ok({"count": len(rows), "units": rows, "message": message})


def _latest_units(conn) -> list:
    rows = list(all_units(conn))
    best: dict[str, object] = {}
    for row in rows:
        current = best.get(row["unit_id"])
        if current is None or row["version"] >= current["version"]:
            best[row["unit_id"]] = row
    return list(best.values())


def units_view(conn, *, kb: str = "", status: str = "", kind: str = "", q: str = "", role: str = "", latest: bool = True) -> dict:
    rows = _latest_units(conn) if latest else list(all_units(conn))
    if role in ("Pharmacy advocate", "Insurance advocate"):
        allowed = set(ROLE_KB[role])
        rows = [
            row for row in rows
            if row["status"] == "approved" and allowed & set(split_csv(row["kb_scope"]))
        ]
    if kb:
        rows = [row for row in rows if kb in split_csv(row["kb_scope"])]
    if status:
        rows = [row for row in rows if row["status"] == status]
    if kind:
        rows = [row for row in rows if row["type"] == kind]
    if q.strip():
        needle = q.strip().lower()
        rows = [
            row for row in rows
            if needle in (row["text"] or "").lower() or needle in (row["title"] or "").lower()
        ]
    return _ok({
        "count": len(rows),
        "units": [unit_dict(row) for row in rows],
        "filters": {"kb": kb, "status": status, "type": kind, "q": q, "role": role, "latest": latest},
    })


def unit_view(conn, unit_id: str) -> dict:
    row = current_unit(conn, unit_id)
    if row is None:
        raise APIError(f"No unit {unit_id}.", 404)
    versions = conn.execute(
        "SELECT version, status, approved_by, effective_date FROM units WHERE unit_id = ? ORDER BY version",
        (unit_id,),
    ).fetchall()
    copies = conn.execute(
        "SELECT unit_id, status FROM units WHERE superseded_by = ? AND version = 1",
        (unit_id,),
    ).fetchall()
    return _ok({
        "unit": unit_dict(row, preview=approval_preview(conn, row)),
        "versions": [as_dict(item) for item in versions],
        "copies": [as_dict(item) for item in copies],
    })


def author_documents_view(conn, include_all: bool = False) -> dict:
    from src.sandbox import author_documents

    docs = author_documents(conn, include_all=include_all)
    return _ok({"count": len(docs), "documents": docs})


def legal_documents_view(conn) -> dict:
    from src.sandbox import legal_documents

    docs = legal_documents(conn)
    return _ok({"count": len(docs), "documents": docs})


def source_requests_view(conn) -> dict:
    from src.sandbox import list_source_requests

    items = list_source_requests(conn)
    return _ok({"count": len(items), "requests": items})


def author_drift_list_view(conn) -> dict:
    from src.sandbox import author_drift_payload

    return _ok(author_drift_payload(conn))


def documents_view(conn) -> dict:
    rows = conn.execute("SELECT doc_id, title, legal_signed, kb FROM documents ORDER BY doc_id").fetchall()
    docs = []
    for row in rows:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM units WHERE source_doc = ? AND version = 1",
            (row["doc_id"],),
        ).fetchone()["n"]
        item = as_dict(row)
        item["unit_count"] = count
        item["name"] = doc_name(row["doc_id"])
        docs.append(item)
    return _ok({"documents": docs})


def document_view(conn, doc_id: str) -> dict:
    row = conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if row is None:
        raise APIError(f"No document {doc_id}.", 404)
    units = [
        unit_dict(unit)
        for unit in all_units(conn)
        if unit["source_doc"] == doc_id and unit["version"] == 1
    ]
    body = as_dict(row)
    document_body = body.get("body") or ""
    for index, unit in enumerate(units, start=1):
        unit["number"] = index
        span = unit.get("source_span") or ""
        if span and span in document_body:
            start = document_body.index(span)
            unit["span_start"] = start
            unit["span_end"] = start + len(span)
    return _ok({
        "doc_id": doc_id,
        "title": body.get("title") or "",
        "name": doc_name(doc_id),
        "legal_signed": body.get("legal_signed") or "",
        "kb": body.get("kb") or "",
        "body": body.get("body") or "",
        "signer": body.get("signer") or "",
        "owner_role": body.get("owner_role") or "",
        "statement": body.get("statement") or "",
        "attested_on": body.get("attested_on") or "",
        "units": units,
    })


def _gap_answered(conn, row: dict) -> bool:
    from src.engine import anchor, live_approved

    cluster = row.get("cluster") or ""
    anchor_name = {
        "Rx pricing disclaimer to read": "pricing",
        "Closing line for Rx education call": "closing",
        "Member website wording for drug price estimate": "pricing",
    }.get(cluster)
    if anchor_name:
        unit_id = anchor(conn, anchor_name)
        return bool(unit_id and live_approved(conn, unit_id))
    if cluster == "Greeting for MA pharmacy education call":
        found = conn.execute(
            """
            SELECT 1 FROM units
            WHERE status = 'approved' AND search_visible = 1 AND title LIKE '%Greeting%'
            LIMIT 1
            """
        ).fetchone()
        return found is not None
    return False


def gaps_view(conn) -> dict:
    from src.sandbox import gap_sources_public

    rows = [gap_dict(row) for row in gaps(conn)]
    for row in rows:
        row["answered"] = _gap_answered(conn, row)
        row["placeholder_sources"] = gap_sources_public(conn, row["id"])
    return _ok({"count": len(rows), "gaps": rows, "message": "" if rows else "AI found no unanswered cluster in the search log."})


def drift_view(conn) -> dict:
    state = drift_state(conn)
    events = []
    for event in state.get("events") or []:
        item = dict(event)
        item["flagged"] = bool(item.get("flagged"))
        events.append(item)
    state = dict(state)
    state["events"] = events
    edits = (load_corpus().get("drift") or {}).get("edits") or {}
    prepared = {}
    for name in ("cosmetic", "material"):
        edit = (edits.get(name) or {}).get("edit") or {}
        if edit:
            prepared[name] = {
                "old_span": edit.get("old_span") or "",
                "new_span": edit.get("new_span") or "",
                "diff": diff_parts(edit.get("old_span") or "", edit.get("new_span") or ""),
            }
    state["prepared"] = prepared
    state["ready"] = bool(state.get("live_text"))
    if not state["ready"]:
        state["message"] = "Drift needs an approved pricing disclaimer to watch."
    elif state.get("verbatim_to_legal"):
        state["message"] = "Sent to Legal. Cosmetic change inside Legal wording."
        state["cosmetic_summary"] = "Sent to Legal. Cosmetic change inside Legal wording."
    elif state.get("material") and not state.get("sent"):
        state["message"] = "Source changed. The approved version stays live until Legal accepts a new one."
    elif state.get("sent"):
        state["message"] = "Sent to Legal. The approved version stays live."
    elif state.get("cosmetic"):
        state["message"] = "Cosmetic edit logged, nothing flagged"
    else:
        state["message"] = "Cached mode knows two prepared edits: a cosmetic comma, and 30-day supply to 31-day supply."
    return _ok(state)


def legal_drift_view(conn) -> dict:
    """Material drift fixes waiting for Legal. These stay out of the unit queue.

    A cosmetic edit inside a verbatim span is listed under automatic. The
    approved wording stays live until Legal acts on a material fix.
    """
    items = legal_drift_items(conn)
    automatic = []
    for row in conn.execute(
        "SELECT id, unit_id, version, old_span, new_span, summary FROM drift_log WHERE status = 'system_escalated' ORDER BY id"
    ):
        automatic.append({
            "id": row["id"],
            "unit_id": row["unit_id"],
            "version": row["version"],
            "actor": "System",
            "automatic": True,
            "source_before": row["old_span"] or "",
            "source_after": row["new_span"] or "",
            "summary": row["summary"] or "",
        })
    return _ok({
        "count": len(items),
        "items": items,
        "automatic": automatic,
        "message": "" if items else "No drift fix is waiting for Legal.",
    })


def quality_view(conn, *, scored: bool | None = None) -> dict:
    from src.finish import decorate_quality, guided_score_connection

    from src.engine import mode_name

    guided = mode_name(conn) != "explore"
    scoring = guided_score_connection() if guided else conn
    opened = scoring if guided else None
    done = True if guided else (flag(conn, "scored") if scored is None else scored)
    if not done:
        return _ok({
            "scored": False,
            "message": "Score the golden set and the duplicate variants with the saved model answers.",
        })
    report = quality_report(scoring)
    held_counts = _held_out_counts(report)
    open_plans = [
        {"id": plan.get("id") or "", "label": plan.get("label") or ""}
        for plan in open_conflicts(conn)
    ]
    report = dict(report)
    report["scored"] = True
    report["held_out_pass"] = held_counts["pass"]
    report["held_out_total"] = held_counts["total"]
    report["open_conflicts"] = open_plans
    report["message"] = (
        f"Held-out questions {held_counts['pass']} of {held_counts['total']} pass. "
        f"{len(open_plans)} open conflicts blocked for Legal. "
        f"{len(report['misses'])} model misses kept visible."
    )
    report["frozen"] = guided
    try:
        return _ok(decorate_quality(scoring, report, explore=not guided))
    finally:
        if opened is not None:
            opened.close()


def feedback_author_view(conn) -> dict:
    return _ok({"groups": feedback_for_author(conn)})


def feedback_product_view(conn) -> dict:
    groups = product_backlog(conn)
    total = sum(group["count"] for group in groups)
    return _ok({"total": total, "groups": groups, "message": "" if groups else "Nothing open."})


def feedback_open_view(conn, route: str) -> dict:
    if route not in ("author", "product"):
        raise APIError("route must be author or product.")
    rows = conn.execute(
        "SELECT * FROM feedback WHERE route = ? AND status = 'open' ORDER BY id DESC",
        (route,),
    ).fetchall()
    return _ok({"route": route, "count": len(rows), "items": [feedback_dict(row) for row in rows]})


def feedback_summary_view(conn) -> dict:
    summary = feedback_summary(conn)
    summary = dict(summary)
    for item in summary.get("by_kind") or []:
        item["label"] = kind_label(item.get("kind") or "")
    return _ok(summary)


def activity_view(conn, limit: int) -> dict:
    limit = max(1, min(int(limit or 12), 100))
    return _ok({"events": [activity_dict(row) for row in activity(conn, limit)]})


def calls_view(role: str) -> dict:
    calls = CALLS.get(role)
    if not calls:
        raise APIError("That role has no agent desktop.")
    items = []
    for reason, call in calls.items():
        items.append({"reason": reason, **call, "fictional": True})
    return _ok({"role": role, "knowledge_bases": list(ROLE_KB.get(role) or []), "calls": items})


def questions_view(role: str) -> dict:
    return _ok({"role": role, "questions": list(QUESTION_BANK.get(role) or [])})


def scope_view(role: str) -> dict:
    if role not in ROLE_KB and role not in ROLE_PAGES:
        raise APIError("Unknown role.")
    return _ok({"role": role, "knowledge_bases": list(ROLE_KB.get(role) or []), "pages": list(ROLE_PAGES.get(role) or [])})


def _topic_row(conn, topic: dict):
    unit_id = anchor(conn, topic["anchor"]) if topic.get("anchor") else topic.get("unit_id")
    return live_approved(conn, unit_id) if unit_id else None


def member_topics_view(conn) -> dict:
    topics = []
    for index, topic in enumerate(MEMBER_TOPICS):
        row = _topic_row(conn, topic)
        member_text = (row["member_text"] or "").strip() if row is not None else ""
        topics.append({
            "index": index,
            "label": topic["label"],
            "question": topic["question"],
            "available": bool(member_text),
            "member_text": member_text,
            "citation": (
                f"Source: Harbor Health, {plain_title(row['title'])}, version {row['version']}"
                if row is not None and member_text
                else ""
            ),
            "version": row["version"] if row is not None else None,
            "effective_date": (row["effective_date"] or row["approved_on"] or "")[:10] if row is not None else "",
            "slug": topic["label"].lower().replace(" ", "-"),
            "phone_reading": member_text or "I do not have an approved answer for that. Please hold while I connect you with a member advocate.",
        })
    from api.plan_data import ivr_prompt_map

    return _ok({
        "topics": topics,
        "ivr_prompts": ivr_prompt_map(conn),
        "message": "The same approved member wording is used by the app, the website, and the phone line.",
    })


def closest_topics(conn, question: str) -> list[int]:
    words = {word.strip("?.,!").lower() for word in (question or "").split()} - _STOP
    words |= {_SAME[word] for word in list(words) if word in _SAME}
    scored = []
    for index, topic in enumerate(MEMBER_TOPICS):
        row = _topic_row(conn, topic)
        text = f"{topic['label']} {topic['question']} {(row['member_text'] if row is not None else '')}".lower()
        overlap = sum(1 for word in words if word and word in text)
        if overlap:
            scored.append((-overlap, index))
    scored.sort()
    return [index for _overlap, index in scored[:2]]


def my_work_view(conn) -> dict:
    """Knowledge Ops work in Explore: documents, drafts, source changes, and Legal returns.

    Advocate and channel flags stay in the feedback table and on Insights.
    """
    from src.sandbox import KO_WORK_GROUPS, author_documents, author_drift_payload

    items = []
    for doc in author_documents(conn, include_all=False):
        if not doc["waiting_for_ko"]:
            continue
        items.append({
            "group": "Documents to review",
            "id": f"doc-{doc['doc_id']}",
            "title": doc["title"],
            "kind": "document",
            "document": doc,
        })
    for gap in gaps(conn):
        if gap["status"] == "in_review" and not (gap["unit_id"] or "").strip():
            items.append({
                "group": "Unanswered questions",
                "id": f"gap-{gap['id']}",
                "title": gap["draft_title"] or gap["cluster"],
                "kind": "gap",
                "gap": gap_dict(gap),
            })
    for drift in author_drift_payload(conn)["items"]:
        items.append({
            "group": "Source changes",
            "id": f"drift-{drift['id']}",
            "title": drift["summary"] or drift["unit_id"],
            "kind": "drift",
            "drift": drift,
        })
    for row in conn.execute(
        "SELECT * FROM units WHERE status = 'returned' AND version = 1 ORDER BY unit_id"
    ).fetchall():
        items.append({
            "group": "Sent back by Legal",
            "id": f"ret-{row['unit_id']}",
            "title": row["title"],
            "kind": "returned",
            "unit": unit_dict(row),
        })
    grouped = []
    empty = []
    for group in KO_WORK_GROUPS:
        members = [item for item in items if item["group"] == group]
        if members:
            grouped.append({"group": group, "count": len(members), "items": members})
        else:
            empty.append(group)
    waiting = [{"id": plan.get("id") or "", "label": plan.get("label") or ""} for plan in open_conflicts(conn)]
    return _ok({
        "count": len(items),
        "items": items,
        "groups": grouped,
        "empty_groups": empty,
        "waiting_on_legal": waiting,
        "message": "" if items else "Nothing needs you right now.",
    })


def _held_out_counts(report: dict) -> dict:
    """Held-out pass rate. A row with no saved answer is not scored."""
    held = report["golden_table"]["held_out"]
    scored = [row for row in held if row["Result"] != "No saved answer"]
    return {
        "pass": sum(1 for row in scored if row["Result"] == "Pass"),
        "total": len(scored),
        "not_scored": sum(1 for row in held if row["Result"] == "No saved answer"),
    }


def insights_view(conn) -> dict:
    rows = [gap_dict(row) for row in gaps(conn)]
    content_gaps = [
        row
        for row in rows
        if row["status"] == "proposed" and row.get("kind") != "unclustered" and not row.get("findability")
    ]
    findability = [
        row
        for row in rows
        if row.get("findability") and row.get("kind") != "unclustered" and row["status"] not in ("dismissed", "closed")
    ]
    for row in rows:
        row["answered"] = _gap_answered(conn, row)
    new_questions = {"count": 0, "examples": []}
    for row in rows:
        if row.get("kind") == "unclustered":
            questions = list(row.get("queries") or [])
            new_questions = {"count": len(questions), "examples": questions[:5]}
            break
    state = drift_state(conn)
    expired = [unit_dict(row) for row in expired_units(conn)]
    from src.finish import decorate_quality, guided_score_connection

    from src.engine import mode_name

    guided = mode_name(conn) != "explore"
    score_conn = guided_score_connection() if guided else conn
    try:
        report = decorate_quality(score_conn, quality_report(score_conn), explore=not guided)
    finally:
        if guided:
            score_conn.close()
    held_counts = _held_out_counts(report)
    tiles = [tile for tile in report["tiles"] if tile["key"] in ("hit_at_1", "over_abstain", "leaks")]
    drift_waiting = 1 if state["material"] and not state["sent"] else 0
    return _ok({
        "open_gaps": len(content_gaps),
        "drift_waiting": drift_waiting,
        "expired_count": len(expired),
        "tiles": tiles,
        "score_counts": report["score_counts"],
        "not_scored": report["not_scored"],
        "held_out": {"pass": held_counts["pass"], "total": held_counts["total"], "not_scored": held_counts["not_scored"]},
        "top_gaps": content_gaps[:6],
        "findability_gaps": findability,
        "findability_count": len(findability),
        "process_gaps": [row for row in rows if row["status"] == "process_gap"],
        "new_questions": new_questions,
        "drift": {
            "material": state["material"],
            "sent": state["sent"],
            "waiting": bool(drift_waiting),
            "summary": state.get("summary") or "",
        },
        "expired_units": expired,
        "feedback": feedback_summary_view(conn),
        "wrapups": wrapup_summary(conn),
        "acknowledgements": acknowledgement_overview(conn),
        "message": "Illustrative, made-up data.",
    })


def _approved_day(value: str) -> str:
    text = (value or "").strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return text


def changes_payload(conn, role: str) -> dict:
    role = (role or "").strip()
    rows = revisions_for_role(conn, role)
    changes = []
    for row in rows:
        previous = previous_revision(conn, row["unit_id"], row["version"])
        previous_text = (previous["text"] or "") if previous is not None else ""
        previous_version = previous["version"] if previous is not None else row["version"] - 1
        changes.append({
            "unit_id": row["unit_id"],
            "title": wording_title(row["title"]),
            "type": row["type"],
            "version": row["version"],
            "previous_version": previous_version,
            "approved_on": _approved_day(row["approved_on"] or ""),
            "approved_by": row["approved_by"] or "",
            "text": row["text"] or "",
            "previous_text": previous_text,
            "diff": diff_parts(previous_text, row["text"] or ""),
            "acknowledged": is_acknowledged(conn, role, row["unit_id"], row["version"]),
        })
    pending = sum(1 for item in changes if not item["acknowledged"])
    return {"role": role, "pending": pending, "changes": changes}


def changes_view(conn, role: str) -> dict:
    try:
        payload = changes_payload(conn, role)
    except ValueError as exc:
        raise APIError(str(exc)) from exc
    return _ok(payload)


def wrapups_view(conn) -> dict:
    return _ok({
        "summary": wrapup_summary(conn),
        "items": list_wrapups(conn),
    })


def _pricing_row(conn):
    rows = conn.execute(
        "SELECT * FROM units WHERE status = 'approved' AND search_visible = 1 ORDER BY unit_id"
    ).fetchall()
    pricing = next((row for row in rows if "Pricing" in (row["title"] or "")), None)
    return pricing or (rows[0] if rows else None)


def portal_quick_view(conn) -> dict:
    row = _pricing_row(conn)
    sample = portal_unit(row, "member_chat") if row is not None else None
    unit_id = sample["unit_id"] if sample else "UNIT_ID"
    version = sample["version"] if sample else 1
    return _ok({
        "base": "/api/portal",
        "sample_request": f"GET /api/portal/units/{unit_id}?channel=member_chat",
        "sample_unit": sample,
        "sample_event": {
            "event": "unit.revised",
            "unit_id": unit_id,
            "version": (version + 1) if sample else 2,
            "previous_version": version if sample else 1,
        },
        "endpoints": [
            {"method": "GET", "path": "/api/portal/units/{unit_id}?channel=", "what": "One approved unit, with the text for that channel, version, and citation."},
            {"method": "GET", "path": "/api/portal/units?knowledge_base=&channel=", "what": "Approved units a channel may render."},
            {"method": "GET", "path": "/api/portal/answers?question=&role=", "what": "One cited unit, or an explicit no-answer."},
            {"method": "GET", "path": "/api/units/{unit_id}/as-of?timestamp=", "what": "The version that was live at a given time."},
            {"method": "GET", "path": "/api/portal/events", "what": "unit.revised, unit.retired, and unit.flagged events from this database."},
        ],
    })


def portal_units_view(conn, knowledge_base: str = "", channel: str = "") -> dict:
    rows = conn.execute(
        "SELECT * FROM units WHERE status = 'approved' AND search_visible = 1 ORDER BY unit_id"
    ).fetchall()
    items = []
    for row in rows:
        if knowledge_base and knowledge_base not in split_csv(row["kb_scope"]):
            continue
        if channel and channel not in split_csv(row["channels"]):
            continue
        items.append(portal_unit(row, channel))
    return _ok({"count": len(items), "units": items})


def portal_one_view(conn, unit_id: str, channel: str = "") -> dict:
    row = conn.execute(
        """
        SELECT * FROM units
        WHERE unit_id = ? AND status = 'approved'
        ORDER BY version DESC
        LIMIT 1
        """,
        (unit_id,),
    ).fetchone()
    if row is None:
        raise APIError(f"No approved unit {unit_id}.", 404)
    if channel:
        from src.finish import ALLOWED_CHANNELS

        if channel not in ALLOWED_CHANNELS:
            raise APIError("Unknown channel.", 400, allowed=list(ALLOWED_CHANNELS))
        if channel not in split_csv(row["channels"]):
            raise APIError(f"{unit_id} is not approved for {channel}.", 404)
    return _ok({"unit": portal_unit(row, channel)})


def portal_events_view(conn, cursor: str = "") -> dict:
    from src.engine import list_events

    events = []
    seen = set()
    for row in list_events(conn):
        item = {
            "event_id": row["event_id"] if "event_id" in row.keys() else "",
            "event": row["event"],
            "unit_id": row["unit_id"],
            "version": row["version"],
            "previous_version": row["previous_version"],
            "ts": row["ts"],
            "occurred_at": row["occurred_at"] if "occurred_at" in row.keys() else row["ts"],
            "actor": row["actor"],
            "title": "",
        }
        events.append(item)
        seen.add((row["event"], row["unit_id"], row["version"]))
    for row in conn.execute(
        "SELECT unit_id, version, title, status, approved_on FROM units ORDER BY approved_on DESC"
    ).fetchall():
        if row["status"] == "approved" and row["version"] > 1:
            key = ("unit.revised", row["unit_id"], row["version"])
            if key not in seen:
                events.append({
                    "event": "unit.revised",
                    "unit_id": row["unit_id"],
                    "version": row["version"],
                    "previous_version": int(row["version"]) - 1,
                    "ts": row["approved_on"] or "",
                    "title": row["title"],
                })
        elif row["status"] == "retired":
            key = ("unit.retired", row["unit_id"], row["version"])
            if key not in seen:
                events.append({
                    "event": "unit.retired",
                    "unit_id": row["unit_id"],
                    "version": row["version"],
                    "previous_version": 0,
                    "ts": row["approved_on"] or "",
                    "title": row["title"],
                })
    flagged = conn.execute(
        "SELECT unit_id, version, title FROM units WHERE stale = 1"
    ).fetchall()
    for row in flagged:
        events.append({
            "event": "unit.flagged",
            "unit_id": row["unit_id"],
            "version": row["version"],
            "previous_version": 0,
            "ts": "",
            "title": row["title"],
        })
    start = 0
    if (cursor or "").strip().isdigit():
        start = int(cursor)
    page = events[start:start + 20]
    next_cursor = "" if start + 20 >= len(events) else str(start + 20)
    return _ok({
        "events": page,
        "cursor": str(start),
        "next_cursor": next_cursor,
        "message": "" if events else "No change events yet. Publish a revision, resolve a conflict, or apply a drift edit.",
    })


def key_configured() -> bool:
    return bool(resolve_api_key())


def env_has_key() -> bool:
    return bool((os.environ.get("ANTHROPIC_API_KEY") or "").strip())
