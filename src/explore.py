"""Explore mode: a free-roaming sandbox, one workspace per user type.

The guided demo never calls this module, and this module never touches the demo's
database, undo state, or step number. Explore keeps its own database in
st.session_state.explore_db.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

from src.components import (
    agent_mockup,
    answer_card,
    badge,
    callout,
    compute_preview,
    diff_html,
    diff_legend,
    doc_name,
    esc,
    full_unit_card,
    member_mockup,
    metric_tile,
    muted,
    show,
    source_panel,
    status_badge,
    subheading,
    unit_card,
)
from src.corpus import load_corpus
from src.feedback_ui import page_product_backlog
from src.insights import page_insights
from src.legal_inbox import page_legal_inbox
from src.portal import page_api_reference, page_change_events, page_quick_start
from src.studio import page_my_work
from src.surfaces import page_agent_desktop, page_member_app, page_member_phone, page_member_website
from src.engine import (
    ABSTAIN_QUERY,
    COST_QUERY,
    MISSPELL_QUERY,
    ROLE_KB,
    act_on_gap,
    activity,
    all_units,
    anchor,
    apply_prepared_drift,
    approve_by_author,
    approve_one,
    author_queue,
    build_database,
    conflict_plans,
    connect,
    drift_state,
    expired_units,
    gaps,
    live_approved,
    open_conflicts,
    publish_revision,
    quality_report,
    resolve_conflict,
    search,
    send_drift_to_legal,
    set_live,
    units_as_of,
    waiting_units,
)

DEMO = "Guided demo"

ROLE_PAGES = {
    "Knowledge Ops author": ["My work", "Library", "Source documents", "Copies and conflicts"],
    "Legal approver": ["Review inbox", "Revise wording", "Version history"],
    "Pharmacy advocate": ["Agent desktop", "What I can read"],
    "Insurance advocate": ["Agent desktop", "What I can read"],
    "Member": ["App chat", "Website", "Phone line"],
    "Knowledge owner": ["Insights", "Gaps", "Drift", "Quality"],
    "Channel and AI team": ["Quick start", "API reference", "Change events", "Product backlog"],
}

ROLE_INTRO = {
    "Knowledge Ops author": "Your workspace opens on what needs you now, with the first item already open.",
    "Legal approver": "A notification brings you here. Each item opens on one page with everything you need to decide.",
    "Pharmacy advocate": "You are on a live call. The knowledge panel already shows the approved answer for the call reason.",
    "Insurance advocate": "You are on a live call. The knowledge panel already shows the approved answer for the call reason.",
    "Member": "You never see the knowledge system. You see Harbor Health's app, website, and phone line, all saying the same thing.",
    "Knowledge owner": "Your weekly view: what people could not find, what changed, and how well retrieval works.",
    "Channel and AI team": "You build channels and AI features. You render approved units by reference through the API.",
}

QUESTION_BANK = {
    "Pharmacy advocate": [
        COST_QUERY,
        MISSPELL_QUERY,
        ABSTAIN_QUERY,
        "Do specialty drugs stay at the specialty pharmacy?",
        "When can I offer 90-day mail order for a maintenance drug?",
        "formulary tier, can I quote a price before I verify the member?",
        "What closing line do I read at the end of an Rx education call?",
        "Can I talk about the drug and the price when a caregiver has no authorization on the account?",
    ],
    "Insurance advocate": [
        COST_QUERY,
        "What do I say before I quote a medical cost?",
        "Does a specialist visit on a Harbor Medicare Advantage HMO need a referral?",
        "What is the MOOP for this MA plan?",
        "Do specialty drugs stay at the specialty pharmacy?",
        "What closing line do I read at the end of an Rx education call?",
    ],
    "Member": [
        "How much will my prescription cost?",
        "Is the price I see a guarantee?",
        "Does my specialist visit need a referral?",
        "Do specialty drugs go through mail order?",
    ],
}

LIVE_CAP = 20


# ---------------------------------------------------------------- state


def explore_options() -> list[str]:
    return [DEMO] + [f"Explore as {role}" for role in ROLE_PAGES]


def view_label(view: str) -> str:
    """Short labels so the closed dropdown is not clipped."""
    return view if view == DEMO else view.replace("Explore as ", "", 1)


def view_changed() -> None:
    """A new role always opens on its own first page, never on a page left over from another role."""
    st.session_state["x-page"] = None


def role_from_view(view: str) -> str | None:
    if not view or view == DEMO:
        return None
    return view.replace("Explore as ", "", 1)


def _fresh_world() -> None:
    folder = Path("/tmp/harbor-demo")
    folder.mkdir(exist_ok=True)
    path = folder / f"explore-{uuid.uuid4().hex}.sqlite"
    build_database(str(path), mode="explore" if _has_explore_mode() else "jump")
    conn = connect(str(path))
    set_live(conn, True)
    conn.close()
    st.session_state.explore_db = str(path)
    st.session_state.explore_live_calls = 0
    for key in list(st.session_state.keys()):
        if str(key).startswith("x-"):
            st.session_state.pop(key, None)


def _has_explore_mode() -> bool:
    """Use the engine's explore start state when it exists. Until then, the approved demo state."""
    import inspect

    from src import engine

    return "explore" in inspect.getsource(engine.build_database)


def explore_conn():
    if not st.session_state.get("explore_db") or not Path(st.session_state.explore_db).exists():
        _fresh_world()
    return connect(st.session_state.explore_db)


def calls_left() -> int:
    return max(0, LIVE_CAP - int(st.session_state.get("explore_live_calls", 0)))


def ask(conn, role: str, query: str) -> dict:
    """Saved answer first. Only a question with no saved answer calls the model, within the visitor's cap."""
    from src.engine import log, redact_query

    set_live(conn, False)
    result = search(conn, role, query, record=False)
    if result.get("ai_source") == "missing" and calls_left() > 0:
        set_live(conn, True)
        with st.spinner("No saved answer. Asking the model…"):
            result = search(conn, role, query, record=False)
        set_live(conn, False)
        if result.get("ai_source") == "live":
            st.session_state.explore_live_calls = int(st.session_state.get("explore_live_calls", 0)) + 1
    if result.get("ai_source") in ("cached", "no_candidates"):
        search(conn, role, query, record=True)
    else:
        outcome = "no approved answer" if result.get("abstained") else f"{result['unit']['unit_id']}"
        log(conn, role, f"Search '{redact_query(query)}' returned {outcome}. Answer source: {result.get('ai_source')}.")
    return result


# ---------------------------------------------------------------- shell


def render_sidebar_explore(role: str) -> None:
    show(
        """
        <div class="brand">Harbor Health Knowledge</div>
        <p class="brand-note">Explore mode. Illustrative, made-up data.</p>
        <p class="side-heading">Your workspace</p>
        """
    )
    pages = ROLE_PAGES[role]
    current = st.session_state.get("x-page")
    if current not in pages:
        current = pages[0]
        st.session_state["x-page"] = current
    for index, page in enumerate(pages):
        suffix = "-current" if page == current else ""
        st.button(page, key=f"nav-x{index}{suffix}", on_click=_go_page, args=(page,), width="stretch")
    show('<p class="side-heading">Sandbox</p>')
    st.button("Reset the sandbox", key="x-reset", on_click=_fresh_world, width="stretch")
    left = calls_left()
    muted(
        f"Saved model answers are used first. A new question calls the model live. "
        f"Live calls left in this visit: {left} of {LIVE_CAP}."
    )


def _go_page(page: str) -> None:
    st.session_state["x-page"] = page


def render_explore(role: str) -> None:
    conn = explore_conn()
    page = st.session_state.get("x-page") or ROLE_PAGES[role][0]
    if page not in ROLE_PAGES[role]:
        page = ROLE_PAGES[role][0]
    show(
        f"""
        <div class="topline">
          <span class="persona">You are: {esc(role)}</span>
          <span class="chip">Explore mode</span>
          <span class="chip">{'Saved answers first, live AI for new questions' if calls_left() else 'Saved answers only (live limit reached)'}</span>
        </div>
        <h1 id="main-content" class="screen-title">{esc(page)}</h1>
        <p class="pain-caption">{esc(ROLE_INTRO[role])}</p>
        """
    )
    PAGES[page](conn, role)
    rows = list(activity(conn, limit=8))
    if rows:
        with st.expander("Sandbox activity"):
            for row in rows:
                st.markdown(f"**{row['role']}** · {row['ts']}  \n{row['message']}")


# ---------------------------------------------------------------- shared pages


def page_library(conn, role: str) -> None:
    rows = [row for row in all_units(conn) if row["version"] == max_version(conn, row["unit_id"])]
    kb_options = ["All"] + sorted({part.strip() for row in rows for part in (row["kb_scope"] or "").split(",") if part.strip()})
    status_options = ["All", "approved", "proposed", "blocked_conflict", "superseded", "merged", "retired"]
    type_options = ["All", "verbatim", "policy", "procedure", "faq"]
    a, b, c, d = st.columns([1, 1, 1, 2])
    kb = a.selectbox("Knowledge base", kb_options, key="x-lib-kb")
    status = b.selectbox("Status", status_options, key="x-lib-status")
    kind = c.selectbox("Type", type_options, key="x-lib-type")
    text = d.text_input("Contains words", key="x-lib-text", placeholder="for example: mail order…")
    if role in ("Pharmacy advocate", "Insurance advocate"):
        allowed = set(ROLE_KB[role])
        rows = [row for row in rows if row["status"] == "approved" and allowed & set(_kbs(row))]
    if kb != "All":
        rows = [row for row in rows if kb in _kbs(row)]
    if status != "All":
        rows = [row for row in rows if row["status"] == status]
    if kind != "All":
        rows = [row for row in rows if row["type"] == kind]
    if text.strip():
        needle = text.strip().lower()
        rows = [row for row in rows if needle in (row["text"] or "").lower() or needle in (row["title"] or "").lower()]
    muted(f"{len(rows)} units match. Illustrative, made-up documents.")
    if not rows:
        callout("No unit matches these filters. Clear a filter to see more.", "neutral")
        return
    picked = st.selectbox(
        "Open a unit",
        [row["unit_id"] for row in rows],
        format_func=lambda unit_id: _unit_label(rows, unit_id),
        key="x-lib-pick",
    )
    row = next(item for item in rows if item["unit_id"] == picked)
    left, right = st.columns([1.4, 1])
    with left:
        unit_card(row, "x-lib", details=True)
    with right:
        subheading("Versions")
        for version in conn.execute(
            "SELECT version, status, approved_by, effective_date FROM units WHERE unit_id = ? ORDER BY version",
            (row["unit_id"],),
        ):
            st.markdown(
                f"Version {version['version']}: {version['status']}, "
                f"{version['approved_by'] or 'not approved'}, {version['effective_date'] or 'no date'}"
            )
        copies = conn.execute(
            "SELECT unit_id, status FROM units WHERE superseded_by = ? AND version = 1",
            (row["unit_id"],),
        ).fetchall()
        if copies:
            subheading("Copies folded into this unit")
            for copy in copies:
                st.markdown(f"{copy['unit_id']} ({copy['status']})")


def max_version(conn, unit_id: str) -> int:
    return conn.execute("SELECT MAX(version) AS v FROM units WHERE unit_id = ?", (unit_id,)).fetchone()["v"]


def _kbs(row) -> list[str]:
    return [part.strip() for part in (row["kb_scope"] or "").split(",") if part.strip()]


def _unit_label(rows, unit_id: str) -> str:
    row = next(item for item in rows if item["unit_id"] == unit_id)
    return f"{row['title']} · {row['type']} · {row['status'].replace('_', ' ')} · {unit_id}"


# ---------------------------------------------------------------- Knowledge Ops author


def page_documents(conn, role: str) -> None:
    corpus = load_corpus()
    docs = sorted({unit["source_doc"] for unit in corpus["units"]})
    doc_id = st.selectbox("Document", docs, format_func=doc_name, key="x-doc")
    units = [row for row in all_units(conn) if row["source_doc"] == doc_id and row["version"] == 1]
    muted(f"AI extracted {len(units)} units from this document. Each highlight is numbered to match the list.")
    left, right = st.columns([1.1, 1])
    with left:
        source_panel(conn, doc_id, units)
    with right:
        with st.container(height=520, border=False):
            for index, row in enumerate(units, start=1):
                unit_card(row, f"x-doc-{index}", number=index, details=False)


def page_copies(conn, role: str) -> None:
    from src.ai import load_human_decisions
    from src.screens import _judgments_by, _pair_block, _status_map

    corpus = load_corpus()
    decisions = load_human_decisions()
    statuses = _status_map(conn)
    muted(f"AI compared {len(corpus['judgments'])} pairs across four documents. People decided what happens next.")
    show(diff_legend())
    labels = {"Near-duplicates": "near_duplicate", "Exact copies": "exact", "Conflicts": "conflict"}
    choice = st.radio("Show", list(labels), horizontal=True, key="x-copies-kind")
    for judgment in _judgments_by(corpus, labels[choice]):
        _pair_block(conn, corpus, decisions, statuses, judgment)


def page_my_approvals(conn, role: str) -> None:
    rows = list(author_queue(conn))
    muted("Procedure and FAQ units do not need Legal. You approve them.")
    if not rows:
        callout("<strong>Nothing waiting.</strong> Every procedure and FAQ unit is approved.", "approved")
        return
    current = rows[0]
    if st.button(f"Approve: {current['title']}", key="x-author-one", type="primary"):
        approve_by_author(conn, current["unit_id"])
        st.toast(f"Approved {current['title']}.")
        st.rerun()
    for row in rows:
        unit_card(row, f"x-author-{row['unit_id']}", details=False)


def page_gap_backlog(conn, role: str) -> None:
    _gaps_page(conn, role)


# ---------------------------------------------------------------- Legal approver


def page_legal_queue(conn, role: str) -> None:
    rows = list(waiting_units(conn))
    if not rows:
        callout(
            "<strong>The Legal queue is empty.</strong> Every regulated unit is approved. "
            "Open Conflicts or Revise wording for more Legal work.",
            "approved",
        )
        return
    current = rows[0]
    blocked = current["source_mismatch"] or current["verbatim_altered"]
    muted(f"{len(rows)} waiting. You see the full unit, its source, and where it will go before you approve.")
    if not blocked and st.button("Approve and publish", key="x-legal-one", type="primary"):
        approve_one(conn, current["unit_id"])
        st.toast(f"Published {current['title']}.")
        st.rerun()
    left, right = st.columns([1, 2.2])
    with left:
        subheading("Waiting")
        for index, row in enumerate(rows[:10], start=1):
            show(f'<div class="meta">{index}. {esc(row["title"])}</div>')
    with right:
        full_unit_card(conn, current, compute_preview(conn, current))


def page_conflicts(conn, role: str) -> None:
    corpus = load_corpus()
    plans = conflict_plans()
    open_ids = {plan.get("id") for plan in open_conflicts(conn)}
    muted("AI found these disagreements. Both versions stay blocked until you pick one and record why.")
    for plan in plans:
        plan_id = plan.get("id") or ""
        chosen = plan.get("chosen_unit_id") or ""
        kept = corpus["by_id"].get(chosen) or {}
        with st.container(border=True):
            is_open = plan_id in open_ids
            state = badge("Blocked: conflict", "blocked") if is_open else badge("Resolved", "approved")
            show(f'<div class="card-head"><div class="card-title">{esc(plan.get("label"))}</div><div>{state}</div></div>')
            for other_id in plan.get("retire_unit_ids") or []:
                other = corpus["by_id"].get(other_id) or {}
                show(
                    f'<div class="meta">{esc(doc_name(kept.get("source_doc", "")))} compared with '
                    f'{esc(doc_name(other.get("source_doc", "")))}</div>'
                    f'<div class="unit-text">{diff_html(kept.get("text", ""), other.get("text", ""))}</div>'
                )
            if not is_open:
                continue
            reason = st.text_input("Reason (required)", key=f"x-reason-{plan_id}")
            if st.button(f"Keep the {doc_name(kept.get('source_doc', ''))} wording", key=f"x-resolve-{plan_id}"):
                if not reason.strip():
                    show('<p class="field-error" role="alert">Add a reason before resolving.</p>')
                else:
                    resolve_conflict(conn, reason, plan_id)
                    st.toast(f"{plan.get('label')} resolved.")
                    st.rerun()


def page_revise(conn, role: str) -> None:
    from src.ai import load_human_decisions
    from src.screens import _previous_version

    unit_id = anchor(conn, "pricing")
    live = live_approved(conn, unit_id) if unit_id else None
    if live is None:
        callout("The pricing disclaimer is not approved yet. Approve it in the Legal queue first.", "review")
        return
    change = load_human_decisions().get("channels_revision") or {}
    new_text = live["text"].replace(change.get("find", ""), change.get("replace", ""))
    previous = _previous_version(conn, live["unit_id"], live["version"]) if live["version"] > 1 else None
    if new_text != live["text"]:
        callout(
            f"<strong>Prepared revision for the pricing disclaimer.</strong> {diff_legend()}"
            f'<div class="unit-text">{diff_html(live["text"], new_text)}</div>',
            "review",
        )
        if st.button(f"Publish version {live['version'] + 1} to every channel", key="x-publish", type="primary"):
            publish_revision(conn)
            st.toast("Published to every channel.")
            st.rerun()
    else:
        callout(f"Version {live['version']} is live. The prepared revision is already published.", "approved")
    left, right = st.columns([1.25, 1])
    with left:
        subheading("Advocate guidance")
        agent_mockup(live)
    with right:
        subheading("Member chat")
        member_mockup(live)
    if previous is not None:
        muted(f"Version {previous['version']} is kept in the history.")


def page_versions(conn, role: str) -> None:
    rows = [row for row in all_units(conn) if row["version"] == 1 and row["status"] in ("approved", "superseded")]
    unit_id = st.selectbox(
        "Unit",
        sorted({row["unit_id"] for row in rows}),
        index=sorted({row["unit_id"] for row in rows}).index(anchor(conn, "pricing")) if anchor(conn, "pricing") in {row["unit_id"] for row in rows} else 0,
        format_func=lambda uid: _unit_label(rows, uid),
        key="x-ver-unit",
    )
    versions = conn.execute(
        "SELECT version, status, approved_by, effective_date, text FROM units WHERE unit_id = ? ORDER BY version",
        (unit_id,),
    ).fetchall()
    frame = pd.DataFrame(
        [
            {"Version": row["version"], "Status": row["status"], "Approved by": row["approved_by"], "Effective": row["effective_date"]}
            for row in versions
        ]
    )
    st.dataframe(frame, hide_index=True)
    moments = [row["effective_date"] for row in versions if row["effective_date"]]
    if moments:
        moment = st.selectbox("What was live at", moments, key="x-ver-time")
        found = units_as_of(conn, unit_id, moment)
        if found:
            show(
                f'<div class="callout"><strong>Version {esc(found["version"])} was live</strong>, approved by '
                f'{esc(found.get("approver"))}.<div class="unit-text">{esc(found.get("text"))}</div></div>'
            )


# ---------------------------------------------------------------- advocates


def page_ask(conn, role: str) -> None:
    bank = QUESTION_BANK.get(role, [])
    if "x-ask-box" not in st.session_state:
        st.session_state["x-ask-box"] = bank[0] if bank else ""
    st.text_input("Your question", key="x-ask-box")
    if st.button("Search", key="x-ask-go", type="primary"):
        st.session_state["x-ask-last"] = st.session_state["x-ask-box"].strip()
    _ask_results(conn, role)
    subheading("Or pick a question with a saved answer")
    columns = st.columns(2)
    for index, question in enumerate(bank):
        with columns[index % 2]:
            st.button(question, key=f"x-bank-{index}", on_click=_pick_question, args=(question,), width="stretch")


def _ask_results(conn, role: str) -> None:
    query = st.session_state.get("x-ask-last")
    if not query:
        muted("Type any question and press Search. Questions without a saved answer call the model live.")
        return
    show(f'<p class="muted">Results for: <strong>{esc(query)}</strong></p>')
    result = _cached_result(conn, role, query)
    answer_card(result)



def _open_in_library(unit_id: str) -> None:
    """From a search hit to the unit in the library, with filters cleared."""
    for key, value in (("x-lib-kb", "All"), ("x-lib-status", "All"), ("x-lib-type", "All"), ("x-lib-text", "")):
        st.session_state[key] = value
    st.session_state["x-lib-pick"] = unit_id
    st.session_state["x-page"] = "Library"


def _set_state(key: str, value) -> None:
    st.session_state[key] = value


def _pick_question(question: str) -> None:
    st.session_state["x-ask-box"] = question
    st.session_state["x-ask-last"] = question


def _cached_result(conn, role: str, query: str) -> dict:
    """Run each (role, query) once per visit, so reruns never spend another live call."""
    key = f"x-result::{role}::{query}"
    if key not in st.session_state:
        with st.spinner("Searching approved units…"):
            st.session_state[key] = ask(conn, role, query)
    return st.session_state[key]


def page_my_scope(conn, role: str) -> None:
    show(f'<p class="muted">You can read these knowledge bases: {esc(", ".join(ROLE_KB[role]))}. Everything else is invisible to you. A person grants a role access to a knowledge base; the AI never does, and unknown scope is denied.</p>')
    page_library(conn, role)


# ---------------------------------------------------------------- member


# ---------------------------------------------------------------- knowledge owner


def _gaps_page(conn, role: str) -> None:
    from src.screens import _draft_html

    rows = list(gaps(conn))
    if not rows:
        callout("No unanswered cluster yet. Ask advocates' questions with no approved answer to fill it.", "neutral")
        return
    pick = st.radio(
        "Unanswered clusters",
        [row["id"] for row in rows],
        format_func=lambda gid: next(f"{r['cluster']} · {r['search_count']} · {r['status'].replace('_', ' ')}" for r in rows if r["id"] == gid),
        key="x-gap-pick",
        horizontal=False,
    )
    row = next(item for item in rows if item["id"] == pick)
    queries = [item for item in (row["queries"] or "").split("\n") if item.strip()]
    if row["status"] == "proposed":
        reason = st.text_input("Reason or note (required)", key=f"x-gap-reason-{row['id']}")
        actions = [("Send draft to author", "write"), ("Fix the process instead", "fix_process"), ("Dismiss", "dismiss")]
        if not (row["draft_text"] or "").strip():
            actions = actions[1:]
        with st.container(horizontal=True, gap="small", key=f"x-gap-actions-{row['id']}"):
            clicked = None
            for label, action in actions:
                if st.button(label, key=f"x-gap-{action}-{row['id']}", type="primary" if action == "write" else "secondary"):
                    clicked = action
        if clicked:
            if not reason.strip():
                show('<p class="field-error" role="alert">Add a reason first. It is saved with the decision.</p>')
            else:
                act_on_gap(conn, row["id"], clicked, reason)
                st.rerun()
    else:
        callout(f"<strong>{esc(row['status'].replace('_', ' ').capitalize())}.</strong> Reason: {esc(row['reason'])}", "approved")
    show(f'<div class="meta">Asked {esc(row["search_count"])} times. Illustrative counts from a made-up search log: {esc("; ".join(queries[:4]))}</div>')
    if (row["draft_text"] or "").strip():
        show(
            f'<div class="card"><div class="card-head"><div class="card-title">{esc(row["draft_title"])}</div>'
            f'<div>{badge("AI draft", "review")}</div></div><div class="unit-text">{_draft_html(row["draft_text"])}</div></div>'
        )


def page_gaps(conn, role: str) -> None:
    _gaps_page(conn, role)


def page_drift(conn, role: str) -> None:
    state = drift_state(conn)
    if not state["live_text"]:
        callout("The pricing disclaimer is not approved yet, so there is nothing to watch.", "review")
        return
    cols = st.columns(3)
    with cols[0]:
        if not state["cosmetic"] and st.button("Apply the cosmetic edit", key="x-drift-c"):
            st.session_state["x-drift-msg"] = apply_prepared_drift(conn, "cosmetic")
            st.rerun()
    with cols[1]:
        if not state["material"] and st.button("Apply the material edit", key="x-drift-m", type="primary"):
            st.session_state["x-drift-msg"] = apply_prepared_drift(conn, "material")
            st.rerun()
    with cols[2]:
        if state["material"] and not state["sent"] and st.button("Send to Legal", key="x-drift-s", type="primary"):
            send_drift_to_legal(conn)
            st.rerun()
    if st.session_state.get("x-drift-msg"):
        callout(esc(st.session_state["x-drift-msg"]), "review")
    if state["cosmetic"]:
        callout(f"<strong>Cosmetic change. Logged, not flagged.</strong> {esc(state['cosmetic_summary'])}", "neutral")
    if state["material"]:
        callout(
            f"<strong>Stale: source changed.</strong> {esc(state['summary'])} The approved version stays live."
            f'{" Sent to Legal." if state["sent"] else ""}'
            f'<div class="unit-text diff">{diff_html(state["live_text"], state["proposed_text"])}</div>',
            "review",
        )
    if not state["cosmetic"] and not state["material"]:
        muted("Two prepared edits are available. Each one runs the drift check on the live unit.")


def page_quality(conn, role: str) -> None:
    from src.screens import GOLDEN_COLUMNS, TILE_LABELS, _golden_frame, _result_style, _tile_detail

    if st.button("Score this sandbox now", key="x-score-go", type="primary"):
        st.session_state["x-report"] = quality_report(conn)
    report = st.session_state.get("x-report")
    if not report:
        muted("Scores the golden set and copy detection against this sandbox's current state.")
        return
    for column, tile in zip(st.columns(len(report["tiles"])), report["tiles"]):
        with column:
            metric_tile(TILE_LABELS.get(tile["key"], tile["label"]), tile["display"], _tile_detail(tile, report))
    muted("Illustrative, made-up data. Scores reflect this sandbox's current state.")
    st.dataframe(_golden_frame(report["golden_table"]["rows"]).style.map(_result_style, subset=["Result"]), hide_index=True, column_config=GOLDEN_COLUMNS)
    subheading("Held-out questions")
    st.dataframe(_golden_frame(report["golden_table"]["held_out"]).style.map(_result_style, subset=["Result"]), hide_index=True, column_config=GOLDEN_COLUMNS)


def page_review_dates(conn, role: str) -> None:
    rows = list(expired_units(conn))
    if rows:
        callout(f"<strong>{len(rows)} approved unit past its review date.</strong> It stays live and is flagged for its owner.", "review")
        for row in rows:
            unit_card(row, f"x-exp-{row['unit_id']}", details=False)
    else:
        callout("No approved unit is past its review date.", "approved")


# ---------------------------------------------------------------- channel and AI team


def page_unit_feed(conn, role: str) -> None:
    rows = [row for row in all_units(conn) if row["status"] == "approved"]
    picked = st.selectbox("Unit", [row["unit_id"] for row in rows], format_func=lambda uid: _unit_label(rows, uid), key="x-feed")
    row = next(item for item in rows if item["unit_id"] == picked)
    payload = {
        "unit_id": row["unit_id"],
        "version": row["version"],
        "type": row["type"],
        "knowledge_base": row["kb_scope"],
        "applicability": row["applicability"] if "applicability" in row.keys() else "",
        "effective_date": row["effective_date"] if "effective_date" in row.keys() else "",
        "review_by": row["review_by"] if "review_by" in row.keys() else "",
        "approved_by": row["approved_by"],
        "channels": [part.strip() for part in (row["channels"] or "").split(",") if part.strip()],
        "advocate_text": row["text"],
        "member_text": row["member_text"],
        "source": row["source_doc"],
    }
    left, right = st.columns([1.2, 1])
    with left:
        st.json(payload)
    with right:
        show(f"<div>{status_badge(row)}</div>")
        muted(
            "A channel renders this by reference and caches it by unit ID and version. When Legal publishes a new "
            "version, the version number changes and every channel picks up the new text."
        )


PAGES = {
    "Library": page_library,
    "Source documents": page_documents,
    "Copies and conflicts": page_copies,
    "My approvals": page_my_approvals,
    "Gap backlog": page_gap_backlog,
    "Legal queue": page_legal_queue,
    "Conflicts": page_conflicts,
    "Revise wording": page_revise,
    "Version history": page_versions,
    "Ask a question": page_ask,
    "Review inbox": page_legal_inbox,
    "Insights": lambda conn, role: page_insights(conn, role, _go_page),
    "Quick start": page_quick_start,
    "Product backlog": page_product_backlog,
    "API reference": page_api_reference,
    "Change events": page_change_events,
    "My work": lambda conn, role: page_my_work(conn, role, _open_in_library),
    "Agent desktop": lambda conn, role: page_agent_desktop(conn, role, _cached_result, _set_state),
    "App chat": lambda conn, role: page_member_app(conn, role, _cached_result),
    "Website": lambda conn, role: page_member_website(conn, role, _cached_result),
    "Phone line": lambda conn, role: page_member_phone(conn, role, _cached_result),
    "What I can read": page_my_scope,
    "Gaps": page_gaps,
    "Drift": page_drift,
    "Quality": page_quality,
    "Review dates": page_review_dates,
    "Unit feed": page_unit_feed,
}
