"""Legal review inbox (EXPERIENCE_SPEC.md section 3).

Legal arrives from a notification, reviews one item per page with everything needed to decide, records a
decision, and moves straight to the next item. There is no library or browsing.
"""

from __future__ import annotations

import streamlit as st

from src.components import badge, callout, compute_preview, doc_name, esc, full_unit_card, muted, show, side_by_side
from src.corpus import load_corpus
from src.engine import approve_one, conflict_plans, decline_unit, open_conflicts, resolve_conflict, waiting_units

INBOX_CSS = """
<style>
.mail { border:1px solid #C9CED4; border-radius:8px; overflow:hidden; background:#FFFFFF; }
.mail .mail-bar { background:#F4F6F8; border-bottom:1px solid #C9CED4; padding:8px 14px; font-size:16px; color:#4A4F55; }
.mail .mail-head { padding:12px 16px 4px 16px; }
.mail .mail-head .subject { font-size:22px; font-weight:700; }
.mail .mail-head .from { font-size:16px; color:#4A4F55; }
.mail .mail-body { padding:4px 16px 14px 16px; font-size:17px; }
.review-head { display:flex; justify-content:space-between; align-items:baseline; gap:12px; }
.review-step { font-size:16px; color:#4A4F55; font-weight:700; }
</style>
"""


def _items(conn) -> list[dict]:
    """Everything waiting for Legal: unit approvals first, then conflicts."""
    items = []
    order = {"verbatim": 0, "policy": 1}
    for row in sorted(waiting_units(conn), key=lambda unit: (order.get(unit["type"], 2), unit["unit_id"])):
        items.append({"kind": "approval", "id": row["unit_id"], "title": row["title"], "row": row})
    open_ids = {plan.get("id") for plan in open_conflicts(conn)}
    for plan in conflict_plans():
        if plan.get("id") in open_ids:
            items.append({"kind": "conflict", "id": plan.get("id"), "title": f"Conflict: {plan.get('label')}", "plan": plan})
    return items


def page_legal_inbox(conn, role: str) -> None:
    show(INBOX_CSS)
    items = _items(conn)
    open_id = st.session_state.get("x-legal-open")
    current = next((item for item in items if item["id"] == open_id), None)
    if current is None:
        st.session_state["x-legal-open"] = None
        _notification(items)
        return
    _review(conn, items, current)


def _notification(items: list[dict]) -> None:
    done = st.session_state.get("x-legal-done", [])
    if done:
        callout(
            "<strong>Decisions recorded this session:</strong> " + esc("; ".join(done[-4:])),
            "approved",
        )
    approvals = [item for item in items if item["kind"] == "approval"]
    conflicts = [item for item in items if item["kind"] == "conflict"]
    if not items:
        show(
            """
            <div class="mail"><div class="mail-bar">Mail · Inbox</div>
            <div class="mail-head"><div class="subject">You are all caught up</div>
            <div class="from">Harbor Health Knowledge &lt;no-reply@harborhealth.example&gt;</div></div>
            <div class="mail-body">Nothing is waiting for Legal. Revisions and version lookups are in the menu.</div></div>
            """
        )
        return
    parts = []
    if approvals:
        parts.append(f"{len(approvals)} unit{'s' if len(approvals) != 1 else ''} to approve")
    if conflicts:
        parts.append(f"{len(conflicts)} conflict{'s' if len(conflicts) != 1 else ''} to resolve")
    subject = " and ".join(parts)
    lines = "".join(
        f"<li>{esc(item['title'])}</li>" for item in items
    )
    show(
        f"""
        <div class="mail"><div class="mail-bar">Mail · Inbox · 1 new message</div>
        <div class="mail-head"><div class="subject">Legal review: {esc(subject)}</div>
        <div class="from">Harbor Health Knowledge &lt;no-reply@harborhealth.example&gt; · to Legal approver</div></div>
        <div class="mail-body">These items need a Legal decision. Each one opens on a single review page with the wording,
        its source, and where it will appear.<ul style="margin:6px 0 0 0;">{lines}</ul></div></div>
        """
    )
    with st.container(horizontal=True, gap="small", key="x-legal-starts"):
        if st.button(f"Start review ({len(items)} items)", key="x-legal-start", type="primary"):
            st.session_state["x-legal-open"] = items[0]["id"]
            st.session_state["x-legal-total"] = len(items)
            st.rerun()
    with st.expander("Open one item directly"):
        for item in items:
            if st.button(item["title"], key=f"x-legal-item-{item['id']}", type="tertiary"):
                st.session_state["x-legal-open"] = item["id"]
                st.session_state["x-legal-total"] = len(items)
                st.rerun()
    muted("Fictional email from a made-up plan. In production, this arrives by email or Teams and opens the review page directly.")


def _advance(items: list[dict], current: dict, label: str) -> None:
    st.session_state.setdefault("x-legal-done", []).append(label)
    remaining = [item for item in items if item["id"] != current["id"]]
    st.session_state["x-legal-open"] = remaining[0]["id"] if remaining else None
    st.session_state.pop("x-legal-sendback", None)
    st.rerun()


def _review(conn, items: list[dict], current: dict) -> None:
    total = max(int(st.session_state.get("x-legal-total") or 0), len(items))
    st.session_state["x-legal-total"] = total
    position = (total - len(items)) + items.index(current) + 1
    if st.button("Back to inbox", key="x-legal-back", type="tertiary"):
        st.session_state["x-legal-open"] = None
        st.rerun()
    kind = "Approval" if current["kind"] == "approval" else "Conflict"
    show(
        f'<div class="review-head"><h2 class="section-heading">{esc(current["title"])}</h2>'
        f'<span class="review-step">{kind} · item {position} of {total}</span></div>'
    )
    if current["kind"] == "approval":
        _review_approval(conn, items, current)
    else:
        _review_conflict(conn, items, current)


def _review_approval(conn, items: list[dict], current: dict) -> None:
    row = current["row"]
    blocked = row["source_mismatch"] or row["verbatim_altered"]
    sending_back = st.session_state.get("x-legal-sendback") == current["id"]
    if not sending_back:
        with st.container(horizontal=True, gap="small", key="x-legal-decide"):
            approve = (not blocked) and st.button("Approve and publish", key="x-legal-approve", type="primary")
            send_back = st.button("Send back to the author", key="x-legal-return")
        if blocked:
            callout("<strong>This unit cannot be approved.</strong> Its wording differs from the source. Send it back.", "blocked")
        if approve:
            approve_one(conn, row["unit_id"])
            _advance(items, current, f"Approved {row['title']}")
        if send_back:
            st.session_state["x-legal-sendback"] = current["id"]
            st.rerun()
    else:
        reason = st.text_input("Why are you sending it back? (required, shared with the author)", key=f"x-legal-why-{current['id']}")
        if st.session_state.get("x-legal-why-error"):
            show('<p class="field-error" role="alert">Add a reason so the author knows what to change.</p>')
        with st.container(horizontal=True, gap="small", key="x-legal-confirm"):
            confirm = st.button("Send back", key="x-legal-confirm-back", type="primary")
            cancel = st.button("Cancel", key="x-legal-cancel", type="tertiary")
        if cancel:
            st.session_state.pop("x-legal-sendback", None)
            st.session_state["x-legal-why-error"] = False
            st.rerun()
        if confirm:
            if not reason.strip():
                st.session_state["x-legal-why-error"] = True
                st.rerun()
            st.session_state["x-legal-why-error"] = False
            decline_unit(conn, row["unit_id"], reason.strip())
            _advance(items, current, f"Sent back {row['title']}")
    full_unit_card(conn, row, compute_preview(conn, row))


def _review_conflict(conn, items: list[dict], current: dict) -> None:
    plan = current["plan"]
    corpus = load_corpus()
    chosen = plan.get("chosen_unit_id") or ""
    kept = corpus["by_id"].get(chosen) or {}
    kept_doc = doc_name(kept.get("source_doc", ""))
    reason_key = f"x-legal-conflict-{plan.get('id')}"
    reason = st.text_input("Reason for your decision (required, saved with the record)", key=reason_key)
    if st.session_state.get("x-legal-conflict-error"):
        show('<p class="field-error" role="alert">Add a reason. It is saved with the decision for audits.</p>')
    if st.button(f"Keep the {kept_doc} wording and retire the other", key="x-legal-resolve", type="primary"):
        if not reason.strip():
            st.session_state["x-legal-conflict-error"] = True
            st.rerun()
        st.session_state["x-legal-conflict-error"] = False
        resolve_conflict(conn, reason, plan.get("id"))
        _advance(items, current, f"Resolved {plan.get('label')}")
    callout(
        "<strong>AI found two versions that cannot both be true.</strong> Both stay blocked from approval and search "
        "until you decide. The other version is retired when you keep one.",
        "blocked",
    )
    for other_id in plan.get("retire_unit_ids") or []:
        other = corpus["by_id"].get(other_id) or {}
        judgment = next(
            (item for item in corpus["judgments"] if {item["a_id"], item["b_id"]} == {chosen, other_id}),
            None,
        )
        reason_ai = (judgment or {}).get("output", {}).get("reason", "")
        left_html, right_html = side_by_side(kept.get("text", ""), other.get("text", ""))
        show(f'<div class="meta"><strong>AI reason:</strong> {esc(reason_ai)}</div>')
        keep_col, retire_col = st.columns(2)
        with keep_col:
            show(
                f'<div class="card"><div class="card-title">{esc(kept_doc)}</div>'
                f'<div>{badge("Kept if you decide", "approved")}</div><div class="unit-text">{left_html}</div></div>'
            )
        with retire_col:
            show(
                f'<div class="card"><div class="card-title">{esc(doc_name(other.get("source_doc", "")))}</div>'
                f'<div>{badge("Retired if you decide", "blocked")}</div><div class="unit-text">{right_html}</div></div>'
            )
