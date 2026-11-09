"""Single Source Studio: the Knowledge Ops author's "My work" landing page (EXPERIENCE_SPEC.md section 2).

Sign-in lands here. The page shows what needs the author now, grouped and counted, and opens the first item
without a click. Layout: the queue on the left, the item in the center, and its source passage on the right.
"""

from __future__ import annotations

import streamlit as st

from src.components import badge, callout, diff_html, doc_name, esc, muted, show, unit_card
from src.engine import (
    activity,
    all_units,
    approve_by_author,
    author_queue,
    document_body,
    gaps,
    open_conflicts,
)

STUDIO_CSS = """
<style>
.q-group { font-size:16px; font-weight:700; color:#4A4F55; margin:10px 0 2px 0; text-transform:uppercase; letter-spacing:.04em; }
.q-empty { font-size:16px; color:#4A4F55; margin:0 0 6px 0; }
.src-pane { border:1px solid #C9CED4; border-radius:6px; padding:10px 12px; font-size:16px; line-height:1.5;
  max-height:520px; overflow:auto; background:#FFFFFF; }
.src-pane mark { background:#FFF3BF; padding:0 2px; }
[class*="st-key-x-work-"] .stButton > button { height:auto !important; min-height:44px; white-space:normal !important; text-align:left; }
[class*="st-key-x-work-"] .stButton > button p { white-space:normal !important; text-align:left; }
</style>
"""


def _work(conn) -> list[dict]:
    """Every item that needs the author, in the order they should be worked."""
    items = []
    queue = list(author_queue(conn))
    for row in queue:
        if row["status"] == "returned":
            items.append({"group": "Sent back by Legal", "id": f"ret-{row['unit_id']}", "title": row["title"], "row": row, "kind": "returned"})
    for row in queue:
        if row["status"] != "returned":
            items.append({"group": "Waiting for your approval", "id": f"app-{row['unit_id']}", "title": row["title"], "row": row, "kind": "approve"})
    unconfirmed = conn.execute(
        "SELECT * FROM units WHERE tags_confirmed = 0 AND version = 1 AND status = 'proposed' ORDER BY unit_id"
    ).fetchall()
    for row in unconfirmed:
        items.append({"group": "New extractions to confirm", "id": f"new-{row['unit_id']}", "title": row["title"], "row": row, "kind": "confirm"})
    for row in conn.execute("SELECT * FROM units WHERE stale = 1 AND status = 'approved' ORDER BY unit_id").fetchall():
        items.append({"group": "Source changed", "id": f"drift-{row['unit_id']}", "title": row["title"], "row": row, "kind": "drift"})
    from src.feedback_ui import label as feedback_label, open_feedback

    for row in open_feedback(conn, "author"):
        items.append({"group": "Flagged by advocates and channels", "id": f"fb-{row['id']}",
                      "title": f"{feedback_label(row['kind'])}: {row['question'] or 'no question'}", "fb": row, "kind": "feedback",
                      "row": current_for(conn, row["unit_id"])})
    for gap in gaps(conn):
        if gap["status"] == "in_review":
            items.append({"group": "Drafts assigned to you", "id": f"gap-{gap['id']}", "title": gap["draft_title"] or gap["cluster"], "gap": gap, "kind": "gap"})
    return items


def current_for(conn, unit_id: str):
    if not unit_id:
        return None
    return conn.execute(
        "SELECT * FROM units WHERE unit_id = ? ORDER BY version DESC LIMIT 1", (unit_id,)
    ).fetchone()


GROUPS = ["Sent back by Legal", "Waiting for your approval", "Flagged by advocates and channels", "New extractions to confirm", "Source changed", "Drafts assigned to you"]


def page_my_work(conn, role: str, go_library) -> None:
    show(STUDIO_CSS)
    items = _work(conn)
    _search_box(conn, go_library)
    if not items:
        callout(
            "<strong>Nothing needs you right now.</strong> New work appears here when a document is extracted, "
            "Legal sends a unit back, a source changes, or the Knowledge owner assigns a draft.",
            "approved",
        )
        _waiting_on_others(conn)
        return
    ids = [item["id"] for item in items]
    seen = st.session_state.get("x-work-seen")
    arrived = [item_id for item_id in ids if seen is not None and item_id not in seen]
    st.session_state["x-work-seen"] = set(ids)
    if arrived:
        # New work takes focus, highest priority first (the items list is already in priority order).
        st.session_state["x-work-open"] = arrived[0]
    elif st.session_state.get("x-work-open") not in ids:
        st.session_state["x-work-open"] = ids[0]
    current = next(item for item in items if item["id"] == st.session_state["x-work-open"])
    queue, center, source = st.columns([0.95, 1.6, 1.15], gap="medium")
    with queue:
        empty = []
        for group in GROUPS:
            members = [item for item in items if item["group"] == group]
            if not members:
                empty.append(group.lower())
                continue
            show(f'<p class="q-group">{esc(group)} ({len(members)})</p>')
            for item in members:
                label = ("Now: " if item["id"] == current["id"] else "") + item["title"]
                st.button(label, key=f"x-work-{item['id']}", on_click=_open, args=(item["id"],), width="stretch",
                          type="primary" if item["id"] == current["id"] else "secondary")
        if empty:
            show(f'<p class="q-empty">Nothing waiting in: {esc(", ".join(empty))}. New items arrive here as soon as they exist.</p>')
        _waiting_on_others(conn)
    with center:
        _item(conn, current, items)
    with source:
        _source(conn, current)


def _open(item_id: str) -> None:
    st.session_state["x-work-open"] = item_id


def _next_after(items: list[dict], current: dict) -> None:
    remaining = [item for item in items if item["id"] != current["id"]]
    st.session_state["x-work-open"] = remaining[0]["id"] if remaining else None


def _item(conn, current: dict, items: list[dict]) -> None:
    kind = current["kind"]
    show(f'<p class="q-group">{esc(current["group"])}</p>')
    if kind == "approve":
        row = current["row"]
        if st.button("Approve", key="x-work-approve", type="primary"):
            approve_by_author(conn, row["unit_id"])
            st.toast(f"Approved {row['title']}.")
            _next_after(items, current)
            st.rerun()
        muted("Procedure and FAQ units do not need Legal. Your approval publishes it to search and its channels.")
        unit_card(row, "x-work-unit", details=False)
    elif kind == "returned":
        row = current["row"]
        reason = row["notes"] or _return_reason(conn, row["unit_id"])
        callout(f"<strong>Legal sent this back.</strong> Reason: {esc(reason or 'not recorded')}", "review")
        muted("Edit the wording in the source document, then extract it again for Legal to review.")
        unit_card(row, "x-work-ret", details=False)
    elif kind == "confirm":
        callout("AI extracted this unit. Confirm its tags and audience in Source documents.", "neutral")
        unit_card(current["row"], "x-work-new", details=False)
    elif kind == "drift":
        row = current["row"]
        callout(
            "<strong>Its source document changed.</strong> The approved version stays live. "
            "The AI's proposed update is waiting for Legal.",
            "review",
        )
        show(f'<div class="unit-text diff">{diff_html(row["text"], row["proposed_text"] or row["text"])}</div>')
    elif kind == "feedback":
        from src.feedback_ui import feedback_card, resolve_control

        feedback_card(current["fb"])
        if resolve_control(conn, current["fb"], f"author-{current['fb']['id']}", "For example: rewrote the member wording and sent it to Legal…"):
            _next_after(items, current)
            st.rerun()
        if current.get("row") is not None:
            muted("The flagged unit is shown on the right with its source.")
    elif kind == "gap":
        from src.screens import _draft_html

        gap = current["gap"]
        queries = [item for item in (gap["queries"] or "").split("\n") if item.strip()]
        show(
            f'<div class="meta">Asked {esc(gap["search_count"])} times: {esc("; ".join(queries[:3]))}</div>'
            f'<div class="card"><div class="card-head"><div class="card-title">{esc(gap["draft_title"])}</div>'
            f'<div>{badge("AI draft", "review")}</div></div><div class="unit-text">{_draft_html(gap["draft_text"])}</div></div>'
        )
        muted("Fill every bracketed placeholder from an approved source, then send the unit to Legal.")


def _return_reason(conn, unit_id: str) -> str:
    for row in activity(conn, limit=50):
        message = row["message"] or ""
        if message.startswith(f"Returned {unit_id} to the author."):
            return message.split("Reason:", 1)[-1].strip()
    return ""


def _source(conn, current: dict) -> None:
    show('<p class="q-group">Source</p>')
    row = current.get("row")
    if row is None:
        muted("No source passage for this item yet.")
        return
    body = esc(document_body(conn, row["source_doc"]))
    quote = esc(row["source_quote"] or "")
    if quote and quote in body:
        start = body.find(quote)
        body = body[max(0, start - 300):start] + f"<mark>{quote}</mark>" + body[start + len(quote):start + len(quote) + 300]
    lines = []
    for line in body.split("\n"):
        if line.startswith("## ") or line.startswith("# "):
            lines.append(f"<strong>{line.lstrip('# ')}</strong>")
        else:
            lines.append(line)
    show(f'<div class="meta">{esc(doc_name(row["source_doc"]))}</div><div class="src-pane">{"<br>".join(lines)}</div>')


def _waiting_on_others(conn) -> None:
    conflicts = open_conflicts(conn)
    if conflicts:
        names = ", ".join(plan.get("label", "") for plan in conflicts)
        show(f'<p class="q-group">Waiting on Legal ({len(conflicts)})</p><p class="q-empty">Conflicts: {esc(names)}</p>')


def _search_box(conn, go_library) -> None:
    query = st.text_input("Search all units", key="x-work-search", placeholder="For example: mail order…")
    if not query.strip():
        return
    needle = query.strip().lower()
    rows = [
        row for row in all_units(conn)
        if row["version"] == 1 and (needle in (row["text"] or "").lower() or needle in (row["title"] or "").lower())
    ]
    if not rows:
        muted("No unit contains those words.")
        return
    for row in rows[:6]:
        st.button(
            f"{row['title']} · {row['status'].replace('_', ' ')}",
            key=f"x-work-hit-{row['unit_id']}",
            on_click=go_library,
            args=(row["unit_id"],),
            type="tertiary",
        )
