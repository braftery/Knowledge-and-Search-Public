"""The full path and the short path, in the order the screens run them.

The demo-path test and scripts/generate_fixtures.py --demo-paths share this walk.
A yielded connection stays open until the next state. The caller does not close it.
"""

from __future__ import annotations

import csv
import re
import tempfile
from pathlib import Path

from src.engine import (
    ABSTAIN_QUERY,
    COST_QUERY,
    MISSPELL_QUERY,
    apply_drift,
    approve_one,
    edit_gap_draft,
    send_gap_to_approval,
    apply_prepared_drift,
    apply_website_merge,
    approve_by_author,
    approve_remaining,
    author_queue,
    build_database,
    confirm_tags,
    connect,
    escalate_conflict,
    extract_units,
    flag,
    gaps,
    keep_canonical,
    mark_today,
    presenter_unit_ids,
    publish_revision,
    resolve_conflict,
    search,
    write_gap,
    conflict_plans,
    DATA,
)

# State name -> the drift call the generator must cache before the walk applies it.
PENDING_DRIFT = {
    "v1-before-cosmetic": "cosmetic",
    "v1-before-material": "material",
    "revised-before-cosmetic": "cosmetic",
    "revised-before-material": "material",
    "revised-material-before-material": "material",
    "revised-material-before-cosmetic": "cosmetic",
}

REDACT_QUERY = "member id H12345678 dob 01/02/1950 phone 415-555-0199 number 123456789 what shoe size is on file"
UNCLUSTERED_QUERY = "what color is the clinic mailbox"

SEARCH_QUERIES = [
    ("Pharmacy advocate", COST_QUERY),
    ("Insurance advocate", COST_QUERY),
    ("Pharmacy advocate", ABSTAIN_QUERY),
    ("Insurance advocate", ABSTAIN_QUERY),
    ("Pharmacy advocate", MISSPELL_QUERY),
]


def golden_queries() -> list[tuple[str, str]]:
    with (DATA / "golden_set.csv").open() as handle:
        return [(row["role"], row["question"]) for row in csv.DictReader(handle)]


def question_bank_queries() -> list[tuple[str, str]]:
    with (DATA / "question_bank.csv").open() as handle:
        return [(row["role"], row["question"]) for row in csv.DictReader(handle)]


def heldout_queries() -> list[tuple[str, str]]:
    """The three questions written before tuning. Every demo state asks them."""
    with (DATA / "golden_set.csv").open() as handle:
        return [
            (row["role"], row["question"])
            for row in csv.DictReader(handle)
            if (row.get("heldout") or "").strip().lower() == "yes"
        ]


def _with_heldout(queries: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen = set()
    ordered = []
    for item in [*queries, *heldout_queries()]:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _mail_order_reason() -> str:
    for plan in conflict_plans():
        if plan.get("resolve_in_demo"):
            return plan.get("reason") or ""
    return ""


def _database(mode: str) -> object:
    folder = tempfile.mkdtemp()
    path = str(Path(folder) / f"{mode}.sqlite")
    build_database(path, mode=mode)
    return connect(path)


def _publish(conn) -> None:
    publish_revision(conn)
    if not flag(conn, "revised"):
        raise RuntimeError("channels revision did not publish")


def _drift(conn) -> None:
    message = apply_drift(conn)
    if message:
        raise RuntimeError(message)


def _apply_drift(conn, kind: str) -> str:
    return apply_prepared_drift(conn, kind)


def walk_demo_paths():
    """Yield (state name, connection, queries) for every search the demo issues."""
    search_and_golden = _with_heldout([*SEARCH_QUERIES, *golden_queries()])
    conn = _database("jump")
    try:
        yield "jump", conn, search_and_golden
        resolve_conflict(conn, _mail_order_reason())
        yield "jump-resolved", conn, search_and_golden
        _publish(conn)
        yield "jump-revised", conn, search_and_golden
        _drift(conn)
        yield "jump-drift", conn, search_and_golden
    finally:
        conn.close()

    conn = _database("start")
    try:
        mark_today(conn)
        extract_units(conn)
        confirm_tags(conn)
        apply_website_merge(conn)
        keep_canonical(conn)
        escalate_conflict(conn)
        yield "full-intake", conn, [
            ("Pharmacy advocate", REDACT_QUERY),
            ("Pharmacy advocate", UNCLUSTERED_QUERY),
        ]
        search(conn, "Pharmacy advocate", REDACT_QUERY, record=True)
        search(conn, "Pharmacy advocate", UNCLUSTERED_QUERY, record=True)
        yield "full-logged", conn, []
        for row in author_queue(conn):
            approve_by_author(conn, row["unit_id"])
        yield "full-author", conn, []
        approve_remaining(conn)
        resolve_conflict(conn, _mail_order_reason())
        yield "full-search", conn, _with_heldout(list(SEARCH_QUERIES))
        _publish(conn)
        yield "full-revised", conn, search_and_golden
        rows = list(gaps(conn))
        if rows:
            write_gap(conn, rows[0]["id"])
        _drift(conn)
        yield "full-quality", conn, search_and_golden
    finally:
        conn.close()

    conn = _database("short")
    try:
        yield "short-partial", conn, _with_heldout(list(SEARCH_QUERIES))
        for unit_id in presenter_unit_ids(conn):
            approve_one(conn, unit_id)
            yield f"short-approved-{unit_id}", conn, _with_heldout(list(SEARCH_QUERIES))
        _publish(conn)
        yield "short-channels", conn, _with_heldout(list(SEARCH_QUERIES))
    finally:
        conn.close()

    # (a) cosmetic, then material, on version 1.
    conn = _database("jump")
    try:
        yield "v1-before-cosmetic", conn, []
        _apply_drift(conn, "cosmetic")
        yield "v1-after-cosmetic", conn, []
        yield "v1-before-material", conn, []
        _apply_drift(conn, "material")
        yield "v1-after-material", conn, []
    finally:
        conn.close()

    # (b) publish, then cosmetic, then material. This is the full demo order.
    conn = _database("jump")
    try:
        _publish(conn)
        yield "revised-before-cosmetic", conn, []
        _apply_drift(conn, "cosmetic")
        yield "revised-after-cosmetic", conn, []
        yield "revised-before-material", conn, []
        _apply_drift(conn, "material")
        yield "revised-after-material", conn, []
    finally:
        conn.close()

    # (c) publish, then material, then cosmetic.
    conn = _database("jump")
    try:
        _publish(conn)
        yield "revised-material-before-material", conn, []
        _apply_drift(conn, "material")
        yield "revised-material-after-material", conn, []
        yield "revised-material-before-cosmetic", conn, []
        _apply_drift(conn, "cosmetic")
        yield "revised-material-after-cosmetic", conn, []
    finally:
        conn.close()

    conn = _database("explore")
    try:
        yield "explore", conn, question_bank_queries()
    finally:
        conn.close()


_SURFACE_QUESTION = "whats the rx pricing disclamer i have to read"


def explore_surface_queries() -> list[tuple[str, str]]:
    """Questions the Explore advocate desktop and member topics send.

    Advocate questions come from web/src/pages/advocate/scenarios.ts.
    Member questions are the topics on GET /api/explore/member/topics.
    """
    from api.catalog import MEMBER_TOPICS

    text = (Path(__file__).resolve().parents[1] / "web/src/pages/advocate/scenarios.ts").read_text()
    pharmacy, insurance = text.split("\n  insurance:", 1)

    def questions(block: str) -> list[str]:
        found = []
        for body in re.findall(r"questions:\s*\[(.*?)\]", block, re.S):
            found.extend(re.findall(r'"([^"]+)"', body))
        return found

    ordered = []
    seen = set()

    def add(role: str, question: str) -> None:
        key = (role, question)
        if key in seen:
            return
        seen.add(key)
        ordered.append(key)

    for question in questions(pharmacy):
        add("Pharmacy advocate", question)
    for question in questions(insurance):
        add("Insurance advocate", question)
    for topic in MEMBER_TOPICS:
        add("Member", topic["question"])
    add("Pharmacy advocate", _SURFACE_QUESTION)
    return ordered


def _clear_placeholders(text: str) -> str:
    return re.sub(r"\[([^\[\]]+)\]", r"\1", text or "")


def approve_gap_c0(conn) -> None:
    """Send gap c0 and have Legal approve U-GAP-c0.

    The draft quotes the pricing disclaimer and mentions price, so the existing
    routing rule places it in the Legal queue once the placeholder is gone.
    """
    row = conn.execute("SELECT * FROM gaps WHERE id = 'c0'").fetchone()
    if row is None:
        raise RuntimeError("gap c0 is missing")
    message = edit_gap_draft(
        conn,
        "c0",
        _clear_placeholders(row["draft_text"] or ""),
        _clear_placeholders(row["draft_member_text"] or ""),
    )
    if message:
        raise RuntimeError(message)
    message = send_gap_to_approval(conn, "c0")
    if message:
        raise RuntimeError(message)
    message = approve_one(conn, "U-GAP-c0")
    if not str(message).startswith("Approved"):
        raise RuntimeError(message or "Legal did not approve U-GAP-c0")


def walk_explore_surface_states():
    """Yield (name, connection) for the four Explore states the surface cache covers.

    fresh; after the version 2 publish; after U-GAP-c0 is approved by Legal; and after both.
    A yielded connection stays open until the next state.
    """
    conn = _database("explore")
    try:
        yield "explore-fresh", conn
    finally:
        conn.close()

    conn = _database("explore")
    try:
        _publish(conn)
        yield "explore-revised", conn
    finally:
        conn.close()

    conn = _database("explore")
    try:
        approve_gap_c0(conn)
        yield "explore-gap", conn
    finally:
        conn.close()

    conn = _database("explore")
    try:
        _publish(conn)
        approve_gap_c0(conn)
        yield "explore-revised-gap", conn
    finally:
        conn.close()
