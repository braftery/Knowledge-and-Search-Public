"""Feedback capture and routing in the UI (SPEC.md section 5, step 8).

Advocates flag answers in one tap. Channels flag themselves when they clarify, hand off, or get "this did not help".
Content issues reach the Knowledge Ops author. Findability and product issues reach the product backlog.
Every question and note is redacted by the engine before it is stored.
"""

from __future__ import annotations

import json

import streamlit as st

from src.components import badge, callout, esc, muted, show
from src.engine import product_backlog, record_feedback, resolve_feedback

KIND_LABELS = {
    "couldnt_find": "Could not find it",
    "hard_to_find": "Hard to find",
    "confusing_wording": "Wording confused the member",
    "wrong_or_outdated": "Looks wrong or out of date",
    "no_answer": "No approved answer",
    "not_helpful": "Member said it did not help",
    "clarified": "Bot had to ask a clarifying question",
    "handed_off": "Bot handed off to a person",
    "rephrased": "Member rephrased the question",
    "slow": "Slow to answer",
}

ADVOCATE_KINDS = ["couldnt_find", "hard_to_find", "confusing_wording", "wrong_or_outdated"]


def label(kind: str) -> str:
    return KIND_LABELS.get(kind, kind.replace("_", " ").capitalize())


def record_once(conn, key: str, **fields) -> None:
    """Automatic signals are recorded once per visit, so reruns never double count."""
    seen = st.session_state.setdefault("x-feedback-seen", set())
    if key in seen:
        return
    seen.add(key)
    record_feedback(
        conn,
        fields.get("source", "channel"),
        fields.get("role", ""),
        fields["kind"],
        fields.get("question", ""),
        fields.get("unit_id") or "",
        fields.get("note", ""),
        fields.get("signals") or {},
    )


def flag_control(conn, role: str, question: str, unit_id: str, key: str) -> None:
    """One-tap flag for an advocate, with an optional note."""
    with st.popover("Flag this answer", width="content"):
        kind = st.radio(
            "What went wrong?",
            ADVOCATE_KINDS,
            format_func=label,
            key=f"x-flag-kind-{key}",
        )
        note = st.text_input("Note (optional)", key=f"x-flag-note-{key}", placeholder="For example: took three searches…")
        if st.button("Send to the knowledge team", key=f"x-flag-send-{key}", type="primary"):
            searches = int(st.session_state.get(f"x-searches-{role}", 0))
            record_feedback(conn, "advocate", role, kind, question, unit_id or "", note, {"searches_in_call": searches})
            st.toast("Flag sent. Member details are removed before it is stored.")


def open_feedback(conn, route: str) -> list:
    return conn.execute(
        "SELECT * FROM feedback WHERE route = ? AND status = 'open' ORDER BY id DESC",
        (route,),
    ).fetchall()


def feedback_card(row) -> None:
    signals = {}
    try:
        signals = json.loads(row["signals"] or "{}") if isinstance(row["signals"], str) else (row["signals"] or {})
    except (TypeError, ValueError):
        signals = {}
    bits = []
    if signals.get("searches_in_call"):
        bits.append(f"{signals['searches_in_call']} searches in the call")
    if signals.get("seconds_to_answer"):
        bits.append(f"{signals['seconds_to_answer']} seconds to answer")
    source = "Advocate" if row["source"] == "advocate" else "Channel"
    show(
        f'<div class="card"><div class="card-head"><div class="card-title">{esc(label(row["kind"]))}</div>'
        f'<div>{badge(source + ": " + (row["role"] or "unknown"), "neutral")}</div></div>'
        f'<div class="unit-text">"{esc(row["question"] or "No question recorded")}"</div>'
        f'<div class="meta">{esc(row["note"] or "")}'
        f'{" · " + esc(", ".join(bits)) if bits else ""}'
        f'{" · unit " + esc(row["unit_id"]) if row["unit_id"] else ""} · {esc(row["ts"])}</div></div>'
    )


def resolve_control(conn, row, key: str, placeholder: str) -> bool:
    note = st.text_input("Resolution (required)", key=f"x-res-{key}", placeholder=placeholder)
    if st.button("Resolve", key=f"x-res-go-{key}", type="primary"):
        if not note.strip():
            show('<p class="field-error" role="alert">Add a resolution note. It is saved with the record.</p>')
            return False
        resolve_feedback(conn, row["id"], note)
        st.toast("Resolved.")
        return True
    return False


def page_product_backlog(conn, role: str) -> None:
    """Findability and product issues for the dev team."""
    from src.insights import INSIGHTS_CSS

    show(INSIGHTS_CSS)
    groups = product_backlog(conn)
    total = sum(group["count"] for group in groups)
    muted(
        "Captured from advocates and channels: questions that were hard to find, slow, rephrased, clarified, or "
        "handed off. Member details are removed before storage. Illustrative, made-up data."
    )
    if not groups:
        callout("<strong>Nothing open.</strong> New findability and product issues appear here as they are captured.", "approved")
        return
    show(f'<h2 class="section-heading">{total} open issues, by kind</h2>')
    top = max(group["count"] for group in groups)
    for group in groups:
        width = max(6, int(100 * group["count"] / top))
        examples = "; ".join(f'"{example}"' for example in group["examples"])
        show(
            f'<div class="rank"><div>{esc(label(group["kind"]))}<div class="sub">{esc(examples)}</div></div>'
            f'<div class="bar-bg"><div class="bar" style="width:{width}%"></div></div>'
            f'<div class="count">{esc(group["count"])}</div></div>'
        )
    rows = open_feedback(conn, "product")
    show('<h2 class="section-heading">Work an issue</h2>')
    ids = [row["id"] for row in rows]
    signature = "-".join(str(fid) for fid in ids)
    picked = st.selectbox(
        "Issue",
        ids,
        index=0,
        format_func=lambda fid: next(f"{label(r['kind'])}: {r['question'] or 'no question'}" for r in rows if r["id"] == fid),
        key=f"x-backlog-pick-{signature}",
    )
    row = next(item for item in rows if item["id"] == picked)
    feedback_card(row)
    if resolve_control(conn, row, f"backlog-{row['id']}", "For example: added a synonym so the first search finds it…"):
        st.rerun()


def insights_panel(conn) -> None:
    from src.engine import feedback_summary

    summary = feedback_summary(conn)
    kinds = summary.get("by_kind") or []
    show('<h2 class="section-heading">What advocates and channels flagged this week</h2>')
    if not kinds:
        muted("Nothing flagged this week.")
        return
    top = max(item["count"] for item in kinds)
    for item in kinds[:6]:
        width = max(6, int(100 * item["count"] / top))
        show(
            f'<div class="rank"><div>{esc(label(item["kind"]))}</div>'
            f'<div class="bar-bg"><div class="bar" style="width:{width}%"></div></div>'
            f'<div class="count">{esc(item["count"])}</div></div>'
        )
    flagged = summary.get("most_flagged") or []
    if flagged:
        names = "; ".join(f'{item["unit_id"]} ({item["count"]})' for item in flagged[:3])
        muted(f"Most-flagged units: {names}. Illustrative.")
