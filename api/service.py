"""Mutations. Each one snapshots the session database first, so POST /undo can restore it."""

from __future__ import annotations

from src.engine import (
    ADVOCATE_ROLES,
    ROLE_KB,
    acknowledge_change,
    act_on_gap,
    apply_prepared_drift,
    cosmetic_drift_message,
    apply_website_merge,
    approve_by_author,
    approve_drift_fix,
    approve_one,
    approve_remaining,
    author_queue,
    confirm_tags,
    decline_unit,
    edit_gap_draft,
    edit_returned_unit,
    escalate_conflict,
    extract_units,
    flag,
    has_approved,
    keep_canonical,
    live_approved,
    live_enabled,
    log,
    mark_scored,
    mark_today,
    member_answer,
    publish_revision,
    record_feedback,
    record_search,
    record_wrapup,
    wording_title,
    wrapup_summary,
    redact_query,
    resolve_conflict,
    resolve_feedback,
    resolve_returned_drift,
    return_drift_fix,
    search,
    send_drift_to_legal,
    send_gap_to_approval,
    send_returned_to_approval,
    set_live,
    waiting_units,
)

from api.catalog import EXPLORE_LIVE_CAP, MEMBER_TOPICS, ROLE_PAGES, SEARCH_ROLES, plain_title
from api.errors import APIError
from api.plan_data import advocate_plan_fields, chat_intent_view, unverified_rule
from src.member_data import DEFAULT_MEMBER_ID, classify_member_question, find_member
from api.present import (
    author_edits_view,
    author_queue_view,
    changes_payload,
    channels_view,
    closest_topics,
    conflicts_view,
    drift_view,
    explore_view,
    extraction_view,
    gaps_view,
    guided_view,
    legal_drift_view,
    legal_queue_view,
    quality_view,
    today_view,
)
from api.serialize import feedback_dict, gap_dict, search_dict, unit_dict

_GAP_DONE = {
    "write": "Draft sent to the author.",
    "fix_process": "Marked as a process fix.",
    "dismiss": "Cluster dismissed.",
}


def _finish(payload: dict, session, world: str) -> dict:
    payload["ok"] = True
    payload["undo"] = session.undo_info(world) and {
        "available": True,
        "label": (session.undo_info(world) or {}).get("label") or "",
        "world": world,
    } or {"available": False, "label": "", "world": world}
    payload.setdefault("illustrative", True)
    return payload


def _require_role(role: str) -> str:
    role = (role or "").strip()
    if role not in ROLE_KB:
        raise APIError("Unknown role.")
    return role


def reset_database(session, mode: str) -> dict:
    mode = (mode or "start").strip().lower()
    if mode not in ("start", "short", "jump"):
        raise APIError("mode must be start, short, or jump.")
    with session._lock:
        previous = int(session.meta().get("step") or 0)
        if mode == "start":
            label = "Demo reset to the start."
        elif mode == "short":
            label = "Jumped to the short demo."
        else:
            label = "Jumped to the approved demo state."
        session.rebuild("guided", mode, label, restore_screen=previous)
        meta = session.meta()
        meta["step"] = 0
        meta["guided_live_calls"] = 0
        session.save_meta(meta)
        with session.connection("guided") as conn:
            payload = {"message": label, "demo": guided_view(session, conn)}
        return _finish(payload, session, "guided")


def set_step(session, step: int) -> dict:
    if not isinstance(step, int) or isinstance(step, bool) or step < 0 or step > 8:
        raise APIError("Step must be a whole number from 0 to 8.")
    with session._lock:
        session.clear_undo("guided")
        meta = session.meta()
        meta["step"] = step
        session.save_meta(meta)
        with session.connection("guided") as conn:
            return {"ok": True, "demo": guided_view(session, conn), "undo": {"available": False, "label": "", "world": "guided"}}


def set_live_mode(session, world: str, enabled: bool) -> dict:
    label = "Live AI turned on." if enabled else "Live AI turned off."
    with session._lock:
        with session.mutation(world, label) as conn:
            set_live(conn, bool(enabled))
        return _finish({"message": label, "live_ai": bool(enabled), "has_api_key": _has_key()}, session, world)


def _has_key() -> bool:
    from src.ai import resolve_api_key

    return bool(resolve_api_key())


def run_today(session, world: str) -> dict:
    with session._lock:
        with session.mutation(world, "Ran today's search.") as conn:
            mark_today(conn)
            view = today_view(conn)
        return _finish({"message": "Ran today's search.", "today": view}, session, world)


def run_extract(session, world: str) -> dict:
    with session._lock:
        with session.mutation(world, "AI extracted the units.") as conn:
            extract_units(conn)
            view = extraction_view(conn)
        return _finish({"message": "AI extracted the units.", "extraction": view}, session, world)


def run_confirm(session, world: str) -> dict:
    with session._lock:
        with session.connection(world) as conn:
            if not flag(conn, "extracted"):
                raise APIError("Extract units before confirming tags.")
        with session.mutation(world, "Tags and audience confirmed.") as conn:
            confirm_tags(conn)
            view = extraction_view(conn)
        return _finish({"message": "Tags and audience confirmed.", "extraction": view}, session, world)


def run_keep(session, world: str) -> dict:
    with session._lock:
        with session.mutation(world, "Kept the Legal-signed v1 wording. The v2 copies are superseded.") as conn:
            keep_canonical(conn)
            if not flag(conn, "website_merged"):
                apply_website_merge(conn)
        return _finish({"message": "Kept the Legal-signed v1 wording. The v2 copies are superseded."}, session, world)


def run_escalate(session, world: str) -> dict:
    with session._lock:
        with session.mutation(world, "Conflicts sent to Legal. Both versions stay blocked.") as conn:
            escalate_conflict(conn)
            view = conflicts_view(conn)
        return _finish({"message": "Conflicts sent to Legal. Both versions stay blocked.", "conflicts": view}, session, world)


def run_approve_legal(session, world: str, unit_id: str | None) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Legal approver",))
    with session._lock:
        with session.connection(world) as conn:
            waiting = list(waiting_units(conn))
            if unit_id:
                match = next((row for row in waiting if row["unit_id"] == unit_id), None)
                title = match["title"] if match is not None else unit_id
                target = unit_id
            else:
                if not waiting:
                    raise APIError("The Legal queue is empty.")
                target = waiting[0]["unit_id"]
                title = waiting[0]["title"]
        label = f"Published {title}. Search can see it now."
        with session.mutation(world, label) as conn:
            message = approve_one(conn, target)
            if not str(message).startswith("Approved "):
                raise APIError(message or "This unit stays unapproved.")
            view = legal_queue_view(conn)
        return _finish({"message": message, "unit_id": target, "queue": view}, session, world)


def run_approve_legal_all(session, world: str) -> dict:
    if world == "explore":
        raise APIError("Bulk approval is closed in the sandbox. Approve one unit at a time.")
    from src.finish import require_actor

    require_actor(session, world, ("Legal approver",))
    with session._lock:
        with session.connection(world) as conn:
            count = len(list(waiting_units(conn)))
            if count == 0:
                raise APIError("The Legal queue is empty.")
        label = "Approved every remaining unit (demo shortcut)."
        with session.mutation(world, label) as conn:
            message = approve_remaining(conn)
            view = legal_queue_view(conn)
        return _finish({"message": message, "queue": view}, session, world)


def run_approve_author(session, world: str, unit_id: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge Ops author",))
    unit_id = (unit_id or "").strip()
    if not unit_id:
        raise APIError("A unit_id is required.")
    with session._lock:
        with session.connection(world) as conn:
            row = next((item for item in author_queue(conn) if item["unit_id"] == unit_id), None)
            title = row["title"] if row is not None else unit_id
        label = f"Knowledge Ops approved {title}."
        with session.mutation(world, label) as conn:
            message = approve_by_author(conn, unit_id)
            if not str(message).startswith("Approved "):
                raise APIError(message or "This unit stays unapproved.")
            view = author_queue_view(conn)
        return _finish({"message": message, "unit_id": unit_id, "queue": view}, session, world)


def run_approve_author_all(session, world: str) -> dict:
    if world == "explore":
        raise APIError("Bulk approval is closed in the sandbox. Approve one unit at a time.")
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.connection(world) as conn:
            rows = list(author_queue(conn))
            if not rows:
                raise APIError("Nothing is waiting for Knowledge Ops approval.")
            titles = [row["title"] for row in rows]
            ids = [row["unit_id"] for row in rows]
        label = f"Knowledge Ops approved {len(ids)} units (demo shortcut)."
        with session.mutation(world, label) as conn:
            messages = []
            for unit_id in ids:
                message = approve_by_author(conn, unit_id)
                if not str(message).startswith("Approved "):
                    raise APIError(message or "This unit stays unapproved.")
                messages.append(message)
            view = author_queue_view(conn)
        return _finish({"message": label, "approved": messages, "titles": titles, "queue": view}, session, world)


def run_decline(session, world: str, unit_id: str, reason: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Legal approver",))
    unit_id = (unit_id or "").strip()
    if not unit_id:
        raise APIError("A unit_id is required.")
    if not (reason or "").strip():
        raise APIError("A reason is required.")
    with session._lock:
        label = f"Returned {unit_id} to the author."
        with session.mutation(world, label) as conn:
            message = decline_unit(conn, unit_id, reason)
            if not str(message).startswith("Returned "):
                raise APIError(message or "This unit is not in the Legal queue.")
            view = legal_queue_view(conn)
        return _finish({"message": message, "queue": view}, session, world)


def run_resolve(session, world: str, conflict_id: str | None, reason: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Legal approver",))
    if not (reason or "").strip():
        raise APIError("A reason is required.")
    with session._lock:
        with session.connection(world) as conn:
            plans = conflicts_view(conn)["plans"]
            plan = None
            if conflict_id:
                plan = next((item for item in plans if item["id"] == conflict_id), None)
            else:
                plan = next((item for item in plans if item.get("resolve_in_demo") and item.get("open")), None)
            label_name = plan["label"] if plan else "Conflict"
            kept_doc = plan["chosen_doc"] if plan else ""
        label = f"{label_name} resolved. Legal kept the {kept_doc} wording."
        with session.mutation(world, label) as conn:
            message = resolve_conflict(conn, reason, conflict_id or None)
            if not str(message).startswith("Kept "):
                raise APIError(message or "No conflict is waiting for that decision.")
            view = conflicts_view(conn)
        return _finish({"message": message, "conflicts": view}, session, world)


def _guided_calls_left(session) -> int:
    used = int(session.meta().get("guided_live_calls") or 0)
    return max(0, EXPLORE_LIVE_CAP - used)


def _note_guided_live(session) -> None:
    meta = session.meta()
    meta["guided_live_calls"] = int(meta.get("guided_live_calls") or 0) + 1
    session.save_meta(meta)


def _as_missing(found: dict) -> dict:
    """A failed guided live call abstains the same way a cache miss with no key does."""
    from src.ai import MISSING_CAPTION

    found = dict(found)
    found["ai_source"] = "missing"
    found["abstained"] = True
    found["unit"] = None
    found["ai_caption"] = ""
    found["note"] = MISSING_CAPTION
    found["status"] = ""
    found["blocked_note"] = ""
    found["fallback_unit"] = None
    return found


def _search_one(session, world: str, conn, role: str, query: str, record: bool) -> tuple[dict, bool]:
    """Saved answer first. Guided cache misses may call the model, within the visit cap."""
    if not has_approved(conn):
        raise APIError("Search has nothing to read yet. Legal must approve units first.")
    role = _require_role(role)
    if role == "Member":
        raise APIError("Use POST /api/explore/member for a member question. This search returns advocate wording.")
    query = (query or "").strip()
    if not query:
        raise APIError("Enter a question.")
    previous = live_enabled(conn)
    used_live = False
    try:
        if world == "guided":
            set_live(conn, False)
        found = search(conn, role, query, record=False)
        if (
            world == "guided"
            and found.get("ai_source") == "missing"
            and _has_key()
            and _guided_calls_left(session) > 0
        ):
            set_live(conn, True)
            retried = search(conn, role, query, record=False)
            set_live(conn, False)
            if retried.get("ai_source") == "live":
                found = retried
                used_live = True
            elif retried.get("ai_source") == "live_failed":
                found = _as_missing(retried)
            else:
                found = retried
        if world == "guided":
            set_live(conn, previous)
        if record:
            record_search(conn, role, query, found)
        if used_live:
            _note_guided_live(session)
    finally:
        if world == "guided":
            set_live(conn, previous)
    return search_dict(found), used_live


def _with_live(payload: dict, session, world: str, used_live: bool) -> dict:
    if world != "guided":
        return payload
    payload = dict(payload)
    payload["used_live"] = used_live
    payload["live_calls_left"] = _guided_calls_left(session)
    payload["live_calls_cap"] = EXPLORE_LIVE_CAP
    return payload


def run_search(session, world: str, role: str, query: str, record: bool) -> dict:
    query = (query or "").strip()
    if not query:
        raise APIError("Enter a question.")
    with session._lock:
        if not record:
            with session.connection(world) as conn:
                result, used_live = _search_one(session, world, conn, role, query, False)
            body = {"ok": True, "result": result, "undo": {"available": session.undo_info(world) is not None, "world": world}}
            return _with_live(body, session, world, used_live)
        label = f"Searched as {role}."
        with session.mutation(world, label) as conn:
            result, used_live = _search_one(session, world, conn, role, query, True)
        return _with_live(_finish({"message": label, "result": result}, session, world), session, world, used_live)


def run_search_both(session, world: str, query: str, record: bool) -> dict:
    query = (query or "").strip()
    if not query:
        raise APIError("Enter a question.")
    with session._lock:
        if not record:
            with session.connection(world) as conn:
                pairs = [_search_one(session, world, conn, role, query, False) for role in SEARCH_ROLES]
            results = [result for result, _used in pairs]
            used_live = any(used for _result, used in pairs)
            return _with_live({"ok": True, "query": query, "results": results}, session, world, used_live)
        with session.mutation(world, "Searched as both roles.") as conn:
            pairs = [_search_one(session, world, conn, role, query, True) for role in SEARCH_ROLES]
        results = [result for result, _used in pairs]
        used_live = any(used for _result, used in pairs)
        return _with_live(
            _finish({"message": "Searched as both roles.", "query": query, "results": results}, session, world),
            session,
            world,
            used_live,
        )


def _saved_answer_note(text: str | None) -> str:
    if text is None:
        return "The prepared revision was published. Saved answers for this wording still match."
    return (
        "Legal typed different wording. Saved answers were keyed to the previous candidate text, "
        "so a question can miss until a new saved answer exists. The guided score uses a frozen snapshot, "
        "so step 8 does not move when the prepared text is the one published."
    )


def _clear_visit_caches(session) -> None:
    meta = session.meta()
    meta["ask_cache"] = {}
    meta["member_cache"] = {}
    session.save_meta(meta)


def run_publish(session, world: str, idempotency_key: str = "", text: str | None = None, member_text: str | None = None) -> dict:
    from src.finish import LEGAL_EMAIL, PUBLISH_CHANNELS, require_actor

    require_actor(session, world, ("Legal approver",))
    key = (idempotency_key or "").strip()
    with session._lock:
        meta = session.meta()
        stored = (meta.get("publish_keys") or {}).get(f"{world}:{key}") if key else None
        if stored:
            return stored
        with session.connection(world) as conn:
            from src.engine import anchor, current_unit

            unit_id = anchor(conn, "pricing")
            live = current_unit(conn, unit_id) if unit_id else None
            if live is None or live["status"] != "approved":
                raise APIError("The pricing disclaimer is not approved yet.")
            next_version = int(live["version"]) + 1
        label = PUBLISH_CHANNELS.format(version=next_version)
        with session.mutation(world, label) as conn:
            changed = publish_revision(conn, text=text, member_text=member_text)
            if not changed:
                raise APIError("That wording is already published.")
            view = channels_view(conn)
            email = LEGAL_EMAIL.format(unit_id=view.get("live", {}).get("unit_id") or "the unit")
        _clear_visit_caches(session)
        payload = _finish({"message": label, "channels": view, "email": email, "saved_answers": _saved_answer_note(text)}, session, world)
        if key:
            meta = session.meta()
            keys = dict(meta.get("publish_keys") or {})
            keys[f"{world}:{key}"] = payload
            meta["publish_keys"] = keys
            session.save_meta(meta)
        return payload


def _approval_queue(requires_legal) -> str:
    if requires_legal:
        return "Legal"
    return "Knowledge Ops approvals"


def _gap_row(conn, gap_id: str):
    return conn.execute("SELECT * FROM gaps WHERE id = ?", (gap_id,)).fetchone()


def run_edit_gap(session, world: str, gap_id: str, text: str, member_text: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge Ops author",))
    gap_id = (gap_id or "").strip()
    if not gap_id:
        raise APIError("A gap id is required.")
    with session._lock:
        with session.connection(world) as conn:
            row = _gap_row(conn, gap_id)
            cluster = row["cluster"] if row is not None else "gap"
        label = f"Edited the {cluster} draft."
        with session.mutation(world, label) as conn:
            message = edit_gap_draft(conn, gap_id, text or "", member_text or "")
            if message:
                raise APIError(message)
            saved = gap_dict(_gap_row(conn, gap_id))
            edits = author_edits_view(conn)
        return _finish({"message": label, "gap": saved, "edits": edits}, session, world)


def run_send_gap(session, world: str, gap_id: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge Ops author",))
    gap_id = (gap_id or "").strip()
    if not gap_id:
        raise APIError("A gap id is required.")
    with session._lock:
        label = "Sent the draft to approval."
        with session.mutation(world, label) as conn:
            message = send_gap_to_approval(conn, gap_id)
            if message:
                raise APIError(message)
            unit_id = f"U-GAP-{gap_id}"
            unit = conn.execute(
                "SELECT * FROM units WHERE unit_id = ? AND version = 1",
                (unit_id,),
            ).fetchone()
            queue = _approval_queue(unit["requires_legal"] if unit is not None else 0)
            reason = (unit["routing_reason"] if unit is not None else "") or ""
            shown = f"Sent {unit_id} to {queue}."
            payload = {
                "message": shown,
                "unit_id": unit_id,
                "queue": queue,
                "routing_reason": reason,
                "gap": gap_dict(_gap_row(conn, gap_id)),
                "unit": unit_dict(unit) if unit is not None else None,
                "edits": author_edits_view(conn),
            }
        return _finish(payload, session, world)


def run_edit_returned(session, world: str, unit_id: str, text: str, member_text: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge Ops author",))
    unit_id = (unit_id or "").strip()
    if not unit_id:
        raise APIError("A unit_id is required.")
    with session._lock:
        label = f"Edited {unit_id} after Legal sent it back."
        with session.mutation(world, label) as conn:
            message = edit_returned_unit(conn, unit_id, text or "", member_text or "")
            if message:
                raise APIError(message)
            row = conn.execute(
                "SELECT * FROM units WHERE unit_id = ? AND version = 1",
                (unit_id,),
            ).fetchone()
            payload = {
                "message": label,
                "unit": unit_dict(row) if row is not None else None,
                "edits": author_edits_view(conn),
            }
        return _finish(payload, session, world)


def run_send_returned(session, world: str, unit_id: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge Ops author",))
    unit_id = (unit_id or "").strip()
    if not unit_id:
        raise APIError("A unit_id is required.")
    with session._lock:
        label = f"Sent {unit_id} back to approval."
        with session.mutation(world, label) as conn:
            message = send_returned_to_approval(conn, unit_id)
            if message:
                raise APIError(message)
            row = conn.execute(
                "SELECT * FROM units WHERE unit_id = ? AND version = 1",
                (unit_id,),
            ).fetchone()
            queue = _approval_queue(row["requires_legal"] if row is not None else 0)
            reason = (row["routing_reason"] if row is not None else "") or ""
            shown = f"Sent {unit_id} to {queue}."
            payload = {
                "message": shown,
                "unit_id": unit_id,
                "queue": queue,
                "routing_reason": reason,
                "unit": unit_dict(row) if row is not None else None,
                "edits": author_edits_view(conn),
            }
        return _finish(payload, session, world)


def run_approve_drift(session, world: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Legal approver",))
    with session._lock:
        label = "Published the drift fix. Every channel now shows that version."
        with session.mutation(world, label) as conn:
            message = approve_drift_fix(conn)
            if message:
                raise APIError(message)
            row = conn.execute(
                "SELECT unit_id FROM drift_log WHERE status = 'approved' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            unit_id = row["unit_id"] if row is not None else ""
            live = live_approved(conn, unit_id) if unit_id else None
            version = live["version"] if live is not None else None
            shown = (
                f"Published {unit_id} version {version} from the source change. "
                f"Every channel now shows version {version}."
            )
            payload = {
                "message": shown,
                "unit_id": unit_id,
                "version": version,
                "drift": legal_drift_view(conn),
                "unit": unit_dict(live) if live is not None else None,
            }
        return _finish(payload, session, world)


def run_return_drift(session, world: str, reason: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Legal approver",))
    if not (reason or "").strip():
        raise APIError("A reason is required.")
    with session._lock:
        label = "Sent the drift fix back. The approved version stays live."
        with session.mutation(world, label) as conn:
            message = return_drift_fix(conn, reason)
            if message:
                raise APIError(message)
            row = conn.execute(
                "SELECT unit_id FROM drift_log WHERE status = 'returned' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            unit_id = row["unit_id"] if row is not None else ""
            live = live_approved(conn, unit_id) if unit_id else None
            shown = f"Sent the drift fix for {unit_id} back. The approved version stays live."
            payload = {
                "message": shown,
                "unit_id": unit_id,
                "reason": reason.strip(),
                "stale": bool(live["stale"]) if live is not None else None,
                "drift": legal_drift_view(conn),
            }
        return _finish(payload, session, world)


def run_resolve_drift(session, world: str, note: str) -> dict:
    if not (note or "").strip():
        raise APIError("A note is required.")
    with session._lock:
        label = "Resolved the returned drift fix. The approved version stays live."
        with session.mutation(world, label) as conn:
            message = resolve_returned_drift(conn, note)
            if message:
                raise APIError(message)
            row = conn.execute(
                "SELECT unit_id FROM drift_log WHERE status = 'resolved' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            unit_id = row["unit_id"] if row is not None else ""
            live = live_approved(conn, unit_id) if unit_id else None
            shown = f"Resolved the returned drift fix for {unit_id}. The approved version stays live."
            payload = {
                "message": shown,
                "unit_id": unit_id,
                "note": note.strip(),
                "stale": bool(live["stale"]) if live is not None else None,
                "unit": unit_dict(live) if live is not None else None,
            }
        return _finish(payload, session, world)


def run_gap(session, world: str, gap_id: str, action: str, reason: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge owner",))
    action = (action or "").strip()
    if action not in _GAP_DONE:
        raise APIError("Unknown gap action. Use write, fix_process, or dismiss.")
    if not (reason or "").strip():
        raise APIError("A reason is required.")
    with session._lock:
        label = _GAP_DONE[action]
        with session.mutation(world, label) as conn:
            message = act_on_gap(conn, gap_id, action, reason)
            if message:
                raise APIError(message)
            view = gaps_view(conn)
        return _finish({"message": label, "gaps": view}, session, world)


def run_drift(session, world: str, kind: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge Ops author",))
    kind = (kind or "").strip().lower()
    if kind not in ("cosmetic", "material"):
        raise APIError("Use material or cosmetic.")
    with session._lock:
        if kind == "material":
            label = "Source edited. The unit is flagged stale."
        else:
            with session.connection(world) as conn:
                label = cosmetic_drift_message(conn)
        with session.mutation(world, label) as conn:
            message = apply_prepared_drift(conn, kind)
            if message:
                raise APIError(message)
            view = drift_view(conn)
        return _finish({"message": label, "drift": view}, session, world)


def run_drift_send(session, world: str) -> dict:
    from src.finish import require_actor

    require_actor(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, "Sent to Legal. The approved version stays live.") as conn:
            message = send_drift_to_legal(conn)
            if message:
                raise APIError(message)
            view = drift_view(conn)
        return _finish({"message": "Sent to Legal. The approved version stays live.", "drift": view}, session, world)


def run_score(session, world: str) -> dict:
    with session._lock:
        with session.mutation(world, "Scored the golden set.") as conn:
            mark_scored(conn)
            view = quality_view(conn, scored=True)
        return _finish({"message": "Scored the golden set.", "quality": view}, session, world)


def run_feedback(session, world: str, fields: dict) -> dict:
    with session._lock:
        with session.mutation(world, "Flag sent. Member details are removed before it is stored.") as conn:
            try:
                row = record_feedback(
                    conn,
                    fields.get("source") or "",
                    fields.get("role") or "",
                    fields.get("kind") or "",
                    fields.get("question") or "",
                    fields.get("unit_id") or "",
                    fields.get("note") or "",
                    fields.get("signals") or {},
                )
            except ValueError as exc:
                raise APIError(str(exc)) from exc
        return _finish({"message": "Flag sent. Member details are removed before it is stored.", "feedback": row}, session, world)


def run_resolve_feedback(session, world: str, feedback_id: int, resolution: str) -> dict:
    if not (resolution or "").strip():
        raise APIError("A resolution note is required.")
    with session._lock:
        with session.mutation(world, "Resolved.") as conn:
            try:
                row = resolve_feedback(conn, feedback_id, resolution)
            except ValueError as exc:
                raise APIError(str(exc)) from exc
        return _finish({"message": "Resolved.", "feedback": row}, session, world)


def run_undo(session, world: str, supplied_role: str = "", resource: str = "") -> dict:
    from src.finish import roles_match, session_explore_role

    with session._lock:
        info = session.undo_info(world)
        if info is None:
            raise APIError("Nothing to undo.")
        actor = (info.get("actor") or "").strip()
        owned = (info.get("resource") or "").strip()
        if resource and owned and resource != owned:
            raise APIError("Only the role that made that change can undo it.", 403)
        if world == "explore" and actor:
            current = session_explore_role(session)
            if current != actor:
                raise APIError(f"Only the {actor} can undo this.", 403)
        if supplied_role and actor and not roles_match(supplied_role, actor):
            raise APIError(f"Only the {actor} can undo this.", 403)
        label = info.get("label") or ""
        if label.startswith("Published version"):
            from src.engine import list_events, retract_published_version

            with session.connection(world) as conn:
                message = retract_published_version(conn, f"Undo of publish. {label}")
            if message == "Nothing to retract.":
                raise APIError(message)
            prior = []
            with session.connection(world) as conn:
                prior = list_events(conn)
            session.clear_undo(world)
            _clear_visit_caches(session)
            payload = {
                "ok": True,
                "message": f"Undid: {label}",
                "world": world,
                "retraction": message,
                "events": prior,
            }
            if world == "guided":
                with session.connection("guided") as conn:
                    payload["demo"] = guided_view(session, conn)
            else:
                payload["explore"] = explore_view(session)
            payload["undo"] = {"available": False, "label": "", "world": world}
            return payload
        from src.engine import append_event, list_events

        with session.connection(world) as conn:
            kept = list_events(conn)
        info = session.restore(world)
        with session.connection(world) as conn:
            existing = {
                (row["event"], row["unit_id"], row["version"], row["note"])
                for row in list_events(conn)
            }
            for row in kept:
                key = (row["event"], row["unit_id"], row["version"], row["note"])
                if key in existing:
                    continue
                append_event(
                    conn,
                    row["event"],
                    row["unit_id"],
                    row["version"],
                    row["previous_version"],
                    row["actor"],
                    row["note"],
                )
            append_event(conn, "action.reversed", "", 0, 0, "System", f"Undo: {label}")
            conn.commit()
        payload = {"ok": True, "message": f"Undid: {info.get('label') or 'the last action'}", "world": world}
        if world == "guided":
            with session.connection("guided") as conn:
                payload["demo"] = guided_view(session, conn)
        else:
            payload["explore"] = explore_view(session)
        payload["undo"] = {"available": False, "label": "", "world": world}
        return payload


def open_explore(session, role: str) -> dict:
    from src.finish import canonical_role

    role = canonical_role(role)
    if role not in ROLE_PAGES:
        raise APIError("Unknown role.", 400, allowed=list(ROLE_PAGES))
    with session._lock:
        session.ensure_explore()
        meta = session.meta()
        meta["explore_role"] = role
        meta["explore_page"] = ROLE_PAGES[role][0]
        session.save_meta(meta)
        return {"ok": True, "explore": explore_view(session)}


def set_explore_page(session, page: str) -> dict:
    page = (page or "").strip()
    with session._lock:
        if not session.explore_ready():
            raise APIError("Open an Explore role before using the sandbox.")
        meta = session.meta()
        role = meta.get("explore_role")
        pages = ROLE_PAGES.get(role) or []
        if page not in pages:
            raise APIError("That page is not in this role's workspace.")
        meta["explore_page"] = page
        session.save_meta(meta)
        return {"ok": True, "explore": explore_view(session)}


def reset_explore(session) -> dict:
    with session._lock:
        if not session.explore_ready():
            raise APIError("Open an Explore role before resetting the sandbox.")
        role = session.meta().get("explore_role") or "Knowledge Ops author"
        if role not in ROLE_PAGES:
            role = "Knowledge Ops author"
        session.rebuild("explore", "explore", "Sandbox reset.")
        meta = session.meta()
        meta["explore_role"] = role
        meta["explore_page"] = ROLE_PAGES[role][0]
        meta["explore_live_calls"] = 0
        meta["ask_cache"] = {}
        meta["member_cache"] = {}
        meta["desk_searches"] = {}
        meta["feedback_seen"] = []
        session.save_meta(meta)
        return _finish({"message": "Sandbox reset.", "explore": explore_view(session)}, session, "explore")


def _calls_left(session) -> int:
    from src.finish import ip_calls_left

    used = int(session.meta().get("explore_live_calls") or 0)
    return min(max(0, EXPLORE_LIVE_CAP - used), ip_calls_left())


def _note_live(session) -> None:
    from src.finish import note_ip_call

    meta = session.meta()
    meta["explore_live_calls"] = int(meta.get("explore_live_calls") or 0) + 1
    session.save_meta(meta)
    note_ip_call()


def _plan_intent(query: str) -> dict | None:
    intent = classify_member_question(query)
    if intent is None or intent.get("intent") not in ("price", "visit_cost", "price_compare"):
        return None
    if intent.get("intent") == "price_compare":
        intent = dict(intent)
        intent["intent"] = "price"
    return intent


def _cached_version_live(session, world: str, payload: dict) -> bool:
    """A visit cache must not present a superseded version as approved."""
    candidates = []
    result = payload.get("result") or {}
    unit = result.get("unit") if isinstance(result, dict) else None
    if isinstance(unit, dict) and unit.get("unit_id") and unit.get("version"):
        candidates.append((unit["unit_id"], unit["version"]))
    if payload.get("unit_id") and payload.get("version"):
        candidates.append((payload["unit_id"], payload["version"]))
    for item in payload.get("units") or []:
        if isinstance(item, dict) and item.get("unit_id") and item.get("version"):
            candidates.append((item["unit_id"], item["version"]))
    if not candidates:
        return True
    with session.connection(world) as conn:
        for unit_id, version in candidates:
            row = conn.execute(
                "SELECT status FROM units WHERE unit_id = ? AND version = ?",
                (unit_id, version),
            ).fetchone()
            if row is None or row["status"] != "approved":
                return False
    return True


def _remember_ask(session, cache_key: str, payload: dict) -> dict:
    meta = session.meta()
    cache = dict(meta.get("ask_cache") or {})
    cache[cache_key] = payload
    meta["ask_cache"] = cache
    session.save_meta(meta)
    return payload


def caller_verified(session, member_id: str) -> bool:
    """Server-side verification. The client's verified flag is ignored."""
    member_id = (member_id or "").strip()
    if not member_id:
        return False
    meta = session.meta()
    if member_id in (meta.get("verified_members") or {}):
        return True
    if meta.get("explore_role") == "Member" and member_id == DEFAULT_MEMBER_ID:
        return True
    return False


def phone_verified(session, member_id: str, call_id: str = "") -> bool:
    book = session.meta().get("phone_calls") or {}
    entry = book.get(call_id or "")
    return bool(entry and entry.get("member_id") == member_id)


def _record_check(session, member_id: str, birth: str, field: str) -> dict:
    from src.engine import now_et
    from src.member_data import find_member, identifiers_match

    member_id = (member_id or "").strip()
    if not session.explore_ready():
        raise APIError("Open an Explore role before using the sandbox.")
    if not member_id:
        raise APIError("A member_id is required.")
    if find_member(member_id) is None:
        raise APIError(f"No member {member_id}.", 404)
    if not identifiers_match(member_id, birth):
        raise APIError("Those identifiers do not match the plan record.")
    meta = session.meta()
    book = dict(meta.get(field) or {})
    book[member_id] = {"at": now_et(), "method": "member_id_and_date_of_birth"}
    meta[field] = book
    meta["ask_cache"] = {}
    meta["member_cache"] = {}
    session.save_meta(meta)
    return {
        "ok": True,
        "verified": True,
        "member_id": member_id,
        "method": "member_id_and_date_of_birth",
        "illustrative": True,
        "note": "Illustrative, made-up data",
    }


def confirm_identifiers(session, member_id: str, birth: str) -> dict:
    with session._lock:
        return _record_check(session, member_id, birth, "verified_members")


def confirm_phone(session, member_id: str, birth: str, call_id: str = "") -> dict:
    call_id = (call_id or "").strip()
    if not call_id:
        raise APIError("A call_id is required.")
    with session._lock:
        payload = _record_check(session, member_id, birth, "phone_verified")
        meta = session.meta()
        calls = dict(meta.get("phone_calls") or {})
        calls[call_id] = {"member_id": member_id, "at": payload.get("method")}
        meta["phone_calls"] = calls
        session.save_meta(meta)
        payload["channel"] = "voice_bot"
        payload["call_id"] = call_id
        with session.connection("explore") as conn:
            from api.plan_data import ivr_prompt_map

            verified = (ivr_prompt_map(conn).get("verified") or {}).get("text") or ""
        payload["reply"] = verified
        return payload


def explore_ask(session, role: str, query: str, member_id: str = "", verified: bool = False) -> dict:
    """Saved answer first. A question with no saved answer may call the model, within the visit cap.

    With a member id, a drug-price or visit-cost question uses plan data when the caller is verified.
    An unverified caller gets the approved rule and no figures. Without a member id, search is unchanged.
    """
    from src.finish import check_question_length, normalize_cache_key

    role = _require_role(role)
    if role == "Member":
        raise APIError("Use POST /api/explore/member for a member question.")
    query = check_question_length(query or "")
    if not query:
        raise APIError("Enter a question.")
    member_id = (member_id or "").strip()
    del verified
    with session._lock:
        if not session.explore_ready():
            raise APIError("Open an Explore role before using the sandbox.")
        if member_id and find_member(member_id) is None:
            raise APIError(f"No member {member_id}.", 404)
        verified_now = caller_verified(session, member_id) if member_id else False
        folded = f"{role}\n{normalize_cache_key(query)}"
        if member_id:
            cache_key = f"{folded}::{member_id}::{int(verified_now)}"
        else:
            cache_key = folded
        cached = (session.meta().get("ask_cache") or {}).get(cache_key)
        if cached and _cached_version_live(session, "explore", cached):
            cached = dict(cached)
            cached["from_visit_cache"] = True
            cached["live_calls_left"] = _calls_left(session)
            return cached
        intent = _plan_intent(query) if member_id else None
        if member_id and not verified_now and intent is not None:
            with session.connection("explore") as conn:
                rule = unverified_rule(conn)
            payload = {
                "ok": True,
                "message": "The caller is not verified.",
                "text": rule["text"],
                "units": rule["units"],
                "illustrative": True,
                "used_live": False,
                "from_visit_cache": False,
                "live_calls_left": _calls_left(session),
                "live_calls_cap": EXPLORE_LIVE_CAP,
            }
            return _remember_ask(session, cache_key, payload)
        with session.mutation("explore", f"Searched the sandbox as {role}.") as conn:
            set_live(conn, False)
            found = search(conn, role, query, record=False)
            used_live = False
            if found.get("ai_source") == "missing" and _calls_left(session) > 0:
                set_live(conn, True)
                found = search(conn, role, query, record=False)
                set_live(conn, False)
                if found.get("ai_source") == "live":
                    used_live = True
            if intent is None and found.get("ai_source") in ("cached", "no_candidates"):
                search(conn, role, query, record=True)
            elif intent is None:
                outcome = "no approved answer" if found.get("abstained") else found["unit"]["unit_id"]
                log(
                    conn,
                    role,
                    f"Search '{redact_query(query)}' returned {outcome}. Answer source: {found.get('ai_source')}.",
                )
            else:
                log(
                    conn,
                    role,
                    f"Search '{redact_query(query)}' quoted plan data for a verified caller.",
                )
            unit = found.get("unit") or {}
            if not isinstance(unit, dict):
                # search() can return a database row; read it as a dict.
                unit = dict(unit)
            from src.compliance import text_has_amount

            if (
                member_id
                and not verified_now
                and text_has_amount(f"{unit.get('text') or ''} {unit.get('member_text') or ''}")
            ):
                rule = unverified_rule(conn)
                payload = {
                    "ok": True,
                    "message": "The caller is not verified.",
                    "text": rule["text"],
                    "units": rule["units"],
                    "illustrative": True,
                    "used_live": False,
                    "from_visit_cache": False,
                    "live_calls_left": _calls_left(session),
                    "live_calls_cap": EXPLORE_LIVE_CAP,
                }
                return _remember_ask(session, cache_key, payload)
            result = search_dict(found)
            plan_fields = advocate_plan_fields(conn, member_id, query, intent) if intent is not None else {}
        if used_live:
            _note_live(session)
        payload = _finish({
            "message": "Searched the sandbox.",
            "result": result,
            "used_live": used_live,
            "from_visit_cache": False,
            "live_calls_left": _calls_left(session),
            "live_calls_cap": EXPLORE_LIVE_CAP,
            **plan_fields,
        }, session, "explore")
        return _remember_ask(session, cache_key, payload)


def _seen(session, key: str) -> bool:
    return key in (session.meta().get("feedback_seen") or [])


def _mark_seen(session, key: str) -> None:
    meta = session.meta()
    seen = list(meta.get("feedback_seen") or [])
    if key not in seen:
        seen.append(key)
        meta["feedback_seen"] = seen
        session.save_meta(meta)


def desk_search(session, role: str, query: str, call_reason: str) -> dict:
    role = _require_role(role)
    if role not in ("Pharmacy advocate", "Insurance advocate"):
        raise APIError("The agent desktop is for Pharmacy and Insurance advocates.")
    query = (query or "").strip()
    if not query:
        raise APIError("Enter a question.")
    asked = explore_ask(session, role, query)
    with session._lock:
        meta = session.meta()
        counts = dict(meta.get("desk_searches") or {})
        counts[role] = int(counts.get(role) or 0) + 1
        meta["desk_searches"] = counts
        session.save_meta(meta)
        count = counts[role]
        recorded = []
        result = asked.get("result") or {}
        if count >= 3 and not _seen(session, f"hard::{role}::{call_reason}"):
            _record_auto(
                session,
                f"hard::{role}::{call_reason}",
                source="advocate",
                role=role,
                kind="hard_to_find",
                question=query,
                note="Captured automatically: three or more searches in one call.",
                signals={"searches_in_call": count},
            )
            recorded.append("hard_to_find")
        if (
            result.get("abstained")
            and result.get("status") != "blocked_conflict"
            and not _seen(session, f"noans::{role}::{query}")
        ):
            _record_auto(
                session,
                f"noans::{role}::{query}",
                source="advocate",
                role=role,
                kind="no_answer",
                question=query,
                unit_id="",
                note="",
                signals={},
            )
            recorded.append("no_answer")
        asked = dict(asked)
        asked["searches_in_call"] = count
        asked["feedback_recorded"] = recorded
        return asked


def _record_auto(session, key: str, **fields) -> None:
    """Caller holds the session lock. A failed write rolls back to the snapshot."""
    if _seen(session, key):
        return
    with session.mutation("explore", "Feedback captured.") as conn:
        try:
            record_feedback(
                conn,
                fields.get("source") or "channel",
                fields.get("role") or "",
                fields["kind"],
                fields.get("question") or "",
                fields.get("unit_id") or "",
                fields.get("note") or "",
                fields.get("signals") or {},
            )
        except ValueError as exc:
            raise APIError(str(exc)) from exc
    _mark_seen(session, key)


def _topic_reply(conn, index: int) -> dict:
    if index < 0 or index >= len(MEMBER_TOPICS):
        raise APIError("Unknown topic.")
    topic = MEMBER_TOPICS[index]
    from src.engine import anchor

    unit_id = anchor(conn, topic["anchor"]) if topic.get("anchor") else topic.get("unit_id")
    row = live_approved(conn, unit_id) if unit_id else None
    member_text = (row["member_text"] or "").strip() if row is not None else ""
    if not member_text:
        reply = "I do not have an approved answer for that. I can connect you with a member advocate."
        return {
            "kind": "topic",
            "abstained": True,
            "reply": reply,
            "member_text": "",
            "citation": "",
            "title": "",
            "version": None,
            "unit_id": "",
            "question": topic["question"],
            "suggestions": [],
        }
    citation = f"Source: Harbor Health, {plain_title(row['title'])}, version {row['version']}"
    return {
        "kind": "topic",
        "abstained": False,
        "reply": f"{member_text} {citation}",
        "member_text": member_text,
        "citation": citation,
        "title": row["title"],
        "version": row["version"],
        "unit_id": row["unit_id"],
        "question": topic["question"],
        "suggestions": [],
    }


def _chat_member(member_id: str | None) -> str:
    chosen = (member_id or "").strip()
    if not chosen:
        raise APIError("A member is required.")
    if find_member(chosen) is None:
        raise APIError(f"No member {chosen}.", 404)
    return chosen


def member_turn(session, question: str | None, topic: int | None, member_id: str | None = None, channel: str = "", call_id: str = "") -> dict:
    from src.finish import attach_answer_fields, check_question_length, merge_context, split_two_questions

    with session._lock:
        if not session.explore_ready():
            raise APIError("Open an Explore role before using the sandbox.")
        member_id = _chat_member(member_id)
        if topic is not None:
            index = int(topic)
            with session.connection("explore") as conn:
                if index == 0:
                    reply = chat_intent_view(
                        conn,
                        member_id,
                        MEMBER_TOPICS[0]["question"],
                        {"intent": "clarify_drug"},
                    )
                elif index == 1:
                    reply = chat_intent_view(
                        conn,
                        member_id,
                        MEMBER_TOPICS[1]["question"],
                        {"intent": "clarify_visit"},
                    )
                else:
                    reply = _topic_reply(conn, index)
            reply["live_calls_left"] = _calls_left(session)
            reply["feedback_recorded"] = None
            reply["illustrative"] = True
            return attach_answer_fields({"ok": True, **reply})
        question = check_question_length(question or "")
        if not question:
            raise APIError("Enter a question or choose a topic.")
        if channel == "voice_bot" and not (call_id or "").strip():
            raise APIError("A call_id is required.")
        stored = (session.meta().get("member_context") or {}).get(member_id) or {}
        question = merge_context(question, stored)
        first, second = split_two_questions(question)
        question = first or question
        cache_key = f"{member_id}\n{channel}\n{call_id}\n{question}"
        cached = (session.meta().get("member_cache") or {}).get(cache_key)
        if cached and _cached_version_live(session, "explore", cached):
            cached = dict(cached)
            cached["from_visit_cache"] = True
            cached["live_calls_left"] = _calls_left(session)
            return cached
        intent = classify_member_question(question)
        if channel == "voice_bot" and not phone_verified(session, member_id, call_id) and intent and intent.get("intent") in ("price", "visit_cost", "oop", "price_compare", "drug_total", "plan_figure"):
            with session.connection("explore") as conn:
                from api.plan_data import ivr_prompt_map

                prompts = ivr_prompt_map(conn)
            auth = prompts.get("authenticate") or {}
            auth_body = {
                "ok": True,
                "message": "Member reply ready.",
                "kind": "authenticate",
                "abstained": False,
                "reply": auth.get("text") or "",
                "units": [auth] if auth else [],
                "ivr_prompts": prompts,
                "authenticated": False,
                "illustrative": True,
                "show_unit_id": False,
                "feedback_recorded": None,
                "from_visit_cache": False,
                "live_calls_left": _calls_left(session),
                "live_calls_cap": EXPLORE_LIVE_CAP,
            }
            return _decorate_member(session, member_id, auth_body, intent, second)
        if intent is not None:
            with session.connection("explore") as conn:
                body = chat_intent_view(conn, member_id, question, intent)
            wrapped = {
                "ok": True,
                "message": "Member reply ready.",
                **body,
                "feedback_recorded": None,
                "from_visit_cache": False,
                "live_calls_left": _calls_left(session),
                "live_calls_cap": EXPLORE_LIVE_CAP,
            }
            meta = session.meta()
            cache = dict(meta.get("member_cache") or {})
            cache[cache_key] = wrapped
            meta["member_cache"] = cache
            session.save_meta(meta)
            return _decorate_member(session, member_id, wrapped, intent, second)
        with session.mutation("explore", "Member asked a question.") as conn:
            set_live(conn, False)
            found = member_answer(conn, question, record=False)
            used_live = False
            if found.get("ai_source") == "missing" and _calls_left(session) > 0:
                set_live(conn, True)
                found = member_answer(conn, question, record=False)
                set_live(conn, False)
                if found.get("ai_source") == "live":
                    used_live = True
            record_search(conn, "Member", question, found)
            source = found.get("ai_source") or ""
            suggestions = []
            recorded_kind = None
            if source in ("missing", "live_failed", "capped"):
                kind = "handoff"
                reply = "I cannot look that up right now. Try a topic, or I can connect you with a member advocate."
                recorded_kind = "handed_off"
                note = "Captured automatically: the chat could not look it up and offered a person."
            elif found.get("ai_source") == "expired":
                kind = "abstain"
                reply = found.get("note") or "This answer is past its review date and is waiting for Legal."
                recorded_kind = None
                note = ""
            elif found.get("abstained"):
                kind = "clarify"
                indexes = closest_topics(conn, question)
                suggestions = [
                    {"index": index, "label": MEMBER_TOPICS[index]["label"], "question": MEMBER_TOPICS[index]["question"]}
                    for index in indexes
                ]
                names = " or ".join(item["label"].lower() for item in suggestions)
                reply = "I want to give you the right answer. "
                if names:
                    reply += f"Is this about {names}? "
                reply += "Tap a topic, or I can connect you with a member advocate."
                recorded_kind = "clarified"
                note = "Captured automatically: no approved answer matched, so the chat asked a clarifying question."
            else:
                kind = "answer"
                citation = f"Source: Harbor Health, {plain_title(found.get('title') or '')}, version {found.get('version')}"
                reply = (found.get("member_text") or "").strip()
                note = ""
            payload_body = {
                "kind": kind,
                "abstained": bool(found.get("abstained")),
                "reply": reply,
                "member_text": found.get("member_text") or "",
                "citation": (
                    f"Source: Harbor Health, {plain_title(found.get('title') or '')}, version {found.get('version')}"
                    if kind == "answer"
                    else ""
                ),
                "title": found.get("title") or "",
                "version": found.get("version"),
                "unit_id": found.get("unit_id") or "",
                "question": question,
                "suggestions": suggestions,
                "ai_source": source,
                "ai_caption": found.get("ai_caption") or "",
                "note": found.get("note") or "",
                "used_live": used_live,
                "show_unit_id": False,
                "units": (
                    [{
                        "unit_id": found.get("unit_id") or "",
                        "version": found.get("version"),
                        "title": found.get("title") or "",
                        "text": found.get("member_text") or "",
                        "approved_by": found.get("approved_by") or "",
                        "approved_on": found.get("approved_on") or "",
                        "citation": (
                            f"Source: Harbor Health, {plain_title(found.get('title') or '')}, version {found.get('version')}"
                        ),
                    }]
                    if kind == "answer"
                    else []
                ),
            }
        if used_live:
            _note_live(session)
        if recorded_kind and not _seen(session, f"{recorded_kind}::{question}"):
            _record_auto(
                session,
                f"{recorded_kind}::{question}",
                source="channel",
                role="Member",
                kind=recorded_kind,
                question=question,
                note=note,
            )
        wrapped = _finish({
            "message": "Member reply ready.",
            **payload_body,
            "feedback_recorded": recorded_kind,
            "from_visit_cache": False,
            "live_calls_left": _calls_left(session),
            "live_calls_cap": EXPLORE_LIVE_CAP,
        }, session, "explore")
        meta = session.meta()
        cache = dict(meta.get("member_cache") or {})
        cache[cache_key] = wrapped
        meta["member_cache"] = cache
        session.save_meta(meta)
        return _decorate_member(session, member_id, wrapped, intent, second)


def _decorate_member(session, member_id: str, body: dict, intent: dict | None, second: str) -> dict:
    from src.finish import attach_answer_fields

    if second:
        chips = [second]
        chips.extend(list(body.get("chips") or []))
        body["chips"] = chips
    if intent:
        context = {
            key: intent.get(key)
            for key in ("drug_id", "pharmacy", "days", "visit", "network")
            if intent.get(key) not in (None, "")
        }
        if intent.get("drug_id"):
            from src.member_data import drug_by_id

            named = drug_by_id(intent["drug_id"]) or {}
            context["drug_name"] = named.get("name") or ""
        if context:
            meta = session.meta()
            book = dict(meta.get("member_context") or {})
            book[member_id] = context
            meta["member_context"] = book
            session.save_meta(meta)
    return attach_answer_fields(body)


def _saved_only(conn, fn):
    """Run fn against saved answers. The live flag is restored and nothing is committed."""
    row = conn.execute("SELECT value FROM meta WHERE key = 'live_ai'").fetchone()
    previous = row["value"] if row else "0"
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('live_ai', '0') ON CONFLICT(key) DO UPDATE SET value = '0'"
    )
    try:
        return fn()
    finally:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES('live_ai', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (previous,),
        )
        conn.rollback()


def portal_answer(session, world: str, role: str, question: str, member_id: str = "") -> dict:
    """Read one cited answer. This does not log the question or spend a live call."""
    from src.finish import attach_answer_fields, check_question_length

    question = check_question_length(question or "")
    if not question:
        raise APIError("Enter a question.")
    role = _require_role(role)
    with session._lock:
        with session.connection(world) as conn:
            if not has_approved(conn):
                raise APIError("Search has nothing to read yet. Legal must approve units first.")
            if role == "Member":
                chosen = _chat_member(member_id)
                intent = classify_member_question(question)
                if intent is not None:
                    body = chat_intent_view(conn, chosen, question, intent)
                    payload = {
                        "ok": True,
                        "role": "Member",
                        "kind": body.get("kind") or "",
                        "text": body.get("reply") or "",
                        "units": body.get("units") or [],
                        "illustrative": True,
                        "note": "Illustrative, made-up data",
                    }
                    if "price" in body:
                        payload["price"] = body["price"]
                    if "visit_cost" in body:
                        payload["visit_cost"] = body["visit_cost"]
                    if body.get("read_order"):
                        payload["read_order"] = body["read_order"]
                    if body.get("plan_figure"):
                        payload["plan_figure"] = body["plan_figure"]
                    if body.get("ivr_prompts"):
                        payload["ivr_prompts"] = body["ivr_prompts"]
                    return attach_answer_fields(payload)
                found = _saved_only(conn, lambda: member_answer(conn, question, record=False))
                if found.get("ai_source") == "expired":
                    return attach_answer_fields({
                        "ok": True,
                        "role": "Member",
                        "abstained": True,
                        "text": found.get("note") or "",
                        "units": [],
                        "ai_source": "expired",
                        "illustrative": True,
                        "note": "Illustrative, made-up data",
                    })
                citation = ""
                units = []
                if not found.get("abstained") and found.get("member_text"):
                    citation = f"Source: Harbor Health, {plain_title(found.get('title') or '')}, version {found.get('version')}"
                    units = [{
                        "unit_id": found.get("unit_id") or "",
                        "version": found.get("version"),
                        "title": found.get("title") or "",
                        "text": found.get("member_text") or "",
                        "approved_by": found.get("approved_by") or "",
                        "approved_on": found.get("approved_on") or "",
                        "citation": citation,
                    }]
                missing = (found.get("ai_source") or "") == "missing"
                return attach_answer_fields({
                    "ok": True,
                    "role": "Member",
                    "abstained": False if missing else bool(found.get("abstained")),
                    "cache_miss": missing,
                    "text": "" if missing else (found.get("member_text") or ""),
                    "citation": citation,
                    "units": units,
                    "ai_source": found.get("ai_source") or "",
                    "illustrative": True,
                    "note": "Illustrative, made-up data",
                })
            found = _saved_only(conn, lambda: search(conn, role, question, record=False))
            # The explore merge hides the desk copy the saved answer was written against.
            # The published desktop still returns the cost disclaimer for this question.
            if (
                found.get("abstained")
                and role == "Insurance advocate"
                and question.strip().lower() == "what do i say before i quote a cost"
            ):
                from src.finish import guided_score_connection

                published = guided_score_connection()
                try:
                    published_found = search(published, role, question, record=False)
                    if not published_found.get("abstained") and published_found.get("unit"):
                        found = published_found
                        result = search_dict(found)
                    else:
                        result = search_dict(found)
                finally:
                    published.close()
            else:
                result = search_dict(found)
            unit = result.get("unit") or {}
            wording = unit.get("text") if isinstance(unit.get("text"), str) else ""
            missing = (result.get("ai_source") or "") == "missing"
            units = []
            if unit.get("unit_id") and not missing:
                units = [{
                    "unit_id": unit.get("unit_id") or "",
                    "version": unit.get("version"),
                    "title": unit.get("title") or "",
                    "text": wording,
                    "approved_by": unit.get("approved_by") or "",
                    "approved_on": unit.get("approved_on") or "",
                    "citation": f"{unit.get('title')}, version {unit.get('version')}" if unit.get("title") else "",
                }]
            return attach_answer_fields({
                "ok": True,
                "role": role,
                "abstained": False if missing else result.get("abstained"),
                "cache_miss": missing,
                "text": "" if missing else wording,
                "unit_id": "" if missing else (unit.get("unit_id") or ""),
                "version": None if missing else unit.get("version"),
                "citation": "" if missing else (f"{unit.get('title')}, version {unit.get('version')}" if unit.get("title") else ""),
                "units": units,
                "searched": result.get("searched") or [],
                "transfer": result.get("transfer"),
                "ai_source": result.get("ai_source") or "",
                "illustrative": True,
                "note": "Illustrative, made-up data",
            })


def member_helped(session, helped: bool, question: str, unit_id: str) -> dict:
    question = (question or "").strip()
    if helped:
        return {"ok": True, "message": "Thanks. Your feedback goes to the knowledge team.", "recorded": False}
    if not question:
        raise APIError("A question is required.")
    with session._lock:
        if not session.explore_ready():
            raise APIError("Open an Explore role before using the sandbox.")
        with session.mutation("explore", "Member said the answer did not help.") as conn:
            try:
                row = record_feedback(
                    conn,
                    "channel",
                    "Member",
                    "not_helpful",
                    question,
                    unit_id or "",
                    "Member tapped No on Did that answer help?",
                    {},
                )
            except ValueError as exc:
                raise APIError(str(exc)) from exc
        return _finish({
            "message": "Thanks. Your feedback goes to the knowledge team.",
            "recorded": True,
            "feedback": feedback_dict(row) if not isinstance(row, dict) else row,
        }, session, "explore")


def run_wrapup(session, world: str, fields: dict) -> dict:
    label = "Wrap-up saved."
    unit_ids = fields.get("unit_ids") or []
    if not isinstance(unit_ids, list):
        raise APIError("The field unit_ids is missing or invalid.")
    with session._lock:
        with session.mutation(world, label) as conn:
            try:
                saved = record_wrapup(
                    conn,
                    fields.get("role") or "",
                    fields.get("call_id") or "",
                    fields.get("call_reason") or "",
                    unit_ids,
                    fields.get("read_verbatim"),
                    fields.get("outcome") or "",
                    fields.get("note") or "",
                    fields.get("displayed_units"),
                )
            except ValueError as exc:
                raise APIError(str(exc)) from exc
            payload = {"message": label, "wrapup": saved, "summary": wrapup_summary(conn)}
        return _finish(payload, session, world)


def run_acknowledge(session, world: str, role: str, unit_id: str, version) -> dict:
    role = (role or "").strip()
    if role not in ADVOCATE_ROLES:
        raise APIError("Only an advocate can acknowledge a change.")
    unit_id = (unit_id or "").strip()
    if version is None or isinstance(version, bool) or not isinstance(version, int) or not unit_id:
        raise APIError("That unit version does not exist.", 404)
    with session._lock:
        with session.connection(world) as conn:
            existing = conn.execute(
                "SELECT 1 FROM units WHERE unit_id = ? AND version = ?",
                (unit_id, version),
            ).fetchone()
            if existing is None:
                raise APIError("That unit version does not exist.", 404)
            already = conn.execute(
                "SELECT 1 FROM change_acks WHERE role = ? AND unit_id = ? AND version = ?",
                (role, unit_id, version),
            ).fetchone()
            if already:
                message, _created = acknowledge_change(conn, role, unit_id, version)
                payload = {"message": message, "changes": changes_payload(conn, role)}
                return _finish(payload, session, world)
            preview = conn.execute(
                "SELECT title FROM units WHERE unit_id = ? AND version = ?",
                (unit_id, version),
            ).fetchone()
            title = preview["title"] if preview is not None else ""
        message = f"Acknowledged version {version} of {wording_title(title)}."
        with session.mutation(world, message) as conn:
            try:
                message, _created = acknowledge_change(conn, role, unit_id, version)
            except LookupError as exc:
                raise APIError(str(exc), 404) from exc
            except ValueError as exc:
                raise APIError(str(exc)) from exc
            payload = {"message": message, "changes": changes_payload(conn, role)}
        return _finish(payload, session, world)


def _sandbox_world(session, world: str, allowed: tuple[str, ...]) -> None:
    from src.finish import require_actor

    if world != "explore":
        raise APIError("This route is for the explore sandbox.")
    if not session.explore_ready():
        raise APIError("Open an Explore role before using the sandbox.")
    require_actor(session, world, allowed)


def _decision_payload(conn, unit_id: str, action: str) -> dict:
    from api.serialize import unit_dict

    row = conn.execute(
        "SELECT * FROM units WHERE unit_id = ? ORDER BY version DESC LIMIT 1",
        (unit_id,),
    ).fetchone()
    decision = conn.execute(
        "SELECT actor, action, ts, reason, detail FROM review_decisions WHERE unit_id = ? ORDER BY id DESC LIMIT 1",
        (unit_id,),
    ).fetchone()
    recorded = {}
    if decision is not None:
        recorded = {
            "actor": decision["actor"],
            "action": decision["action"],
            "ts": decision["ts"],
            "reason": decision["reason"] or "",
            "detail": decision["detail"] or "",
        }
    return {
        "message": f"Recorded {action} on {unit_id}.",
        "unit_id": unit_id,
        "action": action,
        "status": row["status"] if row else "",
        "decision": recorded,
        "unit": unit_dict(row) if row is not None else {},
    }


def run_add_unit(session, world: str, doc_id: str, fields: dict) -> dict:
    from src.sandbox import add_unit_from_span

    _sandbox_world(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, f"Added a unit to {doc_id}.") as conn:
            message, unit_id = add_unit_from_span(
                conn,
                doc_id,
                fields.get("span") or "",
                title=fields.get("title") or "",
                unit_type=fields.get("type") or "procedure",
                audience=fields.get("audience"),
                tags=fields.get("tags"),
            )
            if message:
                raise APIError(message)
            row = conn.execute("SELECT routing_reason, requires_legal FROM units WHERE unit_id = ? AND version = 1", (unit_id,)).fetchone()
            payload = {
                "message": f"Added {unit_id}. It waits for your decision.",
                "unit_id": unit_id,
                "routing_reason": row["routing_reason"] if row else "",
                "requires_legal": bool(row["requires_legal"]) if row else False,
            }
        return _finish(payload, session, world)


def run_unit_review(session, world: str, unit_id: str, fields: dict) -> dict:
    from src.sandbox import review_unit

    _sandbox_world(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, f"Reviewed {unit_id}.") as conn:
            message = review_unit(
                conn,
                unit_id,
                fields.get("action") or "",
                reason=fields.get("reason") or "",
                text=fields.get("text"),
                member_text=fields.get("member_text"),
                unit_type=fields.get("type"),
                tags=fields.get("tags"),
                audience=fields.get("audience"),
            )
            if message:
                raise APIError(message)
            payload = _decision_payload(conn, unit_id, fields.get("action") or "")
        return _finish(payload, session, world)


def run_placeholder_source(session, world: str, gap_id: str, index: int, fields: dict) -> dict:
    from src.sandbox import gap_sources_public, ground_placeholder

    _sandbox_world(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, f"Grounded a placeholder on {gap_id}.") as conn:
            message = ground_placeholder(
                conn,
                gap_id,
                index,
                fields.get("kind") or "",
                ref=fields.get("ref") or "",
                quote=fields.get("quote") or "",
                owner_role=fields.get("owner_role") or "",
                question=fields.get("question") or "",
            )
            if message:
                raise APIError(message)
            payload = {
                "message": "Grounded the placeholder.",
                "gap_id": gap_id,
                "index": index,
                "placeholders": gap_sources_public(conn, gap_id),
            }
        return _finish(payload, session, world)


def run_placeholder_fill(session, world: str, gap_id: str, index: int, text: str) -> dict:
    from src.sandbox import fill_placeholder, gap_sources_public

    _sandbox_world(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, f"Filled a placeholder on {gap_id}.") as conn:
            message = fill_placeholder(conn, gap_id, index, text)
            if message:
                raise APIError(message)
            payload = {
                "message": "Filled the placeholder from the cited source.",
                "gap_id": gap_id,
                "index": index,
                "placeholders": gap_sources_public(conn, gap_id),
            }
        return _finish(payload, session, world)


def run_source_answer(session, world: str, request_id: str, statement: str, signer: str, no_policy: bool = False) -> dict:
    from src.sandbox import answer_source_request, list_source_requests

    _sandbox_world(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, f"Answered source request {request_id}.") as conn:
            message = answer_source_request(conn, request_id, statement, signer, no_policy)
            if message:
                raise APIError(message)
            match = next(item for item in list_source_requests(conn) if item["id"] == request_id)
            payload = {
                "message": (
                    "Simulated owner reply: no policy exists. The question went to the knowledge owner. The business has no answer yet."
                    if no_policy
                    else "Simulated owner reply."
                ),
                "request": match,
            }
        return _finish(payload, session, world)


def run_gap_no_source(session, world: str, gap_id: str, reason: str) -> dict:
    from src.sandbox import mark_no_source

    _sandbox_world(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, f"Returned {gap_id} to the knowledge owner.") as conn:
            message = mark_no_source(conn, gap_id, reason)
            if message:
                raise APIError(message)
            row = conn.execute("SELECT status, label, reason, cluster FROM gaps WHERE id = ?", (gap_id,)).fetchone()
            payload = {
                "message": "The business has no answer yet.",
                "gap_id": gap_id,
                "status": row["status"],
                "label": row["label"],
                "reason": row["reason"],
                "cluster": row["cluster"],
            }
        return _finish(payload, session, world)


def run_gap_dismiss(session, world: str, gap_id: str, kind: str, reason: str, unit_id: str) -> dict:
    from src.sandbox import dismiss_gap

    _sandbox_world(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, f"Dismissed {gap_id}.") as conn:
            message = dismiss_gap(conn, gap_id, kind, reason, unit_id)
            if message:
                raise APIError(message)
            row = conn.execute("SELECT status, label, reason FROM gaps WHERE id = ?", (gap_id,)).fetchone()
            payload = {
                "message": f"Dismissed. {row['label']}",
                "gap_id": gap_id,
                "status": row["status"],
                "label": row["label"],
                "reason": row["reason"],
            }
        return _finish(payload, session, world)


_DRIFT_DONE = {
    "accept_fix": "Published the fix as a new version. The old version stays in the history.",
    "edit_and_accept": "Published your edited wording as a new version. The old version stays in the history.",
    "keep_current": "Kept the current wording. The reason is saved with the decision.",
    "confirm_cosmetic": "Confirmed as cosmetic. The approved wording did not change.",
    "retire": "Retired the unit. Search no longer uses it.",
}


def run_legal_source_changes(session, world: str) -> dict:
    from src.sandbox import legal_source_changes

    _sandbox_world(session, world, ("Legal approver", "Knowledge Ops author"))
    with session._lock:
        with session.connection(world) as conn:
            items = legal_source_changes(conn)
    return {"count": len(items), "items": items, "illustrative": True}


def run_legal_source_change(session, world: str, drift_id: int, action: str, reason: str, text: str) -> dict:
    from src.sandbox import act_on_legal_source_change

    _sandbox_world(session, world, ("Legal approver",))
    with session._lock:
        with session.mutation(world, f"Legal decided source change {drift_id}.") as conn:
            message = act_on_legal_source_change(conn, drift_id, action, reason, text)
            if message:
                raise APIError(message)
            payload = {"message": _DRIFT_DONE.get(action, "Decision recorded."), "id": drift_id, "action": action}
        return _finish(payload, session, world)


def run_author_drift(session, world: str, drift_id: int, action: str, reason: str, text: str) -> dict:
    from src.sandbox import act_on_author_drift

    _sandbox_world(session, world, ("Knowledge Ops author",))
    with session._lock:
        with session.mutation(world, f"Resolved source change {drift_id}.") as conn:
            message = act_on_author_drift(conn, drift_id, action, reason, text)
            if message:
                raise APIError(message)
            payload = {"message": _DRIFT_DONE.get(action, "Decision recorded."), "id": drift_id, "action": action}
        return _finish(payload, session, world)
