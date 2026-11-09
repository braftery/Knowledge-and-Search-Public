"""Feedback routing, redaction, and resolution."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("ANTHROPIC_API_KEY", None)

from src.ai import load_human_decisions
from src.engine import (
    CONTENT_FEEDBACK_KINDS,
    PRODUCT_FEEDBACK_KINDS,
    activity,
    build_database,
    connect,
    feedback_for_author,
    feedback_summary,
    product_backlog,
    record_feedback,
    resolve_feedback,
)

ROOT = Path(__file__).resolve().parents[1]


def _require(condition, message) -> None:
    if not condition:
        raise SystemExit(message)


def _open(path_name: str):
    folder = tempfile.mkdtemp()
    path = str(Path(folder) / path_name)
    build_database(path, mode="start")
    return connect(path)


def _kinds(groups) -> dict:
    return {group["kind"]: group for group in groups}


def _logged(conn) -> str:
    return " ".join(row["message"] for row in activity(conn, 40))


def main() -> None:
    conn = _open("feedback.sqlite")
    _require(
        conn.execute("SELECT COUNT(*) AS n FROM feedback").fetchone()["n"] == 0,
        "start mode seeded feedback",
    )

    author_questions = {
        "couldnt_find": "where is the prior authorization turnaround",
        "confusing_wording": "does the price include my deductible",
        "wrong_or_outdated": "is mail order still a 90 day supply",
        "no_answer": "what is the shoe size benefit",
        "not_helpful": "the pricing disclaimer did not help this caller",
    }
    product_questions = {
        "hard_to_find": "what do I say before I quote a medical cost",
        "rephrased": "is this the price I will pay",
        "clarified": "the advocate explained the estimate in other words",
        "handed_off": "who approves a tiering exception",
        "slow": "how long does a specialty pharmacy fill take",
    }
    stored = {}
    for kind, question in author_questions.items():
        stored[kind] = record_feedback(
            conn,
            "advocate",
            "Pharmacy advocate",
            kind,
            question,
            "U-RX-EDU-001-09" if kind == "not_helpful" else "",
            "Illustrative content note.",
            None,
        )
        _require(stored[kind]["route"] == "author", stored[kind])
        _require(stored[kind]["status"] == "open", stored[kind])
        _require(stored[kind]["signals"] == {}, stored[kind]["signals"])
    for kind, question in product_questions.items():
        signals = {"searches_in_call": 2, "seconds_to_answer": 70} if kind == "slow" else None
        stored[kind] = record_feedback(
            conn,
            "channel",
            "Member",
            kind,
            question,
            "U-RX-EDU-001-13" if kind == "slow" else "U-BEN-COST-001-05",
            "",
            signals,
        )
        _require(stored[kind]["route"] == "product", stored[kind])
    _require(stored["slow"]["signals"] == {"searches_in_call": 2, "seconds_to_answer": 70}, stored["slow"])

    author = _kinds(feedback_for_author(conn))
    product = _kinds(product_backlog(conn))
    _require(set(author) == set(CONTENT_FEEDBACK_KINDS), author)
    _require(set(product) == set(PRODUCT_FEEDBACK_KINDS), product)
    for kind, question in author_questions.items():
        _require(author[kind]["count"] == 1, author[kind])
        _require(author[kind]["examples"] == [question], author[kind])
        _require(author[kind]["ids"] == [stored[kind]["id"]], author[kind])
        _require(kind not in product, kind)
    for kind, question in product_questions.items():
        _require(product[kind]["count"] == 1, product[kind])
        _require(product[kind]["examples"] == [question], product[kind])
        _require(kind not in author, kind)

    secret_question = "member id H12345678 dob 01/02/1950 what is the shoe size"
    secret_note = "Call 415-555-0199 about number 123-45-6789. Illustrative."
    redacted = record_feedback(
        conn,
        "advocate",
        "Pharmacy advocate",
        "couldnt_find",
        secret_question,
        "",
        secret_note,
        {"searches_in_call": 4, "seconds_to_answer": 15},
    )
    for secret in ("H12345678", "01/02/1950", "415-555-0199", "123-45-6789"):
        _require(secret not in redacted["question"], redacted["question"])
        _require(secret not in redacted["note"], redacted["note"])
        _require(secret not in _logged(conn), secret)
    _require("[redacted]" in redacted["question"], redacted["question"])
    _require("[redacted]" in redacted["note"], redacted["note"])
    raw = conn.execute("SELECT question, note FROM feedback").fetchall()
    blob = " ".join(f"{row['question']} {row['note']}" for row in raw)
    _require("H12345678" not in blob, blob)
    author = _kinds(feedback_for_author(conn))
    _require(author["couldnt_find"]["count"] == 2, author["couldnt_find"])
    _require(redacted["question"] in author["couldnt_find"]["examples"], author["couldnt_find"])

    for _index in range(3):
        record_feedback(
            conn,
            "channel",
            "Member",
            "clarified",
            f"clarified example {_index}",
            "U-RX-EDU-001-09",
            "",
            None,
        )
    product = _kinds(product_backlog(conn))
    _require(product["clarified"]["count"] == 4, product["clarified"])
    _require(len(product["clarified"]["examples"]) == 3, product["clarified"]["examples"])
    _require(product["clarified"]["examples"][0] == "clarified example 2", product["clarified"]["examples"])

    summary = feedback_summary(conn)
    counts = {item["kind"]: item["count"] for item in summary["by_kind"]}
    _require(counts["couldnt_find"] == 2, counts)
    _require(counts["clarified"] == 4, counts)
    flagged = {item["unit_id"]: item["count"] for item in summary["most_flagged"]}
    _require(flagged["U-RX-EDU-001-09"] == 4, summary["most_flagged"])
    _require(flagged["U-BEN-COST-001-05"] == 4, summary["most_flagged"])
    _require(summary["most_flagged"][0]["unit_id"] == "U-BEN-COST-001-05", summary["most_flagged"])
    ranked_counts = [item["count"] for item in summary["most_flagged"]]
    _require(ranked_counts == sorted(ranked_counts, reverse=True), ranked_counts)
    _require(summary["week_start"], summary)
    _require("Illustrative" in summary["note"], summary["note"])

    before = feedback_summary(conn)
    before_author = _kinds(feedback_for_author(conn))["couldnt_find"]["count"]
    conn.execute(
        """
        INSERT INTO feedback (
            ts, source, role, kind, question, unit_id, note, signals, route, status, resolution, resolved_on
        ) VALUES ('2020-01-06 09:00 ET', 'advocate', 'Pharmacy advocate', 'couldnt_find',
                  'an old question', 'U-OLD-1', '', '{}', 'author', 'open', '', '')
        """
    )
    conn.commit()
    after = feedback_summary(conn)
    after_counts = {item["kind"]: item["count"] for item in after["by_kind"]}
    before_counts = {item["kind"]: item["count"] for item in before["by_kind"]}
    _require(after_counts == before_counts, (before_counts, after_counts))
    _require("U-OLD-1" not in [item["unit_id"] for item in after["most_flagged"]], after["most_flagged"])
    _require(_kinds(feedback_for_author(conn))["couldnt_find"]["count"] == before_author + 1, "old row left the queue")

    try:
        resolve_feedback(conn, stored["couldnt_find"]["id"], "   ")
        raise SystemExit("blank resolution was accepted")
    except ValueError as exc:
        _require("required" in str(exc).lower(), exc)
    try:
        resolve_feedback(conn, 99999, "Wrote a draft unit. Illustrative.")
        raise SystemExit("missing feedback id was accepted")
    except ValueError as exc:
        _require("99999" in str(exc), exc)

    closed = resolve_feedback(
        conn,
        stored["couldnt_find"]["id"],
        "Wrote a draft for the prior authorization turnaround. member id H12345678. Illustrative.",
    )
    _require(closed["status"] == "resolved", closed)
    _require(closed["resolved_on"], closed)
    _require("H12345678" not in closed["resolution"], closed["resolution"])
    _require("prior authorization turnaround" in closed["resolution"], closed["resolution"])
    _require("H12345678" not in _logged(conn), _logged(conn))
    _require(f"Resolved feedback {closed['id']}" in _logged(conn), _logged(conn))
    _require(stored["couldnt_find"]["id"] not in _kinds(feedback_for_author(conn))["couldnt_find"]["ids"], "resolved row stayed queued")
    try:
        resolve_feedback(conn, closed["id"], "Again.")
        raise SystemExit("a second resolution was accepted")
    except ValueError as exc:
        _require("already resolved" in str(exc), exc)

    try:
        record_feedback(conn, "desk", "Pharmacy advocate", "couldnt_find", "q", "", "", None)
        raise SystemExit("bad source was accepted")
    except ValueError as exc:
        _require("advocate or channel" in str(exc), exc)
    try:
        record_feedback(conn, "advocate", "Pharmacy advocate", "angry", "q", "", "", None)
        raise SystemExit("bad kind was accepted")
    except ValueError as exc:
        _require("Unknown feedback kind" in str(exc), exc)
    try:
        record_feedback(conn, "advocate", "  ", "couldnt_find", "q", "", "", None)
        raise SystemExit("blank role was accepted")
    except ValueError as exc:
        _require("role" in str(exc).lower(), exc)
    try:
        record_feedback(conn, "advocate", "Pharmacy advocate", "slow", "q", "", "", ["nope"])
        raise SystemExit("a signal list was accepted")
    except ValueError as exc:
        _require("JSON object" in str(exc), exc)

    decisions = load_human_decisions()["explore_feedback"]
    _require(decisions["label"] == "Illustrative", decisions["label"])
    _require("Illustrative" in decisions["note"], decisions["note"])
    _require(len(decisions["records"]) == 8, len(decisions["records"]))
    _require(
        {item["source"] for item in decisions["records"]} == {"advocate", "channel"},
        decisions["records"],
    )

    folder = tempfile.mkdtemp()
    explore_path = str(Path(folder) / "explore.sqlite")
    build_database(explore_path, mode="explore")
    explore = connect(explore_path)
    rows = explore.execute("SELECT * FROM feedback ORDER BY id").fetchall()
    _require(len(rows) == 8, len(rows))
    _require({row["source"] for row in rows} == {"advocate", "channel"}, "explore sources")
    _require({row["route"] for row in rows} == {"author", "product"}, "explore routes")
    stored_text = " ".join(f"{row['question']} {row['note']} {row['signals']}" for row in rows)
    for secret in ("H12345678", "415-555-0199", "shoe size"):
        _require(secret not in stored_text, stored_text)
        _require(secret not in _logged(explore), secret)
    shipping = explore.execute(
        "SELECT kind, question FROM feedback WHERE question LIKE '%90-day mail price includes shipping%'"
    ).fetchone()
    _require(shipping is not None, "shipping flag missing")
    _require(shipping["kind"] == "couldnt_find", shipping["kind"])
    explore_author = _kinds(feedback_for_author(explore))
    explore_product = _kinds(product_backlog(explore))
    _require(set(explore_author) == set(CONTENT_FEEDBACK_KINDS) - {"no_answer"}, explore_author)
    _require(explore_author["couldnt_find"]["count"] == 2, explore_author["couldnt_find"])
    _require({"hard_to_find", "rephrased", "slow"} <= set(explore_product), explore_product)
    explore_summary = feedback_summary(explore)
    top = explore_summary["most_flagged"][0]
    _require(top["unit_id"] == "U-RX-EDU-001-09" and top["count"] == 3, top)
    priced = explore.execute(
        "SELECT signals FROM feedback WHERE kind = 'hard_to_find'"
    ).fetchone()
    _require(json.loads(priced["signals"])["searches_in_call"] == 3, priced["signals"])
    print("feedback ok", "explore", len(rows), "week", summary["week_start"])


if __name__ == "__main__":
    main()
