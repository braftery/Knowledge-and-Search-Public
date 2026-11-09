"""Developer portal for channel and AI feature teams (EXPERIENCE_SPEC.md section 7).

A mock documentation site. The prototype has no public API: the sample responses come from the sandbox's live
units, so what a team sees here matches what the channels render.
"""

from __future__ import annotations

import json

import streamlit as st

from src.components import callout, esc, muted, show

PORTAL_CSS = """
<style>
.docs-bar { background:#1A1A1A; color:#FFFFFF; padding:8px 14px; border-radius:6px; font-size:16px; font-weight:700; }
.step { font-size:18px; font-weight:700; margin:12px 0 4px 0; }
.endpoint { font-family: ui-monospace, Menlo, Consolas, monospace; font-size:16px; background:#F4F6F8; border:1px solid #C9CED4;
  border-radius:4px; padding:2px 6px; }
.event { border-left:4px solid #0B3A6A; padding:6px 10px; margin:6px 0; background:#FFFFFF; font-size:16px; }
</style>
"""

BASE = "https://api.harborhealth.example/v1"


def unit_payload(row) -> dict:
    keys = set(row.keys())
    return {
        "unit_id": row["unit_id"],
        "version": row["version"],
        "status": row["status"],
        "type": row["type"],
        "knowledge_base": row["kb_scope"],
        "applicability": row["applicability"] if "applicability" in keys else "",
        "effective_date": row["effective_date"] if "effective_date" in keys else "",
        "review_by": row["review_by"] if "review_by" in keys else "",
        "approved_by": row["approved_by"],
        "channels": [part.strip() for part in (row["channels"] or "").split(",") if part.strip()],
        "advocate_text": row["text"],
        "member_text": row["member_text"],
        "citation": f"Harbor Health, {row['title']}, version {row['version']}",
        "source": row["source_doc"],
    }


def _live_units(conn) -> list:
    return conn.execute(
        "SELECT * FROM units WHERE status = 'approved' AND search_visible = 1 ORDER BY unit_id"
    ).fetchall()


def page_quick_start(conn, role: str) -> None:
    show(PORTAL_CSS)
    show('<div class="docs-bar">Harbor Health Knowledge API · Developer portal</div>')
    callout(
        "<strong>Mock portal.</strong> The prototype has no public API. Every response below comes from the "
        "sandbox's approved units, so it matches what the channels render.",
        "neutral",
    )
    rows = _live_units(conn)
    pricing = next((row for row in rows if "Pricing" in row["title"]), rows[0] if rows else None)
    show('<p class="step">1. Request an approved unit for your channel</p>')
    unit_id = pricing["unit_id"] if pricing is not None else "UNIT_ID"
    st.code(
        f'curl -H "Authorization: Bearer YOUR_API_TOKEN" \\\n  "{BASE}/units/{unit_id}?channel=member_chat"',
        language="bash",
    )
    show('<p class="step">2. Render the text for your audience, with its citation</p>')
    muted("Use member_text in member channels and advocate_text in advocate tools. Show the citation. Never edit the text.")
    if pricing is not None:
        st.code(json.dumps(unit_payload(pricing), indent=2), language="json")
    show('<p class="step">3. Subscribe to changes</p>')
    muted("When Legal publishes a new version, you receive unit.revised. Fetch the unit again and replace the cached copy.")
    st.code(
        json.dumps(
            {"event": "unit.revised", "unit_id": unit_id, "version": 2, "previous_version": 1, "effective_date": "on publish"},
            indent=2,
        ),
        language="json",
    )


def page_api_reference(conn, role: str) -> None:
    show(PORTAL_CSS)
    show('<div class="docs-bar">API reference</div>')
    endpoints = [
        ("GET", "/units/{unit_id}?channel=", "One approved unit, with the text for that channel, version, and citation."),
        ("GET", "/units?knowledge_base=&channel=", "Approved units a channel may render. Scoped by knowledge base and audience."),
        ("GET", "/answers?question=&role=", "One cited unit for a question, or an explicit no-answer. Never generated text."),
        ("GET", "/units/{unit_id}/versions?as_of=", "The version that was live at a given time, for audits."),
        ("POST", "/webhooks", "Subscribe to unit.revised, unit.retired, and unit.flagged events."),
    ]
    for method, path, what in endpoints:
        show(f'<div class="event"><span class="endpoint">{method} {esc(path)}</span><br>{esc(what)}</div>')
    show('<h2 class="section-heading">Try it against the sandbox</h2>')
    rows = _live_units(conn)
    if not rows:
        callout("No approved unit yet.", "review")
        return
    labels = {row["unit_id"]: f"{row['title']} · {row['unit_id']}" for row in rows}
    picked = st.selectbox("Unit", list(labels), format_func=lambda unit_id: labels[unit_id], key="x-api-unit")
    row = next(item for item in rows if item["unit_id"] == picked)
    show(f'<span class="endpoint">GET {BASE}/units/{esc(picked)}</span>')
    st.code(json.dumps(unit_payload(row), indent=2), language="json")


def page_change_events(conn, role: str) -> None:
    show(PORTAL_CSS)
    show('<div class="docs-bar">Change events</div>')
    muted("What a subscribed channel would have received from this sandbox, newest first. Illustrative.")
    events = []
    for row in conn.execute("SELECT unit_id, version, title, status, approved_on FROM units ORDER BY approved_on DESC").fetchall():
        if row["status"] == "approved" and row["version"] > 1:
            events.append(("unit.revised", row))
        elif row["status"] == "retired":
            events.append(("unit.retired", row))
    flagged = conn.execute("SELECT unit_id, version, title, status, approved_on FROM units WHERE stale = 1").fetchall()
    events.extend(("unit.flagged", row) for row in flagged)
    if not events:
        callout(
            "No change events yet. Publish a revision as the Legal approver, resolve a conflict, or apply a drift edit "
            "as the Knowledge owner, then come back.",
            "neutral",
        )
        return
    for name, row in events[:20]:
        payload = {"event": name, "unit_id": row["unit_id"], "version": row["version"], "title": row["title"]}
        show(f'<div class="event"><strong>{esc(name)}</strong> · {esc(row["title"])} · version {esc(row["version"])}</div>')
        st.code(json.dumps(payload), language="json")
