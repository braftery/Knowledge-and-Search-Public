"""Back-end contract for the items left open after the pass 5 pull request.

Figures and minutes in this module are illustrative. Member sentences live on
approved units. This module classifies, scores, and records. It does not invent
a member reply that has no unit.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from api.errors import APIError

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ET = ZoneInfo("America/New_York")

QUESTION_LIMIT = 500
LIVE_TIMEOUT_SECONDS = 6
IP_LIVE_CAP = 20
EXPLORE_CANDIDATE_LIMIT = 20
GUIDED_CANDIDATE_LIMIT = 3

CHANNEL_NAMES = (
    "advocate desktop",
    "member chat",
    "website",
    "phone line",
)
CHANNEL_LIST = ", ".join(CHANNEL_NAMES[:3]) + ", and " + CHANNEL_NAMES[3]
PUBLISH_CHANNELS = (
    "Published version {version} to the advocate desktop, member chat, the website, and the phone line."
)
LEGAL_EMAIL = (
    "Legal approved a new version of {unit_id}. It is now live on the advocate desktop, "
    "member chat, the website, and the phone line."
)

REVIEW_WAIT = "This answer is past its review date and is waiting for Legal."
COSMETIC_LABEL = "Cosmetic change inside Legal wording"
SIBLING_LABEL = "A linked disclaimer may need the same change"
MEMBER_REQUIRED = "A member is required."
OPEN_ROLE = "Open that role first."

PRICE_UNIT = "U-RX-EDU-001-09"
PRICE_ANY = "U-RX-EDU-PRICE-ANY"
SPECIALTY = "U-RX-EDU-001-13"

IVR_GREETING = "U-IVR-GREETING-001"
IVR_ANYTHING = "U-IVR-ANYTHING-001"
IVR_NO_ANSWER = "U-IVR-NOANSWER-001"
IVR_VERIFIED = "U-IVR-VERIFIED-001"

TPL_PRICE = "U-TPL-PRICE-001"
TPL_VISIT = "U-TPL-VISIT-001"
TPL_REFERRAL_NOTE = "U-TPL-REFERRAL-NOTE-001"
TPL_OOP = "U-TPL-OOP-001"
COST_HELP = "U-BEN-COST-HELP-001"
CALLBACK = "U-IVR-CALLBACK-001"
GRIEVANCE = "U-BEN-GRIEVANCE-001"
OON_NEXT = "U-BEN-OON-NEXT-001"
CALLER_CONFIRM = "U-BEN-CALLER-CONFIRM-001"
GLOSSARY_IDS = {
    "tier": "U-GLOSS-TIER-001",
    "coverage_stage": "U-GLOSS-STAGE-001",
    "deductible": "U-GLOSS-DEDUCT-001",
    "preferred_pharmacy": "U-GLOSS-PREF-001",
    "mail_order": "U-GLOSS-MAIL-001",
    "oop_max": "U-GLOSS-OOP-001",
}
SITE_MAIL = "U-SITE-MAIL-001"
SITE_FIND = "U-SITE-FIND-001"
SITE_HELP = "U-SITE-HELP-001"
OVER_ESTIMATE = "U-RX-OVER-ESTIMATE-001"
OVER_SUPPLY = "U-RX-OVER-SUPPLY-001"
OVER_DEDUCT = "U-RX-OVER-DEDUCT-001"
OVER_LIST = "U-RX-OVER-LIST-001"

# Illustrative minutes. Not measured from a real review.
TIER_MINUTES = {"high": 20, "medium": 10, "low": 5}

PRODUCT_ROLES = (
    "Knowledge Ops author",
    "Legal approver",
    "Pharmacy advocate",
    "Insurance advocate",
    "Member",
    "Knowledge owner",
    "Channel and AI team",
)
_ROLE_ALIAS = {
    "knowledge ops author": "Knowledge Ops author",
    "legal approver": "Legal approver",
    "legal / compliance approver": "Legal approver",
    "legal compliance approver": "Legal approver",
    "pharmacy advocate": "Pharmacy advocate",
    "insurance advocate": "Insurance advocate",
    "member": "Member",
    "member chat": "Member",
    "knowledge owner": "Knowledge owner",
    "channel and ai team": "Channel and AI team",
}

ANSWER_STATUS = {
    "answer": "answer",
    "topic": "answer",
    "definition": "answer",
    "claims": "answer",
    "abstain": "abstain",
    "clarify": "clarify",
    "authenticate": "clarify",
    "out_of_scope": "out_of_scope",
    "price": "price",
    "price_compare": "price",
    "drug_total": "price",
    "visit_cost": "visit_cost",
    "plan_figure": "plan_figure",
    "safety": "safety",
    "handoff": "handoff",
    "handoff_offer": "handoff",
    "cost_help": "handoff",
    "callback": "handoff",
    "grievance": "handoff",
    "cache_miss": "cache_miss",
    "transfer": "handoff",
}

ALLOWED_CHANNELS = ("advocate_guidance", "member_chat", "voice_bot", "website")

_SNAPSHOT = {"path": ""}


def problem_body(message: str, status: int, allowed: list | None = None) -> dict:
    titles = {400: "Bad Request", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}
    body = {
        "type": "about:blank",
        "title": titles.get(status, "Error"),
        "status": status,
        "detail": message,
        "error": message,
    }
    if allowed:
        body["allowed"] = list(allowed)
    return body


def canonical_role(value: str, *, required: bool = True) -> str:
    text = (value or "").strip()
    if not text:
        if required:
            raise APIError("Unknown role.", 400, allowed=list(PRODUCT_ROLES))
        return ""
    found = _ROLE_ALIAS.get(text.lower())
    if found is None:
        raise APIError("Unknown role.", 400, allowed=list(PRODUCT_ROLES))
    return found


def roles_match(left: str, right: str) -> bool:
    if not (left or "").strip() or not (right or "").strip():
        return False
    return canonical_role(left) == canonical_role(right)


def session_explore_role(session) -> str:
    stored = (session.meta().get("explore_role") or "").strip()
    if not stored:
        raise APIError(OPEN_ROLE, 403)
    return canonical_role(stored)


def resolve_explore_role(session, supplied: str | None) -> str:
    """Explore uses the role recorded by open. A different role is refused."""
    current = session_explore_role(session)
    given = (supplied or "").strip()
    if given and not roles_match(given, current):
        raise APIError(OPEN_ROLE, 403)
    return current


def require_actor(session, world: str, allowed: tuple[str, ...], supplied: str = "") -> str:
    """Guided records the presenter role. Explore must already be that role."""
    allowed_now = tuple(canonical_role(item) for item in allowed)
    from src.engine import _ACTOR, _RESOURCE

    _ACTOR.set(allowed_now[0] if world != "explore" else "")
    if world != "explore":
        role = allowed_now[0]
        _ACTOR.set(role)
        _record_guided_actor(session, role)
        return role
    _RESOURCE.set(_RESOURCE.get() or allowed_now[0])
    current = session_explore_role(session)
    if current not in allowed_now:
        raise APIError(f"Only the {allowed_now[0]} can do this.", 403)
    if (supplied or "").strip() and not roles_match(supplied, current):
        raise APIError(OPEN_ROLE, 403)
    _ACTOR.set(current)
    return current


def _record_guided_actor(session, role: str) -> None:
    from src.engine import now_iso

    meta = session.meta()
    actors = list(meta.get("guided_actors") or [])
    actors.append({"role": role, "at": now_iso()})
    meta["guided_actors"] = actors[-40:]
    session.save_meta(meta)


def normalize_cache_key(text: str) -> str:
    value = (text or "").lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def check_question_length(question: str) -> str:
    text = question or ""
    if len(text) > QUESTION_LIMIT:
        raise APIError(f"A question can be at most {QUESTION_LIMIT} characters.", 400)
    return text.strip()


def client_ip() -> str:
    from src.engine import _CLIENT_IP

    return (_CLIENT_IP.get() or "").strip()


def ip_calls_left() -> int:
    address = client_ip()
    if not address or address == "testclient":
        return IP_LIVE_CAP
    from src.engine import _day_cap

    _path, data = _day_cap()
    used = int((data.get("ips") or {}).get(address) or 0)
    return max(0, IP_LIVE_CAP - used)


def note_ip_call() -> None:
    address = client_ip()
    if not address or address == "testclient":
        return
    from src.engine import _cap_file, _day_cap

    path, data = _day_cap()
    ips = dict(data.get("ips") or {})
    ips[address] = int(ips.get(address) or 0) + 1
    data["ips"] = ips
    path = _cap_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def wilson_interval(successes: int, total: int, z: float = 1.96) -> dict:
    """Wilson score interval at 95 percent. Illustrative when the counts are demo counts."""
    if total <= 0:
        return {
            "low": None,
            "high": None,
            "confidence": 0.95,
            "measured": False,
            "illustrative": True,
        }
    part = successes / total
    denom = 1 + z * z / total
    center = (part + z * z / (2 * total)) / denom
    margin = z * math.sqrt((part * (1 - part) / total) + (z * z / (4 * total * total))) / denom
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return {
        "low": round(low, 4),
        "high": round(high, 4),
        "confidence": 0.95,
        "measured": True,
        "illustrative": True,
    }


def decorate_quality(conn, report: dict, explore: bool = False) -> dict:
    """Add a Wilson interval to each rate. Zero answers are not measured."""
    scored = int((report.get("score_counts") or {}).get("scored") or 0)
    tiles = []
    for tile in report.get("tiles") or []:
        item = dict(tile)
        match = re.search(r"(\d+) of (\d+)", item.get("detail") or "")
        if match:
            item["wilson"] = wilson_interval(int(match.group(1)), int(match.group(2)))
        elif item.get("key") == "leaks" and scored <= 0:
            item["display"] = "not measured"
            item["detail"] = "not measured"
            item["wilson"] = wilson_interval(0, 0)
        else:
            item["wilson"] = wilson_interval(0, max(scored, 0))
        tiles.append(item)
    updated = dict(report)
    updated["tiles"] = tiles
    updated["illustrative"] = True
    if explore:
        updated["slices"] = robustness_slices(conn)
    return updated


def answer_status(kind: str, *, abstained: bool = False, ai_source: str = "") -> str:
    if ai_source == "missing":
        return "cache_miss"
    if ai_source == "timeout":
        return "abstain"
    mapped = ANSWER_STATUS.get(kind or "")
    if mapped:
        return mapped
    if abstained:
        return "abstain"
    return "answer"


def citation_from_unit(unit: dict) -> dict:
    return {
        "unit_id": unit.get("unit_id") or "",
        "version": unit.get("version"),
        "title": unit.get("title") or "",
        "approved_by": unit.get("approved_by") or unit.get("approver_name") or "",
        "approved_on": unit.get("approved_on") or "",
    }


def attach_answer_fields(body: dict) -> dict:
    """Set answer_status and structured citations. Citation text stays out of the reply."""
    kind = body.get("kind") or ""
    source = body.get("ai_source") or ""
    status = answer_status(kind, abstained=bool(body.get("abstained")), ai_source=source)
    if body.get("transfer"):
        status = "handoff"
    body["answer_status"] = status
    if not body.get("status") or body.get("status") in {"", "answer", "abstain"}:
        if body.get("status") not in {"blocked_conflict", "transfer"}:
            body["status"] = status
    cites = []
    for unit in body.get("units") or []:
        if isinstance(unit, dict) and unit.get("unit_id"):
            cites.append(citation_from_unit(unit))
    one = body.get("unit")
    if isinstance(one, dict) and one.get("unit_id"):
        item = citation_from_unit(one)
        if item not in cites:
            cites.insert(0, item)
    if cites:
        body["citations"] = cites
    for key in ("reply", "text"):
        value = body.get(key)
        if isinstance(value, str) and " Source: Harbor Health" in value:
            body[key] = value.split(" Source: Harbor Health")[0].strip()
    return body


def ensure_schema(conn) -> None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'units'"
    ).fetchone()
    if row is None:
        return
    unit_cols = {item[1] for item in conn.execute("PRAGMA table_info(units)")}
    if "edited_by_legal" not in unit_cols:
        conn.execute("ALTER TABLE units ADD COLUMN edited_by_legal INTEGER DEFAULT 0")
    if "sibling_of" not in unit_cols:
        conn.execute("ALTER TABLE units ADD COLUMN sibling_of TEXT DEFAULT ''")
    event_cols = {item[1] for item in conn.execute("PRAGMA table_info(change_events)")}
    if "event_id" not in event_cols:
        conn.execute("ALTER TABLE change_events ADD COLUMN event_id TEXT DEFAULT ''")
    if "occurred_at" not in event_cols:
        conn.execute("ALTER TABLE change_events ADD COLUMN occurred_at TEXT DEFAULT ''")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS webhook_subs (
            id TEXT PRIMARY KEY,
            url TEXT,
            events TEXT,
            secret TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS webhook_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sub_id TEXT,
            event_id TEXT,
            signature TEXT,
            attempts INTEGER,
            body TEXT,
            recorded_at TEXT
        );
        CREATE TABLE IF NOT EXISTS authorized_callers (
            id TEXT PRIMARY KEY,
            member_id TEXT,
            caller_name TEXT,
            relationship TEXT,
            status TEXT,
            confirmation TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS unit_tag_edits (
            unit_id TEXT PRIMARY KEY,
            audience TEXT,
            domain TEXT,
            tags TEXT,
            actor TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS link_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id TEXT,
            sibling_id TEXT,
            label TEXT,
            status TEXT,
            stays_live INTEGER,
            created_at TEXT
        );
        """
    )
    from src.sandbox import ensure_sandbox_schema

    ensure_sandbox_schema(conn)
    conn.commit()


def new_event_id() -> str:
    return uuid.uuid4().hex


def record_webhook_deliveries(conn, event_id: str, event: str, payload: dict) -> None:
    rows = conn.execute("SELECT id, url, events, secret FROM webhook_subs").fetchall()
    if not rows:
        return
    from src.engine import now_iso

    body = json.dumps(payload, sort_keys=True)
    when = now_iso()
    for row in rows:
        names = [part.strip() for part in (row["events"] or "").split(",") if part.strip()]
        if names and event not in names and "*" not in names:
            continue
        secret = row["secret"] or ""
        signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        conn.execute(
            """
            INSERT INTO webhook_deliveries (sub_id, event_id, signature, attempts, body, recorded_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (row["id"], event_id, signature, body, when),
        )


def register_webhook(conn, url: str, events: list[str]) -> dict:
    url = (url or "").strip()
    if not url.startswith("https://") and not url.startswith("http://"):
        raise APIError("A webhook url must start with http:// or https://.")
    names = [str(item).strip() for item in (events or []) if str(item).strip()]
    if not names:
        raise APIError("Name at least one event.")
    from src.engine import now_iso

    sub_id = uuid.uuid4().hex
    secret = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO webhook_subs (id, url, events, secret, created_at) VALUES (?, ?, ?, ?, ?)",
        (sub_id, url, ", ".join(names), secret, now_iso()),
    )
    conn.commit()
    return {
        "id": sub_id,
        "url": url,
        "events": names,
        "secret": secret,
        "illustrative": True,
        "note": "Deliveries are recorded in this session. They are not sent.",
    }


def link_price_siblings(conn) -> None:
    conn.execute(
        "UPDATE units SET sibling_of = ? WHERE unit_id = ? AND (sibling_of IS NULL OR sibling_of = '')",
        (PRICE_UNIT, PRICE_ANY),
    )
    conn.execute(
        "UPDATE units SET sibling_of = ? WHERE unit_id = ? AND (sibling_of IS NULL OR sibling_of = '')",
        (PRICE_ANY, PRICE_UNIT),
    )


def sibling_id(conn, unit_id: str) -> str:
    """Linked unit, from the newest version that still records one.

    A later version can be inserted before sibling_of is copied. That newest
    row is blank, while an earlier version still names the sibling.
    """
    row = conn.execute(
        """
        SELECT sibling_of FROM units
        WHERE unit_id = ?
          AND sibling_of IS NOT NULL
          AND TRIM(sibling_of) != ''
        ORDER BY version DESC
        LIMIT 1
        """,
        (unit_id,),
    ).fetchone()
    if row is None:
        return ""
    return (row["sibling_of"] or "").strip()


def copy_sibling_of(conn, unit_id: str, version: int) -> None:
    """Write the linked sibling onto a version that was inserted without it."""
    sibling = sibling_id(conn, unit_id)
    if not sibling:
        return
    conn.execute(
        """
        UPDATE units
        SET sibling_of = ?
        WHERE unit_id = ? AND version = ?
          AND (sibling_of IS NULL OR TRIM(sibling_of) = '')
        """,
        (sibling, unit_id, version),
    )


def list_link_reviews(conn) -> dict:
    """Reviews that are still waiting for Legal."""
    rows = conn.execute(
        """
        SELECT unit_id, sibling_id, label, created_at
        FROM link_reviews
        WHERE status = 'sent'
        ORDER BY id
        """
    ).fetchall()
    return {
        "reviews": [
            {
                "unit_id": row["unit_id"] or "",
                "sibling_id": row["sibling_id"] or "",
                "label": row["label"] or "",
                "created_at": row["created_at"] or "",
            }
            for row in rows
        ],
        "illustrative": True,
    }


def open_sibling_review(conn, published_id: str) -> None:
    other = sibling_id(conn, published_id)
    if not other:
        return
    from src.engine import now_et

    existing = conn.execute(
        """
        SELECT 1 FROM link_reviews
        WHERE unit_id = ? AND sibling_id = ? AND status = 'sent'
        """,
        (other, published_id),
    ).fetchone()
    if existing is not None:
        return
    conn.execute(
        """
        INSERT INTO link_reviews (unit_id, sibling_id, label, status, stays_live, created_at)
        VALUES (?, ?, ?, 'sent', 1, ?)
        """,
        (other, published_id, SIBLING_LABEL, now_et()),
    )


def past_review(row) -> bool:
    extension = ""
    review = ""
    try:
        extension = row["review_extension"] or ""
    except (KeyError, IndexError):
        extension = ""
    try:
        review = row["review_by"] or ""
    except (KeyError, IndexError):
        review = ""
    if str(extension).strip():
        return False
    if not str(review).strip():
        return False
    today = datetime.now(ET).strftime("%Y-%m-%d")
    return str(review) < today


def explore_expired_block(conn, query: str, role: str) -> dict | None:
    """In explore, a past-review unit with no extension leaves search."""
    from src.engine import _score_unit, mode_name

    if mode_name(conn) != "explore":
        return None
    rows = conn.execute(
        """
        SELECT * FROM units
        WHERE status = 'approved' AND review_by != '' AND (review_extension IS NULL OR review_extension = '')
        """
    ).fetchall()
    best = None
    best_score = 0.0
    for row in rows:
        if not past_review(row):
            continue
        score, _weight, _overlap, _notes = _score_unit(
            query,
            row["title"] or "",
            row["tags"] or "",
            row["text"] or "",
            row["domain"] or "",
            row["type"] or "",
        )
        if score > best_score:
            best_score = score
            best = row
    if best is None or best_score < 0.34:
        return None
    from src.engine import approved_search_pool

    pool_best = 0.0
    for unit in approved_search_pool(conn):
        score, _weight, _overlap, _notes = _score_unit(
            query,
            unit.get("title") or "",
            ", ".join(unit.get("tags") or []),
            unit.get("text") or "",
            unit.get("domain") or "",
            unit.get("type") or "",
        )
        pool_best = max(pool_best, score)
    if best_score < pool_best:
        return None
    _queue_expired(conn, best)
    return {
        "abstained": True,
        "unit": None,
        "ranked": [],
        "searched": [],
        "note": REVIEW_WAIT,
        "ai_source": "expired",
        "ai_caption": "",
        "status": "abstain",
        "answer_status": "abstain",
        "blocked_note": "",
        "fallback_unit": None,
        "query": query,
        "role": role,
        "expired_unit_id": best["unit_id"],
    }


def _queue_expired(conn, row) -> None:
    from src.engine import now_et

    found = conn.execute(
        "SELECT 1 FROM link_reviews WHERE unit_id = ? AND label = ? AND status = 'sent'",
        (row["unit_id"], "Review date passed"),
    ).fetchone()
    if found is not None:
        return
    conn.execute(
        """
        INSERT INTO link_reviews (unit_id, sibling_id, label, status, stays_live, created_at)
        VALUES (?, '', 'Review date passed', 'sent', 0, ?)
        """,
        (row["unit_id"], now_et()),
    )
    conn.commit()


def extend_review(conn, unit_id: str, reason: str, review_by: str, actor: str) -> str:
    reason = (reason or "").strip()
    review_by = (review_by or "").strip()
    if not reason:
        raise APIError("A reason is required.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", review_by):
        raise APIError("The new review date must look like 2027-06-01.")
    row = conn.execute(
        "SELECT unit_id, version FROM units WHERE unit_id = ? AND status = 'approved' ORDER BY version DESC LIMIT 1",
        (unit_id,),
    ).fetchone()
    if row is None:
        raise APIError(f"No approved unit {unit_id}.", 404)
    note = f"Extended through {review_by} by {actor}. {reason} Illustrative."
    conn.execute(
        """
        UPDATE units
        SET review_extension = ?, review_by = ?
        WHERE unit_id = ? AND status = 'approved'
        """,
        (note, review_by, unit_id),
    )
    conn.execute(
        "UPDATE link_reviews SET status = 'extended' WHERE unit_id = ? AND status = 'sent'",
        (unit_id,),
    )
    from src.engine import log

    log(conn, actor, f"Extended the review of {unit_id} through {review_by}. {reason}")
    conn.commit()
    return note


def retire_unit(conn, unit_id: str, reason: str, actor: str) -> str:
    reason = (reason or "").strip()
    if not reason:
        raise APIError("A reason is required.")
    row = conn.execute(
        "SELECT version FROM units WHERE unit_id = ? AND status = 'approved' ORDER BY version DESC LIMIT 1",
        (unit_id,),
    ).fetchone()
    if row is None:
        raise APIError(f"No approved unit {unit_id}.", 404)
    conn.execute(
        """
        UPDATE units
        SET status = 'retired', search_visible = 0
        WHERE unit_id = ? AND status = 'approved'
        """,
        (unit_id,),
    )
    conn.execute(
        "UPDATE link_reviews SET status = 'retired' WHERE unit_id = ? AND status = 'sent'",
        (unit_id,),
    )
    from src.engine import append_event, log

    append_event(conn, "unit.retired", unit_id, int(row["version"]), int(row["version"]), actor, reason)
    log(conn, actor, f"Retired {unit_id}. {reason}")
    conn.commit()
    return f"Retired {unit_id}."


def accept_link_review(conn, review_id: int | None, actor: str) -> str:
    if review_id is None:
        row = conn.execute(
            "SELECT * FROM link_reviews WHERE status = 'sent' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM link_reviews WHERE id = ?", (review_id,)).fetchone()
    if row is None or row["status"] != "sent":
        return ""
    conn.execute("UPDATE link_reviews SET status = 'accepted' WHERE id = ?", (row["id"],))
    from src.engine import log

    log(conn, actor, f"{row['label']} for {row['unit_id']}. Legal accepted it with no wording change. Both versions stay as approved.")
    conn.commit()
    return row["label"]


def tag_edit_changes_pool(conn, unit_id: str, audience: str) -> bool:
    """True when the new audience would add or drop the unit from a guided role pool."""
    from src.corpus import load_corpus
    from src.engine import ROLE_KB

    corpus = {unit["unit_id"]: unit for unit in load_corpus()["units"]}
    unit = corpus.get(unit_id)
    if unit is None:
        return False
    current = set(unit.get("audience_list") or [])
    from src.ai import with_audience_override

    current_unit = with_audience_override(dict(unit))
    current = set(current_unit.get("audience_list") or current)
    proposed = {part.strip() for part in (audience or "").replace(";", ",").split(",") if part.strip()}
    if not proposed or proposed == current:
        return False

    def visible(audiences: set[str], role: str) -> bool:
        if role != "Member":
            return True
        return "member" in audiences or bool((unit.get("member_text") or "").strip())

    for role in ROLE_KB:
        if not ROLE_KB[role]:
            continue
        scope = set(unit.get("kb_scope") or [])
        if not scope & set(ROLE_KB[role]):
            continue
        if visible(current, role) != visible(proposed, role):
            return True
    return False


def save_tag_edit(conn, unit_id: str, audience: str, domain: str, tags: str, actor: str, world: str) -> None:
    row = conn.execute(
        "SELECT unit_id, audience, tags_confirmed FROM units WHERE unit_id = ? ORDER BY version DESC LIMIT 1",
        (unit_id,),
    ).fetchone()
    if row is None:
        raise APIError(f"No unit {unit_id}.", 404)
    if world != "explore" and tag_edit_changes_pool(conn, unit_id, audience):
        raise APIError(
            "That audience change would change who can see this unit in the guided search pool. "
            "The explore sandbox can record it."
        )
    from src.engine import log, now_et

    conn.execute(
        """
        INSERT INTO unit_tag_edits (unit_id, audience, domain, tags, actor, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(unit_id) DO UPDATE SET
            audience = excluded.audience,
            domain = excluded.domain,
            tags = excluded.tags,
            actor = excluded.actor,
            created_at = excluded.created_at
        """,
        (unit_id, audience, domain, tags, actor, now_et()),
    )
    if world == "explore":
        conn.execute(
            """
            UPDATE units
            SET audience = ?, domain = CASE WHEN ? != '' THEN ? ELSE domain END,
                tags = CASE WHEN ? != '' THEN ? ELSE tags END,
                tags_confirmed = 1
            WHERE unit_id = ?
            """,
            (audience, domain, domain, tags, tags, unit_id),
        )
    else:
        conn.execute(
            "UPDATE units SET tags_confirmed = 1 WHERE unit_id = ?",
            (unit_id,),
        )
    log(conn, actor, f"Recorded tags for {unit_id}. Audience {audience or 'unchanged'}.")
    remaining = conn.execute(
        """
        SELECT COUNT(*) AS n FROM units
        WHERE version = 1 AND origin != 'plan-data' AND tags_confirmed = 0
        """
    ).fetchone()
    if remaining is not None and int(remaining["n"] or 0) == 0:
        from src.engine import _meta_set

        _meta_set(conn, "tags_confirmed", "1")
    conn.commit()


def workload(conn) -> dict:
    from src.compliance import mentions_expanded_cost
    from src.engine import _mentions_cost, waiting_units

    by_type = {"verbatim": 0, "policy": 0, "cost": 0, "other": 0}
    by_tier = {"high": 0, "medium": 0, "low": 0}
    rows = list(waiting_units(conn))
    for row in rows:
        kind = row["type"] or "other"
        text = f"{row['text'] or ''} {row['member_text'] or ''}"
        cost = _mentions_cost(text, "") or mentions_expanded_cost(text)
        if kind == "verbatim":
            by_type["verbatim"] += 1
            tier = "high"
        elif cost:
            by_type["cost"] += 1
            tier = "high"
        elif kind == "policy":
            by_type["policy"] += 1
            tier = "medium"
        else:
            by_type["other"] += 1
            tier = "low"
        by_tier[tier] += 1
    minutes = sum(by_tier[tier] * TIER_MINUTES[tier] for tier in by_tier)
    return {
        "illustrative": True,
        "note": "Illustrative, made-up data. Minutes are assumptions, not a measured review.",
        "by_type": by_type,
        "by_risk_tier": by_tier,
        "minutes_per_tier": dict(TIER_MINUTES),
        "estimated_minutes": minutes,
        "total_hours": round(minutes / 60, 2),
        "queue_count": len(rows),
        "assumptions": (
            "Illustrative: 20 minutes for a high-risk unit, 10 for a medium-risk unit, "
            "and 5 for a low-risk unit."
        ),
        "proposed_tiering": {
            "legal": "Only verbatim, cost, and clinical units need Legal.",
            "knowledge_ops_batch": "Low-risk units go to Knowledge Ops batch review.",
            "illustrative": True,
        },
    }


def mentions_cost_text(text: str) -> bool:
    from src.compliance import mentions_expanded_cost
    from src.engine import _mentions_cost

    return _mentions_cost(text, "") or mentions_expanded_cost(text)


def expand_explore_query(query: str) -> str:
    """Spelling layer and brand names for the explore first stage only."""
    brands = {
        "eliquis": "apixaban",
        "lipitor": "atorvastatin",
        "glucophage": "metformin",
        "atorvastin": "atorvastatin",
        "metforman": "metformin",
    }
    tokens = (query or "").split()
    extra = []
    for token in tokens:
        key = re.sub(r"[^a-z0-9]", "", token.lower())
        mapped = brands.get(key)
        if mapped and mapped not in query.lower():
            extra.append(mapped)
    if not extra:
        return query
    return f"{query} {' '.join(extra)}"


def candidate_limit(conn) -> int:
    from src.engine import mode_name

    if mode_name(conn) == "explore":
        return EXPLORE_CANDIDATE_LIMIT
    return GUIDED_CANDIDATE_LIMIT


def cross_kb_transfer(conn, role: str, query: str) -> dict | None:
    """Send a question that belongs in the other advocate queue.

    The answer stays an abstention. The desktop can offer the transfer.
    """
    del conn
    if role not in {"Pharmacy advocate", "Insurance advocate"}:
        return None
    text = (query or "").lower()
    referral = any(word in text for word in ("referral", "cardiologist", "specialist"))
    pharmacy = any(word in text for word in ("drug", "pharmacy", "mail order", "copay", "formulary"))
    if role == "Pharmacy advocate" and not referral:
        return None
    if role == "Insurance advocate" and not pharmacy:
        return None
    if role == "Insurance advocate" and referral and not pharmacy:
        return None
    queue = "Insurance queue" if role == "Pharmacy advocate" else "Pharmacy queue"
    other_role = "Insurance advocate" if role == "Pharmacy advocate" else "Pharmacy advocate"
    return {
        "queue": queue,
        "reason": f"This question belongs to the {queue}. This role cannot read that knowledge base.",
        "transfer_to": other_role,
    }


def guided_snapshot_path() -> str:
    if _SNAPSHOT["path"] and Path(_SNAPSHOT["path"]).exists():
        return _SNAPSHOT["path"]
    path = Path("/tmp/harbor-guided-snapshot-9813.sqlite")
    if path.exists():
        path.unlink()
    _build_guided_snapshot(str(path))
    _SNAPSHOT["path"] = str(path)
    return str(path)


def _build_guided_snapshot(path: str) -> None:
    """The full guided path the saved answers were recorded against.

    Step 8 reads this snapshot, so the numbers do not depend on which steps
    the current session has clicked.
    """
    from src.demo_paths import _drift, _mail_order_reason, _publish
    from src.engine import (
        apply_website_merge,
        approve_by_author,
        approve_remaining,
        author_queue,
        build_database,
        confirm_tags,
        connect,
        escalate_conflict,
        extract_units,
        gaps,
        keep_canonical,
        mark_today,
        write_gap,
    )

    build_database(path, "start")
    conn = connect(path)
    mark_today(conn)
    extract_units(conn)
    confirm_tags(conn)
    apply_website_merge(conn)
    keep_canonical(conn)
    escalate_conflict(conn)
    for row in list(author_queue(conn)):
        approve_by_author(conn, row["unit_id"])
    approve_remaining(conn)
    resolve = _mail_order_reason()
    from src.engine import resolve_conflict

    resolve_conflict(conn, resolve)
    _publish(conn)
    rows = list(gaps(conn))
    if rows:
        write_gap(conn, rows[0]["id"])
    _drift(conn)
    conn.close()


def guided_score_connection():
    from src.engine import connect

    return connect(guided_snapshot_path())


def robustness_slices(conn) -> dict:
    """Explore-only extra questions. They do not enter the guided golden counts."""
    from src.engine import search

    rows = [
        {"slice": "role", "role": "Pharmacy advocate", "question": "what do I say before I quote a cost", "intent": "price"},
        {"slice": "role", "role": "Insurance advocate", "question": "what do I say before I quote a cost", "intent": "cost"},
        {"slice": "intent", "role": "Pharmacy advocate", "question": "can my specialty drug come by mail", "intent": "specialty"},
        {"slice": "robustness", "role": "Pharmacy advocate", "question": "what do I say before I qote a cost", "intent": "misspelling"},
        {"slice": "robustness", "role": "Member", "question": "is Lipitor covered", "intent": "brand"},
        {"slice": "robustness", "role": "Member", "question": "necesito una referencia para un cardiologo", "intent": "spanish"},
    ]
    grouped: dict[str, list] = {"role": [], "intent": [], "robustness": []}
    for item in rows:
        found = search(conn, item["role"], item["question"], record=False)
        unit = found.get("unit")
        if found.get("abstained") or unit is None:
            got = "ABSTAIN"
        else:
            got = unit["unit_id"]
        grouped[item["slice"]].append({
            "question": item["question"],
            "role": item["role"],
            "intent": item["intent"],
            "got": got,
            "ai_source": found.get("ai_source") or "",
            "illustrative": True,
        })
    return {
        "illustrative": True,
        "note": "Illustrative slices for the explore sandbox. Guided step 8 does not use them.",
        "by_role": grouped["role"],
        "by_intent": grouped["intent"],
        "robustness": grouped["robustness"],
    }


def confirmation_number(member_id: str) -> str:
    digest = hashlib.sha256(f"{member_id}:{uuid.uuid4().hex}".encode()).hexdigest()[:8].upper()
    return f"AC-{digest}"


def store_authorized_caller(conn, member_id: str, caller_name: str, relationship: str) -> dict:
    from src.engine import log, now_et, redact_query
    from src.member_data import find_member

    member_id = (member_id or "").strip()
    caller_name = (caller_name or "").strip()
    relationship = (relationship or "").strip()
    if find_member(member_id) is None:
        raise APIError(f"No member {member_id}.", 404)
    if not caller_name or not relationship:
        raise APIError("A caller name and a relationship are required.")
    confirmation = confirmation_number(member_id)
    safe_name = redact_query(caller_name)
    conn.execute(
        """
        INSERT INTO authorized_callers (id, member_id, caller_name, relationship, status, confirmation, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """,
        (uuid.uuid4().hex, member_id, safe_name, relationship, confirmation, now_et()),
    )
    log(conn, "Member", f"Asked to add an authorized caller. Confirmation {confirmation}. Name {safe_name}.")
    conn.commit()
    return {
        "ok": True,
        "status": "pending",
        "confirmation": confirmation,
        "member_id": member_id,
        "relationship": relationship,
        "illustrative": True,
        "note": "Illustrative, made-up data",
    }


def authorized_contacts(conn, member_id: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT created_at, relationship, status, confirmation
        FROM authorized_callers
        WHERE member_id = ?
        ORDER BY created_at DESC
        """,
        (member_id,),
    ).fetchall()
    return [
        {
            "date": (row["created_at"] or "")[:10],
            "channel": "Chat",
            "summary": "Asked to add an authorized caller",
            "status": row["status"],
            "confirmation": row["confirmation"],
            "relationship": row["relationship"],
        }
        for row in rows
    ]


SUPPORT_UNITS = [
    (
        IVR_GREETING,
        "Phone line greeting",
        "Thank you for calling Harbor Health. In a few words, tell me what you are calling about.",
        "voice_bot",
    ),
    (
        IVR_ANYTHING,
        "Phone line anything else",
        "Is there anything else? Press 0 to talk to a member advocate.",
        "voice_bot",
    ),
    (
        IVR_NO_ANSWER,
        "Phone line no answer",
        "I don't have an approved answer for that yet.",
        "voice_bot",
    ),
    (
        IVR_VERIFIED,
        "Phone line verified",
        "You are verified for this call.",
        "voice_bot",
    ),
    (
        TPL_PRICE,
        "Drug price line",
        "{drug} {strength}, {days}-day supply {place}: {amount}.",
        "member_chat, voice_bot, website",
    ),
    (
        TPL_VISIT,
        "Visit cost line",
        "{article} {visit} {network}: {amount}.",
        "member_chat, voice_bot, website",
    ),
    (
        TPL_REFERRAL_NOTE,
        "Referral next step",
        "You need a referral from your primary care doctor first.",
        "member_chat, voice_bot, website, advocate_guidance",
    ),
    (
        TPL_OOP,
        "Out-of-pocket figure line",
        "Your out-of-pocket maximum is {limit}. You have spent {spent}.",
        "member_chat, voice_bot, website",
    ),
    (
        COST_HELP,
        "Cost help programs",
        "I am sorry this is hard. Harbor has programs that may lower what you pay for medicine. A member advocate can go through them with you. These programs are illustrative.",
        "member_chat, voice_bot, website",
    ),
    (
        CALLBACK,
        "Callback request",
        "We can call you back. Illustrative hours are 8 AM to 8 PM, seven days a week. A member advocate will return the call.",
        "member_chat, voice_bot",
    ),
    (
        GRIEVANCE,
        "Grievance or appeal",
        "You can file a grievance or an appeal. A member advocate will explain the steps and the timing. This path is illustrative.",
        "member_chat, voice_bot, website",
    ),
    (
        OON_NEXT,
        "Out-of-network specialist next step",
        "Ask your primary care doctor for an in-network referral.",
        "member_chat, voice_bot, website, advocate_guidance",
    ),
    (
        CALLER_CONFIRM,
        "Authorized caller confirmation",
        "We recorded your request to add an authorized caller. Dana needs to sign before that person can ask about the plan. A member advocate will follow up within two business days. These times are illustrative. Until Dana signs, the caller cannot hear drug names or prices.",
        "member_chat, voice_bot, website",
    ),
    (
        GLOSSARY_IDS["tier"],
        "Definition of tier",
        "A tier is a group of drugs. A lower tier usually costs less.",
        "member_chat, website",
    ),
    (
        GLOSSARY_IDS["coverage_stage"],
        "Definition of coverage stage",
        "Your coverage stage is the part of the year your drug plan is in. It can change what you pay.",
        "member_chat, website",
    ),
    (
        GLOSSARY_IDS["deductible"],
        "Definition of deductible",
        "A deductible is the amount you pay for drugs before the plan starts to pay more.",
        "member_chat, website",
    ),
    (
        GLOSSARY_IDS["preferred_pharmacy"],
        "Definition of preferred retail pharmacy",
        "A preferred retail pharmacy is a local pharmacy that usually has a lower price on this plan.",
        "member_chat, website",
    ),
    (
        GLOSSARY_IDS["mail_order"],
        "Definition of mail order",
        "Mail order sends a 90-day supply of a drug to your home.",
        "member_chat, website",
    ),
    (
        GLOSSARY_IDS["oop_max"],
        "Definition of out-of-pocket maximum",
        "The out-of-pocket maximum is the most you pay for covered care in a year. After that, the plan pays the covered costs.",
        "member_chat, website",
    ),
    (
        SITE_MAIL,
        "Mail order supply rule",
        "Mail order fills 90-day supplies only.",
        "website, member_chat",
    ),
    (
        SITE_FIND,
        "Find a doctor",
        "To find a doctor, call 1-800-555-0148, 8 AM to 8 PM, seven days a week. The number and the hours are illustrative.",
        "website",
    ),
    (
        SITE_HELP,
        "Advocate help",
        "Call 1-800-555-0148, 8 AM to 8 PM, seven days a week, or ask in chat. A member advocate can take it from there. Hours are illustrative.",
        "website, member_chat",
    ),
    (
        OVER_ESTIMATE,
        "Charge higher than the estimate",
        "The pharmacy may have charged more than the estimate. The estimate is not a promise of what you pay. A member advocate can look at the claim with you.",
        "member_chat, voice_bot, website",
    ),
    (
        OVER_SUPPLY,
        "Different supply charge",
        "A different number of days can change the amount you pay. A member advocate can look at the claim with you.",
        "member_chat, voice_bot, website",
    ),
    (
        OVER_DEDUCT,
        "Deductible charge",
        "This charge may be your deductible. You pay the plan deductible before the plan pays more for some drugs. A member advocate can look at the claim with you.",
        "member_chat, voice_bot, website",
    ),
    (
        OVER_LIST,
        "Drug not on the list charge",
        "A drug that is not on your list is not part of this price estimate. A member advocate can look at the claim with you.",
        "member_chat, voice_bot, website",
    ),
]


PLAIN_PRICE_30 = (
    "This price is an estimate for a 30-day supply at a preferred retail pharmacy. "
    "It uses the plan information we have today. What you pay can change if the pharmacy, "
    "the number of days, or your coverage stage changes. An estimate is not a promise of what you will pay."
)
PLAIN_PRICE_ANY = (
    "This price is an estimate for the supply and the pharmacy shown. "
    "It uses the plan information we have today. What you pay can change if the pharmacy, "
    "the number of days, or your coverage stage changes. An estimate is not a promise of what you will pay."
)


def seed_finish_units(conn) -> None:
    """Approved wording added after pass 5. search_visible stays 0."""
    from src.engine import now_et

    for unit_id, title, member_text, channels in SUPPORT_UNITS:
        existing = conn.execute(
            "SELECT 1 FROM units WHERE unit_id = ? AND version = 1",
            (unit_id,),
        ).fetchone()
        if existing is not None:
            continue
        when = "2026-10-02 09:00 ET"
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
                'shared-legal', 'advocate,member',
                ?,
                'approved', 0, '',
                ?, 'Dana Okafor (Legal)', 'Legal', ?, 0, '',
                1, '', 'Approved member or phone wording. Search does not show this unit.', 0, 0,
                ?, '', 'Harbor Medicare Advantage HMO', ?, '2027-10-02',
                'plan-data', '', 'Dana Okafor (Legal)', 'seed'
            )
            """,
            (
                unit_id,
                title,
                member_text,
                channels,
                member_text,
                when,
                member_text,
                when,
            ),
        )
        conn.execute(
            "INSERT INTO unit_kb(unit_id, version, kb) VALUES(?, 1, 'shared-legal')",
            (unit_id,),
        )
    # U-RX-EDU-001-09 member_text stays as approved. It is the member search
    # candidate, so a plainer sentence here would change the saved answers.
    conn.execute(
        "UPDATE units SET member_text = ? WHERE unit_id = ?",
        (PLAIN_PRICE_ANY, PRICE_ANY),
    )
    link_price_siblings(conn)
    conn.commit()
    del now_et


def glossary_entries(conn) -> list[dict]:
    from api.plan_data import _hidden_member

    items = []
    for key, unit_id in GLOSSARY_IDS.items():
        ref = _hidden_member(conn, unit_id)
        if ref is None:
            continue
        items.append({"key": key, "kind": "definition", **ref})
    return items


def site_unit_ids() -> dict:
    return {
        "mail_order_90": SITE_MAIL,
        "find_care": SITE_FIND,
        "advocate_help": SITE_HELP,
    }


def split_two_questions(question: str) -> tuple[str, str]:
    text = (question or "").strip()
    lowered = text.lower()
    for marker in (" and how ", " and what ", " and can ", " and is "):
        at = lowered.find(marker)
        if at > 12:
            return text[:at].strip(" ?."), text[at + 5 :].strip()
    if "?" in text:
        head, tail = text.split("?", 1)
        tail = tail.strip()
        if tail and len(head.split()) >= 3:
            return head.strip(), tail
    return text, ""


def merge_context(question: str, context: dict | None) -> str:
    """Keep drug, supply, and pharmacy when a follow-up chip leaves them out."""
    from src.member_data import _days, _find_drug, _normalize, _pharmacy

    stored = context or {}
    if not stored:
        return question
    text = _normalize(question)
    continuation = any(word in text for word in ("cheaper", "mail", "90", "yes", "that one", "preferred", "retail"))
    if not continuation:
        return question
    drug = _find_drug(text)
    if drug is None and stored.get("drug_name"):
        question = f"{question} {stored['drug_name']}"
        text = _normalize(question)
    if stored.get("days") and _days(text) == 30 and "90" not in text and stored.get("days") == 90:
        if "mail" in text or stored.get("pharmacy") == "mail_order":
            question = f"{question} 90"
    if stored.get("pharmacy") == "mail_order" and "mail" not in text and "retail" not in text:
        if "cheaper" in text or "90" in text:
            question = f"{question} by mail"
    return question


def portal_openapi() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Harbor Health portal",
            "version": "0.6.0",
            "description": "Portal routes and the error format. Illustrative, made-up data.",
        },
        "paths": {
            "/api/portal/answers": {
                "get": {
                    "summary": "One cited answer",
                    "parameters": [
                        {"name": "role", "in": "query", "schema": {"type": "string"}},
                        {"name": "question", "in": "query", "schema": {"type": "string"}},
                        {"name": "member_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "world", "in": "query", "schema": {"type": "string"}},
                    ],
                }
            },
            "/api/portal/units": {"get": {"summary": "Approved units for a channel"}},
            "/api/portal/units/{unit_id}": {"get": {"summary": "One approved unit by id"}},
            "/api/portal/events": {
                "get": {
                    "summary": "Change events",
                    "parameters": [
                        {"name": "cursor", "in": "query", "schema": {"type": "string"}},
                        {"name": "world", "in": "query", "schema": {"type": "string"}},
                    ],
                }
            },
            "/api/portal/webhooks": {"post": {"summary": "Register a webhook. Deliveries are recorded, not sent."}},
            "/api/portal/openapi.json": {"get": {"summary": "This document"}},
        },
        "components": {
            "schemas": {
                "Problem": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "status": {"type": "integer"},
                        "detail": {"type": "string"},
                        "allowed": {"type": "array", "items": {"type": "string"}},
                    },
                }
            }
        },
    }
