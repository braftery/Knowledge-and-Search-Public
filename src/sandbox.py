"""Explore-only authoring sandbox.

Documents in data/sandbox are loaded only when the database mode is explore.
They stay out of the guided candidate pool. A unit is searchable only after
a person approves it. Figures in these documents are illustrative.
"""

from __future__ import annotations

import json
import re

from src.engine import (
    DATA,
    OPS_SEED_APPROVER,
    OPS_SEED_ROLE,
    _mark_approved,
    apply_prepared_drift,
    log,
    mode_name,
    now_et,
    send_drift_to_legal,
)

_AUTHOR = "Knowledge Ops author"
_LEGAL = "Legal approver"
_PROCESS_LABEL = "The business has no answer yet"
_SIMULATED = "Simulated owner reply"
_KO = "knowledge_ops"
_LEGAL_QUEUE = "legal"

_HOUR_OLD = (
    "Offer a Harbor callback window on weekdays from 8:00 a.m. to 5:00 p.m. Eastern. "
    "These hours are illustrative."
)
_HOUR_NEW = (
    "Offer a Harbor callback window on weekdays from 8:00 a.m. to 6:00 p.m. Eastern. "
    "These hours are illustrative."
)
_NOTE_OLD = "Write the callback reason in the desk note before you end the conversation."
_NOTE_NEW = "Write the callback reason in the desk note before you end the call."
_NUMBER_OLD = "Use only the phone number the person confirmed during this conversation.\n\n"
_CLOSE_OLD = "Read the next two sentences word for word, then stop."
_CLOSE_NEW = "Read the next two sentences word-for-word, then stop."
_POLICY_OLD = "Do not quote a copay, a tier, or a coverage limit to an unverified caller"
_POLICY_NEW = "Do not quote a copay, a tier, a deductible, or a coverage limit to an unverified caller"
_VERBATIM_OLD = "an estimate for a covered in-network medical visit"
_VERBATIM_NEW = "an estimate for a covered, in-network medical visit"
_DUPLICATE_SENTENCE = (
    "Specialty drugs stay at Harbor Specialty Pharmacy and are not converted to mail order on this call."
)
_PA_TIME = (
    "A standard prior authorization decision takes 4 business days after Harbor receives a complete request. "
    "An expedited request takes 24 hours. These figures are illustrative."
)

UNANSWERED_GROUP = "Unanswered questions"
_WEB_MAIL_LINE = (
    "You can get up to a 90-day supply of most maintenance medicines, including insulin, "
    "delivered to your home through Harbor Mail Pharmacy."
)
_PA_TIME_SENTENCE = "A standard prior authorization decision takes 4 business days after Harbor receives a complete request."

# What the AI found for each seeded question, searching every document Harbor holds. Illustrative.
GAP_CANDIDATES = {
    "gap-pa-time": {
        "kind": "document",
        "ref": "SRC-PA-FAQ-001",
        "quote": _PA_TIME_SENTENCE,
        "fill": "4 business days",
        "trust": "review_backlog",
        "trust_label": "Harbor document, waiting in Documents to review",
        "note": "The prior authorization FAQ answers this, but nobody has reviewed that FAQ yet, so search cannot use it.",
        "owner_role": "Pharmacy Knowledge",
    },
    "gap-insulin-mail": {
        "kind": "document",
        "ref": "SRC-WEB-MAIL-001",
        "quote": _WEB_MAIL_LINE,
        "fill": "",
        "trust": "unreviewed",
        "trust_label": "Public website copy, not reviewed by Knowledge Ops or Legal",
        "note": "The member website says insulin is available by mail for 90 days. The page was last updated in March 2025 and states no conditions.",
        "owner_role": "Pharmacy Operations",
    },
    "gap-ride": {
        "kind": "",
        "ref": "",
        "quote": "",
        "fill": "",
        "trust": "none",
        "trust_label": "No source found",
        "note": "No Harbor document, website page, or approved unit mentions rides or transportation to appointments.",
        "owner_role": "Care Coordination",
    },
}

KO_WORK_GROUPS = (
    "Documents to review",
    UNANSWERED_GROUP,
    "Source changes",
    "Sent back by Legal",
)


def ensure_sandbox_schema(conn) -> None:
    unit_cols = {item[1] for item in conn.execute("PRAGMA table_info(units)")}
    if "duplicate_of" not in unit_cols:
        conn.execute("ALTER TABLE units ADD COLUMN duplicate_of TEXT DEFAULT ''")
    if "sources_json" not in unit_cols:
        conn.execute("ALTER TABLE units ADD COLUMN sources_json TEXT DEFAULT ''")
    if "routing_owner" not in unit_cols:
        conn.execute("ALTER TABLE units ADD COLUMN routing_owner TEXT DEFAULT ''")
    gap_cols = {item[1] for item in conn.execute("PRAGMA table_info(gaps)")}
    if "label" not in gap_cols:
        conn.execute("ALTER TABLE gaps ADD COLUMN label TEXT DEFAULT ''")
    if "needs_source" not in gap_cols:
        conn.execute("ALTER TABLE gaps ADD COLUMN needs_source INTEGER DEFAULT 0")
    doc_cols = {item[1] for item in conn.execute("PRAGMA table_info(documents)")}
    for name in ("signer", "owner_role", "attested_on", "statement"):
        if name not in doc_cols:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {name} TEXT DEFAULT ''")
    request_cols = {item[1] for item in conn.execute("PRAGMA table_info(source_requests)")}
    if request_cols and "outcome" not in request_cols:
        conn.execute("ALTER TABLE source_requests ADD COLUMN outcome TEXT DEFAULT ''")
    drift_cols = {item[1] for item in conn.execute("PRAGMA table_info(drift_log)")}
    if "owner_queue" not in drift_cols:
        conn.execute("ALTER TABLE drift_log ADD COLUMN owner_queue TEXT DEFAULT ''")
    if "reason" not in drift_cols:
        conn.execute("ALTER TABLE drift_log ADD COLUMN reason TEXT DEFAULT ''")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS review_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            unit_id TEXT,
            actor TEXT,
            action TEXT,
            reason TEXT,
            detail TEXT
        );
        CREATE TABLE IF NOT EXISTS source_requests (
            id TEXT PRIMARY KEY,
            ts TEXT,
            gap_id TEXT,
            placeholder_index INTEGER,
            owner_role TEXT,
            question TEXT,
            status TEXT,
            statement TEXT,
            signer TEXT,
            doc_id TEXT,
            simulated INTEGER DEFAULT 0,
            answered_at TEXT,
            outcome TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS gap_sources (
            gap_id TEXT,
            placeholder_index INTEGER,
            token TEXT,
            kind TEXT,
            ref TEXT,
            quote TEXT,
            request_id TEXT,
            filled_text TEXT,
            PRIMARY KEY (gap_id, placeholder_index)
        );
        """
    )
    conn.commit()


def _words(text: str) -> list[str]:
    return [part for part in (text or "").split() if part.strip()]


def four_words(text: str) -> bool:
    return len(_words(text)) >= 4


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def _csv(values) -> str:
    if isinstance(values, str):
        return values
    return ", ".join(str(item).strip() for item in values if str(item).strip())


def _split(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _mentions_cost(text: str) -> bool:
    from src.engine import _mentions_cost as mentions

    return mentions(text or "", "")


def routing_for(unit_type: str, text: str, tags: list[str], duplicate_of: str, *, keep_legal: bool = False) -> tuple[str, str, int]:
    """Who may approve this unit, the plain reason, and whether Legal is required.

    A duplicate stays with Knowledge Ops so they can reject it.
    Cost, clinical, policy, and verbatim wording go to Legal.
    An edit never lowers a gate that was already Legal.
    """
    kind = (unit_type or "procedure").strip()
    tag_set = {item.lower() for item in tags}
    if duplicate_of and not keep_legal:
        return _KO, f"Duplicate of {duplicate_of}. Knowledge Ops should reject it", 0
    if kind == "verbatim":
        return _LEGAL_QUEUE, "Verbatim line members hear. Legal approves this wording", 1
    if _mentions_cost(text) or "cost" in tag_set:
        return _LEGAL_QUEUE, "Cost statement. Legal approves cost wording", 1
    if "clinical" in tag_set:
        return _LEGAL_QUEUE, "Clinical statement. Legal approves clinical wording", 1
    if kind == "policy":
        return _LEGAL_QUEUE, "Policy wording. Legal approves it", 1
    if keep_legal:
        return _LEGAL_QUEUE, "This unit was sent to Legal. Legal still approves it", 1
    if kind == "faq":
        return _KO, "FAQ. Knowledge Ops can approve it", 0
    return _KO, "Procedure. Knowledge Ops can approve it", 0


def _record(conn, unit_id: str, action: str, reason: str = "", detail: str = "", actor: str = _AUTHOR) -> dict:
    when = now_et()
    conn.execute(
        """
        INSERT INTO review_decisions(ts, unit_id, actor, action, reason, detail)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (when, unit_id, actor, action, reason or "", detail or ""),
    )
    tail = f" {reason}" if reason else ""
    log(conn, actor, f"Human decision: {action} {unit_id}.{tail}")
    return {"actor": actor, "action": action, "ts": when, "reason": reason or "", "detail": detail or ""}


def _unit_row(conn, unit_id: str):
    return conn.execute(
        "SELECT * FROM units WHERE unit_id = ? ORDER BY version DESC LIMIT 1",
        (unit_id,),
    ).fetchone()


def _insert_extracted(conn, spec: dict, body: str) -> None:
    span = spec["span"]
    if span not in body:
        raise RuntimeError(f"{spec['unit_id']} span is not in {spec['source_doc']}")
    tags = spec.get("tags") or []
    duplicate_of = spec.get("duplicate_of") or ""
    owner, reason, requires = routing_for(spec["type"], spec["text"], tags, duplicate_of)
    audience = spec.get("audience") or ["advocate"]
    channels = spec.get("channels") or (["advocate_guidance", "member_chat", "website"] if "member" in audience else ["advocate_guidance"])
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, tags, tags_confirmed, domain,
            kb_scope, audience, channels, status, search_visible, source_doc,
            source_quote, approved_by, approved_on, stale, proposed_text,
            requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered,
            member_text, applicability, effective_date, review_by, origin, routing_reason,
            duplicate_of, routing_owner, drafted_by
        ) VALUES (
            ?, 1, ?, ?, ?, ?, 0, ?,
            ?, ?, ?, 'extracted', 0, ?,
            ?, '', '', 0, '',
            ?, '', ?, 0, 0,
            ?, ?, '', '2027-11-06', 'sandbox', ?,
            ?, ?, 'AI extraction'
        )
        """,
        (
            spec["unit_id"],
            spec["title"],
            spec["type"],
            spec["text"],
            _csv(tags),
            spec.get("domain") or "Harbor sandbox",
            _csv(spec["kb_scope"]),
            _csv(audience),
            _csv(channels),
            spec["source_doc"],
            span,
            requires,
            spec.get("notes") or "",
            spec.get("member_text") or "",
            spec.get("applicability") or "Harbor Medicare Advantage, illustrative",
            reason,
            duplicate_of,
            owner,
        ),
    )
    for kb in spec["kb_scope"]:
        conn.execute(
            "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, 1, ?)",
            (spec["unit_id"], kb),
        )


def _specs(duplicate_of: str) -> list[dict]:
    pharmacy = ["pharmacy"]
    both = ["benefits", "pharmacy"]
    return [
        {
            "unit_id": "U-SOP-REFERRAL",
            "title": "Confirm the specialty referral before intake",
            "type": "procedure",
            "text": "Confirm the specialty referral is on the account before you open an intake.",
            "span": "Confirm the specialty referral is on the account before you open an intake.",
            "tags": ["intake", "referral-check"],
            "source_doc": "SRC-SPEC-SOP-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "specialty intake",
        },
        {
            "unit_id": "U-SOP-RECORD",
            "title": "Record the prescriber and the medicine",
            "type": "procedure",
            "text": "Record the prescriber name and the medicine name on the intake form before you save it.",
            "span": "Record the prescriber name and the medicine name on the intake form before you save it.",
            "tags": ["intake", "prescriber"],
            "source_doc": "SRC-SPEC-SOP-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "specialty intake",
        },
        {
            "unit_id": "U-SOP-SEND",
            "title": "Send the intake the same day",
            "type": "procedure",
            "text": "Send the completed intake packet to the specialty desk on the same business day.",
            "span": "Send the completed intake packet to the specialty desk on the same business day.",
            "tags": ["intake", "handoff"],
            "source_doc": "SRC-SPEC-SOP-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "specialty intake",
        },
        {
            "unit_id": "U-SOP-COPAY",
            "title": "Specialty intake copay",
            "type": "policy",
            "text": "The specialty intake copay listed for this step is $40. This figure is illustrative.",
            "span": "The specialty intake copay listed for this step is $40. This figure is illustrative.",
            "tags": ["cost", "intake"],
            "source_doc": "SRC-SPEC-SOP-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "specialty intake",
            "member_text": "The specialty intake copay on this step is $40. This figure is illustrative.",
        },
        {
            "unit_id": "U-SOP-DUPLICATE",
            "title": "Specialty pharmacy line already approved",
            "type": "policy",
            "text": _DUPLICATE_SENTENCE,
            "span": _DUPLICATE_SENTENCE,
            "tags": ["duplicate"],
            "source_doc": "SRC-SPEC-SOP-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "specialty intake",
            "duplicate_of": duplicate_of,
            "notes": f"Duplicate of {duplicate_of}.",
        },
        {
            "unit_id": "U-PA-START",
            "title": "How to start a prior authorization",
            "type": "faq",
            "text": "Start a prior authorization by entering the prescriber request in the intake tool before you promise a date.",
            "span": "Start a prior authorization by entering the prescriber request in the intake tool before you promise a date.",
            "tags": ["prior-authorization", "faq"],
            "source_doc": "SRC-PA-FAQ-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "prior authorization",
        },
        {
            "unit_id": "U-PA-ATTACH",
            "title": "What to attach to a prior authorization",
            "type": "faq",
            "text": "Attach the prescriber notes and the member medicine list to the request.",
            "span": "Attach the prescriber notes and the member medicine list to the request.",
            "tags": ["prior-authorization", "faq"],
            "source_doc": "SRC-PA-FAQ-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "prior authorization",
        },
        {
            "unit_id": "U-PA-TIMING",
            "title": "How long a standard prior authorization decision takes",
            "type": "faq",
            "text": _PA_TIME,
            "span": _PA_TIME,
            "tags": ["prior-authorization", "faq", "timing"],
            "source_doc": "SRC-PA-FAQ-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "prior authorization",
            "notes": "Illustrative figures. Gap grounding can cite this passage.",
        },
        {
            "unit_id": "U-PA-TELL",
            "title": "Who tells the member about a prior authorization decision",
            "type": "faq",
            "text": "Tell the member that the prescriber office receives the decision, and offer to explain the next step in plain words.",
            "span": "Tell the member that the prescriber office receives the decision, and offer to explain the next step in plain words.",
            "tags": ["prior-authorization", "faq"],
            "source_doc": "SRC-PA-FAQ-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "prior authorization",
        },
        {
            "unit_id": "U-PA-CLINICAL",
            "title": "Do not advise stopping a medicine during prior authorization",
            "type": "policy",
            "text": "Do not advise the member to stop a prescribed medicine while a prior authorization is pending.",
            "span": "Do not advise the member to stop a prescribed medicine while a prior authorization is pending.",
            "tags": ["clinical", "prior-authorization"],
            "source_doc": "SRC-PA-FAQ-001",
            "kb_scope": pharmacy,
            "audience": ["advocate"],
            "domain": "prior authorization",
        },
        {
            "unit_id": "U-CB-HOURS",
            "title": "Weekday callback window",
            "type": "procedure",
            "text": _HOUR_OLD,
            "span": _HOUR_OLD,
            "tags": ["callback-window"],
            "source_doc": "SRC-CALLBACK-001",
            "kb_scope": both,
            "audience": ["advocate"],
            "domain": "member desk hours",
            "applicability": "Harbor callback desk, illustrative hours",
        },
        {
            "unit_id": "U-CB-NOTE",
            "title": "Write the callback reason in the desk note",
            "type": "procedure",
            "text": _NOTE_OLD,
            "span": _NOTE_OLD,
            "tags": ["callback-window", "desk-note"],
            "source_doc": "SRC-CALLBACK-001",
            "kb_scope": both,
            "audience": ["advocate"],
            "domain": "member desk hours",
        },
        {
            "unit_id": "U-CB-NUMBER",
            "title": "Use the phone number confirmed in this conversation",
            "type": "procedure",
            "text": "Use only the phone number the person confirmed during this conversation.",
            "span": "Use only the phone number the person confirmed during this conversation.",
            "tags": ["callback-window"],
            "source_doc": "SRC-CALLBACK-001",
            "kb_scope": both,
            "audience": ["advocate"],
            "domain": "member desk hours",
        },
        {
            "unit_id": "U-CB-VERBATIM",
            "title": "Callback line members hear",
            "type": "verbatim",
            "text": "We will call you back on the number you confirmed. Please keep that phone nearby.",
            "span": "We will call you back on the number you confirmed. Please keep that phone nearby.",
            "tags": ["verbatim", "callback-window"],
            "source_doc": "SRC-CALLBACK-001",
            "kb_scope": both,
            "audience": ["advocate", "member"],
            "channels": ["advocate_guidance", "member_chat", "voice_bot"],
            "domain": "member desk hours",
            "member_text": "We will call you back on the number you confirmed. Please keep that phone nearby.",
        },
    ]


def _load_docs(conn) -> dict[str, str]:
    files = (
        ("SRC-SPEC-SOP-001", "Specialty pharmacy intake SOP", "sandbox/specialty_pharmacy_intake_sop.md", "Not signed. Waiting for review.", "pharmacy"),
        ("SRC-PA-FAQ-001", "Prior authorization FAQ for advocates", "sandbox/prior_authorization_faq.md", "Not signed. Waiting for review.", "pharmacy"),
        ("SRC-CALLBACK-001", "Member callback policy", "sandbox/member_callback_policy.md", "Not signed. Waiting for review.", "benefits,pharmacy"),
        ("SRC-WEB-MAIL-001", "Member website: mail-order pharmacy page", "sandbox/website_mail_pharmacy.md", "Not reviewed. Public website copy.", "pharmacy"),
    )
    bodies = {}
    for doc_id, title, filename, legal, kb in files:
        body = (DATA / filename).read_text()
        conn.execute(
            "INSERT INTO documents(doc_id, title, body, legal_signed, kb) VALUES(?, ?, ?, ?, ?)",
            (doc_id, title, body, legal, kb),
        )
        bodies[doc_id] = body
    return bodies


def _duplicate_target(conn) -> str:
    row = conn.execute(
        """
        SELECT unit_id FROM units
        WHERE status = 'approved' AND text = ?
        ORDER BY unit_id LIMIT 1
        """,
        (_DUPLICATE_SENTENCE,),
    ).fetchone()
    if row is None:
        raise RuntimeError("The duplicate sentence does not match an approved unit.")
    return row["unit_id"]


def _approve_callback_procedures(conn) -> None:
    when = "2026-10-02 09:00 ET"
    for unit_id in ("U-CB-HOURS", "U-CB-NOTE", "U-CB-NUMBER"):
        _mark_approved(
            conn,
            unit_id,
            OPS_SEED_APPROVER,
            when,
            approver_role=OPS_SEED_ROLE,
            approver_name=OPS_SEED_APPROVER,
            approval_method="seed",
        )
    log(
        conn,
        _AUTHOR,
        "Approved the callback procedures so the source-change cases start on live units. Illustrative.",
    )


def _replace_body(conn, doc_id: str, old: str, new: str) -> None:
    row = conn.execute("SELECT body FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    body = row["body"] or ""
    if old not in body:
        raise RuntimeError(f"{old!r} is not in {doc_id}")
    conn.execute(
        "UPDATE documents SET body = ? WHERE doc_id = ?",
        (body.replace(old, new, 1), doc_id),
    )


def _drift_row(conn, unit_id: str, kind: str, old_span: str, new_span: str, summary: str, proposed: str, status: str, queue: str) -> None:
    conn.execute(
        """
        INSERT INTO drift_log(
            ts, unit_id, version, kind, change, old_span, new_span, summary,
            proposed_text, flagged, ai_source, status, owner_queue
        ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 'cached', ?, ?)
        """,
        (now_et(), unit_id, kind, kind, old_span, new_span, summary, proposed, 1 if queue == "knowledge_ops" and status == "author" else 0, status, queue),
    )
    if status == "author":
        conn.execute("UPDATE units SET stale = 1, proposed_text = ? WHERE unit_id = ? AND status = 'approved'", (proposed, unit_id))


def _seed_callback_drift(conn) -> None:
    """Three source changes that need a Knowledge Ops decision, and one cosmetic edit that is only logged. Illustrative."""
    _replace_body(conn, "SRC-CALLBACK-001", _HOUR_OLD, _HOUR_NEW)
    _replace_body(conn, "SRC-CALLBACK-001", _NOTE_OLD, _NOTE_NEW)
    _replace_body(conn, "SRC-CALLBACK-001", _NUMBER_OLD, "")
    conn.execute("UPDATE units SET source_quote = ? WHERE unit_id = 'U-CB-HOURS' AND version = 1", (_HOUR_NEW,))
    conn.execute("UPDATE units SET source_quote = ? WHERE unit_id = 'U-CB-NOTE' AND version = 1", (_NOTE_NEW,))
    _drift_row(
        conn, "U-CB-HOURS", "material", _HOUR_OLD, _HOUR_NEW,
        "Callback hours changed from 5:00 p.m. to 6:00 p.m. Eastern. These hours are illustrative.",
        _HOUR_NEW, "author", "knowledge_ops",
    )
    _drift_row(
        conn, "U-CB-NOTE", "uncertain", _NOTE_OLD, _NOTE_NEW,
        "\"Conversation\" became \"call\". The AI is not sure this is cosmetic: a call leaves out chat, so the step may no longer apply to chat.",
        _NOTE_NEW, "author", "knowledge_ops",
    )
    _drift_row(
        conn, "U-CB-NUMBER", "removed", _NUMBER_OLD.strip(), "",
        "This sentence was deleted from the callback policy. The approved unit no longer has a source.",
        "", "author", "knowledge_ops",
    )
    _replace_body(conn, "SRC-RX-EDU-001", _CLOSE_OLD, _CLOSE_NEW)
    _drift_row(
        conn, "U-RX-EDU-001-14", "cosmetic", _CLOSE_OLD, _CLOSE_NEW,
        "\"word for word\" became \"word-for-word\". Cosmetic, logged automatically.",
        "", "logged", "knowledge_ops",
    )
    log(conn, "System", "Cosmetic edit logged automatically: hyphenation in the closing-line procedure.")
    log(conn, _AUTHOR, "Three source changes are waiting for Knowledge Ops. The approved versions stay live.")


def _seed_more_legal_drift(conn) -> None:
    """Two more source changes for Legal: a material policy edit, and a comma inside word-for-word wording. Illustrative."""
    _replace_body(conn, "SRC-RX-EDU-001", _POLICY_OLD, _POLICY_NEW)
    live = conn.execute("SELECT text FROM units WHERE unit_id = 'U-RX-EDU-001-07' AND status = 'approved' ORDER BY version DESC LIMIT 1").fetchone()
    _drift_row(
        conn, "U-RX-EDU-001-07", "material", _POLICY_OLD, _POLICY_NEW,
        "A deductible was added to what advocates may not quote to an unverified caller.",
        (live["text"] if live else _POLICY_OLD).replace(_POLICY_OLD, _POLICY_NEW), "author", "legal",
    )
    _replace_body(conn, "SRC-BEN-COST-001", _VERBATIM_OLD, _VERBATIM_NEW)
    live = conn.execute("SELECT text FROM units WHERE unit_id = 'U-BEN-COST-001-02' AND status = 'approved' ORDER BY version DESC LIMIT 1").fetchone()
    _drift_row(
        conn, "U-BEN-COST-001-02", "cosmetic_verbatim", _VERBATIM_OLD, _VERBATIM_NEW,
        "A comma was added inside the cost disclaimer advocates read word for word. Cosmetic, but word-for-word wording must match its source exactly, so Legal confirms.",
        (live["text"] if live else "").replace(_VERBATIM_OLD, _VERBATIM_NEW), "author", "legal",
    )


def _seed_gaps(conn) -> None:
    drafts = (
        (
            "gap-pa-time",
            "How long does a standard prior authorization decision take?",
            "A standard prior authorization decision takes [standard decision time]. These figures are illustrative.",
            "A standard prior authorization decision takes [standard decision time].",
            "policy",
            "[standard decision time]",
            16,
        ),
        (
            "gap-insulin-mail",
            "Can I get a 90-day insulin supply by mail?",
            "A 90-day insulin supply by mail is [mail insulin rule]. These figures are illustrative.",
            "A 90-day insulin supply by mail is [mail insulin rule].",
            "faq",
            "[mail insulin rule]",
            15,
        ),
        (
            "gap-ride",
            "Can Harbor arrange a ride to my appointment?",
            "Harbor transportation for a visit is [ride rule].",
            "",
            "faq",
            "[ride rule]",
            14,
        ),
    )
    for gap_id, question, text, member, draft_type, token, count in drafts:
        conn.execute(
            """
            INSERT INTO gaps(
                id, cluster, query_example, search_count, roles, draft_title, draft_text,
                draft_tags, status, placeholders, checklist, queries, invented_figures,
                draft_type, draft_member_text, reason, needs_source, label
            ) VALUES (?, ?, ?, ?, 'Pharmacy advocate', ?, ?, 'pharmacy', 'in_review', ?, ?, ?, '', ?, ?, '', 1, '')
            """,
            (
                gap_id,
                question,
                question,
                count,
                question,
                text,
                token,
                "Ground every placeholder in a source before sending.",
                question,
                draft_type,
                member,
            ),
        )
        conn.execute(
            """
            INSERT INTO gap_sources(gap_id, placeholder_index, token, kind, ref, quote, request_id, filled_text)
            VALUES (?, 0, ?, '', '', '', '', '')
            """,
            (gap_id, token),
        )
    log(conn, _AUTHOR, "Three unanswered questions are waiting for Knowledge Ops. Each draft still has a placeholder. Illustrative.")


def _seed_legal_drift(conn) -> None:
    message = apply_prepared_drift(conn, "material")
    if message:
        raise RuntimeError(message)
    message = send_drift_to_legal(conn)
    if message:
        raise RuntimeError(message)


def seed_explore_sandbox(conn) -> None:
    """Load sandbox documents, gap drafts, and drift cases. Explore only."""
    if mode_name(conn) != "explore":
        return
    ensure_sandbox_schema(conn)
    if conn.execute("SELECT 1 FROM documents WHERE doc_id = 'SRC-SPEC-SOP-001'").fetchone():
        return
    bodies = _load_docs(conn)
    duplicate_of = _duplicate_target(conn)
    for spec in _specs(duplicate_of):
        _insert_extracted(conn, spec, bodies[spec["source_doc"]])
    _approve_callback_procedures(conn)
    _seed_callback_drift(conn)
    _seed_gaps(conn)
    _seed_legal_drift(conn)
    _seed_more_legal_drift(conn)
    for doc_id, body in bodies.items():
        if doc_id == "SRC-CALLBACK-001":
            continue
        for spec in _specs(duplicate_of):
            if spec["source_doc"] == doc_id and spec["span"] not in body:
                raise RuntimeError(f"span missing after seed: {spec['unit_id']}")
    conn.commit()


def review_unit(conn, unit_id: str, action: str, *, reason: str = "", text=None, member_text=None, unit_type=None, tags=None, audience=None) -> str:
    """Knowledge Ops review. Returns an error string, or empty on success."""
    action = (action or "").strip()
    if action not in {"approve", "send_to_legal", "edit", "reject"}:
        return "Use approve, send_to_legal, edit, or reject."
    row = _unit_row(conn, unit_id)
    if row is None or (row["origin"] or "") != "sandbox":
        return "That unit is not in the sandbox queue."
    status = row["status"] or ""
    if action == "approve":
        if status != "extracted":
            return "This unit is not waiting for Knowledge Ops."
        owner = row["routing_owner"] or ""
        if owner != _KO:
            cause = row["routing_reason"] or "Legal approves this unit"
            return f"This unit goes to Legal: {cause}."
        when = now_et()
        _mark_approved(
            conn,
            unit_id,
            _AUTHOR,
            when,
            approver_role=_AUTHOR,
            approver_name="Sam Patel (Knowledge Ops)",
            approval_method="single",
        )
        _record(conn, unit_id, "approve")
        conn.commit()
        return ""
    if action == "send_to_legal":
        if status not in {"extracted", "returned"}:
            return "This unit is not waiting to be sent to Legal."
        cause = row["routing_reason"] or "Knowledge Ops asked Legal to review this unit"
        conn.execute(
            """
            UPDATE units
            SET status = 'with_legal', search_visible = 0, requires_legal = 1, routing_owner = ?, routing_reason = ?
            WHERE unit_id = ? AND version = ?
            """,
            (_LEGAL_QUEUE, cause, unit_id, row["version"]),
        )
        _record(conn, unit_id, "send_to_legal", cause)
        conn.commit()
        return ""
    if action == "reject":
        if status not in {"extracted", "returned"}:
            return "This unit is not waiting for Knowledge Ops."
        cause = (reason or "").strip()
        if not four_words(cause):
            return "A rejection needs a reason of at least four words."
        conn.execute(
            """
            UPDATE units
            SET status = 'rejected', search_visible = 0, notes = ?
            WHERE unit_id = ? AND version = ?
            """,
            (cause, unit_id, row["version"]),
        )
        _record(conn, unit_id, "reject", cause)
        conn.commit()
        return ""
    if status not in {"extracted", "returned"}:
        return "This unit is not waiting for Knowledge Ops."
    changed = []
    new_text = row["text"] or ""
    new_member = row["member_text"] or ""
    new_type = row["type"] or "procedure"
    new_tags = _split(row["tags"])
    new_audience = _split(row["audience"])
    if text is not None:
        new_text = text.strip()
        if not new_text:
            return "Write the unit text before saving this edit."
        changed.append("text")
    if member_text is not None:
        new_member = member_text.strip()
        changed.append("member_text")
    if unit_type is not None:
        new_type = unit_type.strip()
        if new_type not in {"verbatim", "policy", "procedure", "faq"}:
            return "Type must be verbatim, policy, procedure, or faq."
        changed.append("type")
    if tags is not None:
        new_tags = [str(item).strip() for item in tags] if not isinstance(tags, str) else _split(tags)
        changed.append("tags")
    if audience is not None:
        if isinstance(audience, str):
            new_audience = _split(audience)
        else:
            new_audience = [str(item).strip() for item in audience if str(item).strip()]
        if not new_audience:
            return "Choose an audience before saving this edit."
        changed.append("audience")
    if not changed:
        return "Send the wording, type, tags, or audience to edit."
    keep_legal = (row["routing_owner"] or "") == _LEGAL_QUEUE or bool(row["requires_legal"])
    if row["duplicate_of"] and not keep_legal:
        keep_legal = False
    owner, cause, requires = routing_for(
        new_type,
        f"{new_text}\n{new_member}",
        new_tags,
        row["duplicate_of"] or "",
        keep_legal=keep_legal and not (row["duplicate_of"] or ""),
    )
    if (row["routing_owner"] or "") == _LEGAL_QUEUE or (bool(row["requires_legal"]) and not (row["duplicate_of"] or "")):
        if owner != _LEGAL_QUEUE:
            owner = _LEGAL_QUEUE
            requires = 1
            cause = row["routing_reason"] or cause
    channels = ["advocate_guidance", "member_chat", "website"] if "member" in new_audience else ["advocate_guidance"]
    if new_type == "verbatim" and "member" in new_audience:
        channels = ["advocate_guidance", "member_chat", "voice_bot"]
    conn.execute(
        """
        UPDATE units
        SET text = ?, member_text = ?, type = ?, tags = ?, audience = ?, channels = ?,
            routing_owner = ?, routing_reason = ?, requires_legal = ?
        WHERE unit_id = ? AND version = ?
        """,
        (
            new_text,
            new_member,
            new_type,
            _csv(new_tags),
            _csv(new_audience),
            _csv(channels),
            owner,
            cause,
            requires,
            unit_id,
            row["version"],
        ),
    )
    _record(conn, unit_id, "edit", detail=", ".join(changed))
    conn.commit()
    return ""


def _latest_units(conn, doc_id: str) -> list:
    return conn.execute(
        """
        SELECT * FROM units
        WHERE source_doc = ? AND version = (
            SELECT MAX(version) FROM units AS newer WHERE newer.unit_id = units.unit_id
        )
        ORDER BY unit_id
        """,
        (doc_id,),
    ).fetchall()


def _count_status(rows) -> dict:
    counts = {
        "waiting_for_ko": 0,
        "with_legal": 0,
        "sent_back": 0,
        "approved": 0,
        "rejected": 0,
        "blocked": 0,
    }
    for row in rows:
        status = row["status"] or ""
        if status == "extracted":
            counts["waiting_for_ko"] += 1
        elif status == "with_legal" or (status == "proposed" and row["requires_legal"]):
            counts["with_legal"] += 1
        elif status == "returned":
            counts["sent_back"] += 1
        elif status == "approved":
            counts["approved"] += 1
        elif status == "rejected":
            counts["rejected"] += 1
        elif status in {"blocked", "blocked_conflict"}:
            counts["blocked"] += 1
    return counts


def author_documents(conn, include_all: bool = False) -> list[dict]:
    from api.catalog import doc_name

    docs = []
    for doc in conn.execute("SELECT doc_id, title, kb FROM documents ORDER BY doc_id").fetchall():
        counts = _count_status(_latest_units(conn, doc["doc_id"]))
        if not include_all and counts["waiting_for_ko"] == 0 and counts["sent_back"] == 0:
            continue
        item = {
            "doc_id": doc["doc_id"],
            "title": doc["title"] or "",
            "name": doc_name(doc["doc_id"]),
            "kb": doc["kb"] or "",
        }
        item.update(counts)
        docs.append(item)
    return docs


def legal_documents(conn) -> list[dict]:
    from api.catalog import doc_name
    from src.engine import waiting_units

    grouped: dict[str, int] = {}
    titles: dict[str, str] = {}
    for row in waiting_units(conn):
        doc_id = row["source_doc"] or ""
        if not doc_id:
            continue
        grouped[doc_id] = grouped.get(doc_id, 0) + 1
        titles[doc_id] = row["source_doc"]
    docs = []
    for doc_id in sorted(grouped):
        title_row = conn.execute("SELECT title, kb FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        docs.append({
            "doc_id": doc_id,
            "title": title_row["title"] if title_row else "",
            "name": doc_name(doc_id),
            "kb": title_row["kb"] if title_row else "",
            "waiting": grouped[doc_id],
        })
    return docs


def _gap(conn, gap_id: str):
    return conn.execute("SELECT * FROM gaps WHERE id = ?", (gap_id,)).fetchone()


def _placeholders(conn, gap_id: str) -> list:
    return conn.execute(
        "SELECT * FROM gap_sources WHERE gap_id = ? ORDER BY placeholder_index",
        (gap_id,),
    ).fetchall()


def _approved_passage(conn, unit_id: str) -> str:
    row = conn.execute(
        """
        SELECT text, member_text, source_quote FROM units
        WHERE unit_id = ? AND status = 'approved'
        ORDER BY version DESC LIMIT 1
        """,
        (unit_id,),
    ).fetchone()
    if row is None:
        return ""
    return "\n".join(part or "" for part in (row["text"], row["member_text"], row["source_quote"]))


def ground_placeholder(conn, gap_id: str, index: int, kind: str, ref: str = "", quote: str = "", owner_role: str = "", question: str = "") -> str:
    row = _gap(conn, gap_id)
    if row is None:
        return "That draft is not in the queue."
    if (row["status"] or "") not in {"proposed", "in_review"}:
        return "This draft is not waiting to be finished."
    slot = conn.execute(
        "SELECT * FROM gap_sources WHERE gap_id = ? AND placeholder_index = ?",
        (gap_id, index),
    ).fetchone()
    if slot is None:
        return "That placeholder is not on this draft."
    kind = (kind or "").strip()
    if kind not in {"unit", "document", "request"}:
        return "Kind must be unit, document, or request."
    if kind == "request":
        owner = (owner_role or "").strip()
        asked = (question or "").strip()
        if not owner:
            return "Name the owner of this fact."
        if not asked:
            return "Write the question for the owner."
        request_id = _next_request_id(conn)
        when = now_et()
        conn.execute(
            """
            INSERT INTO source_requests(
                id, ts, gap_id, placeholder_index, owner_role, question, status,
                statement, signer, doc_id, simulated, answered_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', '', '', '', 0, '')
            """,
            (request_id, when, gap_id, index, owner, asked),
        )
        conn.execute(
            """
            UPDATE gap_sources
            SET kind = 'request', ref = ?, quote = '', request_id = ?, filled_text = ''
            WHERE gap_id = ? AND placeholder_index = ?
            """,
            (owner, request_id, gap_id, index),
        )
        log(conn, _AUTHOR, f"Asked {owner} for a source on {gap_id}. Request {request_id}.")
        conn.commit()
        return ""
    passage_quote = quote or ""
    if kind == "unit":
        haystack = _approved_passage(conn, (ref or "").strip())
        if not passage_quote or passage_quote not in haystack:
            return "That passage is not in the source."
    else:
        doc = conn.execute("SELECT body FROM documents WHERE doc_id = ?", ((ref or "").strip(),)).fetchone()
        if doc is None or not passage_quote or passage_quote not in (doc["body"] or ""):
            return "That passage is not in the source."
    conn.execute(
        """
        UPDATE gap_sources
        SET kind = ?, ref = ?, quote = ?, request_id = '', filled_text = ''
        WHERE gap_id = ? AND placeholder_index = ?
        """,
        (kind, (ref or "").strip(), passage_quote, gap_id, index),
    )
    log(conn, _AUTHOR, f"Grounded placeholder {index} on {gap_id} in {kind} {(ref or '').strip()}.")
    conn.commit()
    return ""


def _next_request_id(conn) -> str:
    highest = 0
    for row in conn.execute("SELECT id FROM source_requests").fetchall():
        text = row["id"] or ""
        if text.startswith("SR-"):
            try:
                highest = max(highest, int(text[3:]))
            except ValueError:
                continue
    return f"SR-{highest + 1}"


def list_source_requests(conn) -> list[dict]:
    items = []
    for row in conn.execute("SELECT * FROM source_requests ORDER BY id").fetchall():
        items.append({
            "id": row["id"],
            "ts": row["ts"] or "",
            "gap_id": row["gap_id"] or "",
            "placeholder_index": row["placeholder_index"],
            "owner_role": row["owner_role"] or "",
            "question": row["question"] or "",
            "status": row["status"] or "",
            "statement": row["statement"] or "",
            "signer": row["signer"] or "",
            "doc_id": row["doc_id"] or "",
            "mark": _SIMULATED if row["simulated"] else "",
            "answered_at": row["answered_at"] or "",
            "outcome": (row["outcome"] if "outcome" in row.keys() else "") or "",
        })
    return items


def _next_attest_id(conn) -> str:
    highest = 0
    for row in conn.execute("SELECT doc_id FROM documents WHERE doc_id LIKE 'SRC-ATTEST-%'").fetchall():
        try:
            highest = max(highest, int((row["doc_id"] or "").split("-")[-1]))
        except ValueError:
            continue
    return f"SRC-ATTEST-{highest + 1}"


def answer_source_request(conn, request_id: str, statement: str, signer: str, no_policy: bool = False) -> str:
    row = conn.execute("SELECT * FROM source_requests WHERE id = ?", (request_id,)).fetchone()
    if row is None:
        return "That source request is not in the queue."
    if (row["status"] or "") != "pending":
        return "This request already has an answer."
    statement = (statement or "").strip()
    signer = (signer or "").strip()
    if not statement:
        return "Write the statement."
    if not signer:
        return "Name the signer."
    when = now_et()
    if no_policy:
        gap_row = _gap(conn, row["gap_id"])
        if gap_row is None or (gap_row["status"] or "") not in {"proposed", "in_review"}:
            return "This question is not waiting for Knowledge Ops."
        # The owner says the company has no answer. No unit can be written, so the question becomes a process gap.
        conn.execute(
            """
            UPDATE source_requests
            SET status = 'answered', statement = ?, signer = ?, doc_id = '', simulated = 1, answered_at = ?, outcome = 'no_policy'
            WHERE id = ?
            """,
            (statement, signer, when, request_id),
        )
        conn.commit()
        return mark_no_source(conn, row["gap_id"], f"{row['owner_role']} ({signer}): {statement}")
    doc_id = _next_attest_id(conn)
    title = f"Attested statement from {row['owner_role']}"
    body = (
        f"# {title}\n\n"
        "Illustrative, made-up data. All figures are illustrative.\n\n"
        f"Statement: {statement}\n\n"
        f"Signer: {signer}\n"
        f"Owner role: {row['owner_role']}\n"
        f"Date: {when}\n"
        f"Marked: {_SIMULATED}\n"
    )
    conn.execute(
        """
        INSERT INTO documents(doc_id, title, body, legal_signed, kb, signer, owner_role, attested_on, statement)
        VALUES (?, ?, ?, ?, 'pharmacy', ?, ?, ?, ?)
        """,
        (doc_id, title, body, f"Attested {when}", signer, row["owner_role"] or "", when, statement),
    )
    conn.execute(
        """
        UPDATE source_requests
        SET status = 'answered', statement = ?, signer = ?, doc_id = ?, simulated = 1, answered_at = ?
        WHERE id = ?
        """,
        (statement, signer, doc_id, when, request_id),
    )
    conn.execute(
        """
        UPDATE gap_sources
        SET quote = ?, ref = ?
        WHERE gap_id = ? AND placeholder_index = ? AND request_id = ?
        """,
        (statement, doc_id, row["gap_id"], row["placeholder_index"], request_id),
    )
    log(conn, _AUTHOR, f"{_SIMULATED} on {request_id}. Attested source {doc_id}.")
    conn.commit()
    return ""


def _cited_passage(conn, slot) -> str:
    if (slot["kind"] or "") == "request":
        request = conn.execute(
            "SELECT statement, status FROM source_requests WHERE id = ?",
            (slot["request_id"],),
        ).fetchone()
        if request is None or (request["status"] or "") != "answered":
            return ""
        return request["statement"] or ""
    return slot["quote"] or ""


def fill_placeholder(conn, gap_id: str, index: int, text: str) -> str:
    row = _gap(conn, gap_id)
    if row is None:
        return "That draft is not in the queue."
    slot = conn.execute(
        "SELECT * FROM gap_sources WHERE gap_id = ? AND placeholder_index = ?",
        (gap_id, index),
    ).fetchone()
    if slot is None:
        return "That placeholder is not on this draft."
    if not (slot["kind"] or ""):
        return "Ground this placeholder in a source before filling it."
    passage = _cited_passage(conn, slot)
    fact = (text or "").strip()
    if not fact or _compact(fact) not in _compact(passage):
        return "That fact is not in the cited source."
    token = slot["token"] or ""
    draft = row["draft_text"] or ""
    member = row["draft_member_text"] or ""
    if token and token in draft:
        draft = draft.replace(token, fact, 1)
    if token and token in member:
        member = member.replace(token, fact, 1)
    conn.execute(
        "UPDATE gaps SET draft_text = ?, draft_member_text = ? WHERE id = ?",
        (draft, member, gap_id),
    )
    conn.execute(
        "UPDATE gap_sources SET filled_text = ? WHERE gap_id = ? AND placeholder_index = ?",
        (fact, gap_id, index),
    )
    log(conn, _AUTHOR, f"Filled placeholder {index} on {gap_id} from the cited source.")
    conn.commit()
    return ""


def gap_sources_public(conn, gap_id: str) -> list[dict]:
    items = []
    for slot in _placeholders(conn, gap_id):
        items.append({
            "index": slot["placeholder_index"],
            "token": slot["token"] or "",
            "kind": slot["kind"] or "",
            "ref": slot["ref"] or "",
            "quote": slot["quote"] or "",
            "request_id": slot["request_id"] or "",
            "filled_text": slot["filled_text"] or "",
            "sourced": bool(slot["kind"]),
            "filled": bool((slot["filled_text"] or "").strip()),
        })
    return items


def gap_ready(conn, row) -> bool:
    text = (row["draft_text"] or "").strip()
    member = row["draft_member_text"] or ""
    from src.engine import bracketed_placeholders

    if not text or bracketed_placeholders(f"{text}\n{member}"):
        return False
    try:
        needs = int(row["needs_source"] or 0)
    except (KeyError, IndexError, TypeError, ValueError):
        needs = 0
    if not needs:
        return True
    slots = _placeholders(conn, row["id"])
    if not slots:
        return False
    return all((slot["kind"] or "") and (slot["filled_text"] or "").strip() for slot in slots)


def block_gap_send(conn, row) -> str:
    try:
        needs = int(row["needs_source"] or 0)
    except (KeyError, IndexError, TypeError, ValueError):
        needs = 0
    if not needs:
        return ""
    if (row["status"] or "") == "process_gap":
        return "This question went back to the knowledge owner. The business has no answer yet."
    if not gap_ready(conn, row):
        return "Ground and fill every placeholder before sending this draft."
    return ""


def copy_gap_sources(conn, unit_id: str, gap_id: str) -> None:
    slots = _placeholders(conn, gap_id)
    if not slots:
        return
    sources = []
    for slot in slots:
        if not (slot["kind"] or ""):
            continue
        sources.append({
            "placeholder": slot["token"] or "",
            "kind": slot["kind"] or "",
            "ref": slot["ref"] or "",
            "quote": slot["quote"] or "",
            "text": slot["filled_text"] or "",
            "request_id": slot["request_id"] or "",
        })
    if not sources:
        return
    first_doc = next((item["ref"] for item in sources if item["kind"] in {"document", "request"} and item["ref"]), "")
    conn.execute(
        """
        UPDATE units
        SET sources_json = ?, source_doc = CASE WHEN source_doc = '' AND ? != '' THEN ? ELSE source_doc END
        WHERE unit_id = ? AND version = 1
        """,
        (json.dumps(sources), first_doc, first_doc, unit_id),
    )


def mark_no_source(conn, gap_id: str, reason: str) -> str:
    row = _gap(conn, gap_id)
    if row is None:
        return "That draft is not in the queue."
    if (row["status"] or "") not in {"proposed", "in_review"}:
        return "This draft is not waiting to be finished."
    if (row["unit_id"] or "").strip():
        return "This draft was already sent to approval."
    cause = (reason or "").strip()
    if not cause:
        return "A reason is required."
    conn.execute(
        """
        UPDATE gaps
        SET status = 'process_gap', reason = ?, label = ?
        WHERE id = ?
        """,
        (cause, _PROCESS_LABEL, gap_id),
    )
    log(
        conn,
        _AUTHOR,
        f"Returned {row['cluster']} to the knowledge owner. {_PROCESS_LABEL} Reason: {cause}",
    )
    conn.commit()
    return ""


def process_gap_follow_up(conn, query: str) -> str:
    if mode_name(conn) != "explore":
        return ""
    folded = _compact(query)
    if not folded:
        return ""
    try:
        rows = conn.execute(
            "SELECT cluster, query_example, label FROM gaps WHERE status = 'process_gap'"
        ).fetchall()
    except Exception:
        return ""
    for row in rows:
        for candidate in (row["query_example"], row["cluster"]):
            if candidate and _compact(candidate) == folded:
                return f"{_PROCESS_LABEL}. Follow up with the knowledge owner."
    return ""


_KIND_LABELS = {
    "material": "Material change",
    "uncertain": "AI not sure it matters",
    "removed": "Source passage deleted",
    "cosmetic_verbatim": "Cosmetic, inside word-for-word wording",
    "cosmetic": "Cosmetic",
}


def drift_payload(conn, queue: str) -> list[dict]:
    """Source changes waiting for one queue, with what a reviewer needs to decide."""
    items = []
    for row in conn.execute(
        "SELECT * FROM drift_log WHERE owner_queue = ? AND status = 'author' ORDER BY id",
        (queue,),
    ).fetchall():
        live = conn.execute(
            """
            SELECT * FROM units
            WHERE unit_id = ? AND status = 'approved'
            ORDER BY version DESC LIMIT 1
            """,
            (row["unit_id"],),
        ).fetchone()
        kind = row["kind"] or "material"
        items.append({
            "id": row["id"],
            "unit_id": row["unit_id"],
            "kind": kind,
            "kind_label": _KIND_LABELS.get(kind, kind),
            "title": (live["title"] if live else "") or row["unit_id"],
            "type": (live["type"] if live else "") or "",
            "doc_id": (live["source_doc"] if live else "") or "",
            "version": live["version"] if live else row["version"],
            "old_wording": live["text"] if live else "",
            "new_wording": row["proposed_text"] or "",
            "source_before": row["old_span"] or "",
            "source_after": row["new_span"] or "",
            "summary": row["summary"] or "",
            "member_text": (live["member_text"] if live else "") or "",
            "queue": "Knowledge Ops" if queue == "knowledge_ops" else "Legal",
            "status": row["status"],
        })
    return items


def author_drift_payload(conn) -> dict:
    items = drift_payload(conn, "knowledge_ops")
    automatic = []
    for row in conn.execute(
        """
        SELECT * FROM drift_log
        WHERE owner_queue = 'knowledge_ops' AND status = 'logged' AND flagged = 0
        ORDER BY id
        """
    ).fetchall():
        automatic.append({
            "id": row["id"],
            "unit_id": row["unit_id"],
            "version": row["version"],
            "summary": row["summary"] or "Cosmetic edit logged, nothing flagged.",
            "old_span": row["old_span"] or "",
            "new_span": row["new_span"] or "",
            "actor": "System",
            "automatic": True,
        })
    return {"items": items, "automatic": automatic}


def _publish_drift_version(conn, live, new_text: str, drift_id: int, note: str, actor: str = _AUTHOR, approver_name: str = "Sam Patel (Knowledge Ops)") -> None:
    new_version = int(live["version"]) + 1
    when = now_et()
    member_text = live["member_text"] or ""
    conn.execute(
        """
        UPDATE units
        SET status = 'superseded', search_visible = 0, stale = 0
        WHERE unit_id = ? AND version = ?
        """,
        (live["unit_id"], live["version"]),
    )
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, tags, tags_confirmed, domain,
            kb_scope, audience, channels, status, search_visible, source_doc,
            source_quote, approved_by, approver_role, approved_on, stale, proposed_text,
            requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered, member_text,
            applicability, effective_date, review_by, origin, routing_reason, routing_owner,
            duplicate_of, approver_name, approval_method
        )
        SELECT unit_id, ?, title, type, ?, tags, tags_confirmed, domain,
               kb_scope, audience, channels, 'approved', 1, source_doc,
               ?, ?, ?, ?, 0, '',
               requires_legal, conflicts_with, ?, source_mismatch, verbatim_altered, ?,
               applicability, ?, review_by, origin, routing_reason, routing_owner,
               duplicate_of, ?, 'single'
        FROM units WHERE unit_id = ? AND version = ?
        """,
        (
            new_version,
            new_text,
            new_text,
            actor,
            actor,
            when,
            note,
            member_text,
            when,
            approver_name,
            live["unit_id"],
            live["version"],
        ),
    )
    from src.finish import copy_sibling_of

    copy_sibling_of(conn, live["unit_id"], new_version)
    for kb in _split(live["kb_scope"]):
        conn.execute(
            "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, ?, ?)",
            (live["unit_id"], new_version, kb),
        )
    conn.execute("UPDATE drift_log SET status = 'approved' WHERE id = ?", (drift_id,))
    log(
        conn,
        actor,
        f"Published {live['unit_id']} version {new_version} from the source change. "
        f"Version {live['version']} stays in the history.",
    )


def act_on_drift(conn, drift_id: int, action: str, queue: str, reason: str = "", text: str = "") -> str:
    """One decision on a source change, for Knowledge Ops or Legal. The approved version stays live until then."""
    action = (action or "").strip()
    allowed = {"accept_fix", "edit_and_accept", "keep_current", "confirm_cosmetic", "retire"}
    if action not in allowed:
        return "Use accept_fix, edit_and_accept, keep_current, confirm_cosmetic, or retire."
    who = _AUTHOR if queue == "knowledge_ops" else _LEGAL
    row = conn.execute("SELECT * FROM drift_log WHERE id = ? AND owner_queue = ?", (drift_id, queue)).fetchone()
    if row is None or (row["status"] or "") != "author":
        return f"That source change is not waiting for {'Knowledge Ops' if queue == 'knowledge_ops' else 'Legal'}."
    kind = row["kind"] or "material"
    live = conn.execute(
        """
        SELECT * FROM units
        WHERE unit_id = ? AND status = 'approved'
        ORDER BY version DESC LIMIT 1
        """,
        (row["unit_id"],),
    ).fetchone()
    if live is None:
        return "The approved version is no longer live."
    if action == "retire" and kind != "removed":
        return "Retire is for a unit whose source passage was deleted."
    if action == "confirm_cosmetic" and kind not in {"uncertain", "cosmetic_verbatim"}:
        return "Only a change the AI was unsure about can be confirmed as cosmetic."
    if kind == "removed" and action in {"accept_fix", "edit_and_accept", "confirm_cosmetic"}:
        return "The source passage was deleted. Retire the unit, or keep it with a reason."
    if action in {"keep_current", "retire"}:
        cause = (reason or "").strip()
        if not four_words(cause):
            return "A reason of at least four words is required."
        if action == "retire":
            conn.execute(
                "UPDATE units SET status = 'retired', search_visible = 0, stale = 0 WHERE unit_id = ? AND version = ?",
                (live["unit_id"], live["version"]),
            )
            conn.execute("UPDATE drift_log SET status = 'retired', reason = ? WHERE id = ?", (cause, drift_id))
        else:
            conn.execute("UPDATE units SET stale = 0 WHERE unit_id = ? AND version = ?", (live["unit_id"], live["version"]))
            conn.execute("UPDATE drift_log SET status = 'kept', reason = ? WHERE id = ?", (cause, drift_id))
        _record(conn, live["unit_id"], action, cause, actor=who)
        conn.commit()
        return ""
    if action == "confirm_cosmetic":
        conn.execute("UPDATE units SET stale = 0 WHERE unit_id = ? AND version = ?", (live["unit_id"], live["version"]))
        conn.execute("UPDATE drift_log SET status = 'confirmed_cosmetic', reason = ? WHERE id = ?", ((reason or "").strip(), drift_id))
        _record(conn, live["unit_id"], "confirm_cosmetic", (reason or "").strip(), actor=who)
        conn.commit()
        return ""
    if action == "edit_and_accept":
        new_text = (text or "").strip()
        if not new_text:
            return "Write the wording before accepting this fix."
    else:
        new_text = (row["proposed_text"] or "").strip()
        if not new_text:
            return "The source change has no proposed wording."
    if queue == "knowledge_ops":
        note = "Published from the Knowledge Ops source change." if action == "accept_fix" else "Published from a Knowledge Ops edit of the source change."
        _publish_drift_version(conn, live, new_text, drift_id, note)
    else:
        note = "Published from the Legal source change." if action == "accept_fix" else "Published from a Legal edit of the source change."
        _publish_drift_version(conn, live, new_text, drift_id, note, actor=_LEGAL, approver_name="Legal approver")
    _record(conn, live["unit_id"], action, detail=f"version {int(live['version']) + 1}", actor=who)
    conn.commit()
    return ""


def act_on_author_drift(conn, drift_id: int, action: str, reason: str = "", text: str = "") -> str:
    return act_on_drift(conn, drift_id, action, "knowledge_ops", reason, text)


def sandbox_search_units(conn) -> list[dict]:
    """Approved sandbox units for explore search. Guided never calls this."""
    if mode_name(conn) != "explore":
        return []
    try:
        rows = conn.execute(
            """
            SELECT * FROM units
            WHERE status = 'approved' AND search_visible = 1 AND origin = 'sandbox'
            ORDER BY unit_id, version DESC
            """
        ).fetchall()
    except Exception:
        return []
    seen = set()
    units = []
    for row in rows:
        if row["unit_id"] in seen:
            continue
        seen.add(row["unit_id"])
        units.append({
            "unit_id": row["unit_id"],
            "title": row["title"] or "",
            "text": row["text"] or "",
            "tags": _split(row["tags"]),
            "domain": row["domain"] or "",
            "type": row["type"] or "",
            "kb_scope": _split(row["kb_scope"]),
            "audience_list": _split(row["audience"]),
            "member_text": row["member_text"] or "",
            "sandbox": True,
            "source_mismatch": 0,
            "verbatim_altered": 0,
        })
    return units


def ko_documents_to_review(conn) -> list[dict]:
    return [doc for doc in author_documents(conn, include_all=False) if doc["waiting_for_ko"] or doc["sent_back"]]


def gap_candidate(conn, gap_id: str) -> dict | None:
    """What the AI found when it searched every Harbor document for this question."""
    spec = GAP_CANDIDATES.get(gap_id)
    if spec is None:
        return None
    from api.catalog import doc_name

    item = dict(spec)
    item["source_name"] = doc_name(spec["ref"]) if spec["ref"] else ""
    if spec["ref"]:
        doc = conn.execute("SELECT legal_signed FROM documents WHERE doc_id = ?", (spec["ref"],)).fetchone()
        item["source_status"] = (doc["legal_signed"] if doc else "") or ""
    else:
        item["source_status"] = ""
    item["illustrative"] = True
    return item


_DISMISS_KINDS = {
    "already_answered": "Already answered by an approved unit",
    "out_of_scope": "Outside what Harbor does",
}


def dismiss_gap(conn, gap_id: str, kind: str, reason: str, unit_id: str = "") -> str:
    row = _gap(conn, gap_id)
    if row is None:
        return "That draft is not in the queue."
    if (row["status"] or "") not in {"proposed", "in_review"}:
        return "This question is not waiting for Knowledge Ops."
    if (row["unit_id"] or "").strip():
        return "This draft was already sent to approval."
    if kind not in _DISMISS_KINDS:
        return "Choose why: already answered, or outside what Harbor does."
    cause = (reason or "").strip()
    if not four_words(cause):
        return "Say why, in at least four words."
    target = (unit_id or "").strip()
    if kind == "already_answered":
        live = conn.execute(
            "SELECT 1 FROM units WHERE unit_id = ? AND status = 'approved'",
            (target,),
        ).fetchone()
        if live is None:
            return "Name the approved unit that already answers it."
    label = _DISMISS_KINDS[kind]
    detail = f"{label}: {target}. {cause}" if target else f"{label}. {cause}"
    conn.execute(
        "UPDATE gaps SET status = 'dismissed', reason = ?, label = ? WHERE id = ?",
        (cause, detail, gap_id),
    )
    log(conn, _AUTHOR, f"Dismissed {row['cluster']}. {detail}")
    conn.commit()
    return ""


def add_unit_from_span(
    conn,
    doc_id: str,
    span: str,
    *,
    title: str = "",
    unit_type: str = "procedure",
    audience: list[str] | None = None,
    tags: list[str] | None = None,
) -> tuple[str, str]:
    """Knowledge Ops turns a passage the AI did not extract into a unit. Returns (message, unit_id).

    The passage must be word for word in the document and must not already be a unit. The new unit waits for a
    decision like any extracted unit, and the routing rule decides whether Knowledge Ops or Legal approves it.
    """
    doc = conn.execute("SELECT doc_id, body, kb FROM documents WHERE doc_id = ?", ((doc_id or "").strip(),)).fetchone()
    if doc is None:
        return "That document is not in the sandbox.", ""
    body = doc["body"] or ""
    passage = (span or "").strip()
    if len(_words(passage)) < 4:
        return "Select a whole statement, at least four words.", ""
    if passage not in body:
        return "That passage is not word for word in the document.", ""
    for row in _latest_units(conn, doc["doc_id"]):
        existing = (row["source_quote"] or row["text"] or "").strip()
        if existing and (passage in existing or existing in passage):
            return f"That passage is already unit {row['unit_id']}.", ""
    kind = (unit_type or "procedure").strip()
    if kind not in {"verbatim", "policy", "procedure", "faq"}:
        return "Type must be verbatim, policy, procedure or faq.", ""
    stem = doc["doc_id"].replace("SRC-", "")
    number = 1
    while conn.execute("SELECT 1 FROM units WHERE unit_id = ?", (f"U-KO-{stem}-{number:02d}",)).fetchone():
        number += 1
    unit_id = f"U-KO-{stem}-{number:02d}"
    kbs = [kb.strip() for kb in (doc["kb"] or "pharmacy").split(",") if kb.strip()]
    who = [item for item in (audience or ["advocate"]) if item in {"advocate", "member"}] or ["advocate"]
    _insert_extracted(
        conn,
        {
            "unit_id": unit_id,
            "title": (title or "").strip() or " ".join(passage.split()[:8]),
            "type": kind,
            "text": passage,
            "span": passage,
            "tags": [tag.strip() for tag in (tags or []) if tag.strip()],
            "source_doc": doc["doc_id"],
            "kb_scope": kbs,
            "audience": who,
            "member_text": passage if "member" in who else "",
            "notes": "Added by Knowledge Ops from the source passage.",
        },
        body,
    )
    conn.execute(
        "UPDATE units SET drafted_by = ? WHERE unit_id = ? AND version = 1",
        (_AUTHOR, unit_id),
    )
    _record(conn, unit_id, "add", detail=f"Added from {doc['doc_id']}: {passage}")
    conn.commit()
    return "", unit_id


def legal_source_changes(conn) -> list[dict]:
    """Every source change waiting for Legal: the original drift case and the sandbox cases, in one shape."""
    from src.engine import legal_drift_items, live_approved

    items = []
    for item in legal_drift_items(conn):
        live = live_approved(conn, item["unit_id"])
        items.append({
            **item,
            "kind": "material",
            "kind_label": _KIND_LABELS["material"],
            "title": (live["title"] if live else "") or item["unit_id"],
            "type": (live["type"] if live else "") or "",
            "doc_id": (live["source_doc"] if live else "") or "",
            "queue": "Legal",
            "status": "sent",
            "legacy": True,
        })
    items.extend(drift_payload(conn, "legal"))
    return items


def act_on_legal_source_change(conn, drift_id: int, action: str, reason: str = "", text: str = "") -> str:
    from src.engine import approve_drift_fix, return_drift_fix

    row = conn.execute("SELECT * FROM drift_log WHERE id = ?", (drift_id,)).fetchone()
    if row is None:
        return "That source change is not waiting for Legal."
    if (row["status"] or "") == "sent":
        if action == "edit_and_accept":
            new_text = (text or "").strip()
            if not new_text:
                return "Write the wording before accepting this fix."
            conn.execute("UPDATE drift_log SET proposed_text = ? WHERE id = ?", (new_text, drift_id))
            return approve_drift_fix(conn)
        if action == "accept_fix":
            return approve_drift_fix(conn)
        if action == "keep_current":
            if not four_words(reason):
                return "A reason of at least four words is required."
            return return_drift_fix(conn, reason.strip())
        return "Use accept_fix, edit_and_accept, or keep_current."
    return act_on_drift(conn, drift_id, action, "legal", reason, text)
