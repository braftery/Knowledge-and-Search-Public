"""Author send responses include the routing reason, and Legal can close gap c0."""

COST = "Routed to Legal: mentions cost."
AUTHOR = "Routed to Knowledge Ops approvals: procedure or FAQ with no verbatim or cost wording."
RETURNED = "Routed to Legal: Legal sent it back, so Legal approves the change."
QUOTE = "Routed to Legal: quotes approved verbatim wording from Pricing estimate disclaimer (Legal)."
QUESTION = "whats the rx pricing disclamer i have to read"
PLACEHOLDER = "[approved disclaimer unit ID, e.g., U-RX-EDU-001-09]"
NEUTRAL = "Open the member record and confirm the spelling of the name before the script."


def _gap(client, gap_id: str) -> dict:
    rows = client.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    return next(item for item in rows if item["id"] == gap_id)


def _as(client, role: str):
    opened = client.post("/api/explore/open", json={"role": role})
    assert opened.status_code == 200, opened.text


def _send(client, gap_id: str, text: str, member_text: str = ""):
    _as(client, "Knowledge Ops author")
    edited = client.post(
        f"/api/author/gaps/{gap_id}",
        json={"world": "explore", "text": text, "member_text": member_text},
    )
    assert edited.status_code == 200, edited.text
    sent = client.post(f"/api/author/gaps/{gap_id}/send", json={"world": "explore"})
    assert sent.status_code == 200, sent.text
    return sent.json()


def test_gap_c0_routes_to_legal_and_search_answers(explore):
    gap = _gap(explore, "c0")
    assert PLACEHOLDER in gap["draft_text"]
    assert QUESTION in gap["queries"]
    filled = gap["draft_text"].replace(PLACEHOLDER, "U-RX-EDU-001-09")
    body = _send(explore, "c0", filled)
    assert body["unit_id"] == "U-GAP-c0"
    assert body["queue"] == "Legal"
    assert body["routing_reason"] == QUOTE
    assert body["unit"]["requires_legal"] is True
    assert body["unit"]["routing_reason"] == QUOTE
    assert body["gap"]["status"] == "in_review"
    assert body["gap"]["unit_id"] == "U-GAP-c0"

    legal = explore.get("/api/legal/queue", params={"world": "explore"}).json()
    waiting = next(item for item in legal["waiting"] if item["unit_id"] == "U-GAP-c0")
    assert waiting["routing_reason"] == QUOTE
    assert waiting["requires_legal"] is True
    author_ids = [
        item["unit_id"] for item in explore.get("/api/author/queue", params={"world": "explore"}).json()["waiting"]
    ]
    assert "U-GAP-c0" not in author_ids
    inbox = explore.get("/api/legal/inbox", params={"world": "explore"}).json()
    item = next(row for row in inbox["items"] if row["id"] == "U-GAP-c0")
    assert item["kind"] == "approval"
    assert item["routing_reason"] == QUOTE
    assert item["unit"]["routing_reason"] == QUOTE
    event = explore.get("/api/activity", params={"world": "explore"}).json()["events"][0]
    assert event["role"] == "Knowledge Ops author"
    assert event["message"] == QUOTE

    undone = explore.post("/api/undo", json={"world": "explore"})
    assert undone.status_code == 200, undone.text
    restored = _gap(explore, "c0")
    assert restored["unit_id"] == ""
    assert restored["status"] == "in_review"
    assert restored["draft_text"] == filled
    missing = explore.get("/api/legal/queue", params={"world": "explore"}).json()["waiting"]
    assert all(row["unit_id"] != "U-GAP-c0" for row in missing)

    again = explore.post("/api/author/gaps/c0/send", json={"world": "explore"})
    assert again.status_code == 200, again.text
    assert again.json()["routing_reason"] == QUOTE
    _as(explore, "Legal approver")
    approved = explore.post("/api/legal/approve", json={"world": "explore", "unit_id": "U-GAP-c0"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["message"] == "Approved U-GAP-c0."
    closed = _gap(explore, "c0")
    assert closed["status"] == "closed"
    _as(explore, "Pharmacy advocate")
    answered = explore.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": QUESTION, "record": False, "world": "explore"},
    ).json()["result"]
    assert answered["abstained"] is False
    assert answered["ai_source"] == "closed_gap"
    assert answered["unit"]["unit_id"] == "U-GAP-c0"
    assert "The price I quote is an estimate" in answered["unit"]["text"]


def test_cost_and_whole_words_and_undo(explore):
    cases = [
        ("c9", "The training card shows $35.", COST, "Legal"),
        ("c9", "Ask whether the member already paid the copay at the desk.", COST, "Legal"),
        ("c9", "Ask whether the member already paid the copayment at the desk.", COST, "Legal"),
        ("c9", "The costume for the fair is priceless to the team that made it.", AUTHOR, "Knowledge Ops approvals"),
        ("c1", NEUTRAL, AUTHOR, "Knowledge Ops approvals"),
    ]
    for gap_id, text, reason, queue in cases:
        body = _send(explore, gap_id, text)
        assert body["routing_reason"] == reason, text
        assert body["queue"] == queue
        assert body["unit"]["routing_reason"] == reason
        unit_id = body["unit_id"]
        legal_ids = [
            item["unit_id"] for item in explore.get("/api/legal/queue", params={"world": "explore"}).json()["waiting"]
        ]
        author_ids = [
            item["unit_id"] for item in explore.get("/api/author/queue", params={"world": "explore"}).json()["waiting"]
        ]
        if queue == "Legal":
            assert unit_id in legal_ids
            waiting = next(
                item
                for item in explore.get("/api/legal/queue", params={"world": "explore"}).json()["waiting"]
                if item["unit_id"] == unit_id
            )
            assert waiting["routing_reason"] == reason
        else:
            assert unit_id in author_ids
            waiting = next(
                item
                for item in explore.get("/api/author/queue", params={"world": "explore"}).json()["waiting"]
                if item["unit_id"] == unit_id
            )
            assert waiting["routing_reason"] == reason
        undone = explore.post("/api/undo", json={"world": "explore"})
        assert undone.status_code == 200, undone.text
        restored = _gap(explore, gap_id)
        assert restored["unit_id"] == ""
        assert all(
            item["unit_id"] != unit_id
            for item in explore.get("/api/legal/queue", params={"world": "explore"}).json()["waiting"]
        )
        assert all(
            item["unit_id"] != unit_id
            for item in explore.get("/api/author/queue", params={"world": "explore"}).json()["waiting"]
        )


def test_returned_unit_routing_reason_and_undo(explore):
    _as(explore, "Legal approver")
    declined = explore.post(
        "/api/legal/decline",
        json={"world": "explore", "unit_id": "U-RX-EDU-001-08", "reason": "Needs a plainer line."},
    )
    assert declined.status_code == 200, declined.text
    original = explore.get("/api/units/U-RX-EDU-001-08", params={"world": "explore"}).json()["unit"]["text"]

    _as(explore, "Knowledge Ops author")
    priced = explore.post(
        "/api/author/units/U-RX-EDU-001-08/send",
        json={"world": "explore"},
    )
    assert priced.status_code == 200, priced.text
    assert priced.json()["queue"] == "Legal"
    assert priced.json()["routing_reason"] == COST
    assert priced.json()["unit"]["routing_reason"] == COST
    inbox = explore.get("/api/legal/inbox", params={"world": "explore"}).json()["items"]
    item = next(row for row in inbox if row["id"] == "U-RX-EDU-001-08")
    assert item["routing_reason"] == COST
    undone = explore.post("/api/undo", json={"world": "explore"})
    assert undone.status_code == 200, undone.text
    back = explore.get("/api/author/edits", params={"world": "explore"}).json()["returned"]
    assert any(row["unit_id"] == "U-RX-EDU-001-08" and row["status"] == "returned" for row in back)

    explore.post(
        "/api/author/units/U-RX-EDU-001-08",
        json={"world": "explore", "text": NEUTRAL, "member_text": ""},
    )
    sent = explore.post("/api/author/units/U-RX-EDU-001-08/send", json={"world": "explore"})
    assert sent.status_code == 200, sent.text
    # Legal sent this unit back, so it returns to Legal even with neutral wording.
    assert sent.json()["queue"] == "Legal"
    assert sent.json()["routing_reason"] == RETURNED
    inbox = explore.get("/api/legal/inbox", params={"world": "explore"}).json()["items"]
    waiting = next(row for row in inbox if row["id"] == "U-RX-EDU-001-08")
    assert waiting["routing_reason"] == RETURNED
    undone = explore.post("/api/undo", json={"world": "explore"})
    assert undone.status_code == 200, undone.text
    restored = explore.get("/api/units/U-RX-EDU-001-08", params={"world": "explore"}).json()["unit"]
    assert restored["status"] == "returned"
    assert restored["text"] == NEUTRAL

    copay = "Ask whether the member already paid the copay at the desk."
    explore.post(
        "/api/author/units/U-RX-EDU-001-08",
        json={"world": "explore", "text": copay, "member_text": ""},
    )
    sent = explore.post("/api/author/units/U-RX-EDU-001-08/send", json={"world": "explore"})
    assert sent.status_code == 200, sent.text
    assert sent.json()["routing_reason"] == COST
    assert sent.json()["queue"] == "Legal"
    explore.post("/api/undo", json={"world": "explore"})
    restored = explore.get("/api/units/U-RX-EDU-001-08", params={"world": "explore"}).json()["unit"]
    assert restored["status"] == "returned"
    assert restored["text"] == copay
    assert original.startswith("Before you say any dollar amount")
