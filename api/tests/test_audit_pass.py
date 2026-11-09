"""Audit passes 2 and 3: guided live fallback, one golden score, seed, blocked search, chat."""

import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from api.tests.conftest import session_dir

CAREGIVER = "U-RX-EDU-001-05"
REFERRAL = "U-BEN-COST-001-05"
PRICING = "U-RX-EDU-001-09"
DESK_COPIES = {
    "U-RX-EDU-002-08": "U-RX-EDU-001-10",
    "U-RX-EDU-002-14": "U-RX-EDU-001-16",
    "U-RX-EDU-002-05": "U-RX-EDU-001-06",
    "U-RX-EDU-002-02": "U-RX-EDU-001-03",
    "U-BEN-COST-001-09": "U-BEN-COST-001-05",
}
BLOCKED_NOTE = "Under Legal review. Use the currently approved rule until Legal decides."
HANDOFF = "I'm sorry about that. A member advocate can look at your account with you."


def _tile(body, key):
    return next(tile for tile in body["tiles"] if tile["key"] == key)


def _counts_add_up(counts):
    assert counts["right_first"] + counts["wrong"] + counts["wrong_no_answers"] == counts["scored"]


def test_presenter_step8_scores(client):
    """The guided path in DEMO.md, then the quality score the presenter reads."""
    assert client.post("/api/session/reset", json={"mode": "start"}).status_code == 200
    for path, body in (
        ("/api/demo/extract", {}),
        ("/api/demo/confirm-tags", {}),
        ("/api/demo/keep-canonical", {}),
        ("/api/demo/escalate", {}),
        ("/api/legal/approve", {"unit_id": PRICING}),
        ("/api/legal/approve-all", {}),
        ("/api/author/approve-all", {}),
        ("/api/conflicts/resolve", {"reason": "Legal keeps the signed script."}),
        ("/api/channels/publish", {}),
        ("/api/drift", {"kind": "cosmetic"}),
        ("/api/drift", {"kind": "material"}),
        ("/api/drift/send", {}),
    ):
        response = client.post(path, json=body)
        assert response.status_code == 200, f"{path} {response.text}"
    scored = client.post("/api/quality/score", json={"world": "guided"})
    assert scored.status_code == 200, scored.text
    quality = scored.json()["quality"]
    assert _tile(quality, "hit_at_1")["detail"] == "8 of 8"
    assert _tile(quality, "correct_abstain")["detail"] == "4 of 4"
    assert quality["held_out_pass"] == 2
    assert quality["held_out_total"] == 3
    assert len(quality["misses"]) == 6
    _counts_add_up(quality["score_counts"])
    assert quality["score_counts"]["right_first"] == 8
    assert quality["score_counts"]["scored"] == 8
    assert quality["not_scored"] == 0
    assert all(row["Result"] != "No saved answer" for row in quality["golden_table"]["rows"])


def test_insights_and_quality_share_hit_at_1(explore):
    scored = explore.post("/api/quality/score", json={"world": "explore"})
    assert scored.status_code == 200, scored.text
    quality = explore.get("/api/quality", params={"world": "explore"}).json()
    insights = explore.get("/api/explore/insights").json()
    assert _tile(quality, "hit_at_1")["detail"] == _tile(insights, "hit_at_1")["detail"]
    assert _tile(quality, "hit_at_1")["display"] == _tile(insights, "hit_at_1")["display"]
    assert quality["score_counts"] == insights["score_counts"]
    _counts_add_up(insights["score_counts"])
    assert quality["held_out_pass"] == insights["held_out"]["pass"]
    assert quality["held_out_total"] == insights["held_out"]["total"]
    not_scored_rows = [
        row for row in quality["golden_table"]["rows"] if row["Result"] == "No saved answer"
    ]
    assert quality["not_scored"] == len(not_scored_rows) + sum(
        1 for row in quality["golden_table"]["held_out"] if row["Result"] == "No saved answer"
    )
    assert all(item["miss"] for item in quality["misses"])
    assert not any("No saved answer" in item["miss"] for item in quality["misses"])


def test_guided_cache_miss_without_key_is_missing(short):
    response = short.post(
        "/api/search",
        json={
            "world": "guided",
            "role": "Pharmacy advocate",
            "query": "What is the ZX-999 widget coverage code?",
            "record": False,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"]["ai_source"] == "missing"
    assert body["result"]["abstained"] is True
    assert body["result"]["unit"] is None
    assert body["used_live"] is False


def test_guided_cache_miss_calls_live_when_a_key_is_set(short, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-key")

    def replay(task, user_content, live=False, directory=None):
        if not live:
            return None, "missing"
        return {"answer_unit_id": None, "reason": "None of the units answer this."}, "live"

    monkeypatch.setattr("src.corpus.replay", replay)
    response = short.post(
        "/api/search",
        json={
            "world": "guided",
            "role": "Pharmacy advocate",
            "query": "What is the ZX-998 widget coverage code?",
            "record": False,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["used_live"] is True
    assert body["result"]["ai_source"] == "live"
    assert body["live_calls_left"] == 19


def test_guided_failed_live_call_stays_missing(short, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-key")

    def replay(task, user_content, live=False, directory=None):
        if not live:
            return None, "missing"
        return None, "live_failed"

    monkeypatch.setattr("src.corpus.replay", replay)
    response = short.post(
        "/api/search",
        json={
            "world": "guided",
            "role": "Insurance advocate",
            "query": "What is the ZX-997 widget coverage code?",
            "record": False,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["ai_source"] == "missing"
    assert response.json()["used_live"] is False


def test_seeded_approvers_and_gap_volumes(client, explore):
    jump = client.post("/api/session/reset", json={"mode": "jump"})
    assert jump.status_code == 200, jump.text
    units = client.get("/api/units", params={"world": "guided", "status": "approved", "latest": "true"}).json()
    procedures = [row for row in units["units"] if row["type"] in ("procedure", "faq")]
    legal = [row for row in units["units"] if row["type"] in ("verbatim", "policy")]
    assert procedures
    assert legal
    assert all(row["approved_by"] == "Sam Patel (Knowledge Ops)" for row in procedures)
    assert all(row["approver_role"] == "Knowledge Ops" for row in procedures)
    assert all(row["approved_by"] == "Dana Okafor (Legal)" for row in legal)
    assert all(row["approver_role"] == "Legal" for row in legal)
    for row in units["units"]:
        day = (row["approved_on"] or "")[:10]
        assert "2025-11-02" <= day <= "2026-10-15", row["unit_id"]
    gaps = client.get("/api/gaps", params={"world": "guided"}).json()["gaps"]
    by_id = {row["id"]: row for row in gaps}
    assert by_id["c5"]["search_count"] == 340
    assert by_id["c5"]["findability"] is False
    for gap_id in ("c0", "c2", "c3", "c4"):
        assert by_id[gap_id]["findability"] is True
    others = [row["search_count"] for row in gaps if row["id"] != "c5" and row["kind"] == "cluster"]
    assert others
    assert min(others) >= 12
    assert max(others) <= 210
    insights = explore.get("/api/explore/insights").json()
    assert insights["top_gaps"]
    assert insights["top_gaps"][0]["search_count"] == 340
    assert all(not row["findability"] for row in insights["top_gaps"])
    names = {row["cluster"] for row in insights["findability_gaps"]}
    assert "Rx pricing disclaimer to read" in names
    edits = explore.get("/api/author/edits", params={"world": "explore"}).json()
    assert any(row["id"] == "c0" for row in edits["gaps"])


def test_session_approval_keeps_the_generic_label(explore):
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    explore.post("/api/explore/open", json={"role": "Legal approver"})
    response = explore.post(
        "/api/legal/approve",
        json={"world": "explore", "unit_id": "U-RX-EDU-001-08"},
    )
    assert response.status_code == 200, response.text
    unit = explore.get("/api/units/U-RX-EDU-001-08", params={"world": "explore"}).json()["unit"]
    assert unit["approved_by"] == "Legal approver"
    assert unit["approver_role"] == "Legal approver"
    assert unit["approved_on"].startswith(today)
    explore.post("/api/explore/open", json={"role": "Knowledge Ops author"})
    author = explore.post(
        "/api/author/approve",
        json={"world": "explore", "unit_id": "U-RX-EDU-001-01"},
    )
    assert author.status_code == 200, author.text
    procedure = explore.get("/api/units/U-RX-EDU-001-01", params={"world": "explore"}).json()["unit"]
    assert procedure["approved_by"] == "Knowledge Ops author"
    assert procedure["approved_on"].startswith(today)


def test_merged_desk_copies_leave_approved_search(explore):
    listed = explore.get(
        "/api/units",
        params={"world": "explore", "status": "approved", "latest": "true"},
    ).json()
    ids = {row["unit_id"] for row in listed["units"]}
    for desk_id, canonical_id in DESK_COPIES.items():
        assert desk_id not in ids
        unit = explore.get(f"/api/units/{desk_id}", params={"world": "explore"}).json()["unit"]
        assert unit["status"] == "merged"
        assert unit["superseded_by"] == canonical_id
        assert unit["search_visible"] is False
    found = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "what do I say before I quote a cost",
            "record": False,
        },
    )
    assert found.status_code == 200, found.text
    ranked = {row["unit_id"] for row in found.json()["result"]["ranked"]}
    assert not ranked & set(DESK_COPIES)


def test_blocked_match_hides_the_wording(explore):
    response = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "For a maintenance drug, offer a 90-day mail-order supply on the first fill.",
            "record": True,
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["status"] == "blocked_conflict"
    assert result["blocked_note"] == BLOCKED_NOTE
    assert result["abstained"] is True
    assert result["unit"] is None
    assert "first fill" not in (result.get("note") or "").lower() or result["note"] == BLOCKED_NOTE
    gaps = explore.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    blob = " ".join(" ".join(row.get("queries") or []) for row in gaps)
    assert "first fill" not in blob.lower()
    database = os.path.join(session_dir(explore), "explore.sqlite")
    connection = sqlite3.connect(database)
    connection.execute(
        """
        UPDATE units
        SET status = 'approved', search_visible = 1, approved_by = 'Dana Okafor (Legal)', approver_role = 'Legal'
        WHERE unit_id = 'U-RX-EDU-001-12' AND version = 1
        """
    )
    connection.commit()
    connection.close()
    again = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "For a maintenance drug, offer a 90-day mail-order supply on the first fill.",
            "record": False,
        },
    )
    assert again.status_code == 200, again.text
    follow = again.json()["result"]
    assert follow["status"] == "blocked_conflict"
    assert follow["blocked_note"] == BLOCKED_NOTE
    assert follow["fallback_unit"]["unit_id"] == "U-RX-EDU-001-12"
    assert follow["fallback_unit"]["status"] == "approved"
    assert "first fill" not in (follow["fallback_unit"].get("text") or "")


def test_member_chat_referral_caller_and_complaint(explore):
    before = explore.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    referral = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "do i need a referral for a cardiologist"},
    ).json()
    assert referral["kind"] == "answer"
    assert referral["unit_id"] == REFERRAL
    assert referral["citation"].startswith("Source: Harbor Health,")
    assert "version" in referral["citation"]
    caller = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "can my son call for me"},
    ).json()
    assert caller["kind"] == "answer"
    assert caller["unit_id"] == CAREGIVER
    assert caller["citation"].startswith("Source: Harbor Health,")
    upset = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "I think I was overcharged and I am upset"},
    ).json()
    assert upset["kind"] == "handoff_offer"
    assert upset["reply"] == HANDOFF
    assert upset["chips"][0] == "The pharmacy charged more than the estimate"
    assert upset["chips"][-2:] == ["Talk to a member advocate", "See my recent claims"]
    assert upset["feedback_recorded"] is None
    weather = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": "what is the weather"}).json()
    assert weather["kind"] == "out_of_scope"
    assert weather["reply"].endswith("or I can connect you with a member advocate.")
    after = explore.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    assert after == before
    specialist = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "what will a specialist visit cost"},
    ).json()
    assert specialist["kind"] == "visit_cost"
