"""JSON shapes for units, diffs, feedback, and portal payloads."""

from __future__ import annotations

import difflib
import json
import re

from src.engine import ROLE_KB, UNCLUSTERED_ID, bracketed_placeholders

from api.catalog import ILLUSTRATIVE, MEMBER_CHANNELS, doc_name, kind_label, plain_title

_WORDS = re.compile(r"\S+\s*")
_BOOLS = (
    "tags_confirmed",
    "search_visible",
    "stale",
    "requires_legal",
    "source_mismatch",
    "verbatim_altered",
    "flagged",
)


def as_dict(row) -> dict:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def split_csv(value) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def split_lines(value) -> list[str]:
    return [part.strip() for part in str(value or "").split("\n") if part.strip()]


def _chunks(old: str, new: str) -> list[tuple[str, str, str]]:
    """Word-level opcodes. Short equal runs between changes fold into the change."""
    left = _WORDS.findall(old or "")
    right = _WORDS.findall(new or "")
    raw = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=left, b=right, autojunk=False).get_opcodes():
        raw.append(("equal" if op == "equal" else "change", "".join(left[i1:i2]), "".join(right[j1:j2])))
    merged: list[list[str]] = []
    for index, (kind, old_text, new_text) in enumerate(raw):
        short_bridge = (
            kind == "equal"
            and len(old_text.split()) <= 2
            and 0 < index < len(raw) - 1
            and raw[index - 1][0] == "change"
            and raw[index + 1][0] == "change"
        )
        if short_bridge:
            kind = "change"
        if merged and merged[-1][0] == kind == "change":
            merged[-1][1] += old_text
            merged[-1][2] += new_text
        else:
            merged.append([kind, old_text, new_text])
    return [tuple(item) for item in merged]


def diff_parts(old: str, new: str) -> list[dict]:
    """Word diff the channel screens highlight. kind is equal, remove, or add."""
    parts = []
    for kind, old_text, new_text in _chunks(old, new):
        if kind == "equal":
            if old_text:
                parts.append({"kind": "equal", "text": old_text})
            continue
        if old_text.strip():
            parts.append({"kind": "remove", "text": old_text.strip()})
        if new_text.strip():
            parts.append({"kind": "add", "text": new_text.strip()})
    return parts


def unit_dict(row, *, preview: dict | None = None) -> dict:
    data = as_dict(row)
    if not data:
        return {}
    for key in _BOOLS:
        if key in data and data[key] is not None:
            data[key] = bool(data[key])
    data["tags"] = split_csv(data.get("tags"))
    data["kb_scope"] = split_csv(data.get("kb_scope"))
    data["audience"] = split_csv(data.get("audience"))
    data["channels"] = split_csv(data.get("channels"))
    data["document_name"] = doc_name(data.get("source_doc") or "")
    data["source_span"] = data.get("source_quote") or ""
    raw_sources = data.get("sources_json") or ""
    if isinstance(raw_sources, str) and raw_sources.strip():
        try:
            parsed = json.loads(raw_sources)
        except json.JSONDecodeError:
            parsed = []
        data["sources"] = parsed if isinstance(parsed, list) else []
    else:
        data["sources"] = []
    if preview is not None:
        data["if_you_approve"] = preview
    return data


def approval_preview(conn, row) -> dict:
    raw = as_dict(row)
    kbs = set(split_csv(raw.get("kb_scope")))
    audience = str(raw.get("audience") or "")
    readers = []
    for role in ("Pharmacy advocate", "Insurance advocate"):
        if kbs & set(ROLE_KB[role]):
            readers.append(role)
    if "member" in audience or "both" in audience:
        readers.append("Member chat")
    from src.ai import audience_list, load_human_decisions, override_channels

    override = (load_human_decisions().get("audience_overrides") or {}).get(raw.get("unit_id") or "")
    if isinstance(override, dict) and override:
        channels = override_channels(override, audience_list(override.get("audience") or "advocate"))
    else:
        channels = split_csv(raw.get("channels"))
    replaced = conn.execute(
        "SELECT unit_id, source_doc FROM units WHERE superseded_by = ? AND version = 1",
        (raw.get("unit_id"),),
    ).fetchall()
    docs = sorted({doc_name(item["source_doc"]) for item in replaced})
    if replaced:
        replaces = f"{len(replaced)} other wordings in {', '.join(docs)}"
    else:
        replaces = "No other wording"
    approver = "Legal approver" if raw.get("requires_legal") else "Knowledge Ops author"
    return {
        "searchable_by": readers,
        "appears_in": channels,
        "replaces": replaces,
        "approved_by": approver,
        "applies_to": raw.get("applicability") or "Not recorded",
    }


def placeholder_tokens(*chunks) -> list[str]:
    """Square-bracket tokens, in order, without duplicates.

    A placeholder can contain a comma, so this does not split on commas.
    """
    found = []
    seen = set()
    for chunk in chunks:
        for item in bracketed_placeholders(str(chunk or "")):
            if item in seen:
                continue
            seen.add(item)
            found.append(item)
    return found


def gap_dict(row) -> dict:
    data = as_dict(row)
    gap_id = str(data.get("id") or "")
    figures = split_csv(data.get("invented_figures"))
    return {
        "id": data.get("id"),
        "cluster": data.get("cluster") or "",
        "query_example": data.get("query_example") or "",
        "search_count": int(data.get("search_count") or 0),
        "roles": split_csv(data.get("roles")),
        "draft_title": data.get("draft_title") or "",
        "draft_text": data.get("draft_text") or "",
        "draft_member_text": data.get("draft_member_text") or "",
        "draft_type": data.get("draft_type") or "",
        "unit_id": data.get("unit_id") or "",
        "suggested_kb": data.get("draft_tags") or "",
        "status": data.get("status") or "",
        "placeholders": placeholder_tokens(
            data.get("placeholders"),
            data.get("draft_text"),
            data.get("draft_member_text"),
        ),
        "checklist": split_lines(data.get("checklist")),
        "queries": split_lines(data.get("queries")),
        "invented_figures": figures,
        "has_invented_figures": bool(figures),
        "live": gap_id.startswith("live-"),
        "findability": bool(data.get("findability")),
        "reason": data.get("reason") or "",
        "label": data.get("label") or "",
        "kind": "unclustered" if gap_id == UNCLUSTERED_ID else "cluster",
        "illustrative": True,
    }


def feedback_dict(row) -> dict:
    data = as_dict(row)
    raw = data.get("signals") or ""
    if isinstance(raw, dict):
        signals = raw
    else:
        try:
            signals = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            signals = {}
    if not isinstance(signals, dict):
        signals = {}
    kind = data.get("kind") or ""
    return {
        "id": data.get("id"),
        "ts": data.get("ts") or "",
        "source": data.get("source") or "",
        "role": data.get("role") or "",
        "kind": kind,
        "kind_label": kind_label(kind),
        "question": data.get("question") or "",
        "unit_id": data.get("unit_id") or "",
        "note": data.get("note") or "",
        "signals": signals,
        "route": data.get("route") or "",
        "status": data.get("status") or "",
        "resolution": data.get("resolution") or "",
        "resolved_on": data.get("resolved_on") or "",
    }


def _answer_status(result: dict) -> str:
    from src.finish import answer_status

    if result.get("transfer"):
        return "handoff"
    kind = "abstain" if result.get("abstained") else "answer"
    if result.get("status") in ("blocked_conflict", "transfer"):
        kind = "handoff"
    return answer_status(kind, abstained=bool(result.get("abstained")), ai_source=result.get("ai_source") or "")


def _citations(unit) -> list[dict]:
    if unit is None:
        return []
    data = as_dict(unit)
    if not data.get("unit_id"):
        return []
    return [{
        "unit_id": data.get("unit_id") or "",
        "version": data.get("version"),
        "title": data.get("title") or "",
        "approved_by": data.get("approved_by") or "",
        "approved_on": data.get("approved_on") or "",
    }]


def search_dict(result: dict) -> dict:
    unit = result.get("unit")
    ranked = [{"rank": rank, "unit_id": unit_id} for rank, unit_id in (result.get("ranked") or [])]
    payload = {
        "abstained": bool(result.get("abstained")),
        "unit": unit_dict(unit) if unit is not None else None,
        "ranked": ranked,
        "searched": list(result.get("searched") or []),
        "note": result.get("note") or "",
        "ai_source": result.get("ai_source") or "",
        "ai_caption": result.get("ai_caption") or "",
        "query": result.get("query") or "",
        "logged_query": result.get("logged_query") or "",
        "role": result.get("role") or "",
        "status": result.get("status") or "",
        "blocked_note": result.get("blocked_note") or "",
        "transfer_to": result.get("transfer_to") or "",
        "transfer": result.get("transfer") or None,
        "answer_status": _answer_status(result),
        "citations": _citations(unit),
        "fallback_unit": unit_dict(result.get("fallback_unit")) if result.get("fallback_unit") is not None else None,
        "illustrative": True,
    }
    if result.get("follow_up"):
        payload["follow_up"] = result["follow_up"]
    return payload


def portal_unit(row, channel: str = "") -> dict:
    raw = as_dict(row)
    channels = split_csv(raw.get("channels"))
    member_text = raw.get("member_text") or ""
    advocate_text = raw.get("text") or ""
    use_member = channel in MEMBER_CHANNELS
    payload = {
        "unit_id": raw.get("unit_id"),
        "version": raw.get("version"),
        "status": raw.get("status"),
        "type": raw.get("type"),
        "knowledge_base": split_csv(raw.get("kb_scope")),
        "applicability": raw.get("applicability") or "",
        "effective_date": raw.get("effective_date") or "",
        "review_by": raw.get("review_by") or "",
        "approved_by": raw.get("approved_by") or "",
        "approver_name": raw.get("approver_name") or "",
        "approval_method": raw.get("approval_method") or "",
        "channels": channels,
        "member_text": member_text,
        "text": member_text if use_member else advocate_text,
        "citation": f"Harbor Health, {plain_title(raw.get('title') or '')}, version {raw.get('version')}",
        "source": raw.get("source_doc") or "",
        "source_annotation": raw.get("source_annotation") or "",
        "title": raw.get("title") or "",
        "note": ILLUSTRATIVE,
    }
    if not use_member:
        payload["advocate_text"] = advocate_text
    if channel:
        payload["channel"] = channel
    return payload


def activity_dict(row) -> dict:
    data = as_dict(row)
    return {"ts": data.get("ts") or "", "role": data.get("role") or "", "message": data.get("message") or ""}
