"""Unit fields, routing, redaction, expiry, and as-of lookup."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("ANTHROPIC_API_KEY", None)

from src.engine import (
    activity,
    approve_by_author,
    author_queue,
    build_database,
    connect,
    expired_units,
    gaps,
    live_approved,
    presenter_unit_ids,
    publish_revision,
    quality_report,
    redact_query,
    search,
    units_as_of,
    waiting_units,
)


def _require(condition, message) -> None:
    if not condition:
        raise SystemExit(message)


def _logged(conn) -> str:
    return " ".join(row["message"] for row in activity(conn, 20))


def main() -> None:
    folder = tempfile.mkdtemp()
    path = str(Path(folder) / "gaps.sqlite")
    build_database(path, mode="start")
    conn = connect(path)
    from src.engine import confirm_tags, escalate_conflict, extract_units, keep_canonical

    extract_units(conn)
    confirm_tags(conn)
    keep_canonical(conn)
    escalate_conflict(conn)
    samples = [
        ("member id H12345678 what is the shoe size", "H12345678"),
        ("dob 01/02/1950 what is the shoe size", "01/02/1950"),
        ("phone 415-555-0199 what is the shoe size", "415-555-0199"),
        ("number 123456789 what is the shoe size", "123456789"),
    ]
    for query, secret in samples:
        _require(secret not in redact_query(query), f"redact left {secret}")
        found = search(conn, "Pharmacy advocate", query, record=True)
        _require(found["query"] == query, "search dropped the original query")
        _require(secret not in found["logged_query"], f"logged query kept {secret}")
        _require(secret not in _logged(conn), f"activity kept {secret}")
    cluster = next(row for row in gaps(conn) if row["id"] == "new-unclustered")
    _require(cluster["cluster"] == "New, not yet clustered", cluster["cluster"])
    _require(int(cluster["search_count"]) == 4, cluster["search_count"])
    _require("H12345678" not in (cluster["queries"] or ""), "gap stored a member id")

    authors = [row["unit_id"] for row in author_queue(conn)]
    legal = [row["unit_id"] for row in waiting_units(conn)]
    _require(authors, "author queue is empty")
    _require(all(not row["requires_legal"] for row in author_queue(conn)), "author queue has a legal unit")
    _require(all(row["requires_legal"] for row in waiting_units(conn)), "legal queue has an author unit")
    _require("U-RX-EDU-001-09" not in authors, "pricing disclaimer left Legal")
    approve_by_author(conn, authors[0])
    approved = live_approved(conn, authors[0])
    _require(approved["approved_by"] == "Knowledge Ops author", approved["approved_by"])
    _require(approved["effective_date"], "author approval has no effective date")
    _require(approved["applicability"], f"applicability missing on {authors[0]}")
    _require(authors[0] not in [row["unit_id"] for row in waiting_units(conn)], "author unit stayed in Legal")
    _require("U-RX-EDU-001-09" in legal, "pricing disclaimer left the Legal queue")

    short_path = str(Path(folder) / "short.sqlite")
    build_database(short_path, mode="short")
    short = connect(short_path)
    _require([row["unit_id"] for row in waiting_units(short)] == presenter_unit_ids(short), "short queue changed")
    expired = [row["unit_id"] for row in expired_units(short)]
    _require(expired == ["U-RX-EDU-001-13"], f"expired {expired}")
    report = quality_report(short)
    _require(any(item["miss"].startswith("Expired U-RX-EDU-001-13") for item in report["misses"]), "expiry miss missing")
    _require(any("review" in item["next_step"].lower() for item in report["misses"] if item["miss"].startswith("Expired")), "expiry next step")
    boundary = report["extraction_boundary"]
    _require(boundary["matched"] + boundary["missed"] == 16, boundary)
    _require("after the first model run" in boundary["note"], boundary["note"])

    jump_path = str(Path(folder) / "jump.sqlite")
    build_database(jump_path, mode="jump")
    jump = connect(jump_path)
    publish_revision(jump)
    pricing = "U-RX-EDU-001-09"
    versions = jump.execute(
        "SELECT version, effective_date, status FROM units WHERE unit_id = ? ORDER BY version",
        (pricing,),
    ).fetchall()
    _require(len(versions) == 2, f"versions {list(versions)}")
    jump.execute(
        "UPDATE units SET effective_date = ?, approved_on = ? WHERE unit_id = ? AND version = 1",
        ("2026-11-01 09:00 ET", "2026-11-01 09:00 ET", pricing),
    )
    jump.execute(
        "UPDATE units SET effective_date = ?, approved_on = ? WHERE unit_id = ? AND version = 2",
        ("2026-11-06 10:14 ET", "2026-11-06 10:14 ET", pricing),
    )
    jump.commit()
    before = units_as_of(jump, pricing, "2026-10-01")
    first = units_as_of(jump, pricing, "2026-11-01 09:30")
    second = units_as_of(jump, pricing, "2026-11-06")
    _require(before is None, before)
    _require(first and first["version"] == 1, first)
    _require(second and second["version"] == 2, second)
    _require(second["approver"] == "Legal approver", second)
    _require("available on this call" in second["text"], second["text"])
    _require(set(second) >= {"text", "member_text", "approver", "effective_date"}, second.keys())
    print("spec gaps ok", "authors", len(authors), "boundary", boundary["matched"], boundary["missed"], boundary["extra"])


if __name__ == "__main__":
    main()
