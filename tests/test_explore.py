"""Explore sandbox, member answers, and live-call caps."""

import csv
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("ANTHROPIC_API_KEY", None)

import src.ai as ai
from src.engine import (
    CAP_MESSAGE,
    activity,
    author_queue,
    build_database,
    connect,
    decline_unit,
    flag,
    live_approved,
    member_answer,
    member_candidate_units,
    open_conflicts,
    record_search,
    search,
    set_live,
    waiting_units,
)

ROOT = Path(__file__).resolve().parents[1]
PENDING_LEGAL = ["U-RX-EDU-001-08", "U-RX-EDU-001-17", "U-BEN-COST-001-07"]
PENDING_AUTHOR = ["U-RX-EDU-001-01", "U-RX-EDU-001-03"]


def _require(condition, message) -> None:
    if not condition:
        raise SystemExit(message)


def _bank() -> list[tuple[str, str]]:
    with (ROOT / "data" / "question_bank.csv").open() as handle:
        return [(row["role"], row["question"]) for row in csv.DictReader(handle)]


def main() -> None:
    from src.explore import QUESTION_BANK

    bank = _bank()
    counts = {}
    for role, _question in bank:
        counts[role] = counts.get(role, 0) + 1
    _require(counts == {"Pharmacy advocate": 10, "Insurance advocate": 10, "Member": 10}, counts)
    for role, questions in QUESTION_BANK.items():
        for question in questions:
            _require((role, question) in bank, f"missing bank row {role}: {question}")

    folder = tempfile.mkdtemp()
    path = str(Path(folder) / "explore.sqlite")
    build_database(path, mode="explore")
    conn = connect(path)
    for key in ("extracted", "tags_confirmed", "website_merged", "canonical", "escalated"):
        _require(flag(conn, key), f"explore missing {key}")
    _require(not flag(conn, "conflict_resolved"), "explore resolved a conflict")
    _require(not flag(conn, "revised"), "explore revised the pricing disclaimer")
    _require(flag(conn, "live_ai"), "explore did not turn live AI on")
    _require(len(open_conflicts(conn)) == 3, [plan.get("id") for plan in open_conflicts(conn)])
    pricing = live_approved(conn, "U-RX-EDU-001-09")
    _require(pricing and pricing["version"] == 1, "pricing disclaimer is not the approved version 1")
    _require("on this page" not in (pricing["member_text"] or ""), pricing["member_text"])
    _require("on this call" not in (pricing["member_text"] or ""), pricing["member_text"])
    _require("plan information we have today" in (pricing["member_text"] or ""), pricing["member_text"])
    from src.ai import load_human_decisions

    history = load_human_decisions()["merges"][0]
    _require(history["into_unit_id"] == "U-RX-EDU-001-09", history)
    _require(history["unit_ids"] == ["U-WEB-FAQ-01", "U-WEB-FAQ-02", "U-WEB-FAQ-03"], history["unit_ids"])
    _require("on this page" in history["member_text"], "website merge history changed")
    locked = ("on this page", "this page", "on this call", "this call", "calling")
    stored = conn.execute("SELECT unit_id, member_text FROM units WHERE member_text != ''").fetchall()
    for row in stored:
        lowered = (row["member_text"] or "").lower()
        for phrase in locked:
            _require(phrase not in lowered, f"{row['unit_id']} member wording: {row['member_text']}")
    legal_waiting = [row["unit_id"] for row in waiting_units(conn)]
    author_waiting = [row["unit_id"] for row in author_queue(conn)]
    _require(sorted(legal_waiting) == sorted(PENDING_LEGAL), legal_waiting)
    _require(sorted(author_waiting) == sorted(PENDING_AUTHOR), author_waiting)

    visible = {unit["unit_id"] for unit in member_candidate_units(conn)}
    for unit_id in ("U-RX-EDU-001-09", "U-RX-EDU-001-13", "U-RX-EDU-001-05", "U-BEN-COST-001-05"):
        _require(unit_id in visible, f"member pool dropped {unit_id}")
    _require("U-RX-EDU-001-12" not in visible, "blocked mail-order unit is member eligible")
    for unit in member_candidate_units(conn):
        _require(unit["member_text"].strip(), unit["unit_id"])
        _require(unit["text"] == unit["member_text"], "member pool showed advocate text to the model")

    leak = member_answer(conn, "What do I say before I quote a drug price?")
    _require(leak["role"] == "Member", leak)
    _require("The price I quote" not in leak.get("member_text", ""), leak)
    _require("unit" not in leak, "member answer returned an advocate unit row")
    if not leak["abstained"]:
        _require(leak["member_text"] and leak["citation"], leak)
        _require("version" in leak["citation"], leak["citation"])

    calls = {"n": 0}

    def refuse(*_args, **_kwargs):
        calls["n"] += 1
        raise RuntimeError("model call refused")

    ai.call_model = refuse
    os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
    os.environ["HARBOR_LIVE_CAP_FILE"] = str(Path(folder) / "cap.json")
    set_live(conn, True)
    saved = search(conn, "Pharmacy advocate", "what do I say before I quote a cost", record=False)
    _require(saved["ai_source"] == "cached", saved["ai_source"])
    _require(calls["n"] == 0, "saved answer called the model")

    conn.execute("UPDATE meta SET value = '20' WHERE key = 'live_call_count'")
    if conn.execute("SELECT 1 FROM meta WHERE key = 'live_call_count'").fetchone() is None:
        conn.execute("INSERT INTO meta(key, value) VALUES('live_call_count', '20')")
    conn.commit()
    capped = search(conn, "Pharmacy advocate", "question with no saved answer at all xyz", record=False)
    _require(capped["ai_source"] == "capped", capped["ai_source"])
    _require(capped["ai_caption"] == CAP_MESSAGE, capped["ai_caption"])
    _require(calls["n"] == 0, "a capped call reached the model")

    conn.execute("UPDATE meta SET value = '0' WHERE key = 'live_call_count'")
    conn.commit()
    Path(os.environ["HARBOR_LIVE_CAP_FILE"]).write_text('{"date": "2099-01-01", "count": 300, "cap": 300}')
    # date rolls forward inside the helper when the stored date is not today, so set today's count
    from datetime import datetime
    from zoneinfo import ZoneInfo

    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    Path(os.environ["HARBOR_LIVE_CAP_FILE"]).write_text('{"date": "%s", "count": 300, "cap": 300}' % today)
    daily = search(conn, "Insurance advocate", "another question with no saved answer xyz", record=False)
    _require(daily["ai_source"] == "capped", daily["ai_source"])
    _require(calls["n"] == 0, "the daily cap reached the model")
    os.environ.pop("HARBOR_LIVE_CAP_FILE", None)
    os.environ.pop("ANTHROPIC_API_KEY", None)

    before = calls["n"]
    record_search(
        conn,
        "Pharmacy advocate",
        "member id H12345678 what is the shoe size",
        {"abstained": True, "ai_source": "cached"},
    )
    logged = " ".join(row["message"] for row in activity(conn, 5))
    _require("H12345678" not in logged, logged)
    _require("[redacted]" in logged, logged)
    _require(calls["n"] == before, "record_search called the model")

    referral = member_answer(conn, "Does my specialist visit need a referral?")
    _require(referral["ai_source"] != "missing", referral["ai_source"])
    if not referral["abstained"]:
        _require("your primary care doctor" in referral["member_text"], referral["member_text"])
        _require(referral["citation"].startswith(referral["title"]), referral["citation"])
        _require("version" in referral["citation"], referral["citation"])
        _require("The price I quote" not in referral["member_text"], referral["member_text"])

    member_questions = [question for role, question in bank if role == "Member"]
    answered = []
    for question in member_questions:
        result = member_answer(conn, question)
        _require(result["ai_source"] != "missing", f"missing member answer: {question}")
        _require("The price I quote" not in (result.get("member_text") or ""), result)
        _require("unit" not in result, result)
        if not result["abstained"]:
            answered.append((question, result["unit_id"]))
    print("member answers", len(answered), "of", len(member_questions))
    for question, unit_id in answered:
        print(f"  {unit_id}: {question}")

    _require(decline_unit(conn, "U-RX-EDU-001-08", "  ") == "A reason is required.", "empty decline reason was accepted")
    _require(
        decline_unit(conn, "U-RX-EDU-001-01", "Author units are not in the Legal queue.")
        == "This unit is not in the Legal queue.",
        "an author unit was declined",
    )
    sent = decline_unit(conn, "U-RX-EDU-001-08", "The disclaimer step needs a plain example. Illustrative.")
    _require(sent.startswith("Returned U-RX-EDU-001-08"), sent)
    legal_after = [row["unit_id"] for row in waiting_units(conn)]
    _require("U-RX-EDU-001-08" not in legal_after, legal_after)
    returned = [row for row in author_queue(conn) if row["unit_id"] == "U-RX-EDU-001-08"]
    _require(len(returned) == 1, "returned unit is missing from the author queue")
    _require(returned[0]["status"] == "returned", returned[0]["status"])
    _require(returned[0]["notes"] == "The disclaimer step needs a plain example. Illustrative.", returned[0]["notes"])
    _require(returned[0]["search_visible"] == 0, "returned unit is searchable")
    logged = " ".join(row["message"] for row in activity(conn, 4))
    _require("Returned U-RX-EDU-001-08" in logged and "plain example" in logged, logged)
    print("explore ok", "bank", len(bank), "member units", len(visible))


if __name__ == "__main__":
    main()
