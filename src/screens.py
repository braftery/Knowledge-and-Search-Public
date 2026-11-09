"""One function per demo screen (BUILD_EVALUATION.md section 9)."""

from __future__ import annotations

import html
import re

import pandas as pd
import streamlit as st

from src.ai import load_human_decisions, pricing_sentence
from src.components import (
    checkpoint,
    working,
    action_row,
    added_only_html,
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
    go_to,
    is_short,
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
from src.engine import (
    approve_by_author,
    author_queue,
    units_as_of,
    ABSTAIN_QUERY,
    COST_QUERY,
    MISSPELL_QUERY,
    _meta_get,
    all_units,
    anchor,
    act_on_gap,
    apply_prepared_drift,
    cosmetic_drift_message,
    drift_state,
    quality_report,
    send_drift_to_legal,
    apply_website_merge,
    approve_one,
    approve_remaining,
    confirm_tags,
    conflict_plans,
    current_unit,
    document_body,
    escalate_conflict,
    extract_units,
    flag,
    gaps,
    has_approved,
    keep_canonical,
    live_approved,
    mark_scored,
    mark_today,
    open_conflicts,
    proposed_queue,
    publish_revision,
    resolve_conflict,
    search,
    waiting_units,
)

LEAK_QUERY = "do specialty drugs stay at the specialty pharmacy"
ROLES_SIDE_BY_SIDE = ("Pharmacy advocate", "Insurance advocate")


def _need(conn, message: str, label: str, target: int, key: str) -> None:
    """Empty state: say what is missing and offer the step that fixes it."""
    callout(esc(message), "review")
    if action_row(conn, label, key):
        go_to(target)
        st.rerun()


def _units_v1(conn, doc_id: str) -> list:
    return [row for row in all_units(conn) if row["source_doc"] == doc_id and row["version"] == 1]


def _status_map(conn) -> dict:
    return {row["unit_id"]: row for row in all_units(conn) if row["version"] == 1}


# ---------------------------------------------------------------- 0 Today


def screen_today(conn) -> None:
    if not flag(conn, "today"):
        st.text_input("Today's document search (an illustration of the current state)", value="Rx pricing disclaimer", disabled=True)
        muted("Run the search to see what an advocate gets today.")
        if action_row(conn, "Run today's search", "today-run"):
            checkpoint(conn, "Ran today's search.")
            mark_today(conn)
            st.rerun()
        return
    v1 = pricing_sentence(document_body(conn, "SRC-RX-EDU-001"))
    v2 = pricing_sentence(document_body(conn, "SRC-RX-EDU-002"))
    merges = load_human_decisions().get("merges") or []
    website = merges[0].get("member_text", "") if merges else ""
    callout(
        "<strong>Which wording is current? Which one did Legal approve? The tool cannot say.</strong> "
        "Three documents come back, and each says it a little differently.",
        "review",
    )
    show(diff_legend() + '<span class="legend"> &nbsp; Differences are shown against script v1.</span>')
    cards = [
        ("Rx education script v1", "Legal signed 2025-11-02", esc(v1)),
        ("Rx education script v2 (desk copy)", "Legal signature not recorded", diff_html(v1, v2)),
        ("Website FAQ", "Page dated 2026-01-18", diff_html(v1, website)),
    ]
    for column, (title, signed, body) in zip(st.columns(3), cards):
        with column:
            show(
                f"""
                <div class="card">
                  <div class="card-title">{esc(title)}</div>
                  <div class="muted">{esc(signed)}</div>
                  <div class="unit-text" style="font-size:17px;">{body}</div>
                </div>
                """
            )
    action_row(conn)


# ---------------------------------------------------------------- 1 Extract units


def screen_ingest(conn) -> None:
    extracted = flag(conn, "extracted")
    confirmed = flag(conn, "tags_confirmed")
    v1_units = _units_v1(conn, "SRC-RX-EDU-001") if extracted else []
    if not extracted:
        muted("AI reads the script and proposes units: what each one says, its type, and where it came from.")
        if action_row(conn, "Extract units with AI", "extract"):
            checkpoint(conn, "AI extracted the units.")
            with working("AI is reading the script…"):
                extract_units(conn)
            st.rerun()
    else:
        verbatim = [unit for unit in v1_units if unit["type"] == "verbatim"]
        clean = [unit for unit in verbatim if not unit["source_mismatch"] and not unit["verbatim_altered"]]
        muted(
            f"AI extracted {len(v1_units)} units. Verbatim units matching the source: {len(clean)} of {len(verbatim)}. "
            "AI decides units, types and spans. You confirm tags and audience."
        )
        if not confirmed:
            if action_row(conn, "Confirm tags and audience", "confirm-tags"):
                checkpoint(conn, "Tags and audience confirmed.")
                confirm_tags(conn)
                st.rerun()
        else:
            action_row(conn)
    left, right = st.columns([45, 55])
    with left:
        subheading("Source: Rx education script v1")
        source_panel(conn, "SRC-RX-EDU-001", v1_units)
    with right:
        subheading("Extracted units" if extracted else "Extracted units will appear here")
        if not extracted:
            show('<div class="card" style="height:520px;color:#4A4F55;">No units yet.</div>')
            return
        _audience_corrections(conn, confirmed)
        with st.container(height=440, border=False):
            for index, unit in enumerate(v1_units, start=1):
                unit_card(unit, f"ingest-{index}", number=index)


def _audience_corrections(conn, confirmed: bool) -> None:
    overrides = load_human_decisions().get("audience_overrides") or {}
    rows = []
    for unit_id, override in overrides.items():
        unit = current_unit(conn, unit_id)
        title = unit["title"] if unit is not None else unit_id
        state = "Applied" if confirmed else "Waiting for you"
        rows.append(
            f"<div>{esc(title)}: AI suggested <strong>{esc(override.get('ai_audience', 'member'))}</strong>. "
            f"Knowledge Ops sets <strong>{esc(override.get('audience', 'advocate'))}</strong>. "
            f"{badge(state, 'approved' if confirmed else 'review')}</div>"
        )
    if rows:
        callout("<strong>Audience corrections.</strong> These lines are read by advocates, so a person changes the AI's suggestion." + "".join(rows), "neutral")


# ---------------------------------------------------------------- 2 Find copies


def _judgments_by(corpus, relation: str) -> list:
    """Pairs with one AI label. The pairs the story follows come first, in the order data/human_decisions.json lists them."""
    watched = [
        {item.get("a"), item.get("b")} for item in (load_human_decisions().get("watched_pairs") or [])
    ]

    def rank(item):
        ids = {item["a_id"], item["b_id"]}
        return watched.index(ids) if ids in watched else len(watched)

    found = [item for item in corpus["judgments"] if item["output"].get("relation") == relation]
    return sorted(found, key=rank)


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


def _pair_block(conn, corpus, decisions, statuses, judgment) -> None:
    a_id, b_id = judgment["a_id"], judgment["b_id"]
    a = corpus["by_id"].get(a_id) or {}
    b = corpus["by_id"].get(b_id) or {}
    output = judgment["output"]
    relation = output.get("relation", "")
    tone = {"exact": "neutral", "near_duplicate": "review", "conflict": "blocked"}.get(relation, "neutral")
    label = {"exact": "Exact copy", "near_duplicate": "Near-duplicate", "conflict": "Conflict"}.get(relation, relation)
    state_a = status_badge(statuses[a_id]) if a_id in statuses else ""
    state_b = status_badge(statuses[b_id]) if b_id in statuses else ""
    phrases = output.get("differing_phrases") or []
    noted = "".join(
        f"<div>AI noted: <del>{esc(item.get('a'))}</del> vs <ins>{esc(item.get('b'))}</ins></div>" for item in phrases
    )
    human = _human_line(decisions, a_id, b_id, statuses)
    if human.startswith("Human decision") and not flag(conn, "canonical"):
        human = "Prepared decision: keep the script v1 wording. It applies when you press the button above."
    with st.container(border=True):
        show(
            f"""
            <div class="card-head"><div class="card-title">{esc(a.get('title') or a_id)}</div>
            <div>{badge(label, tone)}{badge("Model's own rating: " + str(output.get('confidence', '')), 'neutral')}</div></div>
            <div class="meta">A: {esc(a_id)} in {esc(doc_name(a.get('source_doc', '')))} {state_a}
            &nbsp; B: {esc(b_id)} in {esc(doc_name(b.get('source_doc', '')))} {state_b}</div>
            <div class="unit-text">{diff_html(a.get('text', ''), b.get('text', ''))}</div>
            <div class="meta diff">{noted}</div>
            <div class="meta"><strong>AI reason:</strong> {esc(output.get('reason', ''))}</div>
            """
        )
        if human:
            show(f'<div class="meta"><strong>{esc(human)}</strong></div>')


def screen_duplicates(conn) -> None:
    if not flag(conn, "extracted"):
        _need(conn, "No units to compare yet. Extract units from script v1 first.", "Go to Extract units", 1, "need-extract")
        return
    corpus = load_corpus()
    decisions = load_human_decisions()
    statuses = _status_map(conn)
    near = _judgments_by(corpus, "near_duplicate")
    exact = _judgments_by(corpus, "exact")
    conflicts = _judgments_by(corpus, "conflict")
    muted(
        f"AI compared {len(corpus['judgments'])} pairs of units across four documents. "
        "People decide what happens next. Illustrative documents."
    )
    if not flag(conn, "canonical"):
        if action_row(conn, "Keep the Legal-signed v1 wording", "keep-v1"):
            checkpoint(conn, "Kept the Legal-signed v1 wording. The v2 copies are superseded.")
            keep_canonical(conn)
            if not flag(conn, "website_merged"):
                apply_website_merge(conn)
            st.rerun()
    elif not flag(conn, "escalated"):
        if action_row(conn, f"Escalate {len(conflicts)} conflicts to Legal", "escalate"):
            checkpoint(conn, "Conflicts sent to Legal. Both versions stay blocked.")
            escalate_conflict(conn)
            st.rerun()
    else:
        action_row(conn)
    show(diff_legend() + '<span class="legend"> &nbsp; B is compared against A.</span>')
    tabs = st.tabs(
        [
            f"Near-duplicates ({len(near)})",
            f"Exact copies ({len(exact)})",
            f"Conflicts ({len(conflicts)})",
            f"All {len(corpus['judgments'])} pairs",
        ],
        key="copies-tabs",
        on_change="rerun",
    )
    with tabs[0]:
        for judgment in near:
            _pair_block(conn, corpus, decisions, statuses, judgment)
        _website_merge(conn, corpus, decisions, statuses)
    with tabs[1]:
        for judgment in exact:
            _pair_block(conn, corpus, decisions, statuses, judgment)
    with tabs[2]:
        callout(
            "<strong>AI found conflicts it cannot settle.</strong> Both versions of each rule are blocked from "
            "approval and search until Legal picks one and records a reason.",
            "blocked",
        )
        for judgment in conflicts:
            _pair_block(conn, corpus, decisions, statuses, judgment)
    with tabs[3]:
        rows = [
            {
                "Unit A": item["a_id"],
                "Unit B": item["b_id"],
                "AI label": item["output"].get("relation", "").replace("_", " "),
                "Model's own rating (not calibrated)": item["output"].get("confidence", ""),
                "AI reason": item["output"].get("reason", ""),
            }
            for item in corpus["judgments"]
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True)


def _website_merge(conn, corpus, decisions, statuses) -> None:
    merges = decisions.get("merges") or []
    if not merges:
        return
    merge = merges[0]
    parts = []
    for unit_id in merge.get("unit_ids") or []:
        unit = corpus["by_id"].get(unit_id)
        if unit:
            state = status_badge(statuses[unit_id]) if unit_id in statuses else ""
            parts.append(f"<div class=\"meta\">{esc(unit_id)} {state} {esc(unit['text'])}</div>")
    done = flag(conn, "website_merged")
    with st.container(border=True):
        show(
            f"""
            <div class="card-head"><div class="card-title">Website price disclaimer</div>
            <div>{badge('Split by AI into 3 units', 'review')}</div></div>
            <div class="meta">AI split one website sentence group into three units. A person merges them back into one
            member-facing wording of the pricing disclaimer.</div>
            {''.join(parts)}
            <div class="unit-text"><strong>Member wording:</strong> {esc(merge.get('member_text', ''))}</div>
            <div class="meta"><strong>{'Merged into ' + esc(merge.get('into_unit_id')) + '. Search cannot see the three pieces.' if done else 'Not merged yet.'}</strong></div>
            """
        )


# ---------------------------------------------------------------- 3 Legal approves


def screen_approve(conn) -> None:
    if not flag(conn, "escalated"):
        _need(conn, "Copies and conflicts are not settled yet. Finish them on Find copies first.", "Go to Find copies", 2, "need-copies")
        return
    waiting = waiting_units(conn)
    authors = list(author_queue(conn))
    open_plans = open_conflicts(conn)
    tabs = st.tabs(
        [
            f"Legal queue ({len(waiting)} waiting)",
            f"Knowledge Ops approvals ({len(authors)} waiting)",
            f"Conflicts for Legal ({len(open_plans)} open)",
        ],
        key="approve-tabs",
        on_change="rerun",
    )
    with tabs[0]:
        _approval_queue(conn, waiting)
    with tabs[1]:
        _author_queue(conn, authors)
    with tabs[2]:
        _conflicts(conn)
    callout(
        "<strong>Design choice:</strong> answers return approved text only, never generated prose. "
        "We trade fluency for compliance and auditability.",
        "neutral",
    )


def _author_queue(conn, authors) -> None:
    """Procedure and FAQ units skip Legal. The Knowledge Ops author approves them (SPEC.md section 4, step 3)."""
    if not authors:
        callout(
            "<strong>Nothing waiting.</strong> Procedure and FAQ units do not need Legal. "
            "The Knowledge Ops author approves them, and every one is approved.",
            "approved",
        )
        return
    muted(
        "Procedure and FAQ units do not need Legal, so the Knowledge Ops author approves them. "
        "Legal's time goes to verbatim, policy, and cost wording."
    )
    current = authors[0]
    with st.container(horizontal=True, gap="small", key="author-actions"):
        one = st.button(f"Approve as Knowledge Ops: {current['title']}", key="author-one", type="primary")
        rest = len(authors) > 1 and st.button(f"Approve all {len(authors)} (demo shortcut)", key="author-all")
    if len(authors) > 1:
        muted("Demo only. In production each unit is approved on its own review page.")
    if one:
        checkpoint(conn, f"Knowledge Ops approved {current['title']}.")
        approve_by_author(conn, current["unit_id"])
        st.rerun()
    if rest:
        checkpoint(conn, f"Knowledge Ops approved {len(authors)} units (demo shortcut).")
        for row in authors:
            approve_by_author(conn, row["unit_id"])
        st.rerun()
    for row in authors:
        unit_card(row, f"author-{row['unit_id']}", details=False)


def _approval_queue(conn, waiting) -> None:
    if not waiting:
        approved = [row for row in all_units(conn) if row["status"] == "approved"]
        callout(
            f"<strong>Queue is empty.</strong> {len(approved)} units are approved and searchable. "
            "Illustrative, made-up documents.",
            "approved",
        )
        action_row(conn)
        held = proposed_queue(conn)
        if held:
            with st.expander(f"{len(held)} units stay unapproved and why"):
                for row in held:
                    st.markdown(f"**{row['unit_id']}** {row['title']}. {row['notes'] or 'Held back as an exact copy.'}")
        return
    current = waiting[0]
    can_approve = not (current["source_mismatch"] or current["verbatim_altered"])
    secondary = []
    if not is_short(conn) and len(waiting) > 1:
        secondary.append(("Approve all remaining (demo shortcut)", "approve-rest"))
    clicked = action_row(conn, "Approve and publish" if can_approve else None, "approve-one", secondary)
    if secondary:
        muted("Demo only. In production each unit is approved on its own review page.")
    if clicked == "approve-one":
        checkpoint(conn, f"Published {current['title']}. Search can see it now.")
        approve_one(conn, current["unit_id"])
        st.rerun()
    if clicked == "approve-rest":
        checkpoint(conn, "Approved every remaining unit (demo shortcut).")
        approve_remaining(conn)
        st.rerun()
    left, right = st.columns([1, 2.2])
    with left:
        subheading("Waiting for you")
        lines = []
        for index, row in enumerate(waiting[:8], start=1):
            marker = "<strong>Now:</strong> " if index == 1 else ""
            lines.append(f'<div class="meta" style="margin-top:6px;">{index}. {marker}{esc(row["title"])}</div>')
        if len(waiting) > 8:
            lines.append(f'<div class="meta">and {len(waiting) - 8} more</div>')
        show("".join(lines))
    with right:
        full_unit_card(conn, current, compute_preview(conn, current))


def _conflicts(conn) -> None:
    corpus = load_corpus()
    statuses = _status_map(conn)
    for plan in conflict_plans():
        plan_id = plan.get("id") or ""
        chosen = plan.get("chosen_unit_id") or ""
        retire = plan.get("retire_unit_ids") or []
        row = statuses.get(chosen)
        still_open = row is not None and row["status"] == "blocked_conflict"
        kept = corpus["by_id"].get(chosen) or {}
        kept_doc = doc_name(kept.get("source_doc", ""))
        with st.container(border=True):
            state = badge("Blocked: conflict", "blocked") if still_open else badge("Resolved", "approved")
            show(f'<div class="card-head"><div class="card-title">{esc(plan.get("label", "Conflict"))}</div><div>{state}</div></div>')
            for other_id in retire:
                other = corpus["by_id"].get(other_id) or {}
                show(
                    f'<div class="meta">{esc(kept_doc)} compared with {esc(doc_name(other.get("source_doc", "")))} '
                    f'({esc(chosen)} vs {esc(other_id)})</div>'
                    f'<div class="unit-text">{diff_html(kept.get("text", ""), other.get("text", ""))}</div>'
                )
            if not still_open:
                reason = _meta_get(conn, "conflict_reason", "") if plan.get("resolve_in_demo") else plan.get("reason", "")
                show(f'<div class="meta"><strong>Legal kept the {esc(kept_doc)} wording.</strong> Reason: {esc(reason)}</div>')
                continue
            error_key = f"reason-error-{plan_id}"
            reason = st.text_input(
                "Reason (required)",
                value=plan.get("reason") or "",
                key=f"reason-{plan_id}",
            )
            if st.session_state.get(error_key):
                show('<p class="field-error" role="alert">Add a reason before resolving. Legal\'s reason is saved with the decision.</p>')
            kind = "primary" if plan.get("resolve_in_demo") else "secondary"
            if st.button(f"Keep the {kept_doc} wording", key=f"resolve-{plan_id}", type=kind):
                if not (reason or "").strip():
                    st.session_state[error_key] = True
                    st.rerun()
                st.session_state[error_key] = False
                checkpoint(conn, f"{plan.get('label', 'Conflict')} resolved. Legal kept the {kept_doc} wording.")
                resolve_conflict(conn, reason, plan_id)
                st.rerun()


# ---------------------------------------------------------------- 4 Search


def _run_search(conn, query: str, from_chip: bool = False) -> None:
    query = (query or "").strip()
    if not query:
        return
    with working():
        for role in ROLES_SIDE_BY_SIDE:
            search(conn, role, query, record=True)
    st.session_state.last_query = query
    if from_chip:
        st.session_state["query-box"] = query


def screen_search(conn) -> None:
    if not has_approved(conn):
        _need(conn, "Search has nothing to read yet. Legal must approve units first.", "Go to Legal approves", 3, "need-approve")
        return
    if "query-box" not in st.session_state:
        st.session_state["query-box"] = st.session_state.get("last_query") or COST_QUERY
    st.text_input("Question", key="query-box")
    if action_row(conn, "Search as both roles", "search-both"):
        _run_search(conn, st.session_state["query-box"])
        st.rerun()
    chips = [
        ("A question with no approved answer", ABSTAIN_QUERY),
        ("A misspelled question", MISSPELL_QUERY),
        ("A pharmacy-only question", LEAK_QUERY),
    ]
    query = st.session_state.get("last_query")
    if query:
        show(f'<p class="muted">Results for: <strong>{esc(query)}</strong></p>')
        for column, role in zip(st.columns(2), ROLES_SIDE_BY_SIDE):
            with column:
                answer_card(search(conn, role, query, record=False))
    else:
        muted("Press Search as both roles. Each role searches only the knowledge bases it is allowed to read.")
    columns = st.columns([0.6, 3, 2.4, 2.6])
    with columns[0]:
        show('<div class="muted" style="padding-top:10px;">Or try:</div>')
    for column, (label, chip_query) in zip(columns[1:], chips):
        with column:
            st.button(label, key=f"chip-{label}", on_click=_run_search, args=(conn, chip_query, True), width="stretch")
            show(f'<p class="chip-q">"{esc(chip_query)}"</p>')


# ---------------------------------------------------------------- 5 Every channel


def _previous_version(conn, unit_id: str, version: int):
    return conn.execute(
        "SELECT * FROM units WHERE unit_id = ? AND version = ?",
        (unit_id, version - 1),
    ).fetchone()


def screen_channels(conn) -> None:
    unit_id = anchor(conn, "pricing")
    live = live_approved(conn, unit_id) if unit_id else None
    if live is None:
        _need(conn, "No channel has an approved pricing disclaimer yet. Legal must approve it first.", "Go to Legal approves", 3, "need-approve-channels")
        return
    previous = _previous_version(conn, live["unit_id"], live["version"]) if live["version"] > 1 else None
    strip = f"Live everywhere: {live['unit_id']} version {live['version']}"
    if previous is not None:
        strip += f" · version {previous['version']} superseded {live['approved_on']}"
    if st.session_state.get("confirm") == "publish":
        change = load_human_decisions().get("channels_revision") or {}
        new_text = live["text"].replace(change.get("find", ""), change.get("replace", ""))
        member_old = live["member_text"] or ""
        member_new = member_old.replace(change.get("member_find", "") or "\x00", change.get("member_replace", ""))
        clicked = action_row(conn, f"Publish version {live['version'] + 1}", "publish-yes", [("Cancel", "publish-cancel")])
        if clicked == "publish-yes":
            checkpoint(conn, f"Published version {live['version'] + 1} to every channel.")
            publish_revision(conn)
            st.session_state.confirm = None
            st.rerun()
        if clicked == "publish-cancel":
            st.session_state.confirm = None
            st.rerun()
        member_block = ""
        if member_old and member_new != member_old:
            member_block = (
                '<div class="meta"><strong>Member wording</strong></div>'
                f'<div class="unit-text">{diff_html(member_old, member_new)}</div>'
            )
        callout(
            f"<strong>Legal revision, prepared edit.</strong> {diff_legend()}"
            '<div class="meta"><strong>Advocate wording</strong></div>'
            f'<div class="unit-text">{diff_html(live["text"], new_text)}</div>'
            f"{member_block}"
            '<div class="meta">Publishing creates one new version for both channels. '
            "The old version stays in the audit history.</div>",
            "review",
        )
        return
    if not flag(conn, "revised"):
        if action_row(conn, "Legal revises the wording", "revise"):
            st.session_state.confirm = "publish"
            st.rerun()
    else:
        action_row(conn)
    show(f'<div class="version-strip">{esc(strip)}</div>')
    advocate_html = added_only_html(previous["text"], live["text"]) if previous is not None else None
    member_html = None
    if previous is not None and previous["member_text"] and live["member_text"]:
        member_html = added_only_html(previous["member_text"], live["member_text"])
    left, right = st.columns([1.25, 1])
    with left:
        agent_mockup(live, advocate_html)
    with right:
        member_mockup(live, member_html)
    with st.expander("For channel and AI teams: what each channel receives"):
        payload = {
            "unit_id": live["unit_id"],
            "version": live["version"],
            "type": live["type"],
            "status": live["status"],
            "approved_by": live["approved_by"],
            "approved_on": live["approved_on"],
            "knowledge_base": live["kb_scope"],
            "channels": [part.strip() for part in (live["channels"] or "").split(",") if part.strip()],
            "advocate_text": live["text"],
            "member_text": live["member_text"],
            "source": live["source_doc"],
        }
        st.json(payload)
        muted("Channels render this by reference. When Legal publishes a new version, every subscriber gets the new version number and text.")
    if previous is not None:
        with st.expander("Show what was live at a given time"):
            versions = conn.execute(
                "SELECT version, effective_date FROM units WHERE unit_id = ? ORDER BY version",
                (live["unit_id"],),
            ).fetchall()
            moments = [row["effective_date"] for row in versions if row["effective_date"]]
            if moments:
                moment = st.selectbox("Time", moments, index=0, key="as-of-time")
                found = units_as_of(conn, live["unit_id"], moment)
                if found:
                    show(
                        f'<div class="callout"><strong>Live at {esc(moment)}: version {esc(found["version"])}</strong>, '
                        f'approved by {esc(found.get("approver"))}.'
                        f'<div class="unit-text">{esc(found.get("text"))}</div></div>'
                    )


# ---------------------------------------------------------------- 6 Gaps


_PLACEHOLDER = re.compile(r"(\[[^\]]+\])")

GAP_ACTIONS = {
    "gap-write": ("write", "Draft sent to the author."),
    "gap-process": ("fix_process", "Marked as a process fix."),
    "gap-dismiss": ("dismiss", "Cluster dismissed."),
}


def _draft_html(text: str) -> str:
    safe = html.escape(text or "")
    safe = _PLACEHOLDER.sub(r'<span class="badge review" style="white-space:normal;">\1</span>', safe)
    return safe.replace("\n", "<br>")


def screen_gaps(conn) -> None:
    rows = list(gaps(conn))
    if not rows:
        callout("AI found no unanswered cluster in the search log.", "neutral")
        action_row(conn)
        return
    ids = [row["id"] for row in rows]
    if st.session_state.get("gap-pick") not in ids:
        st.session_state["gap-pick"] = ids[0]
    selected = next(row for row in rows if row["id"] == st.session_state["gap-pick"])
    no_draft = not (selected["draft_text"] or "").strip()
    if selected["status"] == "proposed":
        reason_key = f"gap-reason-{selected['id']}"
        if reason_key not in st.session_state:
            count = selected["search_count"]
            noun = "time" if count == 1 else "times"
            st.session_state[reason_key] = f"Asked {count} {noun} with no approved answer."
        st.text_input("Reason or note (required, saved with the decision)", key=reason_key)
        if st.session_state.get("gap-error"):
            show('<p class="field-error" role="alert">Add a reason or note first. It is saved with the decision.</p>')
        clicked = action_row(
            conn,
            None if no_draft else "Send draft to author",
            "gap-write",
            [("Fix the process instead", "gap-process"), ("Dismiss", "gap-dismiss")],
        )
        if clicked in GAP_ACTIONS:
            action, done = GAP_ACTIONS[clicked]
            reason = (st.session_state.get(reason_key) or "").strip()
            if not reason:
                st.session_state["gap-error"] = True
                st.rerun()
            st.session_state["gap-error"] = False
            checkpoint(conn, done)
            act_on_gap(conn, selected["id"], action, reason)
            st.rerun()
    else:
        action_row(conn)
    left, right = st.columns([1, 1.8])
    with left:
        st.radio(
            "Unanswered clusters from the search log",
            ids,
            key="gap-pick",
            format_func=lambda gap_id: _gap_label(rows, gap_id),
        )
        muted("Counts are illustrative, from a made-up search log.")
    with right:
        _gap_detail(selected)


def _gap_label(rows, gap_id) -> str:
    row = next(item for item in rows if item["id"] == gap_id)
    state = {"proposed": "", "in_review": " (in review)", "process_fix": " (process fix)", "dismissed": " (dismissed)"}.get(row["status"], "")
    count = row["search_count"]
    noun = "search" if count == 1 else "searches"
    return f"{row['cluster']} · {count} {noun}{state}"


def _gap_detail(row) -> None:
    if not (row["draft_text"] or "").strip():
        queries = [item for item in (row["queries"] or "").split("\n") if item.strip()]
        listed = "".join(f"<li>{esc(item)}</li>" for item in queries)
        callout(
            "<strong>New questions, not yet clustered.</strong> These had no approved answer and match no "
            "existing cluster, so they wait here instead of disappearing. Member identifiers are removed before "
            f"logging.<ul style=\"margin:4px 0 0 0;\">{listed}</ul>",
            "review",
        )
        return
    queries = [item for item in (row["queries"] or "").split("\n") if item.strip()]
    figures = (row["invented_figures"] or "").strip()
    flag_html = ""
    if figures:
        flag_html = badge(f"Contains a figure not in the questions or approved units: {figures}", "blocked")
    checklist = "".join(f"<li>{esc(line.strip())}</li>" for line in (row["checklist"] or "").splitlines() if line.strip())
    decided = ""
    keys = row.keys()
    if row["status"] != "proposed":
        reason = row["reason"] if "reason" in keys else ""
        label = {"in_review": "Sent to the author", "process_fix": "Process fix", "dismissed": "Dismissed"}.get(row["status"], row["status"])
        decided = f'<div class="callout approved"><strong>{esc(label)}.</strong> Reason: {esc(reason)}</div>'
    show(
        f"""
        {decided}
        <div class="meta">Asked by {esc(row['roles'])}. Example questions: {esc('; '.join(queries[:3]))}</div>
        <div class="card">
          <div class="card-head"><div class="card-title">{esc(row['draft_title'])}</div>
          <div>{badge('AI draft', 'review')}{badge('Search cannot see this', 'neutral')}</div></div>
          <div class="meta">Suggested knowledge base: {esc(row['draft_tags'])} {flag_html}</div>
          <div class="unit-text" style="font-size:17px;">{_draft_html(row['draft_text'])}</div>
        </div>
        """
    )
    if checklist:
        show(f'<div class="callout review"><strong>Author must confirm</strong><ul style="margin:4px 0 0 0;">{checklist}</ul></div>')


# ---------------------------------------------------------------- 7 Drift


def screen_drift(conn) -> None:
    unit_id = anchor(conn, "pricing")
    live = live_approved(conn, unit_id) if unit_id else None
    if live is None:
        _need(conn, "Drift needs an approved pricing disclaimer to watch. Legal must approve it first.", "Go to Legal approves", 3, "need-approve-drift")
        return
    state = drift_state(conn)
    edits = load_corpus()["drift"]["edits"]
    material = edits.get("material")
    cosmetic = edits.get("cosmetic")
    if not state["material"]:
        secondary = [] if state["cosmetic"] else [("Apply the cosmetic edit", "drift-cosmetic")]
        clicked = action_row(conn, "Apply the material edit", "drift-material", secondary)
        if clicked:
            kind = "material" if clicked == "drift-material" else "cosmetic"
            label = (
                "Source edited. The unit is flagged stale."
                if kind == "material"
                else cosmetic_drift_message(conn)
            )
            checkpoint(conn, label)
            with working("AI is checking the change…"):
                st.session_state.drift_msg = apply_prepared_drift(conn, kind)
            st.rerun()
    elif not state["sent"]:
        if action_row(conn, "Send to Legal", "drift-send"):
            checkpoint(conn, "Sent to Legal. The approved version stays live.")
            send_drift_to_legal(conn)
            st.rerun()
    else:
        action_row(conn)
    if st.session_state.get("drift_msg"):
        callout(esc(st.session_state.drift_msg), "review")
    if state["cosmetic"]:
        callout(
            f"<strong>Cosmetic change. Logged, not flagged.</strong> {esc(state['cosmetic_summary'])}",
            "neutral",
        )
    if not state["material"]:
        if material:
            edit = material["edit"]
            callout(
                "<strong>Prepared material edit in script v1:</strong> 30-day supply becomes 31-day supply. "
                f"{diff_legend()}<div class=\"unit-text\">{diff_html(edit['old_span'], edit['new_span'])}</div>",
                "neutral",
            )
        if cosmetic and not state["cosmetic"]:
            callout("<strong>Prepared cosmetic edit:</strong> an added comma after supply.", "neutral")
        muted("Cached mode knows these two prepared edits. Other edits need Live AI. Illustrative, made-up source.")
        unit_card(live, "drift-live")
        return
    sent = " Sent to Legal." if state["sent"] else ""
    callout(
        f"<strong>Stale: source changed.</strong> AI judged the edit {esc(state['change'])}. {esc(state['summary'])} "
        f"The approved version stays live in every channel until Legal accepts a new one.{sent}",
        "review",
    )
    current = current_unit(conn, unit_id)
    left, right = st.columns(2)
    with left:
        subheading("Live now (approved)")
        unit_card(current, "drift-current", details=False)
    with right:
        subheading("AI proposed update, waiting for Legal")
        proposed = current["proposed_text"] or ""
        tag = badge("Sent to Legal", "review") if state["sent"] else badge("Proposed", "review")
        show(
            f'<div class="card"><div>{tag}{badge("Not live", "neutral")}</div>'
            f'<div class="read-exactly"><div class="label">Proposed wording</div>'
            f'<div class="text diff">{diff_html(current["text"], proposed)}</div></div></div>'
        )
    if state["events"]:
        with st.expander(f"Drift log ({len(state['events'])} edits)"):
            for event in state["events"]:
                flagged = "flagged" if event.get("flagged") else "logged, not flagged"
                st.markdown(f"**{event.get('ts')}** · {event.get('kind')} edit · {flagged} · {event.get('status')}")


# ---------------------------------------------------------------- 8 Quality


TILE_LABELS = {
    "hit_at_1": "Right answer first",
    "correct_abstain": "Correct no-answers",
    "over_abstain": "Wrong no-answers",
    "leaks": "Cross-role leaks",
    "dedup_precision": "Copy precision",
    "dedup_recall": "Copy recall",
}


def _tile_detail(tile: dict, report: dict) -> str:
    suffix = {
        "hit_at_1": "answerable questions",
        "correct_abstain": "unanswerable questions",
        "over_abstain": "answerable questions",
        "dedup_precision": "flagged copies",
        "dedup_recall": "true copies",
    }.get(tile["key"])
    if tile["key"] == "leaks":
        return f"across {report['scored_questions']} questions"
    return f"{tile['detail']} {suffix}" if suffix else tile["detail"]


GOLDEN_COLUMNS = {
    "Result": st.column_config.TextColumn("Result", width=90),
    "Question": st.column_config.TextColumn("Question", width=400),
    "Role": st.column_config.TextColumn("Role", width=150),
    "Expected": st.column_config.TextColumn("Expected", width=150),
    "Got": st.column_config.TextColumn("Got", width=150),
}


def _result_style(value: str) -> str:
    if value == "Pass":
        return "background-color: #E6F2EA; color: #1E6B3A; font-weight: 700;"
    if value == "Fail":
        return "background-color: #FBEAEA; color: #9B1C1C; font-weight: 700;"
    return ""


def _golden_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Result": row["Result"], "Question": row["Question"], "Role": row["Role"], "Expected": row["Expected"], "Got": row["Got"]}
            for row in rows
        ]
    )


def screen_quality(conn) -> None:
    if not st.session_state.get("scored"):
        muted("Score the golden set and the duplicate variants with the saved model answers.")
        if action_row(conn, "Score the golden set", "score"):
            st.session_state.report = quality_report(conn)
            st.session_state.scored = True
            mark_scored(conn)
            st.rerun()
        return
    action_row(conn)
    report = st.session_state.get("report") or quality_report(conn)
    tiles = report["tiles"]
    held_rows = report["golden_table"]["held_out"]
    held_ok = sum(1 for row in held_rows if row["Result"] == "Pass")
    open_now = open_conflicts(conn)
    show(
        f'<div class="callout review" style="font-size:20px;"><strong>What we got wrong, kept visible:</strong> '
        f"held-out questions {held_ok} of {len(held_rows)} pass · {len(open_now)} open conflicts blocked for Legal · "
        f"{len(report['misses'])} model misses. Every one is listed under What failed. Illustrative.</div>"
    )
    for column, tile in zip(st.columns(len(tiles)), tiles):
        with column:
            metric_tile(TILE_LABELS.get(tile["key"], tile["label"]), tile["display"], _tile_detail(tile, report))
    verbatim = report.get("verbatim_source") or {}
    verbatim_line = ""
    if isinstance(verbatim, dict) and verbatim.get("total"):
        verbatim_line = f" Verbatim units matching their source exactly: {verbatim.get('ok')} of {verbatim.get('total')}."
    muted(f"Illustrative, made-up data. Rates use the {report['scored_questions']} scored questions, a demonstration set; a launch gate needs about 150 labeled questions.{verbatim_line}")
    muted("Proposed launch gate: 100% verbatim match, zero cross-role leaks, and sign-off by Compliance. A person decides the release.")
    golden = report["golden_table"]
    held = golden["held_out"]
    held_pass = sum(1 for row in held if row["Result"] == "Pass")
    misses = report["misses"]
    open_plans = open_conflicts(conn)
    tabs = st.tabs(
        [
            f"What failed ({len(misses) + len(open_plans)})",
            f"Held-out questions ({held_pass} of {len(held)} pass)",
            "Golden set",
            "Copy detection",
        ],
        key="quality-tabs",
        on_change="rerun",
    )
    with tabs[0]:
        if not misses and not open_plans:
            callout("No miss was recorded. Next: add held-out questions written before any tuning.", "approved")
        for plan in open_plans:
            callout(
                f"<strong>Open conflict: {esc(plan.get('label'))}.</strong> Both versions stay blocked until Legal "
                "decides.<div class=\"meta\">Next step: route to Legal with the AI's reason attached.</div>",
                "blocked",
            )
        for item in misses:
            callout(
                f"<strong>Miss.</strong> {esc(item['miss'])}<div class=\"meta\">Next step: {esc(item['next_step'])}</div>",
                "review",
            )
    with tabs[1]:
        callout(
            "<strong>Held-out questions were written before any model run and never tuned to.</strong> "
            "They are scored separately so a good score on the main set cannot hide overfitting.",
            "neutral",
        )
        st.dataframe(_golden_frame(held).style.map(_result_style, subset=["Result"]), hide_index=True, column_config=GOLDEN_COLUMNS)
    with tabs[2]:
        st.dataframe(_golden_frame(golden["rows"]).style.map(_result_style, subset=["Result"]), hide_index=True, column_config=GOLDEN_COLUMNS)
    with tabs[3]:
        frame = pd.DataFrame(
            [
                {
                    "Result": row["result"],
                    "Variant": row["variant_text"],
                    "True label": row["label"].replace("_", " "),
                    "AI judgment": str(row["judgment"]).replace("_", " "),
                    "AI reason": row["reason"],
                }
                for row in report["dedup_table"]["rows"]
            ]
        )
        st.dataframe(frame.style.map(_result_style, subset=["Result"]), hide_index=True)


SCREENS_FN = {
    0: screen_today,
    1: screen_ingest,
    2: screen_duplicates,
    3: screen_approve,
    4: screen_search,
    5: screen_channels,
    6: screen_gaps,
    7: screen_drift,
    8: screen_quality,
}
