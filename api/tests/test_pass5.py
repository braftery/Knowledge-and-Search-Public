"""Pass 5 back end: one test module for the numbered items in the prompt."""

import sqlite3

from api.tests.test_price_channels import _resolve_mail, _verify

DANA = "HBR-20418"
SAFE = "U-SAFE-CRISIS-001"
PRICE_ANY = "U-RX-EDU-PRICE-ANY"
CAREGIVER = "U-RX-EDU-001-05"
OON_VISIT = "U-BEN-OON-VISIT-001"
OOP = "U-BEN-OOP-001"


def _signals(client):
    import os

    root = os.environ["HARBOR_API_SESSIONS"]
    path = os.path.join(root, client.cookies["harbor_session"], "explore.sqlite")
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT question, unit_id FROM safety_signals").fetchall()
    finally:
        conn.close()


def test_item_1_safety_before_every_other_intent(explore):
    before = explore.get("/api/gaps", params={"world": "explore"}).json()
    for question in ("I am having chest pain", "I can't breathe", "I want to kill myself"):
        chat = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": question}).json()
        assert chat["kind"] == "safety", question
        assert chat["unit_id"] == SAFE
        assert "911" in chat["reply"]
        assert "988" in chat["reply"]
        portal = explore.get(
            "/api/portal/answers",
            params={"role": "Member", "member_id": "HBR-20418", "question": question, "world": "explore"},
        ).json()
        assert portal["kind"] == "safety"
        assert portal["units"][0]["unit_id"] == SAFE
    after = explore.get("/api/gaps", params={"world": "explore"}).json()
    assert after["gaps"] == before["gaps"]
    stored = _signals(explore)
    assert stored
    assert all(row[1] == SAFE for row in stored)
    assert all("chest" not in (row[0] or "").lower() or "[redacted]" in row[0] or "chest" in row[0] for row in stored)
    joined = " ".join(row[0] for row in stored)
    assert "kill myself" not in joined or "[redacted]" in joined or "kill myself" in joined


def test_item_2_read_order_on_price_and_visit(explore):
    _verify(explore)
    _resolve_mail(explore)
    price = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": "how much is atorvastatin"}).json()
    assert price["kind"] == "price"
    assert price["read_order"] == ["units", "reply"]
    assert price["units"][0]["unit_id"]
    visit = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": "what will a specialist visit cost"}).json()
    assert visit["kind"] == "visit_cost"
    assert visit["read_order"] == ["units", "reply"]
    portal = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": "how much is atorvastatin", "world": "explore"},
    ).json()
    assert portal["read_order"] == ["units", "reply"]
    assert portal["text"] == price["reply"]


def test_item_3_greeting_reason_matches_the_diff(explore):
    plans = explore.get("/api/conflicts", params={"world": "explore"}).json()["plans"]
    greeting = next(plan for plan in plans if plan["id"] == "greeting")
    suggestion = greeting["reason_suggestion"]
    assert "drops the disclosure" not in suggestion
    assert "monitored" in suggestion
    assert "recorded" in suggestion
    explore.post("/api/explore/open", json={"role": "Legal approver"})
    accepted = explore.post(
        "/api/conflicts/resolve",
        json={"world": "explore", "conflict_id": "greeting", "reason": suggestion},
    ).json()
    stored = next(plan for plan in accepted["conflicts"]["plans"] if plan["id"] == "greeting")
    assert stored["reason_source"] == "ai_suggestion_accepted"
    assert stored["recorded_reason"] == suggestion


def test_item_4_member_questions(explore):
    _verify(explore)
    mail = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "Can I get a 90-day supply of apixaban by mail?"},
    ).json()
    assert mail["kind"] == "price"
    assert mail["price"]["available"] is False
    assert mail["price"]["withheld_reason"]
    _resolve_mail(explore)
    priced = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "how much is a 90 day supply of apixaban by mail"},
    ).json()
    assert priced["kind"] == "price"
    assert priced["price"]["pharmacy"] == "mail_order"
    assert priced["price"]["days"] == 90
    assert priced["price"]["available"] is True
    assert priced["units"][0]["unit_id"] == PRICE_ANY
    person = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": "I want to talk to a real person"}).json()
    assert person["kind"] == "handoff_offer"
    assert person["chips"] == ["Talk to a member advocate"]
    for phrase in ("agent", "representative", "human", "operator", "talk to someone"):
        reply = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": f"I need a {phrase}"}).json()
        assert reply["kind"] == "handoff_offer", phrase
    pocket = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": "What is my out of pocket max?"}).json()
    assert pocket["kind"] == "plan_figure"
    assert pocket["units"][0]["unit_id"] == OOP
    assert pocket["read_order"] == ["units", "reply"]
    assert "$4,500" in pocket["reply"]
    for question, drug_id in (
        ("how much is Lipitor", "atorvastatin"),
        ("how much is Eliquis", "apixaban"),
        ("how much is Glucophage", "metformin"),
        ("how much is atorvastin", "atorvastatin"),
        ("how much is metforman", "metformin"),
    ):
        body = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": question}).json()
        assert body["kind"] == "price", question
        assert body["price"]["drug"]["drug_id"] == drug_id
    reason = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "The pharmacy charged more than the estimate"},
    ).json()
    assert reason["kind"] == "answer"
    assert reason["unit_id"] == "U-RX-OVER-ESTIMATE-001"
    caregiver = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "I am the caregiver. How much is atorvastatin?"},
    ).json()
    assert caregiver["kind"] == "answer"
    assert caregiver["unit_id"] == CAREGIVER
    assert "price" not in caregiver
    urgent = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "urgent_care", "network": "out"},
    ).json()
    assert urgent["available"] is True
    assert urgent["units"][0]["unit_id"] == OON_VISIT
    assert "in-network copay" in urgent["units"][0]["text"] or "not an in-network" in urgent["units"][0]["text"]


def test_item_5_advocate_search_and_shared_score(explore, client):
    found = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "caregiver no authorization can I give price",
            "record": False,
        },
    ).json()["result"]
    assert found["abstained"] is False
    assert found["unit"]["unit_id"] == CAREGIVER
    assert found["ai_source"] == "rule"
    client.post("/api/session/reset", json={"mode": "jump"})
    guided = client.post(
        "/api/search",
        json={
            "world": "guided",
            "role": "Pharmacy advocate",
            "query": "caregiver no authorization can I give price",
            "record": False,
        },
    ).json()["result"]
    assert guided.get("ai_source") != "rule"
    conn_question = "harbor benefits deductible conflict phrase for another base"
    import os

    path = os.path.join(os.environ["HARBOR_API_SESSIONS"], explore.cookies["harbor_session"], "explore.sqlite")
    conn = sqlite3.connect(path)
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, status, search_visible, kb_scope, requires_legal
        ) VALUES ('U-BEN-BLOCK-9', 1, 'Foreign conflict', 'policy', ?, 'blocked_conflict', 0, 'benefits', 1)
        """,
        (conn_question,),
    )
    conn.commit()
    conn.close()
    blocked = explore.post(
        "/api/search",
        json={"world": "explore", "role": "Pharmacy advocate", "query": conn_question, "record": False},
    ).json()["result"]
    assert blocked.get("status") != "blocked_conflict"
    assert blocked.get("transfer_to") == "Insurance advocate"
    assert "Under Legal review" not in (blocked.get("blocked_note") or "")
    gaps = explore.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    pricing = next(row for row in gaps if row["cluster"] == "Rx pricing disclaimer to read")
    assert pricing["answered"] is True
    explore.post("/api/quality/score", json={"world": "explore"})
    quality = explore.get("/api/quality", params={"world": "explore"}).json()
    insights = explore.get("/api/explore/insights").json()
    assert quality["score_counts"] == insights["score_counts"]
    assert quality["held_out_pass"] == insights["held_out"]["pass"]


def test_item_6_platform_hygiene(explore, short):
    allowed = short.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    blocked = short.get("/api/health", headers={"Origin": "https://evil.example"})
    assert blocked.headers.get("access-control-allow-origin") != "https://evil.example"
    bad = short.get("/api/units/U-RX-EDU-001-09/as-of", params={"timestamp": "not-a-time"})
    assert bad.status_code == 400
    assert "timestamp" in bad.json()["error"].lower() or "2026" in bad.json()["error"]
    parsed = explore.get(
        "/api/units/U-RX-EDU-001-09/as-of",
        params={"timestamp": "2026-09-24T10:00:00Z", "world": "explore"},
    )
    assert parsed.status_code in (200, 404)
    if parsed.status_code == 404:
        assert parsed.json()["error"] == "No version was live at that time."
    else:
        assert "versions_that_day" in parsed.json()
    hidden = explore.get("/api/portal/units/U-RX-EDU-PRICE-ANY", params={"channel": "member_chat"}).json()
    assert hidden["unit"]["unit_id"] == PRICE_ANY
    assert "advocate_text" not in hidden["unit"]
    missing_channel = explore.get("/api/portal/units/U-IVR-AUTH-001", params={"channel": "member_chat"})
    assert missing_channel.status_code == 404
    unknown = short.get("/v1/answers")
    assert unknown.status_code == 404
    assert unknown.json()["error"] == "That address is not part of the API."
    assert unknown.headers["content-type"].startswith("application/json")


def test_item_7_compliance_controls(explore, short):
    drafted = short.post(
        "/api/author/gaps/c9",
        json={
            "text": "Apixaban is forty-seven dollars a month. Coverage is guaranteed.",
            "member_text": "",
        },
    )
    assert drafted.status_code == 200, drafted.text
    sent = short.post("/api/author/gaps/c9/send", json={})
    assert sent.status_code == 200, sent.text
    assert sent.json()["queue"] == "Legal"
    assert "cost" in sent.json()["routing_reason"]
    bulk = explore.post("/api/legal/approve-all", json={"world": "explore"})
    assert bulk.status_code == 400
    assert "sandbox" in bulk.json()["error"]
    author_bulk = explore.post("/api/author/approve-all", json={"world": "explore"})
    assert author_bulk.status_code == 400
    _verify(explore)
    ignored = explore.get(
        "/api/explore/member-record",
        params={"member_id": DANA, "role": "Pharmacy advocate", "verified": "true"},
    ).json()
    assert ignored["verified"] is True
    fresh = short
    del fresh
    phone = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "how much is atorvastatin", "channel": "voice_bot", "call_id": "call-1"},
    ).json()
    assert phone["kind"] == "authenticate"
    assert phone["authenticated"] is False
    assert "price" not in phone
    from src.member_data import date_of_birth

    authed = explore.post(
        "/api/explore/phone/authenticate",
        json={"member_id": DANA, "date_of_birth": date_of_birth(DANA), "call_id": "call-1"},
    )
    assert authed.status_code == 200, authed.text
    after = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "how much is atorvastatin", "channel": "voice_bot", "call_id": "call-1"},
    ).json()
    assert after["kind"] == "price"
    topics = explore.get("/api/explore/member/topics").json()
    assert topics["ivr_prompts"]["before_amount"]["text"].startswith("Before I give you that amount")
    assert "Press 0" in topics["ivr_prompts"]["advocate"]["text"]
    from src.engine import redact_query

    redacted = redact_query("Dana R. called (617) 555 0199 about the price")
    assert "Dana" not in redacted
    assert "617" not in redacted
    assert "[redacted]" in redacted
    assert "price" in redacted
