"""Empty queues, repeated actions, and live-call caps. No API key is printed."""

import json
import os
import sqlite3

from api.tests.conftest import session_dir


def test_empty_queues_leave_undo(client):
    created = client.post("/api/session/reset", json={"mode": "jump"})
    assert created.status_code == 200
    assert client.get("/api/legal/queue").json()["count"] == 0
    assert client.get("/api/author/queue").json()["count"] == 0
    legal = client.post("/api/legal/approve-all", json={})
    author = client.post("/api/author/approve-all", json={})
    assert legal.status_code == 400
    assert legal.json()["error"] == "The Legal queue is empty."
    assert author.status_code == 400
    assert author.json()["error"] == "Nothing is waiting for Knowledge Ops approval."
    assert client.get("/api/undo").json()["available"] is True


def test_repeated_approve_keeps_prior_undo(short):
    unit_id = short.get("/api/legal/queue").json()["waiting"][0]["unit_id"]
    first = short.post("/api/legal/approve", json={"unit_id": unit_id})
    assert first.status_code == 200
    again = short.post("/api/legal/approve", json={"unit_id": unit_id})
    assert again.status_code == 400
    assert again.json()["error"]
    assert "traceback" not in again.text.lower()
    assert short.get("/api/undo").json()["available"] is True
    restored = short.post("/api/undo", json={})
    assert restored.status_code == 200
    waiting = [item["unit_id"] for item in short.get("/api/legal/queue").json()["waiting"]]
    assert unit_id in waiting
    second_undo = short.post("/api/undo", json={})
    assert second_undo.status_code == 400
    assert second_undo.json()["error"] == "Nothing to undo."


def test_unknown_world(short):
    response = short.post("/api/demo/today", json={"world": "other"})
    assert response.status_code == 400
    assert response.json()["error"] == "world must be guided or explore."


def test_explore_closed(client):
    response = client.get("/api/explore/my-work")
    assert response.status_code == 400
    assert response.json()["error"] == "Open an Explore role before using the sandbox."


def test_repeated_ask_uses_visit_cache(explore):
    body = {"role": "Pharmacy advocate", "query": "what do I say before I quote a cost"}
    first = explore.post("/api/explore/ask", json=body)
    assert first.status_code == 200
    assert first.json()["from_visit_cache"] is False
    second = explore.post("/api/explore/ask", json=body)
    assert second.status_code == 200
    assert second.json()["from_visit_cache"] is True
    assert second.json()["result"]["unit"]["unit_id"] == first.json()["result"]["unit"]["unit_id"]


def test_visit_cap_skips_live(explore, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-key")
    path = os.path.join(session_dir(explore), "meta.json")
    meta = json.loads(open(path, encoding="utf-8").read())
    meta["explore_live_calls"] = 20
    open(path, "w", encoding="utf-8").write(json.dumps(meta))
    response = explore.post(
        "/api/explore/ask",
        json={"role": "Pharmacy advocate", "query": "What is the ZX-999 widget coverage code?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["used_live"] is False
    assert body["live_calls_left"] == 0
    assert body["result"]["ai_source"] == "missing"


def test_database_live_cap(explore, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-key")
    database = os.path.join(session_dir(explore), "explore.sqlite")
    connection = sqlite3.connect(database)
    connection.execute(
        "INSERT INTO meta(key, value) VALUES('live_call_count', '20') "
        "ON CONFLICT(key) DO UPDATE SET value = '20'"
    )
    connection.commit()
    connection.close()
    response = explore.post(
        "/api/explore/ask",
        json={"role": "Pharmacy advocate", "query": "What is the ZX-998 widget coverage code?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["used_live"] is False
    assert body["result"]["ai_source"] == "capped"
    assert "Live call limit reached" in body["result"]["ai_caption"]


def test_daily_live_cap(explore, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-key")
    from datetime import datetime
    from zoneinfo import ZoneInfo

    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    cap_path = os.environ["HARBOR_LIVE_CAP_FILE"]
    open(cap_path, "w", encoding="utf-8").write(json.dumps({"date": today, "count": 300, "cap": 300}))
    explore.post("/api/explore/open", json={"role": "Insurance advocate"})
    response = explore.post(
        "/api/explore/ask",
        json={"role": "Insurance advocate", "query": "What is the ZX-997 widget coverage code?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["ai_source"] == "capped"
    assert body["used_live"] is False
