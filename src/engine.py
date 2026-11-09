"""Demo state, retrieval, and evaluation. Cached AI outputs live in fixtures/."""

from __future__ import annotations

import contextvars
import csv
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIXTURES = ROOT / "fixtures"
CATALOG = json.loads((FIXTURES / "catalog.json").read_text())

ROLE_KB = {
    "Pharmacy advocate": ["pharmacy", "shared-legal"],
    "Insurance advocate": ["benefits", "shared-legal"],
    "Member": ["pharmacy", "benefits"],
    "Knowledge Ops author": ["pharmacy", "benefits", "shared-legal"],
    "Legal approver": ["pharmacy", "benefits", "shared-legal"],
    "Knowledge owner": [],
}

ADVOCATE_ROLES = ("Pharmacy advocate", "Insurance advocate")
EXPLORE_ROLES = ADVOCATE_ROLES + (
    "Knowledge Ops author",
    "Legal approver",
    "Member",
    "Knowledge owner",
    "Channel and AI team",
)
WRAP_OUTCOMES = ("resolved", "follow_up", "transferred")

# Content problems go to the Knowledge Ops author. Findability and product
# problems, including a slow answer, go to the product backlog.
FEEDBACK_SOURCES = ("advocate", "channel")
CONTENT_FEEDBACK_KINDS = (
    "couldnt_find",
    "confusing_wording",
    "wrong_or_outdated",
    "no_answer",
    "not_helpful",
)
PRODUCT_FEEDBACK_KINDS = (
    "hard_to_find",
    "rephrased",
    "clarified",
    "handed_off",
    "slow",
)
FEEDBACK_KINDS = CONTENT_FEEDBACK_KINDS + PRODUCT_FEEDBACK_KINDS
_FEEDBACK_EXAMPLE_LIMIT = 3

DOCUMENTS = [
    ("SRC-RX-EDU-001", "Rx education script", "rx_education_script.md", "Legal last signed: 2025-11-02", "pharmacy"),
    ("SRC-RX-EDU-002", "Rx education script, desk copy", "rx_education_script_v2.md", "Legal last signed: not recorded", "pharmacy"),
    ("SRC-WEB-FAQ", "Website FAQ excerpt", "website_faq_excerpt.md", "Page date: 2026-01-18", "pharmacy"),
    ("SRC-BEN-COST-001", "Benefits cost guide", "benefits_cost_guide.md", "Legal last signed: 2025-10-14", "benefits"),
]

STOP = set(
    """
    a an the of to for and or on in at is are was be do does did i you your we our
    me my it this that with before after end line read say says what when how who
    can may from by as them their not
    """.split()
)

def now_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M ET")


def now_iso() -> str:
    """ISO-8601 timestamp in America/New_York, including the offset."""
    return datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds")


_CLIENT_IP: contextvars.ContextVar[str] = contextvars.ContextVar("harbor_client_ip", default="")
_EXPLORE_TIMEOUT: contextvars.ContextVar[bool] = contextvars.ContextVar("harbor_explore_timeout", default=False)
_ACTOR: contextvars.ContextVar[str] = contextvars.ContextVar("harbor_actor", default="")
_RESOURCE: contextvars.ContextVar[str] = contextvars.ContextVar("harbor_resource", default="")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    from src.finish import ensure_schema

    ensure_schema(conn)
    return conn


def _meta_get(conn, key, default=""):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return default if row is None else row["value"]


def _meta_set(conn, key, value):
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def log(conn, role: str, message: str) -> None:
    conn.execute(
        "INSERT INTO activity(ts, role, message) VALUES(?, ?, ?)",
        (now_et(), role, message),
    )
    conn.commit()


def activity(conn, limit=12):
    return conn.execute(
        "SELECT ts, role, message FROM activity ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def flag(conn, key) -> bool:
    return _meta_get(conn, key, "0") == "1"


def mode_name(conn) -> str:
    return _meta_get(conn, "mode", "")


def _create_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT,
            body TEXT,
            legal_signed TEXT,
            kb TEXT
        );
        CREATE TABLE IF NOT EXISTS units (
            unit_id TEXT,
            version INTEGER,
            title TEXT,
            type TEXT,
            text TEXT,
            tags TEXT,
            tags_confirmed INTEGER,
            domain TEXT,
            kb_scope TEXT,
            audience TEXT,
            channels TEXT,
            status TEXT,
            search_visible INTEGER,
            source_doc TEXT,
            source_quote TEXT,
            approved_by TEXT,
            approver_role TEXT DEFAULT '',
            approved_on TEXT,
            stale INTEGER,
            proposed_text TEXT,
            requires_legal INTEGER,
            conflicts_with TEXT,
            notes TEXT,
            source_mismatch INTEGER,
            verbatim_altered INTEGER,
            member_text TEXT DEFAULT '',
            superseded_by TEXT DEFAULT '',
            applicability TEXT DEFAULT '',
            effective_date TEXT DEFAULT '',
            review_by TEXT DEFAULT '',
            origin TEXT DEFAULT '',
            routing_reason TEXT DEFAULT '',
            approver_name TEXT DEFAULT '',
            approval_method TEXT DEFAULT '',
            drafted_by TEXT DEFAULT '',
            source_annotation TEXT DEFAULT '',
            review_extension TEXT DEFAULT '',
            PRIMARY KEY (unit_id, version)
        );
        CREATE TABLE IF NOT EXISTS unit_kb (
            unit_id TEXT,
            version INTEGER,
            kb TEXT
        );
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            role TEXT,
            message TEXT
        );
        CREATE TABLE IF NOT EXISTS gaps (
            id TEXT PRIMARY KEY,
            cluster TEXT,
            query_example TEXT,
            search_count INTEGER,
            roles TEXT,
            draft_title TEXT,
            draft_text TEXT,
            draft_tags TEXT,
            status TEXT,
            placeholders TEXT,
            checklist TEXT,
            queries TEXT,
            invented_figures TEXT DEFAULT '',
            reason TEXT DEFAULT '',
            draft_member_text TEXT DEFAULT '',
            draft_type TEXT DEFAULT '',
            unit_id TEXT DEFAULT '',
            findability INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS drift_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            unit_id TEXT,
            version INTEGER,
            kind TEXT,
            change TEXT,
            old_span TEXT,
            new_span TEXT,
            summary TEXT,
            proposed_text TEXT,
            flagged INTEGER,
            ai_source TEXT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            source TEXT,
            role TEXT,
            kind TEXT,
            question TEXT,
            unit_id TEXT,
            note TEXT,
            signals TEXT,
            route TEXT,
            status TEXT,
            resolution TEXT,
            resolved_on TEXT
        );
        CREATE TABLE IF NOT EXISTS call_wrapups (
            id TEXT PRIMARY KEY,
            role TEXT,
            call_id TEXT,
            call_reason TEXT,
            read_verbatim INTEGER,
            unit_ids TEXT,
            outcome TEXT,
            note TEXT,
            created_at TEXT,
            displayed_units TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS change_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            event TEXT,
            unit_id TEXT,
            version INTEGER,
            previous_version INTEGER,
            actor TEXT,
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS safety_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            question TEXT,
            unit_id TEXT,
            channel TEXT
        );
        CREATE TABLE IF NOT EXISTS change_acks (
            role TEXT,
            unit_id TEXT,
            version INTEGER,
            created_at TEXT,
            PRIMARY KEY (role, unit_id, version)
        );
        """
    )


def _insert_unit(conn, spec, status, search_visible, tags_confirmed, notes=""):
    tags = ", ".join(spec["tags"])
    channels = ", ".join(spec.get("channels") or [])
    audience = ",".join(spec["audience"])
    kb_scope = ",".join(spec["kb_scope"])
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, tags, tags_confirmed, domain,
            kb_scope, audience, channels, status, search_visible, source_doc,
            source_quote, approved_by, approved_on, stale, proposed_text,
            requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered,
            applicability, effective_date, review_by
        ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', 0, '', ?, ?, ?, ?, ?, ?, '', ?)
        """,
        (
            spec["unit_id"],
            spec["title"],
            spec["type"],
            spec["text"],
            tags,
            tags_confirmed,
            spec["domain"],
            kb_scope,
            audience,
            channels,
            status,
            search_visible,
            spec["source_doc"],
            spec["source_quote"],
            spec["requires_legal"],
            spec.get("conflicts_with", ""),
            notes or spec.get("notes", ""),
            spec.get("source_mismatch", 0),
            spec.get("verbatim_altered", 0),
            spec.get("applicability", ""),
            spec.get("review_by", ""),
        ),
    )
    for kb in spec["kb_scope"]:
        conn.execute(
            "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, 1, ?)",
            (spec["unit_id"], kb),
        )


def build_database(path: str, mode: str = "start") -> None:
    target = Path(path)
    if target.exists():
        target.unlink()
    conn = connect(path)
    _create_schema(conn)
    from src.finish import ensure_schema

    ensure_schema(conn)
    for doc_id, title, filename, legal, kb in DOCUMENTS:
        body = (DATA / filename).read_text()
        conn.execute(
            "INSERT INTO documents(doc_id, title, body, legal_signed, kb) VALUES(?, ?, ?, ?, ?)",
            (doc_id, title, body, legal, kb),
        )
    from src.corpus import load_corpus

    for draft in load_corpus()["drafts"]:
        output = draft["output"]
        conn.execute(
            """
            INSERT INTO gaps(
                id, cluster, query_example, search_count, roles, draft_title, draft_text,
                draft_tags, status, placeholders, checklist, queries, invented_figures,
                draft_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?, ?, ?, ?, ?)
            """,
            (
                draft["id"],
                draft["cluster"],
                draft["query_example"],
                draft["search_count"],
                draft["roles"],
                output.get("title", ""),
                output.get("draft_text", ""),
                output.get("suggested_kb", ""),
                ", ".join(output.get("placeholders") or []),
                "\n".join(output.get("author_checklist") or []),
                "\n".join(draft["queries"]),
                ", ".join(draft.get("invented_figures") or []),
                output.get("type", ""),
            ),
        )
    _seed_gap_volumes(conn)
    _meta_set(conn, "mode", mode)
    if mode == "jump":
        log(conn, "Knowledge Ops author", "Jumped to the approved demo state. Illustrative.")
        extract_units(conn, record=True)
        confirm_tags(conn)
        apply_website_merge(conn)
        keep_canonical(conn)
        escalate_conflict(conn)
        approve_units(conn)
    elif mode == "short":
        log(
            conn,
            "Knowledge Ops author",
            "Jumped to the short demo. Extraction and duplicate decisions are loaded. Illustrative.",
        )
        extract_units(conn, record=True)
        keep_canonical(conn)
        apply_website_merge(conn)
        escalate_conflict(conn)
        preapprove_short(conn)
    elif mode == "explore":
        log(conn, "Knowledge Ops author", "Explore sandbox is ready. Illustrative, made-up data.")
        extract_units(conn, record=True)
        confirm_tags(conn)
        apply_website_merge(conn)
        keep_canonical(conn)
        escalate_conflict(conn)
        from src.ai import load_human_decisions

        pending = load_human_decisions().get("explore_pending") or {}
        skip = set(pending.get("legal") or []) | set(pending.get("author") or [])
        approve_units(conn, skip_ids=skip)
        log(
            conn,
            "Knowledge Ops author",
            "Left 3 Legal units and 2 author units waiting. The pricing disclaimer is approved and not revised. Illustrative.",
        )
        set_live(conn, True)
        _seed_explore_feedback(conn)
        conn.execute(
            "UPDATE gaps SET status = 'in_review', reason = ? WHERE id = 'c0'",
            ("Asked with no approved answer; sent to the author.",),
        )
        _merge_explore_copies(conn)
        from src.sandbox import seed_explore_sandbox

        seed_explore_sandbox(conn)
    else:
        log(conn, "Pharmacy advocate", "Demo is at the start. Search can see no units.")
    conn.commit()
    conn.close()


PRICE_ANY_ID = "U-RX-EDU-PRICE-ANY"
PRICE_ANY_MEMBER = (
    "This price is an estimate for the supply and the pharmacy shown. "
    "It uses the plan information we have today. What you pay can change if the pharmacy, "
    "the number of days, or your coverage stage changes. An estimate is not a promise of what you will pay."
)
PRICE_ANY_ADVOCATE = (
    "The price I quote is an estimate for the supply and pharmacy we discussed, based on the plan records I can see today. "
    "Your actual cost can change if the pharmacy, the days' supply, or your stage of coverage is different. "
    "This estimate is not a guarantee of payment."
)


def _seed_price_any_unit(conn) -> None:
    """Approved plan-data wording that search does not see.

    The unit is not in the extraction corpus, and search_visible stays 0, so
    advocate search and member search keep the same candidate pools.
    """
    existing = conn.execute(
        "SELECT 1 FROM units WHERE unit_id = ? AND version = 1",
        (PRICE_ANY_ID,),
    ).fetchone()
    if existing is not None:
        return
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, tags, tags_confirmed, domain,
            kb_scope, audience, channels, status, search_visible, source_doc,
            source_quote, approved_by, approver_role, approved_on, stale, proposed_text,
            requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered,
            member_text, superseded_by, applicability, effective_date, review_by,
            origin, routing_reason
        ) VALUES (
            ?, 1, ?, 'verbatim', ?, 'pricing, disclaimer', 1,
            'Pharmacy education, Medicare Advantage',
            'pharmacy', 'advocate,member',
            'advocate_guidance, member_chat, website, voice_bot',
            'approved', 0, '',
            ?, 'Dana Okafor (Legal)', 'Legal', '2026-09-23 10:15 ET', 0, '',
            1, '', ?, 0, 0,
            ?, '', ?, '2026-09-23 10:15 ET', '2027-09-23',
            'plan-data', ''
        )
        """,
        (
            PRICE_ANY_ID,
            "Drug price estimate disclaimer (any supply or pharmacy)",
            PRICE_ANY_ADVOCATE,
            PRICE_ANY_ADVOCATE,
            "Plan-data wording for a price that is not a 30-day supply at a preferred retail pharmacy. Search does not show this unit.",
            PRICE_ANY_MEMBER,
            "Harbor Medicare Advantage HMO, any drug price quote",
        ),
    )
    conn.execute(
        "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, 1, 'pharmacy')",
        (PRICE_ANY_ID,),
    )


def _seed_support_units(conn) -> None:
    """Approved wording for plan figures, safety, and the phone line.

    search_visible stays 0, so these rows are not in the guided candidate pool.
    """
    from src.compliance import (
        CLAIMS_ID,
        DEDUCT_ID,
        ER_ID,
        IVR_ADD_ID,
        IVR_ADVOCATE_ID,
        IVR_AUTH_ID,
        IVR_BEFORE_ID,
        NOT_ON_LIST_ID,
        OON_RULE_ID,
        OON_VISIT_ID,
        OOP_ID,
        PERSON_ID,
        SAFE_ID,
        UC_ID,
    )

    rows = [
        (
            SAFE_ID,
            "Medical emergency and crisis",
            "If you think you are having a medical emergency, call 911 now. If you are thinking about harming yourself, call or text 988. For a clinical question that is not an emergency, call the Harbor nurse line at 1-800-555-0199.",
            "If the caller may be in danger, stop the script. Say: If you think you are having a medical emergency, call 911 now. If you are thinking about harming yourself, call or text 988. For a clinical question that is not an emergency, the Harbor nurse line is 1-800-555-0199. That number is illustrative.",
            "shared-legal",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 09:00 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            OOP_ID,
            "Out-of-pocket maximum disclaimer",
            "The out-of-pocket maximum and the amount already counted toward it are estimates from the plan records we have today. A claim that is still processing can change the amount. This figure is not a guarantee of what you will pay.",
            "Read this before you quote the out-of-pocket maximum. The figure is an estimate from the plan records on this call. A claim that is still processing can change it. This figure is not a guarantee of what the member will pay.",
            "benefits",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 09:10 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            OON_RULE_ID,
            "Out-of-network coverage rule",
            "Out of network is not covered, except emergency and urgent care.",
            "Out of network is not covered, except emergency and urgent care. Do not cite the referral rule for this sentence.",
            "benefits",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 09:20 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            OON_VISIT_ID,
            "Out-of-network urgent care and emergency disclaimer",
            "This cost is an estimate for out-of-network urgent care or an emergency room visit, based on the plan records we have today. It is not an in-network copay. The amount you pay can change. This estimate is not a guarantee of payment.",
            "Read this before an out-of-network urgent care or emergency room amount. It is not an in-network copay. The amount can change. This estimate is not a guarantee of payment.",
            "benefits",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 09:30 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            ER_ID,
            "Emergency room cost disclaimer",
            "This cost is an estimate for an in-network emergency room visit, based on the plan records we have today. The amount you pay can change. This estimate is not a guarantee of payment.",
            "Read this before an in-network emergency room amount. The amount can change. This estimate is not a guarantee of payment.",
            "benefits",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 09:40 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            UC_ID,
            "Urgent care cost disclaimer",
            "This cost is an estimate for an in-network urgent care visit, based on the plan records we have today. The amount you pay can change. This estimate is not a guarantee of payment.",
            "Read this before an in-network urgent care amount. The amount can change. This estimate is not a guarantee of payment.",
            "benefits",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 09:50 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            CLAIMS_ID,
            "Claims figure disclaimer",
            "Claim amounts on this page are illustrative snapshots from the plan records we have today. A claim that is still processing can change. These figures are not a guarantee of payment.",
            "Claim amounts are illustrative snapshots from the plan records on this call. A claim that is still processing can change. These figures are not a guarantee of payment.",
            "benefits",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 10:00 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            DEDUCT_ID,
            "Part D deductible stage disclaimer",
            "A tier 3 drug is priced in the deductible stage until the Part D deductible is met. The deductible does not apply to tiers 1 and 2. The amount can change when the deductible is met. This estimate is not a guarantee of payment.",
            "Say this before a tier 3 price while the Part D deductible is unmet. The deductible does not apply to tiers 1 and 2. The amount can change when the deductible is met. This estimate is not a guarantee of payment.",
            "pharmacy",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 10:10 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            NOT_ON_LIST_ID,
            "Drug not on the member list",
            "A drug that is not on your list is not part of this price estimate. A member advocate can look at the claim with you.",
            "If the member says the drug is not on their list, do not quote a price for it. A member advocate looks at the claim with them.",
            "pharmacy",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 10:20 ET",
            "member_chat, voice_bot, website, advocate_guidance",
        ),
        (
            IVR_AUTH_ID,
            "Phone line authentication",
            "Please say or enter your member ID, then your date of birth. These checks are illustrative.",
            "Before a member-specific amount on the automated line, collect the member ID and the date of birth. These checks are illustrative.",
            "shared-legal",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 10:30 ET",
            "voice_bot",
        ),
        (
            IVR_BEFORE_ID,
            "Phone line disclaimer lead-in",
            "Before I give you that amount, here is some important information.",
            "Before I give you that amount, here is some important information.",
            "shared-legal",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 10:40 ET",
            "voice_bot",
        ),
        (
            IVR_ADVOCATE_ID,
            "Phone line advocate prompt",
            "Press 0 to talk to a member advocate.",
            "Press 0 to talk to a member advocate.",
            "shared-legal",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 10:50 ET",
            "voice_bot, member_chat",
        ),
        (
            IVR_ADD_ID,
            "Phone line authorized caller prompt",
            "To add someone to your account, press 0 and a member advocate will help you set it up.",
            "To add someone to the account, the caller presses 0 and a member advocate sets it up.",
            "shared-legal",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 11:00 ET",
            "voice_bot, member_chat",
        ),
        (
            PERSON_ID,
            "Talk with a member advocate",
            "A member advocate can talk with you about your account.",
            "Offer a member advocate when the caller asks for a person.",
            "shared-legal",
            "Dana Okafor (Legal)",
            "Legal",
            "2026-08-12 11:10 ET",
            "member_chat, voice_bot, website",
        ),
    ]
    for (
        unit_id,
        title,
        member_text,
        advocate_text,
        kb,
        approver,
        role,
        when,
        channels,
    ) in rows:
        existing = conn.execute(
            "SELECT 1 FROM units WHERE unit_id = ? AND version = 1",
            (unit_id,),
        ).fetchone()
        if existing is not None:
            continue
        conn.execute(
            """
            INSERT INTO units (
                unit_id, version, title, type, text, tags, tags_confirmed, domain,
                kb_scope, audience, channels, status, search_visible, source_doc,
                source_quote, approved_by, approver_role, approved_on, stale, proposed_text,
                requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered,
                member_text, superseded_by, applicability, effective_date, review_by,
                origin, routing_reason, approver_name, approval_method
            ) VALUES (
                ?, 1, ?, 'verbatim', ?, 'plan-data', 1,
                'Harbor Medicare Advantage',
                ?, 'advocate,member',
                ?,
                'approved', 0, '',
                ?, ?, ?, ?, 0, '',
                1, '', 'Plan-data or phone wording. Search does not show this unit.', 0, 0,
                ?, '', 'Harbor Medicare Advantage HMO', ?, '2027-08-12',
                'plan-data', '', ?, 'seed'
            )
            """,
            (
                unit_id,
                title,
                advocate_text,
                kb,
                channels,
                advocate_text,
                approver,
                role,
                when,
                member_text,
                when,
                approver,
            ),
        )
        conn.execute(
            "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, 1, ?)",
            (unit_id, kb),
        )
        if unit_id == SAFE_ID:
            conn.execute(
                "UPDATE units SET approver_name = ? WHERE unit_id = ? AND version = 1",
                ("Riley Chen (Legal and clinical)", unit_id),
            )


def _apply_review_extension(conn) -> None:
    """Guided keeps an explicit extension so the specialty answer stays in the pool.

    Explore does not. A past-review unit with no extension leaves search there.
    """
    if mode_name(conn) == "explore":
        return
    from src.compliance import REVIEW_EXTENSION, SPECIALTY_REVIEW_ID

    conn.execute(
        """
        UPDATE units
        SET review_extension = ?
        WHERE unit_id = ? AND review_extension = ''
        """,
        (REVIEW_EXTENSION, SPECIALTY_REVIEW_ID),
    )


def extract_units(conn, record=True) -> None:
    if flag(conn, "extracted"):
        return
    from src.corpus import as_spec, load_corpus

    corpus = load_corpus()
    for unit in corpus["units"]:
        _insert_unit(conn, as_spec(unit), "proposed", 0, 0)
    for name, unit in corpus["anchors"].items():
        if unit:
            _meta_set(conn, f"anchor_{name}", unit["unit_id"])
    apply_conflict_blocks(conn, corpus["judgments"])
    _meta_set(conn, "extracted", "1")
    if record:
        v1 = [unit for unit in corpus["units"] if unit["source_doc"] == "SRC-RX-EDU-001"]
        mismatches = sum(1 for unit in v1 if unit["source_mismatch"] or unit["verbatim_altered"])
        log(
            conn,
            "Knowledge Ops author",
            f"AI extracted {len(v1)} units from script v1, and {len(corpus['units'])} units across the four sources. "
            f"Source check failures on script v1: {mismatches}. Tags are suggestions. Search can see these units: No.",
        )
    _seed_price_any_unit(conn)
    _seed_support_units(conn)
    _apply_review_extension(conn)
    from src.finish import seed_finish_units

    seed_finish_units(conn)
    conn.commit()


def confirm_tags(conn) -> None:
    from src.ai import audience_list, load_human_decisions, override_channels

    conn.execute("UPDATE units SET tags_confirmed = 1")
    _meta_set(conn, "tags_confirmed", "1")
    log(conn, "Knowledge Ops author", "Confirmed the suggested tags on the extracted units.")
    decisions = load_human_decisions()
    overrides = decisions.get("audience_overrides") or {}
    for unit_id, override in overrides.items():
        audience_values = audience_list(override.get("audience", "advocate"))
        audience = ",".join(audience_values)
        channels = ", ".join(override_channels(override, audience_values))
        member_text = _member_wording(unit_id) or override.get("member_text") or ""
        conn.execute(
            """
            UPDATE units
            SET audience = ?, channels = ?, member_text = CASE WHEN ? != '' THEN ? ELSE member_text END
            WHERE unit_id = ? AND version = 1
            """,
            (audience, channels, member_text, member_text, unit_id),
        )
        if override.get("log"):
            log(conn, "Knowledge Ops author", override["log"])
    conn.commit()


def apply_website_merge(conn) -> None:
    """Record the human merge of the website disclaimer split. Units stay as the model extracted them."""
    if flag(conn, "website_merged"):
        return
    from src.ai import load_human_decisions

    merges = load_human_decisions().get("merges") or []
    if not merges:
        return
    merge = merges[0]
    into_id = merge.get("into_unit_id") or ""
    # The merge record keeps the website sentence. The unit stores channel-neutral wording when a person has approved it.
    member_text = _member_wording(into_id) or merge.get("member_text") or ""
    if into_id and member_text:
        conn.execute(
            "UPDATE units SET member_text = ? WHERE unit_id = ? AND version = 1",
            (member_text, into_id),
        )
    for unit_id in merge.get("unit_ids") or []:
        conn.execute(
            """
            UPDATE units
            SET status = 'merged', search_visible = 0, superseded_by = ?
            WHERE unit_id = ? AND version = 1 AND status = 'proposed'
            """,
            (into_id, unit_id),
        )
    _meta_set(conn, "website_merged", "1")
    log(conn, "Knowledge Ops author", merge.get("action") or "Merged the website units into the pricing disclaimer.")
    conn.commit()


def keep_canonical(conn) -> None:
    if not flag(conn, "extracted"):
        extract_units(conn)
    from src.ai import load_human_decisions
    from src.corpus import load_corpus

    corpus = load_corpus()
    decisions = load_human_decisions()
    choices = decisions.get("canonical_choices") or {}
    chosen = choices.get("pricing_disclaimer", "")
    parts = [f"Kept {chosen} as the canonical pricing disclaimer for the channels."]
    for pair in choices.get("pairs") or []:
        kept = pair.get("kept") or ""
        other = pair.get("superseded") or ""
        if not kept or not other:
            continue
        conn.execute(
            """
            UPDATE units
            SET status = 'superseded', search_visible = 0, superseded_by = ?
            WHERE unit_id = ? AND version = 1 AND status = 'proposed'
            """,
            (kept, other),
        )
        parts.append(f"Superseded {other} by {kept}.")
    by_pair = {(item["a_id"], item["b_id"]): item for item in corpus["judgments"]}
    for watched in decisions.get("watched_pairs") or []:
        if watched.get("a") != chosen and watched.get("b") != chosen:
            continue
        judgment = by_pair.get((watched["a"], watched["b"])) or by_pair.get((watched["b"], watched["a"]))
        if judgment is None:
            parts.append(f"No cached judgment for {watched['a']} and {watched['b']}.")
            continue
        parts.append(
            f"AI judged {judgment['a_id']} and {judgment['b_id']} {judgment['output'].get('relation')}."
        )
    _meta_set(conn, "canonical", "1")
    log(conn, "Knowledge Ops author", " ".join(parts))
    conn.commit()
    apply_member_texts(conn)


def escalate_conflict(conn) -> None:
    from src.ai import load_human_decisions
    from src.corpus import load_corpus

    corpus = load_corpus()
    decisions = load_human_decisions()
    blocked = {
        row["unit_id"]
        for row in conn.execute("SELECT unit_id FROM units WHERE status = 'blocked_conflict'").fetchall()
    }
    mail = [item for item in (decisions.get("watched_pairs") or []) if item.get("label") == "Mail-order rule"]
    notes = []
    for item in mail:
        judgment = next(
            (
                found
                for found in corpus["judgments"]
                if {found["a_id"], found["b_id"]} == {item["a"], item["b"]}
            ),
            None,
        )
        if judgment is None:
            notes.append(f"No cached judgment for {item['a']} and {item['b']}.")
            continue
        relation = judgment["output"].get("relation", "")
        if relation == "conflict" and item["a"] in blocked and item["b"] in blocked:
            notes.append(f"AI marked {item['a']} and {item['b']} as a conflict. Both units are blocked.")
        else:
            notes.append(f"AI judged {item['a']} and {item['b']} as {relation}. Those units were not blocked.")
    if not notes:
        notes.append("No mail-order pair was on the candidate list.")
    for plan in conflict_plans():
        if plan.get("resolve_in_demo"):
            continue
        ids = [plan.get("chosen_unit_id") or "", *(plan.get("retire_unit_ids") or [])]
        ids = [unit_id for unit_id in ids if unit_id]
        if ids and all(unit_id in blocked for unit_id in ids):
            notes.append(
                f"AI marked {plan.get('label', 'a pair')} ({', '.join(ids)}) as a conflict. Those units are blocked."
            )
    _meta_set(conn, "escalated", "1")
    log(
        conn,
        "Knowledge Ops author",
        "Escalated the mail-order disagreement to Legal. " + " ".join(notes),
    )
    conn.commit()


def _member_wording(unit_id: str) -> str:
    """Human-approved member wording for one unit. Empty when none is recorded."""
    from src.ai import load_human_decisions

    spec = (load_human_decisions().get("member_texts") or {}).get(unit_id) or {}
    if isinstance(spec, dict):
        return (spec.get("member_text") or "").strip()
    return ""


def apply_member_texts(conn) -> int:
    """Write human-approved member wording onto units the model marked audience both."""
    from src.ai import load_human_decisions

    decisions = load_human_decisions()
    texts = decisions.get("member_texts") or {}
    merge_targets = {
        item.get("into_unit_id")
        for item in (decisions.get("merges") or [])
        if item.get("into_unit_id")
    }
    applied = 0
    for unit_id, spec in texts.items():
        if unit_id in merge_targets:
            continue
        member_text = spec.get("member_text") if isinstance(spec, dict) else ""
        if not member_text:
            continue
        changed = conn.execute(
            """
            UPDATE units
            SET member_text = ?
            WHERE unit_id = ? AND version = 1 AND (member_text IS NULL OR member_text = '')
            """,
            (member_text, unit_id),
        ).rowcount
        applied += changed
    if applied:
        log(
            conn,
            "Knowledge Ops author",
            f"Approved member wording for {applied} units with audience both. Illustrative.",
        )
    conn.commit()
    return applied


def apply_conflict_blocks(conn, judgments: list[dict]) -> None:
    """A T2 conflict blocks both units. They stay out of approval and search until Legal resolves the pair."""
    blocked: dict[str, set[str]] = {}
    for judgment in judgments:
        if (judgment.get("output") or {}).get("relation") != "conflict":
            continue
        left = judgment["a_id"]
        right = judgment["b_id"]
        blocked.setdefault(left, set()).add(right)
        blocked.setdefault(right, set()).add(left)
    for unit_id, others in blocked.items():
        conn.execute(
            """
            UPDATE units
            SET status = 'blocked_conflict', search_visible = 0, conflicts_with = ?
            WHERE unit_id = ? AND version = 1
            """,
            (",".join(sorted(others)), unit_id),
        )
    conn.commit()


def _mark_approved(
    conn,
    unit_id: str,
    approver: str,
    when: str,
    version: int = 1,
    approver_role: str = "",
    approver_name: str = "",
    approval_method: str = "",
) -> None:
    role = approver_role or approver
    name = approver_name
    method = approval_method
    if not name and "(" in (approver or ""):
        name = approver
        method = method or "seed"
    conn.execute(
        """
        UPDATE units
        SET status = 'approved', search_visible = 1, approved_by = ?, approver_role = ?,
            approved_on = ?, effective_date = ?,
            approver_name = CASE WHEN ? != '' THEN ? ELSE approver_name END,
            approval_method = CASE WHEN ? != '' THEN ? ELSE approval_method END
        WHERE unit_id = ? AND version = ?
        """,
        (approver, role, when, when, name, name, method, method, unit_id, version),
    )
    _close_authored_gap(conn, unit_id, approver)


def _past_approval_on(unit_id: str) -> str:
    """A stable approval time between 2025-11-02 and 2026-10-15 for one seeded unit."""
    digest = int(hashlib.sha256(unit_id.encode("utf-8")).hexdigest()[:8], 16)
    start = datetime(2025, 11, 2)
    end = datetime(2026, 10, 15)
    span = (end - start).days
    day = start + timedelta(days=digest % (span + 1))
    hour = 9 + (digest % 8)
    minute = (digest // 8) % 60
    return f"{day.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d} ET"


def _row_field(row, key: str, default: str = "") -> str:
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else str(value)


def _seed_approver(row) -> tuple[str, str]:
    """Named approver for a unit approved before the demo starts.

    Procedures and FAQs are Knowledge Ops unless the routing rule sent the unit to Legal.
    """
    routed_legal = _row_field(row, "routing_reason").startswith("Routed to Legal")
    if _row_field(row, "type") in ("procedure", "faq") and not routed_legal:
        return OPS_SEED_APPROVER, OPS_SEED_ROLE
    return LEGAL_SEED_APPROVER, LEGAL_SEED_ROLE


def _seed_gap_volumes(conn) -> None:
    """Replace clustered search-log counts with illustrative weekly volumes."""
    rows = conn.execute("SELECT id, cluster FROM gaps").fetchall()
    for row in rows:
        findability = 1 if (row["cluster"] or "") in _FINDABILITY_CLUSTERS else 0
        count = _WEEKLY_COUNTS.get(row["id"])
        if count is None:
            conn.execute("UPDATE gaps SET findability = ? WHERE id = ?", (findability, row["id"]))
        else:
            conn.execute(
                "UPDATE gaps SET search_count = ?, findability = ? WHERE id = ?",
                (count, findability, row["id"]),
            )


def _merge_explore_copies(conn) -> None:
    """Mark desk-copy duplicates merged into the canonical unit. Explore seed only."""
    merged = []
    for desk_id, canonical_id in _EXPLORE_MERGES:
        changed = conn.execute(
            """
            UPDATE units
            SET status = 'merged', search_visible = 0, superseded_by = ?
            WHERE unit_id = ? AND version = 1 AND status = 'approved'
            """,
            (canonical_id, desk_id),
        ).rowcount
        if changed:
            merged.append(f"{desk_id} into {canonical_id}")
    if merged:
        log(
            conn,
            SESSION_AUTHOR,
            "Merged desk-copy duplicates into the canonical units. " + "; ".join(merged) + ". Illustrative.",
        )


def _close_authored_gap(conn, unit_id: str, approver: str) -> None:
    """When an approved unit was written to close a gap, mark that gap closed."""
    row = conn.execute(
        "SELECT id, cluster, status FROM gaps WHERE unit_id = ?",
        (unit_id,),
    ).fetchone()
    if row is None or row["status"] == "closed":
        return
    conn.execute("UPDATE gaps SET status = 'closed' WHERE id = ?", (row["id"],))
    log(conn, approver, f"Closed the {row['cluster']} gap. {unit_id} is searchable.")


def approve_units(conn, skip_ids: set[str] | None = None) -> None:
    """Approve every pool unit in one step.

    Bulk approval is a demo shortcut for Jump to demo state.
    The author approves procedure and faq units. Legal approves the gated units.
    skip_ids stay proposed. The guided demo passes none.
    """
    if not flag(conn, "canonical"):
        keep_canonical(conn)
    if not flag(conn, "escalated"):
        escalate_conflict(conn)
    from src.corpus import load_corpus

    skip = set(skip_ids or [])
    pool_ids = load_corpus()["pool_ids"]
    by_author = 0
    by_legal = 0
    held = 0
    rows = conn.execute(
        """
        SELECT unit_id, status, source_mismatch, verbatim_altered, requires_legal, origin,
               text, member_text, type, routing_reason
        FROM units WHERE version = 1
        """
    ).fetchall()
    for row in rows:
        if row["status"] != "proposed":
            continue
        if row["unit_id"] in skip:
            held += 1
            continue
        if row["unit_id"] in pool_ids and not row["source_mismatch"] and not row["verbatim_altered"]:
            approver, role = _seed_approver(row)
            _mark_approved(conn, row["unit_id"], approver, _past_approval_on(row["unit_id"]), approver_role=role)
            if role == LEGAL_SEED_ROLE:
                by_legal += 1
            else:
                by_author += 1
        else:
            held += 1
    _meta_set(conn, "approved", "1")
    log(
        conn,
        "Knowledge Ops author",
        f"Approved {by_author} procedure and faq units. Search can see these units: Yes. Illustrative.",
    )
    log(
        conn,
        "Legal approver",
        f"Approved {by_legal} units that passed the source check and were not blocked as conflicts or exact copies. "
        f"Search can see these units: Yes. Held back: {held}.",
    )
    conn.commit()


def _origin(row) -> str:
    try:
        return row["origin"] or ""
    except (IndexError, KeyError):
        return ""


def _can_approve(row, pool_ids: set[str]) -> bool:
    """A proposed unit can be approved when it is in the extracted pool, or it was written to close a gap.

    A gap unit that still contains a bracketed placeholder stays out of the queue.
    """
    authored = _origin(row).startswith("gap:")
    if row["status"] == "with_legal":
        return True
    if row["status"] != "proposed":
        return False
    if row["unit_id"] not in pool_ids and not authored:
        return False
    if row["source_mismatch"] or row["verbatim_altered"]:
        return False
    if authored and bracketed_placeholders(f"{row['text'] or ''}\n{row['member_text'] or ''}"):
        return False
    return True


PRESENTER_ANCHORS = ("pricing", "verify", "benefits")
COST_QUERY = "what do I say before I quote a cost"
ABSTAIN_QUERY = "how long does a part d prior auth take"
MISSPELL_QUERY = "rx price disclamer"
BLOCKED_NOTE = "Under Legal review. Use the currently approved rule until Legal decides."
LEGAL_SEED_APPROVER = "Dana Okafor (Legal)"
OPS_SEED_APPROVER = "Sam Patel (Knowledge Ops)"
LEGAL_SEED_ROLE = "Legal"
OPS_SEED_ROLE = "Knowledge Ops"
SESSION_LEGAL = "Legal approver"
SESSION_AUTHOR = "Knowledge Ops author"

# Illustrative weekly volumes for the seeded gap clusters. c5 is the top content gap.
_WEEKLY_COUNTS = {
    "c5": 340,
    "c6": 210,
    "c0": 160,
    "c1": 128,
    "c2": 96,
    "c7": 74,
    "c3": 52,
    "c8": 33,
    "c9": 18,
    "c4": 12,
}
_FINDABILITY_CLUSTERS = {
    "Rx pricing disclaimer to read",
    "Closing line for Rx education call",
    "Greeting for MA pharmacy education call",
    "Member website wording for drug price estimate",
}
# Desk copies merged only in the Explore seed. The canonical id is superseded_by.
_EXPLORE_MERGES = (
    ("U-RX-EDU-002-08", "U-RX-EDU-001-10"),
    ("U-RX-EDU-002-14", "U-RX-EDU-001-16"),
    ("U-RX-EDU-002-05", "U-RX-EDU-001-06"),
    ("U-RX-EDU-002-02", "U-RX-EDU-001-03"),
    ("U-BEN-COST-001-09", "U-BEN-COST-001-05"),
)


def presenter_unit_ids(conn) -> list[str]:
    """The three units Legal approves live in the short demo, pricing first."""
    found = []
    for name in PRESENTER_ANCHORS:
        unit_id = anchor(conn, name)
        if unit_id and unit_id not in found:
            found.append(unit_id)
    return found


def waiting_units(conn) -> list:
    """Proposed units Legal can still approve. The short demo lists its three first."""
    from src.corpus import load_corpus

    pool_ids = load_corpus()["pool_ids"]
    rows = [
        row
        for row in proposed_queue(conn)
        if _can_approve(row, pool_ids) and row["requires_legal"]
    ]
    if mode_name(conn) == "short":
        order = {unit_id: index for index, unit_id in enumerate(presenter_unit_ids(conn))}
        rows.sort(key=lambda row: (order.get(row["unit_id"], 100), row["unit_id"]))
    if mode_name(conn) == "explore":
        seen = {row["unit_id"] for row in rows}
        extra = conn.execute(
            """
            SELECT * FROM units
            WHERE status = 'with_legal' AND version = 1
            ORDER BY unit_id
            """
        ).fetchall()
        for row in extra:
            if row["unit_id"] not in seen:
                rows.append(row)
    return rows


def author_queue(conn) -> list:
    """Procedure and faq units for the author, plus units Legal sent back.

    A returned row keeps the decline reason in notes.
    """
    from src.corpus import load_corpus

    pool_ids = load_corpus()["pool_ids"]
    rows = [
        row
        for row in proposed_queue(conn)
        if _can_approve(row, pool_ids) and not row["requires_legal"]
    ]
    returned = conn.execute(
        """
        SELECT * FROM units
        WHERE status = 'returned' AND version = 1
        ORDER BY unit_id
        """
    ).fetchall()
    return rows + list(returned)


def decline_unit(conn, unit_id: str, reason: str) -> str:
    """Legal sends a proposed unit back to the author.

    Status becomes returned. The unit leaves the Legal queue and appears in
    author_queue with the reason. Returns a short message.
    """
    reason = (reason or "").strip()
    if not reason:
        return "A reason is required."
    row = conn.execute(
        """
        SELECT unit_id, status, requires_legal
        FROM units WHERE unit_id = ? AND version = 1
        """,
        (unit_id,),
    ).fetchone()
    legal_ids = {item["unit_id"] for item in waiting_units(conn)}
    if row is None or unit_id not in legal_ids:
        return "This unit is not in the Legal queue."
    conn.execute(
        """
        UPDATE units
        SET status = 'returned', search_visible = 0, notes = ?
        WHERE unit_id = ? AND version = 1
        """,
        (reason, unit_id),
    )
    log(conn, "Legal approver", f"Returned {unit_id} to the author. Reason: {reason}")
    conn.commit()
    return f"Returned {unit_id} to the author."


_AUTHOR_ROLE = "Knowledge Ops author"
_GAP_EDITABLE = {"proposed", "in_review"}
_PLACEHOLDER = re.compile(r"\[[^\[\]]+\]")


def bracketed_placeholders(text: str) -> list[str]:
    """Square-bracket placeholders, in order, without duplicates."""
    found = []
    seen = set()
    for item in _PLACEHOLDER.findall(text or ""):
        if item in seen:
            continue
        seen.add(item)
        found.append(item)
    return found


def _placeholder_message(text: str, member_text: str) -> str:
    found = []
    seen = set()
    for item in bracketed_placeholders(text) + bracketed_placeholders(member_text):
        if item in seen:
            continue
        seen.add(item)
        found.append(item)
    if not found:
        return ""
    shown = ", ".join(found[:6])
    if len(found) > 6:
        shown = f"{shown}, and {len(found) - 6} more"
    return (
        "Replace every bracketed placeholder before sending this to approval. "
        f"Still open: {shown}."
    )


def edit_gap_draft(conn, gap_id: str, text: str, member_text: str = "", role: str = _AUTHOR_ROLE) -> str:
    """The Knowledge Ops author rewrites a gap draft, including its member wording.

    Placeholders may remain while the draft is being edited. Sending is blocked
    until they are gone. Returns a message when the edit is refused, or empty.
    """
    if role != _AUTHOR_ROLE:
        return "Only a Knowledge Ops author can edit a draft."
    row = conn.execute("SELECT * FROM gaps WHERE id = ?", (gap_id,)).fetchone()
    if row is None:
        return "That cluster is not in the queue."
    if row["status"] not in _GAP_EDITABLE:
        return "This draft can no longer be edited."
    linked = (row["unit_id"] or "").strip()
    if linked:
        unit = conn.execute(
            "SELECT status FROM units WHERE unit_id = ? ORDER BY version DESC LIMIT 1",
            (linked,),
        ).fetchone()
        if unit is not None and unit["status"] == "approved":
            return "An approved unit cannot be edited. A change publishes a new version."
        if unit is not None:
            return "This draft was already sent to approval."
    text = text or ""
    member_text = member_text or ""
    if not text.strip():
        return "Write the unit text before saving this draft."
    remaining = bracketed_placeholders(text) + bracketed_placeholders(member_text)
    conn.execute(
        """
        UPDATE gaps
        SET draft_text = ?, draft_member_text = ?, placeholders = ?
        WHERE id = ?
        """,
        (text, member_text, ", ".join(remaining), gap_id),
    )
    log(conn, role, f"Edited the {row['cluster']} draft.")
    conn.commit()
    return ""


def edit_returned_unit(conn, unit_id: str, text: str, member_text: str = "", role: str = _AUTHOR_ROLE) -> str:
    """The Knowledge Ops author rewrites a unit Legal sent back.

    An approved unit is refused. Returns a message when the edit is refused, or empty.
    """
    if role != _AUTHOR_ROLE:
        return "Only a Knowledge Ops author can edit a unit sent back by Legal."
    row = conn.execute(
        "SELECT status FROM units WHERE unit_id = ? AND version = 1",
        (unit_id,),
    ).fetchone()
    if row is None:
        return "That unit is not in the queue."
    if row["status"] == "approved":
        return "An approved unit cannot be edited. A change publishes a new version."
    if row["status"] != "returned":
        return "Only a unit Legal sent back can be edited here."
    text = text or ""
    member_text = member_text or ""
    if not text.strip():
        return "Write the unit text before saving this draft."
    conn.execute(
        """
        UPDATE units
        SET text = ?, member_text = ?
        WHERE unit_id = ? AND version = 1
        """,
        (text, member_text, unit_id),
    )
    log(conn, role, f"Edited {unit_id} after Legal sent it back.")
    conn.commit()
    return ""


def _queue_name(requires_legal: int) -> str:
    if requires_legal:
        return "Legal"
    return "Knowledge Ops approvals"


# Curly quotes and guillemets fold to straight quotes before a verbatim compare.
_QUOTE_FOLDS = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u00ab": '"',
    "\u00bb": '"',
    "\u2032": "'",
    "\u2033": '"',
})
# A span shorter than this is a few words, not a sentence we treat as a quotation.
_MIN_QUOTE_WORDS = 5
_DOLLAR_AMOUNT = re.compile(r"\$\d+(?:,\d{3})*(?:\.\d+)?")
_COST_WORD = re.compile(
    r"\b(?:cost|costs|price|prices|pricing|copay|copays|copayment|coinsurance|"
    r"deductible|premium|out-of-pocket|moop)\b",
    re.IGNORECASE,
)
_REASON_TYPE = "Routed to Legal: policy or verbatim type."
_REASON_COST = "Routed to Legal: mentions cost."
_REASON_MEMBER = "Routed to Legal: member audience."
_REASON_RETURNED = "Routed to Legal: Legal sent it back, so Legal approves the change."
_REASON_AUTHOR = (
    "Routed to Knowledge Ops approvals: procedure or FAQ with no verbatim or cost wording."
)


def _normalize_wording(text: str) -> str:
    """Collapse whitespace and fold curly quotes so a quotation can match exactly."""
    cleaned = (text or "").translate(_QUOTE_FOLDS)
    return re.sub(r"\s+", " ", cleaned).strip()


def _sentence_or_longer(text: str) -> bool:
    """A full sentence, or more than one, and not a few words."""
    if len((text or "").split()) < _MIN_QUOTE_WORDS:
        return False
    return bool(re.search(r"[.!?]", text or ""))


def _quotable_spans(raw: str) -> list[str]:
    """The unit's full wording, plus each sentence, when each is long enough to quote."""
    normal = _normalize_wording(raw)
    if not normal:
        return []
    spans = []
    if _sentence_or_longer(normal):
        spans.append(normal)
    for part in re.split(r"(?<=[.!?])\s+", normal):
        part = part.strip()
        if part and part not in spans and _sentence_or_longer(part):
            spans.append(part)
    return spans


def _mentions_cost(text: str, member_text: str) -> bool:
    from src.compliance import mentions_expanded_cost

    for chunk in (text or "", member_text or ""):
        if _DOLLAR_AMOUNT.search(chunk) or _COST_WORD.search(chunk) or mentions_expanded_cost(chunk):
            return True
    return False


def _quoted_title(conn, text: str, member_text: str, exclude_unit_id: str = "") -> str:
    """Title of the approved legal unit whose wording the draft quotes, if any.

    The longest matching span wins. Equal lengths keep the lowest unit id.
    """
    haystacks = [item for item in (_normalize_wording(text), _normalize_wording(member_text)) if item]
    if not haystacks:
        return ""
    rows = conn.execute(
        """
        SELECT unit_id, title, text, member_text
        FROM units
        WHERE status = 'approved' AND (type = 'verbatim' OR requires_legal = 1) AND unit_id != ?
        """,
        (exclude_unit_id or "",),
    ).fetchall()
    best_len = -1
    best_id = ""
    best_title = ""
    for row in rows:
        title = (row["title"] or row["unit_id"] or "").strip()
        unit_id = row["unit_id"] or ""
        for raw in (row["text"], row["member_text"]):
            for span in _quotable_spans(raw or ""):
                if not any(span in hay for hay in haystacks):
                    continue
                if len(span) > best_len or (len(span) == best_len and unit_id < best_id):
                    best_len = len(span)
                    best_id = unit_id
                    best_title = title
    return best_title


def _member_audience(member_text: str, audience: str = "") -> bool:
    if (member_text or "").strip():
        return True
    return "member" in (audience or "").lower()


def _routing_decision(
    conn, draft_type: str, text: str, member_text: str, exclude_unit_id: str = "", audience: str = ""
) -> tuple[int, str]:
    """Choose the approval queue and the plain-language reason.

    Policy and verbatim types go to Legal. A procedure or FAQ also goes to Legal
    when it quotes an approved verbatim or legally gated unit, when it mentions
    cost (including spelled-out amounts), or when a member would see it.
    The first match wins, in that order.
    """
    kind = (draft_type or "faq").strip()
    if kind not in {"verbatim", "policy", "procedure", "faq"}:
        kind = "faq"
    if kind in {"verbatim", "policy"}:
        return 1, _REASON_TYPE
    title = _quoted_title(conn, text, member_text, exclude_unit_id)
    if title:
        return 1, f"Routed to Legal: quotes approved verbatim wording from {title}."
    if _mentions_cost(text, member_text):
        return 1, _REASON_COST
    if _member_audience(member_text, audience) and _mentions_cost(text, member_text):
        return 1, _REASON_MEMBER
    return 0, _REASON_AUTHOR


def send_gap_to_approval(conn, gap_id: str, role: str = _AUTHOR_ROLE) -> str:
    """Turn an edited gap draft into a proposed unit and place it in the right queue.

    Policy and verbatim drafts go to the Legal queue. A procedure or FAQ also goes
    to Legal when it quotes approved legal wording or mentions cost. Other procedure
    and FAQ drafts go to Knowledge Ops approvals. A bracketed placeholder blocks the
    send. The unclustered bucket is refused until those questions are grouped
    into a topic. Returns a message when the send is refused, or empty.
    """
    if role != _AUTHOR_ROLE:
        return "Only a Knowledge Ops author can send a draft to approval."
    row = conn.execute("SELECT * FROM gaps WHERE id = ?", (gap_id,)).fetchone()
    if row is None:
        return "That cluster is not in the queue."
    if gap_id == UNCLUSTERED_ID:
        return "Group these questions into a topic first."
    if row["status"] not in _GAP_EDITABLE:
        return "This draft is not waiting to be sent."
    if (row["unit_id"] or "").strip():
        return "This draft was already sent to approval."
    text = row["draft_text"] or ""
    member_text = row["draft_member_text"] or ""
    if not text.strip():
        return "Write the unit text before sending this to approval."
    blocked = _placeholder_message(text, member_text)
    if blocked:
        return blocked
    from src.sandbox import block_gap_send, copy_gap_sources

    sourced = block_gap_send(conn, row)
    if sourced:
        return sourced
    draft_type = (row["draft_type"] or "faq").strip()
    if draft_type not in {"verbatim", "policy", "procedure", "faq"}:
        draft_type = "faq"
    requires, reason = _routing_decision(conn, draft_type, text, member_text)
    kb = (row["draft_tags"] or "").strip()
    if kb not in {"pharmacy", "benefits", "shared-legal"}:
        kb = "pharmacy"
    audience = "advocate,member" if member_text.strip() else "advocate"
    from src.ai import audience_list, channels_for

    channels = ", ".join(channels_for(audience_list("both" if member_text.strip() else "advocate")))
    unit_id = f"U-GAP-{gap_id}"
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, tags, tags_confirmed, domain,
            kb_scope, audience, channels, status, search_visible, source_doc,
            source_quote, approved_by, approved_on, stale, proposed_text,
            requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered,
            member_text, applicability, effective_date, review_by, origin, routing_reason,
            drafted_by
        ) VALUES (
            ?, 1, ?, ?, ?, ?, 1, ?,
            ?, ?, ?, 'proposed', 0, '',
            '', '', '', 0, '',
            ?, '', ?, 0, 0,
            ?, '', '', '2027-11-06', ?, ?,
            ?
        )
        """,
        (
            unit_id,
            row["draft_title"] or row["cluster"],
            draft_type,
            text,
            row["cluster"] or "",
            kb,
            kb,
            audience,
            channels,
            requires,
            "Written to close a gap.",
            member_text,
            f"gap:{gap_id}",
            reason,
            "Sam Patel (Knowledge Ops)",
        ),
    )
    conn.execute(
        "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, 1, ?)",
        (unit_id, kb),
    )
    conn.execute(
        "UPDATE gaps SET status = 'in_review', unit_id = ? WHERE id = ?",
        (unit_id, gap_id),
    )
    copy_gap_sources(conn, unit_id, gap_id)
    log(conn, role, f"Sent {unit_id} from the {row['cluster']} gap to {_queue_name(requires)}.")
    log(conn, role, reason)
    conn.commit()
    return ""


def send_returned_to_approval(conn, unit_id: str, role: str = _AUTHOR_ROLE) -> str:
    """Send a unit Legal returned back to the queue the routing rule chooses.

    The same placeholder block and the same Legal rule as a gap draft apply.
    A bracketed placeholder blocks the send. Returns a message when refused, or empty.
    """
    if role != _AUTHOR_ROLE:
        return "Only a Knowledge Ops author can send a unit to approval."
    row = conn.execute(
        "SELECT * FROM units WHERE unit_id = ? AND version = 1",
        (unit_id,),
    ).fetchone()
    if row is None or row["status"] != "returned":
        return "This unit is not waiting to be sent back to approval."
    if not (row["text"] or "").strip():
        return "Write the unit text before sending this to approval."
    blocked = _placeholder_message(row["text"] or "", row["member_text"] or "")
    if blocked:
        return blocked
    requires, reason = _routing_decision(
        conn, row["type"], row["text"] or "", row["member_text"] or "", exclude_unit_id=unit_id
    )
    if not requires and row["requires_legal"]:
        # Legal sent this unit back, so Legal approves the change. The rule never lowers a gate.
        requires, reason = 1, _REASON_RETURNED
    conn.execute(
        """
        UPDATE units
        SET status = 'proposed', search_visible = 0, requires_legal = ?, routing_reason = ?
        WHERE unit_id = ? AND version = 1
        """,
        (requires, reason, unit_id),
    )
    log(conn, role, f"Sent {unit_id} to {_queue_name(requires)}.")
    log(conn, role, reason)
    conn.commit()
    return ""


def preapprove_short(conn) -> None:
    """Approve every reviewable unit except the three the short demo leaves for Legal.

    The author approves procedure and faq units. Legal approves the other gated
    units. Units blocked by a conflict stay blocked. The approved flag stays off
    until those three are approved on screen.
    """
    from src.corpus import load_corpus

    hold = set(presenter_unit_ids(conn))
    pool_ids = load_corpus()["pool_ids"]
    by_author = 0
    by_legal = 0
    rows = conn.execute(
        """
        SELECT unit_id, status, source_mismatch, verbatim_altered, requires_legal, origin,
               text, member_text, type, routing_reason
        FROM units WHERE version = 1
        """
    ).fetchall()
    for row in rows:
        if row["unit_id"] in hold or not _can_approve(row, pool_ids):
            continue
        approver, role = _seed_approver(row)
        _mark_approved(conn, row["unit_id"], approver, _past_approval_on(row["unit_id"]), approver_role=role)
        if role == LEGAL_SEED_ROLE:
            by_legal += 1
        else:
            by_author += 1
    log(
        conn,
        "Knowledge Ops author",
        f"Knowledge Ops author approved {by_author} units earlier this week. Illustrative.",
    )
    log(conn, "Legal approver", f"Legal approved {by_legal} units earlier this week. Illustrative.")
    conn.commit()


def has_approved(conn) -> bool:
    row = conn.execute(
        "SELECT 1 FROM units WHERE status = 'approved' AND search_visible = 1 LIMIT 1"
    ).fetchone()
    return row is not None


def _session_approver_name(drafted_by: str, *, legal: bool) -> str:
    from src.compliance import OTHER_AUTHOR_NAME, SESSION_AUTHOR_NAME, SESSION_LEGAL_NAME

    if legal:
        return SESSION_LEGAL_NAME
    if drafted_by and SESSION_AUTHOR_NAME in drafted_by:
        return OTHER_AUTHOR_NAME
    return SESSION_AUTHOR_NAME


def approve_one(conn, unit_id: str, shortcut: bool = False, method: str = "single") -> str:
    """Approve a single proposed unit. Used by the interactive Approve screen."""
    if not flag(conn, "canonical"):
        keep_canonical(conn)
    if not flag(conn, "escalated"):
        escalate_conflict(conn)
    from src.corpus import load_corpus

    pool_ids = load_corpus()["pool_ids"]
    row = conn.execute(
        """
        SELECT unit_id, status, source_mismatch, verbatim_altered, title, requires_legal, origin, text, member_text, drafted_by
        FROM units WHERE unit_id = ? AND version = 1
        """,
        (unit_id,),
    ).fetchone()
    if row is None or not _can_approve(row, pool_ids):
        return "This unit stays unapproved."
    if not row["requires_legal"]:
        return "The Knowledge Ops author approves this unit."
    when = now_et()
    approver_name = _session_approver_name(_row_field(row, "drafted_by"), legal=True)
    used_method = "bulk" if shortcut else method
    _mark_approved(
        conn,
        unit_id,
        "Legal approver",
        when,
        approver_name=approver_name,
        approval_method=used_method,
    )
    shortcut_note = " Demo shortcut." if shortcut or used_method == "bulk" else ""
    log(
        conn,
        "Legal approver",
        f"Approved {unit_id}. Approver: {approver_name}. Method: {used_method}. Search can see this unit: Yes.{shortcut_note}",
    )
    remaining = [
        item
        for item in conn.execute(
            "SELECT unit_id, status, source_mismatch, verbatim_altered, requires_legal, origin, text, member_text FROM units WHERE version = 1"
        ).fetchall()
        if _can_approve(item, pool_ids) and item["requires_legal"]
    ]
    if not remaining:
        _meta_set(conn, "approved", "1")
        log(conn, "Legal approver", "Every unit that passed the source check is approved. Search can see these units: Yes.")
    conn.commit()
    return f"Approved {unit_id}."


def approve_by_author(conn, unit_id: str) -> str:
    """The Knowledge Ops author approves a procedure or faq unit."""
    if not flag(conn, "canonical"):
        keep_canonical(conn)
    if not flag(conn, "escalated"):
        escalate_conflict(conn)
    from src.corpus import load_corpus

    pool_ids = load_corpus()["pool_ids"]
    row = conn.execute(
        """
        SELECT unit_id, status, source_mismatch, verbatim_altered, requires_legal, origin, text, member_text, drafted_by
        FROM units WHERE unit_id = ? AND version = 1
        """,
        (unit_id,),
    ).fetchone()
    if row is None or not _can_approve(row, pool_ids):
        return "This unit stays unapproved."
    if row["requires_legal"]:
        return "Legal approves this unit."
    when = now_et()
    approver_name = _session_approver_name(_row_field(row, "drafted_by"), legal=False)
    _mark_approved(
        conn,
        unit_id,
        "Knowledge Ops author",
        when,
        approver_name=approver_name,
        approval_method="single",
    )
    log(
        conn,
        "Knowledge Ops author",
        f"Approved {unit_id}. Approver: {approver_name}. Method: single. Search can see this unit: Yes.",
    )
    conn.commit()
    return f"Approved {unit_id}."


def approve_remaining(conn) -> str:
    """Full-path shortcut. Each Legal unit is logged on its own."""
    ids = [row["unit_id"] for row in waiting_units(conn)]
    for unit_id in ids:
        approve_one(conn, unit_id, shortcut=True, method="bulk")
    return f"Approved {len(ids)} units. Demo shortcut."


def conflict_plans() -> list[dict]:
    """Human conflict decisions. Each entry names the kept unit, the units to retire, and a reason."""
    from src.ai import load_human_decisions

    raw = load_human_decisions().get("conflicts") or []
    if isinstance(raw, dict):
        return [raw]
    return list(raw)


def open_conflicts(conn) -> list[dict]:
    """Conflicts that still have a blocked unit."""
    open_plans = []
    for plan in conflict_plans():
        ids = [plan.get("chosen_unit_id") or "", *(plan.get("retire_unit_ids") or [])]
        ids = [unit_id for unit_id in ids if unit_id]
        if not ids:
            continue
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT status FROM units WHERE version = 1 AND unit_id IN ({placeholders})",
            ids,
        ).fetchall()
        if any(row["status"] == "blocked_conflict" for row in rows):
            open_plans.append(plan)
    return open_plans


def resolve_conflict(conn, reason: str, conflict_id: str | None = None) -> str:
    """Legal picks one blocked wording, with a reason, and retires the other blocked wording.

    With no conflict id, this resolves the conflict the demo handles live.
    Other recorded conflicts stay blocked until that id is passed.
    """
    reason = (reason or "").strip()
    if not reason:
        return "A reason is required."
    plans = conflict_plans()
    if conflict_id:
        plan = next((item for item in plans if item.get("id") == conflict_id), None)
    else:
        plan = next((item for item in plans if item.get("resolve_in_demo")), None)
    if plan is None:
        return "No conflict is waiting for that decision."
    chosen = plan.get("chosen_unit_id") or ""
    retire_ids = plan.get("retire_unit_ids") or []
    row = conn.execute(
        "SELECT status FROM units WHERE unit_id = ? AND version = 1",
        (chosen,),
    ).fetchone()
    if row is None or row["status"] != "blocked_conflict":
        return "Legal can resolve this once AI has marked the pair a conflict and both units are blocked."
    when = now_et()
    _mark_approved(conn, chosen, "Legal approver", when)
    retired = []
    for unit_id in retire_ids:
        changed = conn.execute(
            """
            UPDATE units
            SET status = 'retired', search_visible = 0
            WHERE unit_id = ? AND version = 1 AND status = 'blocked_conflict'
            """,
            (unit_id,),
        ).rowcount
        if changed:
            retired.append(unit_id)
    done = [part for part in _meta_get(conn, "conflicts_resolved", "").split(",") if part]
    plan_id = plan.get("id") or chosen
    if plan_id not in done:
        done.append(plan_id)
    _meta_set(conn, "conflicts_resolved", ",".join(done))
    if plan.get("resolve_in_demo"):
        _meta_set(conn, "conflict_resolved", "1")
        _meta_set(conn, "conflict_reason", reason)
    suggestion = (plan.get("reason") or "").strip()
    reason_source = "ai_suggestion_accepted" if reason.strip() == suggestion and suggestion else "typed"
    stored = {}
    raw_sources = _meta_get(conn, "conflict_sources", "")
    if raw_sources:
        try:
            stored = json.loads(raw_sources)
        except json.JSONDecodeError:
            stored = {}
    if not isinstance(stored, dict):
        stored = {}
    stored[plan_id] = reason_source
    _meta_set(conn, "conflict_sources", json.dumps(stored))
    append_event(
        conn,
        "conflict.resolved",
        chosen,
        1,
        0,
        "Legal approver",
        json.dumps({"reason_source": reason_source, "conflict_id": plan_id, "reason": reason}),
    )
    retired_text = ", ".join(retired) if retired else "none"
    label = plan.get("label") or "conflict"
    log(
        conn,
        "Legal approver",
        f"Resolved the {label}. Kept {chosen}. Retired {retired_text}. Reason: {reason}",
    )
    conn.commit()
    return f"Kept {chosen}. Retired {retired_text}."


def anchor(conn, name: str) -> str:
    return _meta_get(conn, f"anchor_{name}", "")


def _configured_channels(row) -> str:
    from src.ai import audience_list, load_human_decisions, override_channels

    override = (load_human_decisions().get("audience_overrides") or {}).get(row["unit_id"])
    if isinstance(override, dict) and override:
        channels = override_channels(override, audience_list(override.get("audience") or "advocate"))
        return ", ".join(channels)
    return row["channels"] or ""


def append_event(conn, event: str, unit_id: str, version: int, previous_version: int, actor: str, note: str) -> None:
    from src.finish import new_event_id, record_webhook_deliveries

    event_id = new_event_id()
    occurred = now_iso()
    conn.execute(
        """
        INSERT INTO change_events (ts, event, unit_id, version, previous_version, actor, note, event_id, occurred_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (now_et(), event, unit_id, int(version or 0), int(previous_version or 0), actor, note, event_id, occurred),
    )
    record_webhook_deliveries(
        conn,
        event_id,
        event,
        {
            "event_id": event_id,
            "event": event,
            "unit_id": unit_id,
            "version": int(version or 0),
            "previous_version": int(previous_version or 0),
            "occurred_at": occurred,
            "actor": actor,
        },
    )


def list_events(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM change_events ORDER BY id"
    ).fetchall()
    return [
        {
            "event": row["event"],
            "event_id": row["event_id"] if "event_id" in row.keys() else "",
            "unit_id": row["unit_id"],
            "version": row["version"],
            "previous_version": row["previous_version"],
            "ts": row["ts"],
            "occurred_at": (row["occurred_at"] if "occurred_at" in row.keys() else "") or "",
            "actor": row["actor"] or "",
            "note": row["note"] or "",
        }
        for row in rows
    ]


def _publish_text_error(conn, live, new_text: str, member_text: str) -> str:
    """Refuse an empty edit, an unchanged edit, or verbatim that leaves the source."""
    if not (new_text or "").strip() or (member_text is not None and member_text == ""):
        return "Write the wording before publishing."
    if new_text == (live["text"] or "") and member_text == (live["member_text"] or ""):
        return "That wording is already published."
    if (live["type"] or "") == "verbatim":
        doc_id = live["source_doc"] or "SRC-RX-EDU-001"
        body = document_body(conn, doc_id) or ""
        prepared = new_text
        from src.ai import load_human_decisions

        change = load_human_decisions().get("channels_revision") or CATALOG.get("channels_revision") or {}
        expected = (live["text"] or "").replace(change.get("find") or "", change.get("replace") or "")
        in_source = new_text in body or (live["source_quote"] or "") in new_text or new_text in (live["source_quote"] or "")
        if new_text != expected and new_text != (live["text"] or "") and not in_source:
            return "Verbatim wording has to match the source, or the prepared revision."
    return ""


def publish_revision(conn, text: str | None = None, member_text: str | None = None):
    unit_id = anchor(conn, "pricing")
    live = current_unit(conn, unit_id) if unit_id else None
    if live is None or live["status"] != "approved":
        return False
    from src.ai import load_human_decisions

    change = (load_human_decisions().get("channels_revision") or CATALOG["channels_revision"])
    edited = text is not None or member_text is not None
    if text is None:
        new_text = live["text"].replace(change["find"], change["replace"])
    else:
        new_text = text
    if member_text is None:
        next_member = live["member_text"] or ""
        member_find = change.get("member_find") or ""
        member_replace = change.get("member_replace") or ""
        if member_find and member_find in next_member:
            next_member = next_member.replace(member_find, member_replace, 1)
    else:
        next_member = member_text
    if not edited and new_text == (live["text"] or "") and next_member == (live["member_text"] or ""):
        return False
    if edited:
        from api.errors import APIError

        problem = _publish_text_error(conn, live, new_text, next_member)
        if problem:
            raise APIError(problem)
    member_text = next_member
    new_version = live["version"] + 1
    channels = _configured_channels(live)
    conn.execute(
        "UPDATE units SET status = 'superseded', search_visible = 0 WHERE unit_id = ? AND version = ?",
        (live["unit_id"], live["version"]),
    )
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, tags, tags_confirmed, domain,
            kb_scope, audience, channels, status, search_visible, source_doc,
            source_quote, approved_by, approver_role, approved_on, stale, proposed_text,
            requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered, member_text,
            applicability, effective_date, review_by, sibling_of
        )
        SELECT unit_id, ?, title, type, ?, tags, tags_confirmed, domain,
               kb_scope, audience, ?, 'approved', 1, source_doc,
               ?, 'Legal approver', 'Legal approver', ?, 0, '',
               requires_legal, conflicts_with, 'Published from the channel revision.',
               source_mismatch, verbatim_altered, ?,
               applicability, ?, review_by, sibling_of
        FROM units WHERE unit_id = ? AND version = ?
        """,
        (new_version, new_text, channels, new_text, now_et(), member_text, now_et(), live["unit_id"], live["version"]),
    )
    annotation = (
        f"Source annotated on version {new_version}. The live wording replaced the extracted span in "
        f"{live['source_doc'] or 'SRC-RX-EDU-001'}."
    )
    conn.execute(
        """
        UPDATE units
        SET source_annotation = ?, approver_name = ?, approval_method = 'single'
        WHERE unit_id = ? AND version = ?
        """,
        (annotation, "Dana Okafor (Legal)", live["unit_id"], new_version),
    )
    if edited:
        reason = ""
        if _mentions_cost(new_text, member_text):
            reason = "Routed to Legal: mentions cost."
        conn.execute(
            """
            UPDATE units
            SET edited_by_legal = 1, approver_name = ?, routing_reason = CASE WHEN ? != '' THEN ? ELSE routing_reason END
            WHERE unit_id = ? AND version = ?
            """,
            ("Dana Okafor (Legal)", reason, reason, live["unit_id"], new_version),
        )
    from src.finish import copy_sibling_of, open_sibling_review

    copy_sibling_of(conn, live["unit_id"], new_version)
    open_sibling_review(conn, live["unit_id"])
    append_event(
        conn,
        "unit.revised",
        live["unit_id"],
        new_version,
        int(live["version"]),
        "Legal approver",
        annotation,
    )
    for kb in live["kb_scope"].split(","):
        kb = kb.strip()
        if not kb:
            continue
        conn.execute(
            "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, ?, ?)",
            (live["unit_id"], new_version, kb),
        )
    source_note = _revise_source_passage(conn, live, new_text, change)
    _meta_set(conn, "revised", "1")
    log(
        conn,
        "Legal approver",
        (
            f"Published {live['unit_id']} version {new_version}. "
            f"The advocate desktop, member chat, the website, and the phone line now show version {new_version}. "
            f"Version {live['version']} is superseded."
        ),
    )
    if source_note:
        log(conn, "Legal approver", source_note)
    conn.commit()
    return True


def retract_published_version(conn, reason: str) -> str:
    """Append a restoring version. The published version stays in history."""
    unit_id = anchor(conn, "pricing")
    live = current_unit(conn, unit_id) if unit_id else None
    if live is None or live["status"] != "approved" or int(live["version"]) < 2:
        return "Nothing to retract."
    previous = conn.execute(
        """
        SELECT * FROM units
        WHERE unit_id = ? AND version < ?
        ORDER BY version DESC
        LIMIT 1
        """,
        (live["unit_id"], live["version"]),
    ).fetchone()
    if previous is None:
        return "Nothing to retract."
    new_version = int(live["version"]) + 1
    when = now_et()
    note = (reason or "Undo restored the earlier wording.").strip()
    conn.execute(
        "UPDATE units SET status = 'superseded', search_visible = 0 WHERE unit_id = ? AND version = ?",
        (live["unit_id"], live["version"]),
    )
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, tags, tags_confirmed, domain,
            kb_scope, audience, channels, status, search_visible, source_doc,
            source_quote, approved_by, approver_role, approved_on, stale, proposed_text,
            requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered, member_text,
            applicability, effective_date, review_by, approver_name, approval_method, source_annotation,
            sibling_of
        )
        SELECT unit_id, ?, title, type, ?, tags, tags_confirmed, domain,
               kb_scope, audience, channels, 'approved', 1, source_doc,
               ?, 'Legal approver', 'Legal approver', ?, 0, '',
               requires_legal, conflicts_with, ?,
               source_mismatch, verbatim_altered, ?,
               applicability, ?, review_by, 'Dana Okafor (Legal)', 'single', ?,
               sibling_of
        FROM units WHERE unit_id = ? AND version = ?
        """,
        (
            new_version,
            previous["text"],
            previous["text"],
            when,
            note,
            previous["member_text"] or "",
            when,
            note,
            live["unit_id"],
            previous["version"],
        ),
    )
    from src.finish import copy_sibling_of

    copy_sibling_of(conn, live["unit_id"], new_version)
    for kb in (live["kb_scope"] or "").split(","):
        kb = kb.strip()
        if kb:
            conn.execute(
                "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, ?, ?)",
                (live["unit_id"], new_version, kb),
            )
    append_event(conn, "unit.retracted", live["unit_id"], int(live["version"]), int(previous["version"]), "Legal approver", note)
    append_event(conn, "unit.revised", live["unit_id"], new_version, int(live["version"]), "Legal approver", note)
    log(conn, "Legal approver", f"Retracted version {live['version']} of {live['unit_id']}. Version {new_version} restores the earlier wording.")
    conn.commit()
    return f"Restored the earlier wording as version {new_version}."


def _revise_source_passage(conn, live, new_text: str, change: dict) -> str:
    """Write the published wording into the source span the unit was extracted from."""
    doc_id = live["source_doc"] or "SRC-RX-EDU-001"
    row = conn.execute("SELECT body FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if row is None:
        return ""
    body = row["body"] or ""
    old_span = live["source_quote"] or ""
    updated = body
    if old_span and old_span in body and old_span != new_text:
        updated = body.replace(old_span, new_text, 1)
    else:
        find = change.get("find") or ""
        replace = change.get("replace") or ""
        if find and replace and find in body:
            updated = body.replace(find, replace, 1)
    if updated == body:
        return ""
    conn.execute("UPDATE documents SET body = ? WHERE doc_id = ?", (updated, doc_id))
    return (
        f"Updated the source passage for {live['unit_id']} in {doc_id}. "
        f"The script now matches version {live['version'] + 1}."
    )


def _drift_spec(kind: str) -> dict:
    from src.ai import load_human_decisions

    edits = load_human_decisions().get("drift_edits") or {}
    spec = edits.get(kind) or {}
    if spec.get("find"):
        return spec
    catalog = CATALOG.get("drift_edit") or {}
    nested = catalog.get(kind) or {}
    if isinstance(nested, dict) and nested.get("find"):
        return nested
    if kind == "material" and catalog.get("find"):
        return {"find": catalog["find"], "replace": catalog["replace"]}
    return {}


COSMETIC_LOGGED = "Cosmetic edit logged. Nothing was flagged."
COSMETIC_INSIDE_VERBATIM = "Sent to Legal: a comma inside Legal wording. The approved version stays live."


def span_inside_verbatim(live, old_span: str) -> bool:
    """True when the edited span sits in a verbatim unit's approved text or source quote."""
    if live is None:
        return False
    return (live["type"] or "") == "verbatim" and bool(old_span) and (
        old_span in (live["text"] or "") or old_span in (live["source_quote"] or "")
    )


def cosmetic_drift_message(conn) -> str:
    """Activity line for the prepared cosmetic edit.

    The guided comma sits inside the verbatim pricing sentence, so that edit
    is sent to Legal. A cosmetic edit outside a verbatim span keeps the log line.
    """
    unit_id = anchor(conn, "pricing")
    live = current_unit(conn, unit_id) if unit_id else None
    old_span = (_drift_spec("cosmetic").get("find") or "")
    if span_inside_verbatim(live, old_span):
        return COSMETIC_INSIDE_VERBATIM
    return COSMETIC_LOGGED


def _store_drift(conn, live, kind: str, output: dict, old_span: str, new_span: str, source: str) -> str:
    """Log every drift edit. Flag only a material change. The approved text stays live."""
    change = output.get("change") or ("material" if kind == "material" else "cosmetic")
    flagged = kind == "material" or (kind == "" and change == "material")
    inside_verbatim = span_inside_verbatim(live, old_span)
    cosmetic_legal = kind == "cosmetic" and inside_verbatim
    if kind == "cosmetic" and not cosmetic_legal:
        flagged = False
    if cosmetic_legal:
        flagged = True
        change = "cosmetic"
    summary = output.get("summary") or ""
    if cosmetic_legal:
        summary = "Cosmetic change inside Legal wording. " + summary
    proposed = output.get("proposed_text") or ""
    if cosmetic_legal:
        status = "sent"
        message = (
            "Sent to Legal. Cosmetic change inside Legal wording. "
            f"{live['unit_id']} stays live on the approved version."
        )
        _meta_set(conn, "drift_cosmetic", "1")
        _meta_set(conn, "drift_cosmetic_summary", summary)
        _meta_set(conn, "drift_cosmetic_source", source)
        _meta_set(conn, "drift_cosmetic_line", "Sent to Legal. Cosmetic change inside Legal wording.")
        _meta_set(conn, "drift_verbatim_legal", "1")
    elif flagged:
        conn.execute(
            "UPDATE units SET stale = 1, proposed_text = ? WHERE unit_id = ? AND version = ?",
            (proposed, live["unit_id"], live["version"]),
        )
        status = "awaiting_legal"
        message = (
            f"Source changed. AI judged the edit {change}. {live['unit_id']} stays live on the approved version. "
            "Waiting for Legal. The approved version stays live. Search can see this unit: Yes."
        )
        _meta_set(conn, "drift", "1")
        _meta_set(conn, "drift_change", change)
        _meta_set(conn, "drift_summary", summary)
        _meta_set(conn, "drift_source", source)
        _meta_set(conn, "drift_status_line", "Waiting for Legal. The approved version stays live.")
    else:
        status = "system_escalated" if (live["type"] or "") == "verbatim" else "logged"
        message = f"Cosmetic change. Logged, not flagged. AI judged it {change}. {summary}"
        _meta_set(conn, "drift_cosmetic", "1")
        _meta_set(conn, "drift_cosmetic_summary", summary)
        _meta_set(conn, "drift_cosmetic_source", source)
        _meta_set(conn, "drift_cosmetic_line", "Cosmetic change. Logged, not flagged.")
    conn.execute(
        """
        INSERT INTO drift_log(
            ts, unit_id, version, kind, change, old_span, new_span, summary,
            proposed_text, flagged, ai_source, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now_et(),
            live["unit_id"],
            live["version"],
            kind or change,
            change,
            old_span,
            new_span,
            summary,
            proposed,
            1 if flagged else 0,
            source,
            status,
        ),
    )
    log(conn, "Knowledge owner", message)
    if status == "system_escalated":
        log(
            conn,
            "System",
            "Automatic: a change inside a verbatim span was sent to Legal. No person acted.",
        )
    conn.commit()
    return ""


def prepared_drift_request(conn, kind: str):
    """The T5 input for this live unit and the source sentence as it stands now.

    Returns (user_message, edit) or (None, None) when the sentence is not in the source.
    """
    from src.ai import drift_user, prepared_drift_edits, pricing_sentence

    if kind not in {"material", "cosmetic"}:
        return None, None
    unit_id = anchor(conn, "pricing")
    live = current_unit(conn, unit_id) if unit_id else None
    if live is None:
        return None, None
    doc_id = live["source_doc"] or "SRC-RX-EDU-001"
    sentence = pricing_sentence(document_body(conn, doc_id))
    if not sentence:
        return None, None
    edit = next((item for item in prepared_drift_edits(live["text"], sentence) if item["name"] == kind), None)
    if edit is None:
        return None, None
    return drift_user(edit["unit_text"], edit["old_span"], edit["new_span"]), edit


def apply_prepared_drift(conn, kind: str) -> str:
    """Apply the prepared material or cosmetic edit. Cosmetic is logged and not flagged.

    The model call uses the live unit text and the source sentence after any revision,
    so a drift check that follows version 2 does not replay the version 1 proposal.
    """
    if kind not in {"material", "cosmetic"}:
        return "Use material or cosmetic."
    from src.ai import MISSING_CAPTION, replay

    unit_id = anchor(conn, "pricing")
    live = current_unit(conn, unit_id) if unit_id else None
    if live is None or live["status"] != "approved":
        return "Approve the disclaimer before a source change can be compared."
    user, _edit = prepared_drift_request(conn, kind)
    if user is None:
        return "No cached result for this input. Turn on Live AI to run the model."
    output, source = replay("propose_drift_fix", user, live=live_enabled(conn))
    if output is None:
        return MISSING_CAPTION if source == "missing" else "Live call failed, and no cached result is stored."
    spec = _drift_spec(kind)
    find = spec.get("find") or ""
    replace = spec.get("replace") or ""
    doc_id = live["source_doc"] or "SRC-RX-EDU-001"
    doc = conn.execute("SELECT body FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if not find or find not in (doc["body"] if doc else ""):
        if kind == "material":
            return (
                "Cached mode knows the prepared edit, from 30-day supply to 31-day supply. "
                "Restore that phrase in the source, or turn on Live AI in Settings."
            )
        return (
            "Cached mode knows the prepared cosmetic edit, an extra comma after supply. "
            "Restore that phrase in the source, or turn on Live AI in Settings."
        )
    conn.execute(
        "UPDATE documents SET body = ? WHERE doc_id = ?",
        (doc["body"].replace(find, replace, 1), doc_id),
    )
    return _store_drift(conn, live, kind, output, find, replace, source if source != "live_failed" else "fallback")


def apply_drift(conn) -> str:
    """Prepared material edit. Kept for the current Drift screen."""
    return apply_prepared_drift(conn, "material")


def apply_source_span(conn, new_span: str) -> str:
    """Apply a free-text source edit. Prepared edits replay the cache. Others need live mode."""
    from src.ai import FALLBACK_CAPTION, MISSING_CAPTION, drift_user, replay
    from src.corpus import load_corpus

    unit_id = anchor(conn, "pricing")
    live = current_unit(conn, unit_id) if unit_id else None
    if live is None or live["status"] != "approved":
        return "Approve the disclaimer before a source change can be compared."
    corpus_drift = load_corpus()["drift"]
    for name, item in (corpus_drift.get("edits") or {}).items():
        if item["edit"]["new_span"] == new_span:
            return apply_prepared_drift(conn, name)
    sentence = corpus_drift.get("sentence") or ""
    if not live_enabled(conn):
        return MISSING_CAPTION
    output, source = replay(
        "propose_drift_fix",
        drift_user(live["text"], sentence, new_span),
        live=True,
    )
    if output is None:
        return MISSING_CAPTION
    doc = conn.execute("SELECT body FROM documents WHERE doc_id = 'SRC-RX-EDU-001'").fetchone()
    if sentence and doc and sentence in doc["body"]:
        conn.execute(
            "UPDATE documents SET body = ? WHERE doc_id = 'SRC-RX-EDU-001'",
            (doc["body"].replace(sentence, new_span, 1),),
        )
    _store_drift(conn, live, "", output, sentence, new_span, source)
    if source == "fallback":
        return FALLBACK_CAPTION
    return ""


def send_drift_to_legal(conn) -> str:
    """Hand the material proposal to Legal. The approved version stays searchable."""
    if not flag(conn, "drift"):
        return "No material change is waiting for Legal."
    _meta_set(conn, "drift_sent", "1")
    conn.execute(
        "UPDATE drift_log SET status = 'sent' WHERE flagged = 1 AND status = 'awaiting_legal'"
    )
    log(conn, "Knowledge owner", "Sent the proposed wording to Legal. The approved version stays live.")
    conn.commit()
    return ""


def legal_drift_items(conn) -> list[dict]:
    """Material drift fixes waiting for Legal, with the old wording, the new wording, and the source change."""
    rows = conn.execute(
        """
        SELECT * FROM drift_log
        WHERE flagged = 1 AND status = 'sent'
        ORDER BY id
        """
    ).fetchall()
    items = []
    for row in rows:
        live = live_approved(conn, row["unit_id"])
        items.append(
            {
                "id": row["id"],
                "unit_id": row["unit_id"],
                "version": row["version"],
                "old_wording": live["text"] if live else "",
                "new_wording": row["proposed_text"] or "",
                "source_before": row["old_span"] or "",
                "source_after": row["new_span"] or "",
                "summary": row["summary"] or "",
                "member_text": (live["member_text"] if live else "") or "",
            }
        )
    return items


def _latest_drift(conn, status: str):
    return conn.execute(
        """
        SELECT * FROM drift_log
        WHERE flagged = 1 AND status = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (status,),
    ).fetchone()


def approve_drift_fix(conn, role: str = "Legal approver") -> str:
    """Publish the drift proposal as the next version. Every channel reads that version.

    The current approved version stays in history. Returns a message when refused, or empty.
    """
    if role != "Legal approver":
        return "Only a Legal approver can approve a drift fix."
    row = _latest_drift(conn, "sent")
    if row is None:
        return "No drift fix is waiting for Legal."
    if (row["change"] or "") == "cosmetic" or "Cosmetic change inside Legal wording" in (row["summary"] or ""):
        conn.execute("UPDATE drift_log SET status = 'accepted' WHERE id = ?", (row["id"],))
        log(
            conn,
            role,
            f"Accepted the cosmetic change inside Legal wording for {row['unit_id']} as no change. "
            "The approved version stays live.",
        )
        conn.commit()
        return ""
    live = live_approved(conn, row["unit_id"])
    if live is None:
        return "The approved version is no longer live."
    proposed = (row["proposed_text"] or "").strip()
    if not proposed:
        return "The drift fix has no proposed wording."
    new_version = int(live["version"]) + 1
    member_text = live["member_text"] or ""
    old_span = row["old_span"] or ""
    new_span = row["new_span"] or ""
    if old_span and old_span in member_text:
        member_text = member_text.replace(old_span, new_span, 1)
    source_quote = live["source_quote"] or ""
    if old_span and old_span in source_quote:
        source_quote = source_quote.replace(old_span, new_span, 1)
    when = now_et()
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
            applicability, effective_date, review_by, sibling_of
        )
        SELECT unit_id, ?, title, type, ?, tags, tags_confirmed, domain,
               kb_scope, audience, channels, 'approved', 1, source_doc,
               ?, 'Legal approver', 'Legal approver', ?, 0, '',
               requires_legal, conflicts_with, 'Published from the drift fix.',
               source_mismatch, verbatim_altered, ?,
               applicability, ?, review_by, sibling_of
        FROM units WHERE unit_id = ? AND version = ?
        """,
        (
            new_version,
            proposed,
            source_quote,
            when,
            member_text,
            when,
            live["unit_id"],
            live["version"],
        ),
    )
    from src.finish import copy_sibling_of

    copy_sibling_of(conn, live["unit_id"], new_version)
    for kb in (live["kb_scope"] or "").split(","):
        kb = kb.strip()
        if not kb:
            continue
        conn.execute(
            "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, ?, ?)",
            (live["unit_id"], new_version, kb),
        )
    conn.execute("UPDATE drift_log SET status = 'approved' WHERE id = ?", (row["id"],))
    log(
        conn,
        role,
        f"Published {live['unit_id']} version {new_version} from the source change. "
        f"Every channel now shows version {new_version}. Version {live['version']} is superseded.",
    )
    conn.commit()
    return ""


def return_drift_fix(conn, reason: str, role: str = "Legal approver") -> str:
    """Send the drift proposal back. The approved version stays live and stays marked stale.

    Returns a message when refused, or empty.
    """
    if role != "Legal approver":
        return "Only a Legal approver can send a drift fix back."
    reason = (reason or "").strip()
    if not reason:
        return "A reason is required."
    row = _latest_drift(conn, "sent")
    if row is None:
        return "No drift fix is waiting for Legal."
    conn.execute("UPDATE drift_log SET status = 'returned' WHERE id = ?", (row["id"],))
    log(
        conn,
        role,
        f"Sent the drift fix for {row['unit_id']} back. The approved version stays live. Reason: {reason}",
    )
    conn.commit()
    return ""


def resolve_returned_drift(conn, note: str, role: str = _AUTHOR_ROLE) -> str:
    """The author accepts the current wording. The stale flag clears only here.

    Returns a message when refused, or empty.
    """
    if role != _AUTHOR_ROLE:
        return "Only a Knowledge Ops author can resolve a returned drift fix."
    note = (note or "").strip()
    if not note:
        return "A note is required."
    row = _latest_drift(conn, "returned")
    if row is None:
        return "No drift fix is waiting for the author."
    changed = conn.execute(
        """
        UPDATE units
        SET stale = 0
        WHERE unit_id = ? AND version = ? AND status = 'approved'
        """,
        (row["unit_id"], row["version"]),
    ).rowcount
    if not changed:
        return "The approved version is no longer the one Legal sent back."
    conn.execute("UPDATE drift_log SET status = 'resolved' WHERE id = ?", (row["id"],))
    log(
        conn,
        role,
        f"Resolved the returned drift fix for {row['unit_id']}. The approved version stays live. {note}",
    )
    conn.commit()
    return ""


def drift_events(conn):
    return conn.execute("SELECT * FROM drift_log ORDER BY id").fetchall()


def drift_state(conn) -> dict:
    """Everything the Drift screen needs after a cosmetic edit, a material edit, or both."""
    unit_id = anchor(conn, "pricing")
    live = live_approved(conn, unit_id) if unit_id else None
    current = current_unit(conn, unit_id) if unit_id else None
    return {
        "unit_id": unit_id,
        "live_text": live["text"] if live else "",
        "live_version": live["version"] if live else None,
        "member_text": live["member_text"] if live else "",
        "stale": bool(current["stale"]) if current else False,
        "proposed_text": current["proposed_text"] if current else "",
        "material": flag(conn, "drift"),
        "cosmetic": flag(conn, "drift_cosmetic"),
        "verbatim_to_legal": flag(conn, "drift_verbatim_legal"),
        "legal_label": "Cosmetic change inside Legal wording" if flag(conn, "drift_verbatim_legal") else "",
        "sent": flag(conn, "drift_sent"),
        "material_line": _meta_get(conn, "drift_status_line", ""),
        "cosmetic_line": _meta_get(conn, "drift_cosmetic_line", ""),
        "summary": _meta_get(conn, "drift_summary", ""),
        "cosmetic_summary": _meta_get(conn, "drift_cosmetic_summary", ""),
        "change": _meta_get(conn, "drift_change", ""),
        "ai_source": _meta_get(conn, "drift_source", "") or _meta_get(conn, "drift_cosmetic_source", ""),
        "events": [dict(row) for row in drift_events(conn)],
        "note": "Illustrative, made-up data",
    }


_GAP_STATUS = {
    "write": "in_review",
    "fix_process": "process_fix",
    "dismiss": "dismissed",
}


def act_on_gap(conn, gap_id: str, action: str, reason: str) -> str:
    """write, fix_process, or dismiss. A reason is required and is logged."""
    reason = (reason or "").strip()
    if action not in _GAP_STATUS:
        return "Unknown gap action."
    if not reason:
        return "A reason is required."
    row = conn.execute("SELECT cluster FROM gaps WHERE id = ?", (gap_id,)).fetchone()
    if row is None:
        return "That cluster is not in the queue."
    conn.execute(
        "UPDATE gaps SET status = ?, reason = ? WHERE id = ?",
        (_GAP_STATUS[action], reason, gap_id),
    )
    if action == "write":
        message = (
            f"Sent the {row['cluster']} draft to review. Reason: {reason} "
            "Search still has no approved answer for that question."
        )
    elif action == "fix_process":
        message = f"Marked {row['cluster']} as a process fix. Reason: {reason} No new unit was published."
    else:
        message = f"Dismissed the {row['cluster']} cluster. Reason: {reason}"
    log(conn, "Knowledge owner", message)
    conn.commit()
    return ""


def write_gap(conn, gap_id: str, reason: str = "") -> None:
    if (reason or "").strip():
        act_on_gap(conn, gap_id, "write", reason)
        return
    conn.execute("UPDATE gaps SET status = 'in_review' WHERE id = ?", (gap_id,))
    row = conn.execute("SELECT cluster FROM gaps WHERE id = ?", (gap_id,)).fetchone()
    log(
        conn,
        "Knowledge owner",
        f"Sent the {row['cluster']} draft to review. Search still has no approved answer for that question.",
    )
    conn.commit()


def dismiss_gap(conn, gap_id: str, reason: str = "") -> None:
    if (reason or "").strip():
        act_on_gap(conn, gap_id, "dismiss", reason)
        return
    conn.execute("UPDATE gaps SET status = 'dismissed' WHERE id = ?", (gap_id,))
    row = conn.execute("SELECT cluster FROM gaps WHERE id = ?", (gap_id,)).fetchone()
    log(conn, "Knowledge owner", f"Dismissed the {row['cluster']} cluster.")
    conn.commit()


def fix_process_gap(conn, gap_id: str, reason: str = "") -> None:
    if (reason or "").strip():
        act_on_gap(conn, gap_id, "fix_process", reason)
        return
    conn.execute("UPDATE gaps SET status = 'process_fix' WHERE id = ?", (gap_id,))
    row = conn.execute("SELECT cluster FROM gaps WHERE id = ?", (gap_id,)).fetchone()
    log(
        conn,
        "Knowledge owner",
        f"Marked {row['cluster']} as a process fix. No new unit was published.",
    )
    conn.commit()


LIVE_DB_CAP = 20
LIVE_DAY_CAP = 300
LIVE_CAP_FILE = Path("/tmp/harbor-knowledge-live-cap.json")
CAP_MESSAGE = "Live call limit reached. A saved answer is used when one exists."
_LIVE_CONN = contextvars.ContextVar("harbor_live_conn", default=None)


def set_live(conn, enabled: bool) -> None:
    """Turn live model calls on or off for this demo database."""
    _meta_set(conn, "live_ai", "1" if enabled else "0")
    conn.commit()


def bind_live_conn(conn):
    return _LIVE_CONN.set(conn)


def unbind_live_conn(token) -> None:
    _LIVE_CONN.reset(token)


def _cap_file() -> Path:
    override = os.environ.get("HARBOR_LIVE_CAP_FILE", "")
    return Path(override) if override else LIVE_CAP_FILE


def _day_cap() -> tuple[Path, dict]:
    path = _cap_file()
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    data = {"date": today, "count": 0, "cap": LIVE_DAY_CAP}
    if path.exists():
        try:
            loaded = json.loads(path.read_text())
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, json.JSONDecodeError):
            data = {"date": today, "count": 0, "cap": LIVE_DAY_CAP}
    if data.get("date") != today:
        data = {"date": today, "count": 0, "cap": int(data.get("cap") or LIVE_DAY_CAP)}
    data["cap"] = int(data.get("cap") or LIVE_DAY_CAP)
    data["count"] = int(data.get("count") or 0)
    return path, data


def live_slot_available() -> str:
    """Empty when a live call is allowed. Otherwise a short limit message."""
    conn = _LIVE_CONN.get()
    if conn is not None:
        count = int(_meta_get(conn, "live_call_count", "0") or 0)
        cap = int(_meta_get(conn, "live_call_cap", str(LIVE_DB_CAP)) or LIVE_DB_CAP)
        if count >= cap:
            return CAP_MESSAGE
    _path, data = _day_cap()
    if data["count"] >= data["cap"]:
        return CAP_MESSAGE
    return ""


def note_live_call() -> None:
    """Count one live model attempt against the database cap and the daily cap."""
    conn = _LIVE_CONN.get()
    if conn is not None:
        count = int(_meta_get(conn, "live_call_count", "0") or 0) + 1
        _meta_set(conn, "live_call_count", str(count))
        conn.commit()
    path, data = _day_cap()
    data["count"] = int(data["count"]) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def live_enabled(conn) -> bool:
    return flag(conn, "live_ai")


def synonym_entries() -> list[dict]:
    """The hand-written synonym map. Each entry is labeled seed."""
    origin = CATALOG.get("synonym_origin") or "seed"
    return [
        {"term": term, "maps_to": mapped, "origin": origin}
        for term, mapped in CATALOG["synonyms"].items()
    ]


def mark_today(conn) -> None:
    _meta_set(conn, "today", "1")
    log(
        conn,
        "Pharmacy advocate",
        "Ran today's document search for Rx pricing disclaimer. 3 documents. The tool cannot say which wording is current.",
    )
    conn.commit()


def _tokenize(text: str) -> list[str]:
    text = text.lower().replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = []
    synonyms = CATALOG["synonyms"]
    notes = []
    for token in text.split():
        mapped = synonyms.get(token, token)
        if mapped != token:
            notes.append(f"{token} -> {mapped}")
        tokens.append(mapped)
    return tokens, notes


def _content_tokens(text: str):
    tokens, notes = _tokenize(text)
    content = [token for token in tokens if token not in STOP and len(token) > 2]
    return content, notes


VERBATIM_CUES = {"say", "read", "wording", "verbatim", "disclaimer", "script"}


def _score_unit(query: str, title: str, tags: str, text: str, domain: str, unit_type: str):
    content, notes = _content_tokens(query)
    if not content:
        return 0.0, 0, 0, notes
    blob, _ = _tokenize(" ".join([title, tags, text, domain]))
    title_tags, _ = _tokenize(f"{title} {tags}")
    raw_tokens, _ = _tokenize(query)
    present = set(blob)
    titled = set(title_tags)
    overlap = [token for token in content if token in present]
    score = len(overlap) / len(content)
    if content[0] in titled:
        score += 0.35
    if len(overlap) >= 2 and unit_type == "verbatim" and any(token in VERBATIM_CUES for token in raw_tokens):
        score += 0.4
    weight = sum(len(token) for token in overlap)
    return score, weight, len(overlap), notes


def approved_search_pool(conn) -> list[dict]:
    """Approved units search may show the model, using the live wording when a revision replaced it."""
    from src.ai import with_audience_override
    from src.corpus import load_corpus

    corpus = load_corpus()
    approved = {
        row["unit_id"]
        for row in conn.execute(
            "SELECT unit_id FROM units WHERE status = 'approved' AND search_visible = 1"
        )
    }
    confirmed = flag(conn, "tags_confirmed")
    pool = []
    for unit in corpus["units"]:
        if unit["unit_id"] not in approved:
            continue
        if unit["source_mismatch"] or unit["verbatim_altered"]:
            continue
        live = live_approved(conn, unit["unit_id"])
        if live is not None and live["text"] != unit.get("text"):
            unit = dict(unit)
            unit["text"] = live["text"]
        if confirmed:
            unit = with_audience_override(unit)
        if mode_name(conn) == "explore" and live is not None:
            from src.finish import past_review

            if past_review(live):
                continue
        pool.append(unit)
    if mode_name(conn) == "explore":
        from src.sandbox import sandbox_search_units

        pool.extend(sandbox_search_units(conn))
    return pool


_PHONE = re.compile(r"\b(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}\b")
_DOB = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)
_MEMBER_LABELED = re.compile(
    r"\b(?:member\s*id|mbr\s*id|member)\s*[:#-]?\s*[A-Za-z]?\d{5,}\b",
    re.IGNORECASE,
)
_MEMBER_TOKEN = re.compile(r"\b[A-Za-z]{1,3}\d{6,}\b")
_NINE_DIGIT = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b")
# CMS Medicare Beneficiary Identifier: 11 characters, grouped 4-3-4, dashes optional.
# Letters S, L, O, I, B, and Z are not used.
_MBI = re.compile(
    r"\b[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d"
    r"-?[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d"
    r"-?[AC-HJKMNP-RT-Y]{2}\d{2}\b",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_STREET = re.compile(
    r"\b\d{1,6}\s+(?:[A-Za-z][A-Za-z0-9'.-]*\s+){1,4}"
    r"(?:Street|Avenue|Road|Boulevard|Drive|Lane|St|Ave|Rd|Blvd|Dr|Ln)\.?\b",
    re.IGNORECASE,
)
_ZIP = re.compile(r"\b\d{5}(?:-\d{4})?\b")
_CLAIM_RUN = re.compile(r"\b\d{10,}\b")
_CLAIM_DASHED = re.compile(r"\b\d{2,}(?:-\d{2,})+\b")
_DOLLAR = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
UNCLUSTERED_ID = "new-unclustered"
UNCLUSTERED_LABEL = "New, not yet clustered"


def _redact_claim_numbers(text: str) -> str:
    """Claim or reference numbers of 10 or more digits, with or without dashes."""
    text = _CLAIM_RUN.sub("[redacted]", text)

    def replace(match):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) >= 10:
            return "[redacted]"
        return match.group(0)

    return _CLAIM_DASHED.sub(replace, text)


def redact_query(query: str) -> str:
    """Remove member identifiers before a query is stored or sent to a model.

    Local lexical ranking still uses the original text. Dollar amounts, drug
    names, conditions, and plan names are left as written.
    """
    text = query or ""
    held = []

    def hold_dollar(match):
        held.append(match.group(0))
        return f"CURR{len(held) - 1}CURR"

    from src.compliance import redact_names, redact_phones

    text = _DOLLAR.sub(hold_dollar, text)
    text = redact_phones(text)
    text = _EMAIL.sub("[redacted]", text)
    text = _DOB.sub("[redacted]", text)
    text = _MBI.sub("[redacted]", text)
    text = _STREET.sub("[redacted]", text)
    text = _MEMBER_LABELED.sub("[redacted]", text)
    text = _MEMBER_TOKEN.sub("[redacted]", text)
    text = _redact_claim_numbers(text)
    text = _NINE_DIGIT.sub("[redacted]", text)
    text = _ZIP.sub("[redacted]", text)
    for index, original in enumerate(held):
        text = text.replace(f"CURR{index}CURR", original)
    return redact_names(text)


def _feedback_route(kind: str) -> str:
    if kind in CONTENT_FEEDBACK_KINDS:
        return "author"
    if kind in PRODUCT_FEEDBACK_KINDS:
        return "product"
    raise ValueError(f"Unknown feedback kind '{kind}'.")


def _signals_dict(signals) -> dict:
    """Optional signals object. Known keys: searches_in_call, seconds_to_answer."""
    if signals is None or signals == "":
        return {}
    if isinstance(signals, str):
        try:
            signals = json.loads(signals)
        except json.JSONDecodeError as exc:
            raise ValueError("signals must be a JSON object.") from exc
    if not isinstance(signals, dict):
        raise ValueError("signals must be a JSON object.")
    for key in ("searches_in_call", "seconds_to_answer"):
        if key in signals and signals[key] is not None and not isinstance(signals[key], (int, float)):
            raise ValueError(f"signals.{key} must be a number.")
    return signals


def _feedback_dict(row) -> dict:
    raw = row["signals"] or ""
    try:
        signals = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        signals = {}
    if not isinstance(signals, dict):
        signals = {}
    return {
        "id": row["id"],
        "ts": row["ts"],
        "source": row["source"],
        "role": row["role"],
        "kind": row["kind"],
        "question": row["question"] or "",
        "unit_id": row["unit_id"] or "",
        "note": row["note"] or "",
        "signals": signals,
        "route": row["route"],
        "status": row["status"],
        "resolution": row["resolution"] or "",
        "resolved_on": row["resolved_on"] or "",
    }


def record_feedback(conn, source, role, kind, question, unit_id, note, signals) -> dict:
    """Store one feedback record, redact the question and note, route it, and log it.

    source is "advocate" or "channel".
    kind is a content kind (routed to the Knowledge Ops author) or a findability
    or product kind, including "slow" (routed to the product backlog).
    signals is an optional object with searches_in_call and seconds_to_answer.

    Returns the stored row: id, ts, source, role, kind, question, unit_id, note,
    signals, route ("author" or "product"), status ("open"), resolution, resolved_on.
    question and note are the redacted text.
    """
    source = (source or "").strip()
    if source not in FEEDBACK_SOURCES:
        raise ValueError("Feedback source must be advocate or channel.")
    role = "" if role is None else str(role).strip()
    if not role:
        raise ValueError("A role is required.")
    kind = (kind or "").strip()
    if kind not in FEEDBACK_KINDS:
        raise ValueError(f"Unknown feedback kind '{kind}'.")
    safe_question = redact_query("" if question is None else str(question))
    safe_note = redact_query("" if note is None else str(note))
    unit = "" if unit_id is None else str(unit_id).strip()
    stored_signals = _signals_dict(signals)
    route = _feedback_route(kind)
    cursor = conn.execute(
        """
        INSERT INTO feedback (
            ts, source, role, kind, question, unit_id, note, signals, route, status, resolution, resolved_on
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', '', '')
        """,
        (
            now_et(),
            source,
            role,
            kind,
            safe_question,
            unit,
            safe_note,
            json.dumps(stored_signals, sort_keys=True),
            route,
        ),
    )
    feedback_id = cursor.lastrowid
    target = "Knowledge Ops author" if route == "author" else "product backlog"
    unit_bit = f" Unit {unit}." if unit else ""
    log(
        conn,
        role,
        f"Recorded {kind} feedback from {source}.{unit_bit} Routed to the {target}. Question: '{safe_question}'.",
    )
    row = conn.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    return _feedback_dict(row)


def _feedback_groups(conn, kinds: tuple[str, ...], route: str) -> list[dict]:
    """Open records for one route, grouped by kind, with counts and example questions."""
    rows = conn.execute(
        """
        SELECT id, kind, question FROM feedback
        WHERE route = ? AND status = 'open'
        ORDER BY id DESC
        """,
        (route,),
    ).fetchall()
    by_kind: dict[str, list] = {}
    for row in rows:
        by_kind.setdefault(row["kind"], []).append(row)
    ordered = [kind for kind in kinds if by_kind.get(kind)]
    extras = [kind for kind in by_kind if kind not in kinds and by_kind[kind]]
    groups = []
    for kind in ordered + extras:
        items = by_kind[kind]
        examples = [item["question"] for item in items if item["question"]][:_FEEDBACK_EXAMPLE_LIMIT]
        groups.append(
            {
                "kind": kind,
                "count": len(items),
                "examples": examples,
                "ids": [item["id"] for item in items],
            }
        )
    return groups


def feedback_for_author(conn) -> list[dict]:
    """Open content feedback for the Knowledge Ops author.

    Returns a list of groups, one per kind that has open records, in content-kind order.
    Each group has kind, count, examples (up to three redacted questions, newest first),
    and ids.
    """
    return _feedback_groups(conn, CONTENT_FEEDBACK_KINDS, "author")


def product_backlog(conn) -> list[dict]:
    """Open findability and product feedback.

    Returns a list of groups, one per kind that has open records, in product-kind order.
    Each group has kind, count, examples (up to three redacted questions, newest first),
    and ids.
    """
    return _feedback_groups(conn, PRODUCT_FEEDBACK_KINDS, "product")


def _feedback_moment(value: str):
    text = (value or "").replace(" ET", "").strip()
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return parsed.replace(tzinfo=ZoneInfo("America/New_York"))


def _this_week_start() -> datetime:
    """Monday 00:00 in America/New_York."""
    now = datetime.now(ZoneInfo("America/New_York"))
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight - timedelta(days=now.weekday())


def feedback_summary(conn) -> dict:
    """Insights for the current week: counts by kind, and the most-flagged units.

    The week starts Monday 00:00 America/New_York. Open and resolved records both count.
    most_flagged is up to five units, highest count first. Records with no unit id are
    left out of that ranking.

    Returns week_start (YYYY-MM-DD), by_kind (kind, count), most_flagged
    (unit_id, count, kinds), and note.
    """
    start = _this_week_start()
    end = start + timedelta(days=7)
    rows = conn.execute("SELECT kind, unit_id, ts FROM feedback").fetchall()
    kind_counts = {kind: 0 for kind in FEEDBACK_KINDS}
    unit_counts: dict[str, int] = {}
    unit_kinds: dict[str, set[str]] = {}
    extra_kinds: list[str] = []
    for row in rows:
        moment = _feedback_moment(row["ts"])
        if moment is None or moment < start or moment >= end:
            continue
        kind = row["kind"]
        if kind in kind_counts:
            kind_counts[kind] += 1
        else:
            if kind not in extra_kinds:
                extra_kinds.append(kind)
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
        unit_id = (row["unit_id"] or "").strip()
        if not unit_id:
            continue
        unit_counts[unit_id] = unit_counts.get(unit_id, 0) + 1
        unit_kinds.setdefault(unit_id, set()).add(kind)
    by_kind = [{"kind": kind, "count": kind_counts[kind]} for kind in FEEDBACK_KINDS if kind_counts[kind]]
    for kind in extra_kinds:
        by_kind.append({"kind": kind, "count": kind_counts[kind]})
    ranked = []
    for unit_id, count in unit_counts.items():
        kinds = [kind for kind in FEEDBACK_KINDS if kind in unit_kinds[unit_id]]
        kinds.extend(sorted(kind for kind in unit_kinds[unit_id] if kind not in FEEDBACK_KINDS))
        ranked.append({"unit_id": unit_id, "count": count, "kinds": kinds})
    ranked.sort(key=lambda item: (-item["count"], item["unit_id"]))
    return {
        "week_start": start.strftime("%Y-%m-%d"),
        "by_kind": by_kind,
        "most_flagged": ranked[:5],
        "note": "Illustrative, made-up data",
    }


def resolve_feedback(conn, feedback_id, resolution) -> dict:
    """Close one feedback record. A resolution note is required.

    The note is redacted before it is stored. The resolution is logged.
    Returns the updated row, with status "resolved" and resolved_on set.
    """
    note = redact_query((resolution or "").strip())
    if not note:
        raise ValueError("A resolution note is required.")
    try:
        feedback_id = int(feedback_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("No feedback record for that id.") from exc
    row = conn.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    if row is None:
        raise ValueError(f"No feedback record {feedback_id}.")
    if row["status"] == "resolved":
        raise ValueError(f"Feedback {feedback_id} is already resolved.")
    when = now_et()
    conn.execute(
        """
        UPDATE feedback
        SET status = 'resolved', resolution = ?, resolved_on = ?
        WHERE id = ?
        """,
        (note, when, feedback_id),
    )
    actor = "Knowledge Ops author" if row["route"] == "author" else "Knowledge owner"
    log(conn, actor, f"Resolved feedback {feedback_id} ({row['kind']}). {note}")
    updated = conn.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    return _feedback_dict(updated)


def _seed_explore_feedback(conn) -> None:
    """Load the illustrative Explore feedback records from human_decisions.json."""
    from src.ai import load_human_decisions

    spec = load_human_decisions().get("explore_feedback") or {}
    for item in spec.get("records") or []:
        record_feedback(
            conn,
            item.get("source") or "",
            item.get("role") or "",
            item.get("kind") or "",
            item.get("question") or "",
            item.get("unit_id") or "",
            item.get("note") or "",
            item.get("signals"),
        )


def wording_title(title: str) -> str:
    """The wording name, without the Legal queue suffix stored on the unit title."""
    text = (title or "").strip()
    for suffix in (" (Legal verbatim)", " (Legal)"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text


def _role_can_read(role: str, kb_scope: str) -> bool:
    """Same knowledge-base overlap search uses before it ranks."""
    allowed = set(ROLE_KB.get(role, []))
    if not allowed:
        return False
    scopes = {part.strip() for part in (kb_scope or "").split(",") if part.strip()}
    return bool(allowed & scopes)


def _known_unit_ids(conn, unit_ids) -> list[str]:
    known = []
    seen = set()
    for raw in unit_ids or []:
        unit_id = str(raw or "").strip()
        if not unit_id or unit_id in seen:
            continue
        row = conn.execute(
            "SELECT 1 FROM units WHERE unit_id = ? LIMIT 1",
            (unit_id,),
        ).fetchone()
        if row is None:
            continue
        seen.add(unit_id)
        known.append(unit_id)
    return known


def _approved_verbatim(conn, unit_id: str) -> bool:
    row = conn.execute(
        """
        SELECT type, requires_legal FROM units
        WHERE unit_id = ? AND status = 'approved'
        ORDER BY version DESC LIMIT 1
        """,
        (unit_id,),
    ).fetchone()
    if row is None:
        return False
    return row["type"] == "verbatim" or (bool(row["requires_legal"]) and row["type"] == "verbatim")


def _next_wrapup_id(conn) -> str:
    highest = 0
    for row in conn.execute("SELECT id FROM call_wrapups").fetchall():
        text = row["id"] or ""
        if not text.startswith("W-"):
            continue
        try:
            highest = max(highest, int(text[2:]))
        except ValueError:
            continue
    return f"W-{highest + 1}"


def _wrapup_message(role: str, call_reason: str, read_verbatim, outcome: str) -> str:
    message = f"{role} wrapped up a call about {call_reason}."
    if read_verbatim is True:
        message += " Read the approved wording word for word: yes."
    elif read_verbatim is False:
        message += " Read the approved wording word for word: no."
    if outcome == "follow_up":
        message += " Follow-up needed."
    return message


def _wrapup_dict(row) -> dict:
    flag = row["read_verbatim"]
    if flag is None:
        read = None
    else:
        read = bool(flag)
    return {
        "id": row["id"],
        "role": row["role"],
        "call_id": row["call_id"] or "",
        "call_reason": row["call_reason"] or "",
        "unit_ids": [part.strip() for part in (row["unit_ids"] or "").split(",") if part.strip()],
        "displayed_units": _displayed_units(row),
        "read_verbatim": read,
        "outcome": row["outcome"],
        "note": row["note"] or "",
        "created_at": row["created_at"] or "",
    }


def record_wrapup(conn, role, call_id, call_reason, unit_ids, read_verbatim, outcome, note, displayed_units=None) -> dict:
    """Store one call wrap-up. Free-text fields are redacted before they are stored or logged.

    Unknown unit ids are dropped. Returns the stored row.
    Raises ValueError with the refusal sentence when the call cannot be saved.
    """
    role = "" if role is None else str(role).strip()
    if role not in ADVOCATE_ROLES:
        raise ValueError("Only an advocate can wrap up a call.")
    outcome = "" if outcome is None else str(outcome).strip()
    if outcome not in WRAP_OUTCOMES:
        raise ValueError("Choose how the call ended.")
    known = _known_unit_ids(conn, unit_ids)
    needs_confirmation = any(_approved_verbatim(conn, unit_id) for unit_id in known)
    if needs_confirmation and read_verbatim is not True and read_verbatim is not False:
        raise ValueError("Confirm whether you read the approved wording word for word.")
    if read_verbatim is True:
        stored_flag = 1
    elif read_verbatim is False:
        stored_flag = 0
    else:
        stored_flag = None
        read_verbatim = None
    raw_note = "" if note is None else str(note)
    if outcome == "follow_up" and not raw_note.strip():
        raise ValueError("Add a note so the follow-up has what it needs.")
    safe_call_id = redact_query("" if call_id is None else str(call_id)).strip()
    safe_reason = redact_query("" if call_reason is None else str(call_reason)).strip()
    safe_note = redact_query(raw_note).strip()
    wrapup_id = _next_wrapup_id(conn)
    created = now_iso()
    conn.execute(
        """
        INSERT INTO call_wrapups (
            id, role, call_id, call_reason, read_verbatim, unit_ids, outcome, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            wrapup_id,
            role,
            safe_call_id,
            safe_reason,
            stored_flag,
            ",".join(known),
            outcome,
            safe_note,
            created,
        ),
    )
    shown = _prepare_displayed(conn, known, displayed_units)
    conn.execute(
        "UPDATE call_wrapups SET displayed_units = ? WHERE id = ?",
        (json.dumps(shown), wrapup_id),
    )
    log(conn, role, _wrapup_message(role, safe_reason, read_verbatim, outcome))
    row = conn.execute("SELECT * FROM call_wrapups WHERE id = ?", (wrapup_id,)).fetchone()
    return _wrapup_dict(row)


def _prepare_displayed(conn, known: list[str], displayed_units) -> list[dict]:
    """unit_id, version, and a hash of the text that was on screen."""
    prepared = []
    items = displayed_units if isinstance(displayed_units, list) else []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        unit_id = str(item.get("unit_id") or "").strip()
        if not unit_id:
            continue
        try:
            version = int(item.get("version") or 0)
        except (TypeError, ValueError):
            version = 0
        text = "" if item.get("text") is None else str(item.get("text"))
        text_hash = str(item.get("text_hash") or "").strip() or hashlib.sha256(text.encode("utf-8")).hexdigest()
        row = None
        if version:
            row = conn.execute(
                "SELECT status, version FROM units WHERE unit_id = ? AND version = ?",
                (unit_id, version),
            ).fetchone()
        live = conn.execute(
            """
            SELECT version FROM units
            WHERE unit_id = ? AND status = 'approved'
            ORDER BY version DESC LIMIT 1
            """,
            (unit_id,),
        ).fetchone()
        superseded = row is None or row["status"] != "approved"
        if live is not None and version and int(live["version"]) != version:
            superseded = True
        prepared.append({
            "unit_id": unit_id,
            "version": version,
            "text_hash": text_hash,
            "superseded_read": superseded,
        })
        seen.add(unit_id)
    for unit_id in known:
        if unit_id in seen:
            continue
        live = conn.execute(
            """
            SELECT version, text FROM units
            WHERE unit_id = ? AND status = 'approved'
            ORDER BY version DESC LIMIT 1
            """,
            (unit_id,),
        ).fetchone()
        if live is None:
            continue
        prepared.append({
            "unit_id": unit_id,
            "version": int(live["version"]),
            "text_hash": hashlib.sha256((live["text"] or "").encode("utf-8")).hexdigest(),
            "superseded_read": False,
        })
    return prepared


def _displayed_units(row) -> list:
    raw = ""
    try:
        raw = row["displayed_units"] or ""
    except (KeyError, IndexError):
        raw = ""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def wrapup_summary(conn) -> dict:
    rows = conn.execute("SELECT read_verbatim, outcome FROM call_wrapups").fetchall()
    return {
        "count": len(rows),
        "verbatim_required": sum(1 for row in rows if row["read_verbatim"] is not None),
        "verbatim_confirmed": sum(1 for row in rows if row["read_verbatim"] == 1),
        "follow_ups": sum(1 for row in rows if row["outcome"] == "follow_up"),
    }


def list_wrapups(conn, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM call_wrapups ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_wrapup_dict(row) for row in rows]


def _approved_revisions(conn):
    return conn.execute(
        """
        SELECT * FROM units
        WHERE status = 'approved' AND search_visible = 1 AND version > 1
        ORDER BY version DESC, approved_on DESC, unit_id
        """
    ).fetchall()


def revisions_for_role(conn, role: str) -> list:
    """Approved versions above 1 that this role can search. Unknown roles raise ValueError."""
    role = "" if role is None else str(role).strip()
    if role not in EXPLORE_ROLES:
        raise ValueError("Unknown role.")
    return [row for row in _approved_revisions(conn) if _role_can_read(role, row["kb_scope"])]


def previous_revision(conn, unit_id: str, version: int):
    return conn.execute(
        """
        SELECT * FROM units
        WHERE unit_id = ? AND version < ?
        ORDER BY version DESC LIMIT 1
        """,
        (unit_id, version),
    ).fetchone()


def is_acknowledged(conn, role: str, unit_id: str, version: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM change_acks WHERE role = ? AND unit_id = ? AND version = ?",
        (role, unit_id, version),
    ).fetchone()
    return row is not None


def acknowledge_change(conn, role: str, unit_id: str, version: int) -> tuple[str, bool]:
    """Record that this advocate saw this version.

    Returns (message, created). A repeat returns the same message and created False,
    with no new activity row. A missing version raises LookupError. A non-advocate
    raises ValueError.
    """
    role = "" if role is None else str(role).strip()
    if role not in ADVOCATE_ROLES:
        raise ValueError("Only an advocate can acknowledge a change.")
    unit_id = "" if unit_id is None else str(unit_id).strip()
    try:
        version = int(version)
    except (TypeError, ValueError) as exc:
        raise LookupError("That unit version does not exist.") from exc
    row = conn.execute(
        "SELECT title FROM units WHERE unit_id = ? AND version = ?",
        (unit_id, version),
    ).fetchone()
    if row is None or not unit_id:
        raise LookupError("That unit version does not exist.")
    title = wording_title(row["title"])
    message = f"Acknowledged version {version} of {title}."
    if is_acknowledged(conn, role, unit_id, version):
        return message, False
    conn.execute(
        """
        INSERT INTO change_acks (role, unit_id, version, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (role, unit_id, version, now_iso()),
    )
    log(conn, role, f"{role} acknowledged version {version} of {title}.")
    return message, True


def acknowledgement_overview(conn) -> list[dict]:
    """Each live revision, with the advocate roles in scope split by confirmation."""
    items = []
    for row in _approved_revisions(conn):
        acknowledged = []
        pending = []
        for role in ADVOCATE_ROLES:
            if not _role_can_read(role, row["kb_scope"]):
                continue
            if is_acknowledged(conn, role, row["unit_id"], row["version"]):
                acknowledged.append(role)
            else:
                pending.append(role)
        if not acknowledged and not pending:
            continue
        items.append({
            "unit_id": row["unit_id"],
            "title": wording_title(row["title"]),
            "version": row["version"],
            "acknowledged_by": acknowledged,
            "pending": pending,
        })
    return items


def _closed_gap_hit(conn, role: str, query: str):
    """The approved unit that closed this exact question, when the role may read its knowledge bases."""
    safe = redact_query(query or "").strip().lower()
    if not safe:
        return None
    allowed = set(ROLE_KB.get(role, []))
    if not allowed:
        return None
    rows = conn.execute(
        "SELECT queries, unit_id FROM gaps WHERE status = 'closed' AND unit_id != ''"
    ).fetchall()
    for row in rows:
        queries = [redact_query(item).strip().lower() for item in _query_lines(row["queries"])]
        if safe not in queries:
            continue
        unit = live_approved(conn, row["unit_id"])
        if unit is None:
            continue
        kbs = {part.strip() for part in (unit["kb_scope"] or "").split(",") if part.strip()}
        if not (kbs & allowed):
            continue
        if role == "Member" and not (unit["member_text"] or "").strip():
            continue
        return unit
    return None


def _ranked_for_role(query: str, role: str, units: list[dict]) -> list[tuple]:
    """Lexical rank for one role. Each item is (score, weight, unit_id, unit)."""
    kbs = set(ROLE_KB.get(role, []))
    scored = []
    for unit in units:
        scope = unit.get("kb_scope") or []
        if isinstance(scope, str):
            scope = [part.strip() for part in scope.split(",") if part.strip()]
        if not set(scope) & kbs:
            continue
        audience = unit.get("audience_list") or []
        member_wording = (unit.get("member_text") or "").strip()
        if role == "Member" and "member" not in audience and not member_wording:
            continue
        tags = ", ".join(unit.get("tags") or [])
        score, weight, _overlap, _notes = _score_unit(
            query,
            unit.get("title") or "",
            tags,
            unit.get("text") or "",
            unit.get("domain") or "",
            unit.get("type") or "",
        )
        scored.append((score, weight, unit.get("unit_id") or "", unit))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return scored


_SCORING = contextvars.ContextVar("harbor_scoring", default=False)


def _explore_caregiver_hit(conn, role: str, query: str):
    """Explore-only answer for the known caregiver miss. Scoring does not use it."""
    from src.compliance import CAREGIVER_ID, caregiver_price_question

    if _SCORING.get() or mode_name(conn) != "explore":
        return None
    if role != "Pharmacy advocate" or not caregiver_price_question(query):
        return None
    return live_approved(conn, CAREGIVER_ID)


def _foreign_conflict(role: str, unit: dict) -> bool:
    scopes = unit.get("kb_scope") or []
    if isinstance(scopes, str):
        scopes = [part.strip() for part in scopes.split(",") if part.strip()]
    home = {part for part in scopes if part and part != "shared-legal"}
    allowed = set(ROLE_KB.get(role, []))
    role_home = {part for part in allowed if part != "shared-legal"}
    return bool(home) and not bool(home & role_home)


def _transfer_role(role: str) -> str:
    if role == "Pharmacy advocate":
        return "Insurance advocate"
    if role == "Insurance advocate":
        return "Pharmacy advocate"
    return "queue that owns that knowledge base"


def _blocked_best(conn, role: str, query: str):
    """The blocked unit that outranks every approved unit for this question, or None."""
    if role == "Member" or not (query or "").strip():
        return None
    from src.ai import with_audience_override
    from src.corpus import load_corpus

    blocked_ids = [
        row["unit_id"]
        for row in conn.execute(
            "SELECT unit_id FROM units WHERE status = 'blocked_conflict' AND version = 1"
        )
    ]
    if not blocked_ids:
        return None
    by_id = {unit["unit_id"]: unit for unit in load_corpus()["units"]}
    confirmed = flag(conn, "tags_confirmed")
    blocked = []
    for unit_id in blocked_ids:
        unit = by_id.get(unit_id)
        if unit is None:
            row = conn.execute(
                "SELECT * FROM units WHERE unit_id = ? AND version = 1",
                (unit_id,),
            ).fetchone()
            if row is None:
                continue
            unit = {
                "unit_id": row["unit_id"],
                "title": row["title"] or "",
                "text": row["text"] or "",
                "kb_scope": [part.strip() for part in (row["kb_scope"] or "").split(",") if part.strip()],
                "audience_list": [],
                "tags": [],
                "domain": "",
                "type": row["type"] or "",
            }
        unit = dict(unit)
        if confirmed:
            unit = with_audience_override(unit)
        blocked.append(unit)
    unscoped = []
    for unit in blocked:
        score, weight, _overlap, _notes = _score_unit(
            query,
            unit.get("title") or "",
            ", ".join(unit.get("tags") or []),
            unit.get("text") or "",
            unit.get("domain") or "",
            unit.get("type") or "",
        )
        unscoped.append((score, weight, unit.get("unit_id") or "", unit))
    unscoped.sort(key=lambda item: (-item[0], -item[1], item[2]))
    if unscoped and unscoped[0][0] > 0 and _foreign_conflict(role, unscoped[0][3]):
        approved_ranked = _ranked_for_role(query, role, approved_search_pool(conn))
        best_approved = approved_ranked[0][0] if approved_ranked else -1.0
        if unscoped[0][0] > best_approved:
            return unscoped[0][3]
    blocked_ranked = _ranked_for_role(query, role, blocked)
    if not blocked_ranked or blocked_ranked[0][0] <= 0:
        return None
    approved_ranked = _ranked_for_role(query, role, approved_search_pool(conn))
    best_approved = approved_ranked[0][0] if approved_ranked else -1.0
    if blocked_ranked[0][0] > best_approved:
        return blocked_ranked[0][3]
    return None


def _fallback_unit(conn, unit_id: str):
    """An approved unit this blocked wording conflicts with, when one is live."""
    row = conn.execute(
        "SELECT conflicts_with FROM units WHERE unit_id = ? AND version = 1",
        (unit_id,),
    ).fetchone()
    if row is None:
        return None
    for other_id in (row["conflicts_with"] or "").split(","):
        other_id = other_id.strip()
        if not other_id:
            continue
        live = live_approved(conn, other_id)
        if live is not None:
            return live
    return None


def search(conn, role: str, query: str, record: bool = False):
    from src.ai import FALLBACK_CAPTION
    from src.corpus import decide

    closed = _closed_gap_hit(conn, role, query)
    closed_source = "closed_gap"
    closed_note = "This question was closed by an approved unit."
    if closed is None:
        caregiver = _explore_caregiver_hit(conn, role, query)
        if caregiver is not None:
            closed = caregiver
            closed_source = "rule"
            closed_note = "The approved caregiver rule answers this question."
    if closed is not None:
        result = {
            "abstained": False,
            "unit": closed,
            "ranked": [(1, closed["unit_id"])],
            "searched": list(ROLE_KB.get(role, [])),
            "note": closed_note,
            "ai_source": closed_source,
            "ai_caption": "",
            "query": query,
            "logged_query": redact_query(query),
            "role": role,
        }
        if record:
            record_search(conn, role, query, result)
        return result
    from src.finish import explore_expired_block

    expired = explore_expired_block(conn, query, role)
    if expired is not None:
        expired["searched"] = list(ROLE_KB.get(role, []))
        expired["logged_query"] = redact_query(query)
        if record:
            log(conn, role, f"Search '{expired['logged_query']}' is past its review date.")
            conn.commit()
        return expired
    blocked = _blocked_best(conn, role, query)
    if blocked is not None and _foreign_conflict(role, blocked):
        target = _transfer_role(role)
        queue = "Insurance queue" if role == "Pharmacy advocate" else "Pharmacy queue"
        result = {
            "abstained": True,
            "unit": None,
            "ranked": [],
            "searched": list(ROLE_KB.get(role, [])),
            "note": f"No approved answer in this knowledge base. Transfer this call to the {target}.",
            "ai_source": "transfer",
            "ai_caption": "",
            "status": "transfer",
            "blocked_note": "",
            "transfer_to": target,
            "transfer": {"queue": queue, "reason": f"This question belongs to the {queue}."},
            "fallback_unit": None,
            "query": query,
            "logged_query": redact_query(query),
            "role": role,
        }
        if record:
            log(conn, role, f"Search '{result['logged_query']}' is outside this knowledge base. Transfer to the {target}.")
            conn.commit()
        return result
    if blocked is not None:
        result = {
            "abstained": True,
            "unit": None,
            "ranked": [(1, blocked["unit_id"])],
            "searched": list(ROLE_KB.get(role, [])),
            "note": BLOCKED_NOTE,
            "ai_source": "blocked",
            "ai_caption": "",
            "status": "blocked_conflict",
            "blocked_note": BLOCKED_NOTE,
            "fallback_unit": _fallback_unit(conn, blocked["unit_id"]),
            "query": query,
            "logged_query": redact_query(query),
            "role": role,
        }
        if record:
            record_search(conn, role, query, result)
        return result
    from src.finish import candidate_limit, expand_explore_query

    pool = approved_search_pool(conn)
    limit = candidate_limit(conn)
    rank_query = expand_explore_query(query) if limit > 3 else query
    timeout_token = _EXPLORE_TIMEOUT.set(mode_name(conn) == "explore")
    token = bind_live_conn(conn)
    try:
        decision = decide(query, role, pool, live=live_enabled(conn), limit=limit, rank_query=rank_query)
    finally:
        unbind_live_conn(token)
        _EXPLORE_TIMEOUT.reset(timeout_token)
    answer = decision["answer_unit_id"]
    unit = live_approved(conn, answer) if answer else None
    abstained = unit is None
    source = decision["source"]
    result = {
        "abstained": abstained,
        "unit": None if abstained else unit,
        "ranked": [(index + 1, unit_id) for index, unit_id in enumerate(decision["candidates"])],
        "searched": list(ROLE_KB.get(role, [])),
        "note": decision["reason"],
        "ai_source": source,
        "ai_caption": (
            FALLBACK_CAPTION
            if source == "fallback"
            else (decision["reason"] if source == "capped" else "")
        ),
        "query": query,
        "logged_query": redact_query(query),
        "role": role,
    }
    if source == "timeout":
        result["abstained"] = True
        result["unit"] = None
        result["note"] = "The lookup took too long, so no answer is shown."
        result["ai_source"] = "timeout"
        result["status"] = "abstain"
    elif result["abstained"]:
        from src.finish import cross_kb_transfer

        transfer = cross_kb_transfer(conn, role, query)
        if transfer is not None:
            result["status"] = "transfer"
            result["ai_source"] = "transfer"
            result["transfer_to"] = transfer["transfer_to"]
            result["transfer"] = {"queue": transfer["queue"], "reason": transfer["reason"]}
            result["note"] = transfer["reason"]
            result["blocked_note"] = ""
    if record:
        safe = result["logged_query"]
        if result["abstained"]:
            _bump_gap(conn, query, role)
            log(
                conn,
                role,
                f"Search '{safe}' returned no approved answer. The question was logged for the knowledge team. Searched: {', '.join(result['searched']) or 'none'}.",
            )
        else:
            chosen = result["unit"]
            log(
                conn,
                role,
                f"Search '{safe}' returned {chosen['unit_id']} version {chosen['version']}. AI chose that unit. Searched: {', '.join(result['searched'])}.",
            )
        _meta_set(conn, f"asked:{role}:{safe}", "1")
        conn.commit()
    if (
        result.get("abstained")
        and result.get("status") not in {"blocked_conflict", "transfer"}
        and result.get("ai_source") not in {"blocked", "transfer"}
    ):
        from src.sandbox import process_gap_follow_up

        follow = process_gap_follow_up(conn, query)
        if follow:
            result["follow_up"] = follow
            note = result.get("note") or "No approved answer"
            if "The business has no answer yet" not in note:
                result["note"] = note.rstrip(".") + ". The business has no answer yet. Follow up with the knowledge owner."
    return result


def record_search(conn, role: str, query: str, result: dict) -> None:
    """Log and count a search that already has a result.

    An abstention drafts a gap unit when Live AI is on and the question matches
    no cluster. Cached mode only counts the question.
    """
    safe = redact_query(query)
    unit = result.get("unit")
    unit_id = ""
    version = ""
    if unit is not None:
        unit_id = unit["unit_id"]
        version = str(unit["version"])
    elif result.get("unit_id"):
        unit_id = result["unit_id"]
        version = str(result.get("version") or "")
    if result.get("ai_source") == "blocked":
        log(
            conn,
            role,
            f"Search '{safe}' matched a unit under Legal review. The blocked wording was not shown.",
        )
        _meta_set(conn, f"asked:{role}:{safe}", "1")
        conn.commit()
        return
    if result.get("abstained") or not unit_id:
        _bump_gap(conn, query, role)
        log(
            conn,
            role,
            f"Search '{safe}' returned no approved answer. The question was logged for the knowledge team. "
            f"Answer source: {result.get('ai_source', '')}.",
        )
    else:
        log(
            conn,
            role,
            f"Search '{safe}' returned {unit_id} version {version}. Answer source: {result.get('ai_source', '')}.",
        )
    _meta_set(conn, f"asked:{role}:{safe}", "1")
    conn.commit()


def _human_member_ids() -> set[str]:
    """Unit ids whose member wording was recorded as a human decision."""
    from src.ai import load_human_decisions

    texts = load_human_decisions().get("member_texts") or {}
    return {
        unit_id
        for unit_id, spec in texts.items()
        if isinstance(spec, dict) and (spec.get("member_text") or "").strip()
    }


def member_candidate_units(conn) -> list[dict]:
    """Approved units a member may read.

    A unit is eligible when it is approved and its member_text is non-empty
    and human-approved. The advocate audience does not matter. The model
    sees member_text, never the advocate script.
    """
    from src.corpus import load_corpus

    approved_wording = _human_member_ids()
    by_id = {unit["unit_id"]: unit for unit in load_corpus()["units"]}
    rows = conn.execute(
        """
        SELECT unit_id, version, title, audience, member_text, review_by, review_extension
        FROM units
        WHERE status = 'approved' AND search_visible = 1
        ORDER BY unit_id, version DESC
        """
    ).fetchall()
    seen = set()
    pool = []
    for row in rows:
        if row["unit_id"] in seen:
            continue
        seen.add(row["unit_id"])
        if row["unit_id"] not in approved_wording:
            continue
        if mode_name(conn) == "explore":
            from src.finish import past_review

            if past_review(row):
                continue
        audience = [part.strip() for part in (row["audience"] or "").split(",") if part.strip()]
        member_text = (row["member_text"] or "").strip()
        if not member_text:
            continue
        base = dict(by_id.get(row["unit_id"]) or {})
        base["unit_id"] = row["unit_id"]
        base["title"] = row["title"]
        base["text"] = member_text
        base["member_text"] = member_text
        base["version"] = row["version"]
        base["audience_list"] = audience
        if "kb_scope" not in base:
            base["kb_scope"] = ["pharmacy"]
        pool.append(base)
    return pool


def member_answer(conn, question: str, record: bool = False) -> dict:
    """Member search. Returns member wording and a plain citation, or an abstention.

    Advocate text is never returned. Units without member wording are not shown to the model.
    A question closed by an approved unit returns that unit's member wording when the
    member knowledge bases cover it.
    """
    from src.corpus import decide

    closed = _closed_gap_hit(conn, "Member", question)
    if closed is not None:
        member_text = (closed["member_text"] or "").strip()
        result = {
            "abstained": False,
            "member_text": member_text,
            "citation": f"{closed['title']}, version {closed['version']}",
            "title": closed["title"],
            "version": closed["version"],
            "unit_id": closed["unit_id"],
            "ai_source": "closed_gap",
            "ai_caption": "",
            "note": "This question was closed by an approved unit.",
            "query": question,
            "role": "Member",
        }
        if record:
            record_search(conn, "Member", question, result)
        return result
    from src.finish import explore_expired_block

    blocked = explore_expired_block(conn, question, "Member")
    if blocked is not None:
        result = {
            "abstained": True,
            "member_text": "",
            "citation": "",
            "title": "",
            "version": None,
            "unit_id": "",
            "ai_source": "expired",
            "ai_caption": "",
            "note": blocked.get("note") or "",
            "query": question,
            "role": "Member",
        }
        if record:
            record_search(conn, "Member", question, result)
        return result
    pool = member_candidate_units(conn)
    token = bind_live_conn(conn)
    try:
        decision = decide(question, "Member", pool, live=live_enabled(conn))
    finally:
        unbind_live_conn(token)
    source = decision["source"]
    caption = decision["reason"] if source == "capped" else ""
    row = live_approved(conn, decision["answer_unit_id"]) if decision.get("answer_unit_id") else None
    member_text = (row["member_text"] or "").strip() if row else ""
    if row is None or not member_text or row["unit_id"] not in _human_member_ids():
        result = {
            "abstained": True,
            "member_text": "",
            "citation": "",
            "title": "",
            "version": None,
            "unit_id": "",
            "ai_source": source,
            "ai_caption": caption,
            "note": decision["reason"],
            "query": question,
            "role": "Member",
        }
    else:
        result = {
            "abstained": False,
            "member_text": member_text,
            "citation": f"{row['title']}, version {row['version']}",
            "title": row["title"],
            "version": row["version"],
            "unit_id": row["unit_id"],
            "ai_source": source,
            "ai_caption": caption,
            "note": decision["reason"],
            "query": question,
            "role": "Member",
        }
    if record:
        record_search(conn, "Member", question, result)
    return result


def _query_lines(stored: str) -> list[str]:
    return [item.strip() for item in (stored or "").split("\n") if item.strip()]


def _live_gap_id(safe: str) -> str:
    digest = hashlib.sha256(safe.encode("utf-8")).hexdigest()[:8]
    return f"live-{digest}"


def _draft_live_gap(conn, raw_query: str, safe: str, role: str) -> bool:
    """Draft a proposed unit for one novel abstention and store it as its own cluster.

    The cluster label is the redacted question. Nearby units are ranked on the
    original question. A missing, capped, or failed draft returns False.
    """
    from src.ai import gap_user, invented_figures, replay
    from src.corpus import top_candidates

    pool = approved_search_pool(conn)
    nearby = top_candidates(raw_query, role, pool) if pool else []
    user = gap_user(safe, [{"query": safe, "role": role}], nearby)
    token = bind_live_conn(conn)
    try:
        output, source = replay("draft_gap_unit", user, live=True)
    finally:
        unbind_live_conn(token)
    if source not in {"cached", "live"} or not isinstance(output, dict):
        return False
    draft = (output.get("draft_text") or "").strip()
    if not draft:
        return False
    placeholders = []
    seen = set()
    for item in list(output.get("placeholders") or []) + bracketed_placeholders(draft):
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        placeholders.append(text)
    figures = invented_figures(draft, [safe], [unit.get("text") or "" for unit in pool])
    draft_type = output.get("type") or "faq"
    if draft_type not in {"verbatim", "policy", "procedure", "faq"}:
        draft_type = "faq"
    kb = output.get("suggested_kb") or "pharmacy"
    if kb not in {"pharmacy", "benefits", "shared-legal"}:
        kb = "pharmacy"
    gap_id = _live_gap_id(safe)
    if conn.execute("SELECT 1 FROM gaps WHERE id = ?", (gap_id,)).fetchone():
        gap_id = _live_gap_id(safe + "\n" + role)
    checklist = output.get("author_checklist") or []
    if isinstance(checklist, str):
        checklist = [checklist]
    title = (output.get("title") or "").strip() or safe
    conn.execute(
        """
        INSERT INTO gaps(
            id, cluster, query_example, search_count, roles, draft_title, draft_text,
            draft_tags, status, placeholders, checklist, queries, invented_figures,
            draft_type, reason
        ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, 'proposed', ?, ?, ?, ?, ?, ?)
        """,
        (
            gap_id,
            safe,
            safe,
            role,
            title,
            draft,
            kb,
            ", ".join(placeholders),
            "\n".join(str(item) for item in checklist),
            safe,
            ", ".join(figures),
            draft_type,
            "Drafted from a live search.",
        ),
    )
    log(
        conn,
        role,
        f"Drafted a proposed unit for '{safe}' and added cluster {gap_id} to the gap queue.",
    )
    return True


def _bump_gap(conn, query: str, role: str) -> None:
    """Count an abstained query on its cluster, or keep it in the unclustered gap.

    When Live AI is on and the question matches no cluster, draft a proposed
    unit for it. The original question is used for local ranking. Stored text
    is redacted. A missing or capped draft keeps the unclustered bucket.
    """
    safe = redact_query(query)
    lowered = safe.lower()
    rows = conn.execute("SELECT id, queries, roles FROM gaps").fetchall()
    for row in rows:
        if row["id"] == UNCLUSTERED_ID:
            continue
        if lowered in [item.lower() for item in _query_lines(row["queries"])]:
            conn.execute(
                "UPDATE gaps SET search_count = search_count + 1 WHERE id = ?",
                (row["id"],),
            )
            return
    if live_enabled(conn) and _draft_live_gap(conn, query, safe, role):
        return
    current = conn.execute("SELECT queries, roles, search_count FROM gaps WHERE id = ?", (UNCLUSTERED_ID,)).fetchone()
    if current is None:
        conn.execute(
            """
            INSERT INTO gaps(
                id, cluster, query_example, search_count, roles, draft_title, draft_text,
                draft_tags, status, placeholders, checklist, queries, invented_figures, reason
            ) VALUES (?, ?, ?, 1, ?, '', '', '', 'proposed', '', '', ?, '', '')
            """,
            (UNCLUSTERED_ID, UNCLUSTERED_LABEL, safe, role, safe),
        )
        return
    queries = _query_lines(current["queries"])
    if safe not in queries and lowered not in [item.lower() for item in queries]:
        queries.append(safe)
    roles = [item.strip() for item in (current["roles"] or "").split(",") if item.strip()]
    if role not in roles:
        roles.append(role)
    conn.execute(
        """
        UPDATE gaps
        SET search_count = search_count + 1, queries = ?, roles = ?, query_example = ?
        WHERE id = ?
        """,
        ("\n".join(queries), ", ".join(roles), queries[0] if queries else safe, UNCLUSTERED_ID),
    )


def _moment(value: str) -> datetime:
    from src.compliance import parse_timestamp

    try:
        return parse_timestamp(value)
    except ValueError:
        return datetime.min


def expired_units(conn) -> list:
    """Approved units whose review date is before today. Illustrative dates."""
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    rows = conn.execute(
        """
        SELECT * FROM units
        WHERE status = 'approved' AND search_visible = 1 AND review_by != '' AND review_by < ?
        ORDER BY review_by, unit_id
        """,
        (today,),
    ).fetchall()
    return list(rows)


def units_as_of(conn, unit_id: str, timestamp: str):
    """The version that was live at timestamp, or None.

    A date with no time means the end of that day. The returned dict has text,
    member_text, approver, and effective_date.
    """
    moment = _moment(timestamp)
    rows = conn.execute(
        """
        SELECT * FROM units
        WHERE unit_id = ? AND approved_on != ''
        ORDER BY version
        """,
        (unit_id,),
    ).fetchall()
    chosen = None
    for row in rows:
        started = _moment(row["effective_date"] or row["approved_on"])
        if started <= moment:
            chosen = row
    if chosen is None:
        return None
    return {
        "unit_id": chosen["unit_id"],
        "version": chosen["version"],
        "text": chosen["text"],
        "member_text": chosen["member_text"] or "",
        "approver": chosen["approved_by"] or "",
        "effective_date": chosen["effective_date"] or "",
        "versions_that_day": _versions_that_day(rows, moment),
        "note": "Illustrative, made-up data",
    }


def _versions_that_day(rows, moment: datetime) -> list[dict]:
    """Every version whose live interval overlaps the requested calendar day."""
    day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = moment.replace(hour=23, minute=59, second=59, microsecond=0)
    spans = []
    ordered = list(rows)
    for index, row in enumerate(ordered):
        start = _moment(row["effective_date"] or row["approved_on"])
        if index + 1 < len(ordered):
            end = _moment(ordered[index + 1]["effective_date"] or ordered[index + 1]["approved_on"])
            end_label = ordered[index + 1]["effective_date"] or ordered[index + 1]["approved_on"] or ""
        else:
            end = None
            end_label = ""
        if start <= day_end and (end is None or end >= day_start):
            spans.append({
                "version": row["version"],
                "start": row["effective_date"] or row["approved_on"] or "",
                "end": end_label,
            })
    return spans


def current_unit(conn, unit_id: str):
    return conn.execute(
        """
        SELECT * FROM units
        WHERE unit_id = ?
        ORDER BY CASE status WHEN 'approved' THEN 0 ELSE 1 END, version DESC
        LIMIT 1
        """,
        (unit_id,),
    ).fetchone()


def mark_scored(conn) -> None:
    _meta_set(conn, "scored", "1")
    conn.commit()


def step_done(conn, number: int) -> bool:
    """A story step is Done only when its own work is recorded."""
    if number == 0:
        return flag(conn, "today")
    if number == 1:
        return flag(conn, "tags_confirmed")
    if number == 2:
        return flag(conn, "escalated")
    if number == 3:
        if flag(conn, "approved"):
            return True
        if mode_name(conn) != "short":
            return False
        ids = presenter_unit_ids(conn)
        return bool(ids) and all(live_approved(conn, unit_id) for unit_id in ids)
    if number == 4:
        return flag(conn, f"asked:Pharmacy advocate:{COST_QUERY}") and flag(
            conn, f"asked:Insurance advocate:{COST_QUERY}"
        )
    if number == 5:
        return flag(conn, "revised")
    if number == 6:
        row = conn.execute("SELECT 1 FROM gaps WHERE status != 'proposed' LIMIT 1").fetchone()
        return row is not None
    if number == 7:
        return flag(conn, "drift")
    if number == 8:
        return flag(conn, "scored")
    return False


def live_approved(conn, unit_id: str):
    return conn.execute(
        """
        SELECT * FROM units
        WHERE unit_id = ? AND status = 'approved' AND search_visible = 1
        ORDER BY version DESC LIMIT 1
        """,
        (unit_id,),
    ).fetchone()


def all_units(conn):
    return conn.execute(
        "SELECT * FROM units ORDER BY source_doc, unit_id, version"
    ).fetchall()


def proposed_queue(conn):
    return conn.execute(
        """
        SELECT * FROM units
        WHERE status = 'proposed'
        ORDER BY CASE unit_id WHEN 'U-RX-MAIL-ORDER-FIRST-FILL' THEN 1 ELSE 0 END, unit_id
        """
    ).fetchall()


def document_body(conn, doc_id: str) -> str:
    row = conn.execute("SELECT body FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    return row["body"] if row else ""


def gaps(conn):
    return conn.execute("SELECT * FROM gaps ORDER BY search_count DESC").fetchall()


def score_dedup():
    from src.corpus import load_corpus

    rows = load_corpus()["variants"]
    judged = []
    tp = fp = fn = tn = 0
    for row in rows:
        label = row["label"]
        guess = row["guess"]
        ok = row["pass"]
        if label == "duplicate" and guess == "duplicate":
            tp += 1
        elif label != "duplicate" and guess == "duplicate":
            fp += 1
        elif label == "duplicate" and guess != "duplicate":
            fn += 1
        else:
            tn += 1
        judged.append(row)
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    return {
        "rows": judged,
        "precision": precision,
        "recall": recall,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def verbatim_source_count(conn):
    row = conn.execute(
        """
        SELECT
          SUM(CASE WHEN type = 'verbatim' AND version = 1 THEN 1 ELSE 0 END) AS total,
          SUM(CASE WHEN type = 'verbatim' AND version = 1 AND source_mismatch = 0 AND verbatim_altered = 0 THEN 1 ELSE 0 END) AS ok
        FROM units
        """
    ).fetchone()
    return int(row["ok"] or 0), int(row["total"] or 0)


def _is_heldout(item: dict) -> bool:
    return (item.get("heldout") or "").strip().lower() in {"yes", "y", "true", "1"}


def score_golden(conn):
    """Score the golden set. Held-out rows are returned and left out of the tile rates.

    Every world uses expected_unit. A row with no saved answer is not scored:
    it is not a pass, a miss, or an abstention. Right answers, wrong units, and
    wrong no-answers are the scored answerable rows, and those three sum to that total.
    """
    from src.corpus import legacy_target

    path = DATA / "golden_set.csv"
    questions = list(csv.DictReader(path.open()))
    results = []
    hits1 = hits3 = answerable = 0
    correct_abstain = expected_abstain = 0
    over_abstain = 0
    wrong = 0
    leaks = 0
    not_scored = 0
    token = _SCORING.set(True)
    previous_live = _meta_get(conn, "live_ai", "0")
    _meta_set(conn, "live_ai", "0")
    try:
        return _score_golden_rows(conn, questions)
    finally:
        _SCORING.reset(token)
        _meta_set(conn, "live_ai", previous_live)


def _score_golden_rows(conn, questions):
    from src.corpus import legacy_target

    results = []
    hits1 = hits3 = answerable = 0
    correct_abstain = expected_abstain = 0
    over_abstain = 0
    wrong = 0
    leaks = 0
    not_scored = 0
    for item in questions:
        heldout = _is_heldout(item)
        found = search(conn, item["role"], item["question"], record=False)
        legacy = item["expected_unit"]
        expected = "ABSTAIN" if legacy == "ABSTAIN" else legacy_target(legacy)
        missing = found.get("ai_source") == "missing"
        leaked = False
        if missing:
            got = "No saved answer"
            result = "No saved answer"
            passed = False
        else:
            got = "ABSTAIN" if found["abstained"] else found["unit"]["unit_id"]
            if not found["abstained"] and found.get("unit") is not None:
                allowed = set(ROLE_KB[item["role"]])
                unit_kbs = {part.strip() for part in found["unit"]["kb_scope"].split(",") if part.strip()}
                if not unit_kbs <= allowed:
                    leaked = True
                audience = found["unit"]["audience"] or ""
                if item["role"] == "Member" and "member" not in audience:
                    leaked = True
            passed = (got == expected if expected else False) and not leaked
            result = "Pass" if passed else "Fail"
        candidate_ids = [unit_id for _, unit_id in found["ranked"]]
        if not heldout:
            if missing:
                not_scored += 1
            elif legacy == "ABSTAIN":
                expected_abstain += 1
                if found["abstained"] and not leaked:
                    correct_abstain += 1
            else:
                answerable += 1
                if expected and got == expected and not leaked:
                    hits1 += 1
                elif found["abstained"]:
                    over_abstain += 1
                else:
                    wrong += 1
                if (
                    expected
                    and expected in candidate_ids
                    and found.get("ai_source") != "blocked"
                ):
                    hits3 += 1
            if leaked:
                leaks += 1
        results.append(
            {
                "question": item["question"],
                "role": item["role"],
                "expected": expected or legacy,
                "legacy": legacy,
                "got": got,
                "pass": passed,
                "result": result,
                "heldout": heldout,
                "reason": found["note"],
                "ai_source": found.get("ai_source", ""),
            }
        )

    def rate(part, whole):
        return part / whole if whole else 0

    verbatim_ok, verbatim_total = verbatim_source_count(conn)
    return {
        "rows": results,
        "hit_at_1": rate(hits1, answerable),
        "hit_at_3": rate(hits3, answerable),
        "hits_at_1": hits1,
        "hits_at_3": hits3,
        "wrong": wrong,
        "verbatim_ok": verbatim_ok,
        "verbatim_total": verbatim_total,
        "correct_abstain": rate(correct_abstain, expected_abstain),
        "correct_abstain_count": correct_abstain,
        "over_abstain": rate(over_abstain, answerable),
        "over_abstain_count": over_abstain,
        "leaks": leaks,
        "answerable": answerable,
        "expected_abstain": expected_abstain,
        "not_scored": not_scored,
        "not_cached": not_scored,
    }


ILLUSTRATIVE = "Illustrative, made-up data"


def next_step_for(miss: str) -> str:
    """One line the Quality screen can show under a miss."""
    text = miss or ""
    lower = text.lower()
    if "verbatim" in lower and "altered" in lower:
        return "Leave the badge visible and have a person rewrite the unit before approval."
    if "source span" in lower or "source mismatch" in lower:
        return "Leave the badge visible and have a person rewrite the unit before approval."
    if text.startswith("T2") or "variant" in lower:
        return "Keep this row in the dedup table and do not change the prompt to fit it."
    if "not cached" in lower or "no saved answer" in lower or "fixture missing" in lower:
        return "Generate a fixture for this input. Do not treat a missing cache as an abstention."
    if "abstained" in lower:
        return "Check the candidate list before changing the prompt, and leave the miss on the Quality screen."
    if "abstention" in lower or "leak" in lower:
        return "Review the unit scope before the next prompt change, and leave the miss visible."
    if text.startswith("T3") or lower.startswith("golden"):
        return "Compare the chosen unit with the expected unit and keep the miss visible."
    if "placeholder" in lower:
        return "Send the draft back so the author can fill every square-bracket fact."
    if "figure" in lower:
        return "Have the author remove the figure. The draft must not add numbers."
    if text.startswith("T5"):
        return "Keep the model judgment on screen and let Legal decide."
    if "split the website" in lower:
        return "Keep the merge as a human decision and leave the split visible."
    if "audience" in lower:
        return "Keep the human audience correction and leave the model audience visible."
    if lower.startswith("expired"):
        return "Send the unit to its owner for review before the next call. Illustrative."
    return "Keep the miss visible. Add a held-out question before changing a prompt."


def _tile(key: str, label: str, display: str, detail: str) -> dict:
    return {
        "key": key,
        "label": label,
        "display": display,
        "detail": detail,
        "note": ILLUSTRATIVE,
    }


def _golden_line(row: dict) -> dict:
    return {
        "Question": row["question"],
        "Role": row["role"],
        "Expected": row["expected"],
        "Got": row["got"],
        "Result": row["result"],
        "reason": row["reason"],
        "ai_source": row["ai_source"],
        "heldout": "yes" if row["heldout"] else "no",
    }


def _verbatim_from_t1(conn) -> dict:
    ok, total = verbatim_source_count(conn)
    if total == 0:
        from src.corpus import load_corpus

        verbatim = [unit for unit in load_corpus()["units"] if unit["type"] == "verbatim"]
        total = len(verbatim)
        ok = sum(1 for unit in verbatim if not unit["source_mismatch"] and not unit["verbatim_altered"])
    return {
        "label": "Verbatim units matching source",
        "ok": ok,
        "total": total,
        "display": f"{ok} of {total}",
        "note": "Illustrative, made-up data. Count from the T1 source check.",
    }


def extraction_boundary() -> dict:
    """Agreement between the hand labels for script v1 and the extracted units.

    The labels were written after the first model run. Illustrative.
    """
    path = DATA / "expected_units_v1.csv"
    note = "Illustrative, made-up data. Labels were written after the first model run."
    if not path.exists():
        return {"matched": 0, "missed": 0, "extra": 0, "rows": [], "note": note}
    lines = [line for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]
    expected = list(csv.DictReader(lines))
    from src.corpus import load_corpus

    extracted = [unit for unit in load_corpus()["units"] if unit.get("source_doc") == "SRC-RX-EDU-001"]
    used = set()
    matched = 0
    missed = 0
    detail = []
    for item in expected:
        span = item.get("span_text") or ""
        label = item.get("type") or ""
        hit = None
        for unit in extracted:
            if unit["unit_id"] in used:
                continue
            source = unit.get("source_span") or ""
            text = unit.get("text") or ""
            covered = span and (span in source or span in text or source in span or text in span)
            if covered and unit.get("type") == label:
                hit = unit
                break
        if hit:
            used.add(hit["unit_id"])
            matched += 1
            detail.append({"span_text": span, "type": label, "result": "matched", "unit_id": hit["unit_id"]})
        else:
            missed += 1
            detail.append({"span_text": span, "type": label, "result": "missed", "unit_id": ""})
    extra_ids = [unit["unit_id"] for unit in extracted if unit["unit_id"] not in used]
    return {
        "matched": matched,
        "missed": missed,
        "extra": len(extra_ids),
        "extra_unit_ids": extra_ids,
        "rows": detail,
        "note": note,
    }


def quality_report(conn) -> dict:
    """Tiles, golden table, dedup table, verbatim count, and every miss with a next step.

    Tile rates use the scored golden rows. Held-out rows are returned separately.
    """
    from src.corpus import load_corpus

    golden = score_golden(conn)
    dedup = score_dedup()
    scored = [_golden_line(row) for row in golden["rows"] if not row["heldout"]]
    held = [_golden_line(row) for row in golden["rows"] if row["heldout"]]
    dedup_rows = [
        {
            "variant_text": row["variant_text"],
            "label": row["label"],
            "judgment": row.get("relation") or "",
            "reason": row.get("reason") or "",
            "result": "Pass" if row["pass"] else "Fail",
        }
        for row in dedup["rows"]
    ]
    misses = []
    seen = set()

    def add_miss(text: str) -> None:
        if not text or text in seen:
            return
        seen.add(text)
        misses.append({"miss": text, "next_step": next_step_for(text)})

    for miss in load_corpus()["misses"]:
        add_miss(miss)
    for row in golden["rows"]:
        if row["result"] in ("Pass", "No saved answer"):
            continue
        if any(row["question"] in earlier for earlier in seen):
            continue
        add_miss(
            f"Golden {row['role']}: expected {row['expected']}, got {row['got']}. {row['question']}"
        )
    for row in dedup_rows:
        if row["result"] == "Pass":
            continue
        add_miss(
            f"T2 variant labeled {row['label']}, model said {row['judgment']}. Reason: {row['reason']}"
        )
    for row in expired_units(conn):
        add_miss(
            f"Expired {row['unit_id']}. Review date {row['review_by']} has passed. Illustrative."
        )

    def pct(value: float) -> str:
        return f"{value:.0%}"

    tiles = [
        _tile(
            "hit_at_1",
            "hit@1",
            pct(golden["hit_at_1"]),
            f"{golden['hits_at_1']} of {golden['answerable']}",
        ),
        _tile(
            "correct_abstain",
            "correct abstentions",
            pct(golden["correct_abstain"]),
            f"{golden['correct_abstain_count']} of {golden['expected_abstain']}",
        ),
        _tile(
            "over_abstain",
            "over-abstentions",
            pct(golden["over_abstain"]),
            f"{golden['over_abstain_count']} of {golden['answerable']}",
        ),
        _tile("leaks", "cross-role leaks", str(golden["leaks"]), f"{golden['leaks']} leaks"),
        _tile(
            "dedup_precision",
            "dedup precision",
            pct(dedup["precision"]),
            f"{dedup['tp']} of {dedup['tp'] + dedup['fp']}",
        ),
        _tile(
            "dedup_recall",
            "dedup recall",
            pct(dedup["recall"]),
            f"{dedup['tp']} of {dedup['tp'] + dedup['fn']}",
        ),
    ]
    return {
        "note": ILLUSTRATIVE,
        "tiles": tiles,
        "verbatim_source": _verbatim_from_t1(conn),
        "golden_table": {
            "columns": ["Question", "Role", "Expected", "Got", "Result"],
            "rows": scored,
            "held_out": held,
            "note": ILLUSTRATIVE,
        },
        "dedup_table": {
            "columns": ["variant text", "label", "AI judgment", "AI reason", "Result"],
            "rows": dedup_rows,
            "precision": dedup["precision"],
            "recall": dedup["recall"],
            "note": ILLUSTRATIVE,
        },
        "misses": misses,
        "scored_questions": sum(1 for row in scored if row["Result"] != "No saved answer"),
        "held_out_questions": len(held),
        "score_counts": {
            "right_first": golden["hits_at_1"],
            "wrong": golden["wrong"],
            "wrong_no_answers": golden["over_abstain_count"],
            "scored": golden["answerable"],
            "not_scored": golden["not_scored"],
        },
        "not_scored": golden["not_scored"],
        "extraction_boundary": extraction_boundary(),
    }
