"""Authoring, drift approval, live gap drafts, and the pricing unit's channels."""

import src.ai as ai

PRIOR_AUTH = "how long does a part d prior auth take"
NOVEL = "what time does the clinic mailbox get painted"
EMAIL_Q = "email pat@example.com what time does the clinic mailbox get painted"
FAQ_TEXT = (
    "A standard Part D prior authorization decision is made within 7 calendar days "
    "after Harbor Health receives a complete request. An expedited request is decided within 72 hours."
)
FAQ_MEMBER = (
    "A standard prior authorization decision takes 7 calendar days. An expedited request takes 72 hours."
)
CLEAN = "Paint visits happen during weekday hours. The illustrative count is not a promise."
CLEAN_MEMBER = "Mailbox paint visits happen on weekdays."
PRICING = "U-RX-EDU-001-09"
FOUR = ["advocate_guidance", "member_chat", "voice_bot", "website"]
DRAFT = {
    "title": "Clinic mailbox paint visits",
    "type": "faq",
    "draft_text": "Paint visits happen during [clinic hours]. The illustrative count is 1000001.",
    "placeholders": ["[clinic hours]"],
    "author_checklist": ["Replace the clinic hours placeholder."],
    "suggested_kb": "pharmacy",
}


def _mock_draft(monkeypatch):
    def fake(task, user_content, input_ref=""):
        if task == "assess_sufficiency":
            return {"answer_unit_id": None, "reason": "No approved unit covers this question."}, {}
        if task == "draft_gap_unit":
            return DRAFT, {}
        raise AssertionError(task)

    monkeypatch.setattr(ai, "call_model", fake)


def _prior_auth(client):
    gaps = client.get("/api/gaps").json()["gaps"]
    return next(item for item in gaps if PRIOR_AUTH in item["queries"])


def _prepare_drift(client):
    created = client.post("/api/session/reset", json={"mode": "jump"})
    assert created.status_code == 200, created.text
    material = client.post("/api/drift", json={"kind": "material"})
    assert material.status_code == 200, material.text
    sent = client.post("/api/drift/send", json={})
    assert sent.status_code == 200, sent.text


def test_author_edits_lists_open_drafts(short):
    waiting = short.get("/api/author/edits").json()
    assert waiting["illustrative"] is True
    assert waiting["returned"] == []
    prior = _prior_auth(short)
    assert prior["status"] == "proposed"
    assert prior["id"] not in [item["id"] for item in waiting["gaps"]]
    guided_c0 = next(item for item in short.get("/api/gaps").json()["gaps"] if item["id"] == "c0")
    assert guided_c0["status"] == "proposed"
    assert guided_c0["id"] not in [item["id"] for item in waiting["gaps"]]
    sent = short.post(
        f"/api/gaps/{prior['id']}",
        json={"action": "write", "reason": "Asked with no approved answer."},
    )
    assert sent.status_code == 200, sent.text
    body = short.get("/api/author/edits").json()
    gap = next(item for item in body["gaps"] if PRIOR_AUTH in item["queries"])
    assert gap["status"] == "in_review"
    assert gap["unit_id"] == ""
    assert gap["can_send"] is False
    assert gap["open_placeholders"]
    assert "[standard decision timeframe]" in gap["placeholders"]
    assert "U-RX-EDU-001-09" not in [item.get("unit_id") for item in body["gaps"]]


def test_explore_seeds_c0_for_the_author(explore):
    edits = explore.get("/api/author/edits", params={"world": "explore"}).json()
    gap = next(item for item in edits["gaps"] if item["id"] == "c0")
    assert gap["cluster"] == "Rx pricing disclaimer to read"
    assert gap["status"] == "in_review"
    assert gap["unit_id"] == ""
    assert gap["reason"] == "Asked with no approved answer; sent to the author."
    explore.post("/api/explore/open", json={"role": "Knowledge Ops author"})
    work = explore.get("/api/explore/my-work").json()
    assert any(item["id"] == "gap-c0" for item in work["items"])
    assert any(item["group"] == "Unanswered questions" and item["id"] == "gap-c0" for item in work["items"])


def test_edit_gap_draft(short):
    gap = _prior_auth(short)
    original = gap["draft_text"]
    empty = short.post(f"/api/author/gaps/{gap['id']}", json={"text": "  ", "member_text": ""})
    assert empty.status_code == 400
    assert empty.json()["error"] == "Write the unit text before saving this draft."
    missing = short.post("/api/author/gaps/missing-cluster", json={"text": FAQ_TEXT})
    assert missing.status_code == 400
    assert missing.json()["error"] == "That cluster is not in the queue."
    saved = short.post(
        f"/api/author/gaps/{gap['id']}",
        json={"text": FAQ_TEXT, "member_text": FAQ_MEMBER},
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["ok"] is True
    assert body["gap"]["draft_text"] == FAQ_TEXT
    assert body["gap"]["draft_member_text"] == FAQ_MEMBER
    assert body["gap"]["placeholders"] == []
    assert body["undo"]["available"] is True
    assert body["undo"]["world"] == "guided"
    event = short.get("/api/activity").json()["events"][0]
    assert event["role"] == "Knowledge Ops author"
    assert event["message"].startswith("Edited the")
    undone = short.post("/api/undo", json={})
    assert undone.status_code == 200
    restored = _prior_auth(short)
    assert restored["draft_text"] == original


def test_send_gap_blocks_open_placeholders(short):
    gap = _prior_auth(short)
    blocked = short.post(f"/api/author/gaps/{gap['id']}/send", json={})
    assert blocked.status_code == 400
    error = blocked.json()["error"]
    assert error.startswith("Replace every bracketed placeholder before sending this to approval.")
    assert "Still open:" in error
    assert "[standard decision timeframe]" in error
    assert _prior_auth(short)["draft_text"] == gap["draft_text"]
    assert _prior_auth(short)["status"] == "proposed"
    unknown = short.post("/api/author/gaps/missing-cluster/send", json={})
    assert unknown.status_code == 400
    assert unknown.json()["error"] == "That cluster is not in the queue."


def test_edit_returned_unit(explore):
    explore.post("/api/explore/open", json={"role": "Legal approver"})
    waiting = explore.get("/api/legal/queue?world=explore").json()["waiting"]
    unit_id = waiting[0]["unit_id"]
    declined = explore.post(
        "/api/legal/decline",
        json={"world": "explore", "unit_id": unit_id, "reason": "Needs a plain example."},
    )
    assert declined.status_code == 200
    edits = explore.get("/api/author/edits?world=explore").json()
    returned = next(item for item in edits["returned"] if item["unit_id"] == unit_id)
    assert returned["status"] == "returned"
    assert "plain example" in returned["notes"]
    explore.post("/api/explore/open", json={"role": "Knowledge Ops author"})
    approved = explore.post(
        "/api/author/units/U-RX-EDU-001-09",
        json={"world": "explore", "text": "Do not edit the live disclaimer."},
    )
    assert approved.status_code == 400
    assert "approved unit cannot be edited" in approved.json()["error"]
    saved = explore.post(
        f"/api/author/units/{unit_id}",
        json={
            "world": "explore",
            "text": "Read this [plain example] to the member.",
            "member_text": "Member [plain example].",
        },
    )
    assert saved.status_code == 200, saved.text
    assert "[plain example]" in saved.json()["unit"]["text"]
    event = explore.get("/api/activity?world=explore").json()["events"][0]
    assert event["role"] == "Knowledge Ops author"
    assert unit_id in event["message"]


def test_send_returned_unit(explore):
    explore.post("/api/explore/open", json={"role": "Legal approver"})
    waiting = explore.get("/api/legal/queue?world=explore").json()["waiting"]
    unit_id = waiting[0]["unit_id"]
    original = explore.get(f"/api/units/{unit_id}?world=explore").json()["unit"]["text"]
    explore.post(
        "/api/legal/decline",
        json={"world": "explore", "unit_id": unit_id, "reason": "Needs a plain example."},
    )
    explore.post("/api/explore/open", json={"role": "Knowledge Ops author"})
    explore.post(
        f"/api/author/units/{unit_id}",
        json={
            "world": "explore",
            "text": "Read this [plain example] to the member.",
            "member_text": "Member [plain example].",
        },
    )
    blocked = explore.post(f"/api/author/units/{unit_id}/send", json={"world": "explore"})
    assert blocked.status_code == 400
    assert "[plain example]" in blocked.json()["error"]
    assert blocked.json()["error"].startswith("Replace every bracketed placeholder")
    clean = original + " Here is the plain example the author added."
    explore.post(
        f"/api/author/units/{unit_id}",
        json={"world": "explore", "text": clean, "member_text": "Here is the plain example for a member."},
    )
    sent = explore.post(f"/api/author/units/{unit_id}/send", json={"world": "explore"})
    assert sent.status_code == 200, sent.text
    body = sent.json()
    assert body["unit_id"] == unit_id
    assert body["queue"] == "Legal"
    assert body["unit"]["status"] == "proposed"
    legal = [item["unit_id"] for item in explore.get("/api/legal/queue?world=explore").json()["waiting"]]
    assert unit_id in legal
    edits = explore.get("/api/author/edits?world=explore").json()
    assert unit_id not in [item["unit_id"] for item in edits["returned"]]


def test_legal_drift_items(client):
    empty = client.post("/api/session/reset", json={"mode": "jump"})
    assert empty.status_code == 200
    before = client.get("/api/legal/drift").json()
    assert before["count"] == 0
    assert before["items"] == []
    assert before["message"] == "No drift fix is waiting for Legal."
    queue_before = client.get("/api/legal/queue").json()["count"]
    _prepare_drift(client)
    body = client.get("/api/legal/drift").json()
    assert body["count"] == 1
    item = body["items"][0]
    assert item["unit_id"] == PRICING
    assert "31-day" in item["new_wording"]
    assert "31-day" not in item["old_wording"]
    assert item["source_before"] == "30-day supply"
    assert item["source_after"] == "31-day supply"
    assert "30-day supply" in item["member_text"]
    assert client.get("/api/legal/queue").json()["count"] == queue_before


def test_approve_drift_fix(client):
    created = client.post("/api/session/reset", json={"mode": "jump"})
    assert created.status_code == 200
    refused = client.post("/api/legal/drift/approve", json={})
    assert refused.status_code == 400
    assert refused.json()["error"] == "No drift fix is waiting for Legal."
    _prepare_drift(client)
    before = client.get("/api/channels").json()["live"]
    approved = client.post("/api/legal/drift/approve", json={})
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["unit_id"] == PRICING
    assert body["version"] == before["version"] + 1
    assert body["drift"]["count"] == 0
    assert "31-day" in body["unit"]["text"]
    assert body["unit"]["channels"] == FOUR
    assert body["unit"]["stale"] is False
    event = client.get("/api/activity").json()["events"][0]
    assert event["role"] == "Legal approver"
    assert "Every channel now shows" in event["message"]
    again = client.post("/api/legal/drift/approve", json={})
    assert again.status_code == 400
    assert again.json()["error"] == "No drift fix is waiting for Legal."


def test_return_drift_fix(client):
    _prepare_drift(client)
    blank = client.post("/api/legal/drift/return", json={"reason": "  "})
    assert blank.status_code == 400
    assert blank.json()["error"] == "A reason is required."
    assert client.get("/api/legal/drift").json()["count"] == 1
    reason = "The 30-day supply is still the signed wording."
    returned = client.post("/api/legal/drift/return", json={"reason": reason})
    assert returned.status_code == 200, returned.text
    body = returned.json()
    assert body["unit_id"] == PRICING
    assert body["stale"] is True
    assert body["drift"]["count"] == 0
    live = client.get("/api/channels").json()["live"]
    assert live["version"] == 1
    assert live["stale"] is True
    assert "31-day" not in live["text"]
    event = client.get("/api/activity").json()["events"][0]
    assert event["role"] == "Legal approver"
    assert reason in event["message"]


def test_resolve_returned_drift(client):
    _prepare_drift(client)
    client.post(
        "/api/legal/drift/return",
        json={"reason": "The 30-day supply is still the signed wording."},
    )
    blank = client.post("/api/author/drift/resolve", json={"note": "  "})
    assert blank.status_code == 400
    assert blank.json()["error"] == "A note is required."
    assert client.get("/api/channels").json()["live"]["stale"] is True
    note = "Keep the signed 30-day wording."
    resolved = client.post("/api/author/drift/resolve", json={"note": note})
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["unit_id"] == PRICING
    assert body["stale"] is False
    assert body["unit"]["text"]
    assert "31-day" not in body["unit"]["text"]
    assert client.get("/api/channels").json()["live"]["stale"] is False
    event = client.get("/api/activity").json()["events"][0]
    assert event["role"] == "Knowledge Ops author"
    assert note in event["message"]
    gone = client.post("/api/author/drift/resolve", json={"note": note})
    assert gone.status_code == 400
    assert gone.json()["error"] == "No drift fix is waiting for the author."


def test_gaps_surface_live_clusters(client, monkeypatch):
    _mock_draft(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    client.post("/api/session/reset", json={"mode": "jump"})
    cached = client.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": NOVEL, "record": True},
    ).json()
    assert cached["result"]["abstained"] is True
    cached_gaps = client.get("/api/gaps").json()["gaps"]
    assert not any(item["live"] for item in cached_gaps)
    unclustered = next(item for item in cached_gaps if item["id"] == "new-unclustered")
    assert unclustered["cluster"] == "New, not yet clustered"
    assert NOVEL in unclustered["queries"]

    client.post("/api/settings/live", json={"enabled": True})
    found = client.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": EMAIL_Q, "record": True},
    )
    assert found.status_code == 200, found.text
    assert found.json()["result"]["abstained"] is True
    gaps = client.get("/api/gaps").json()["gaps"]
    live = next(item for item in gaps if item["live"])
    assert live["id"].startswith("live-")
    assert live["status"] == "proposed"
    assert "pat@example.com" not in live["cluster"]
    assert "pat@example.com" not in " ".join(live["queries"])
    assert "[redacted]" in live["cluster"]
    assert "[clinic hours]" in live["placeholders"]
    assert live["invented_figures"] == ["1000001"]
    assert live["has_invented_figures"] is True
    assert live["draft_type"] == "faq"
    other = next(item for item in gaps if item["id"] != live["id"] and item["status"] == "proposed")
    acted = client.post(
        f"/api/gaps/{other['id']}",
        json={"action": "dismiss", "reason": "Leave the live draft on the list."},
    )
    assert acted.status_code == 200, acted.text
    echoed = next(item for item in acted.json()["gaps"]["gaps"] if item["id"] == live["id"])
    assert echoed["live"] is True
    assert "[clinic hours]" in echoed["placeholders"]
    assert echoed["has_invented_figures"] is True


def test_pricing_channels_on_portal_and_channels(client):
    client.post("/api/explore/open", json={"role": "Channel and AI team"})
    portal = client.get(f"/api/portal/units/{PRICING}").json()["unit"]
    assert portal["channels"] == FOUR
    sample = client.get("/api/portal/quick-start").json()["sample_unit"]
    assert sample["unit_id"] == PRICING
    assert sample["channels"] == FOUR
    listed = client.get("/api/portal/units", params={"channel": "voice_bot"}).json()["units"]
    match = next(item for item in listed if item["unit_id"] == PRICING)
    assert match["channels"] == FOUR
    assert match["channel"] == "voice_bot"
    assert match["text"] == match["member_text"]
    explore_channels = client.get("/api/channels", params={"world": "explore"}).json()
    assert explore_channels["live"]["unit_id"] == PRICING
    assert explore_channels["live"]["channels"] == FOUR

    client.post("/api/session/reset", json={"mode": "jump"})
    assert client.get("/api/channels").json()["live"]["channels"] == FOUR

    client.post("/api/session/jump-short")
    client.post("/api/demo/confirm-tags", json={})
    approved = client.post("/api/legal/approve", json={"unit_id": PRICING})
    assert approved.status_code == 200, approved.text
    short_channels = client.get("/api/channels").json()["live"]
    assert short_channels["channels"] == FOUR
    guided_portal = client.get(f"/api/portal/units/{PRICING}", params={"world": "guided", "channel": "voice_bot"}).json()
    assert guided_portal["unit"]["channels"] == FOUR


def test_authoring_loop(short):
    gap = _prior_auth(short)
    abstained = short.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": PRIOR_AUTH, "record": True},
    ).json()
    assert abstained["result"]["abstained"] is True
    drafted = _prior_auth(short)
    assert drafted["draft_text"]
    assert drafted["placeholders"]
    assert drafted["search_count"] == gap["search_count"] + 1

    written = short.post(
        f"/api/gaps/{gap['id']}",
        json={"action": "write", "reason": "Asked with no approved answer."},
    )
    assert written.status_code == 200, written.text
    edited = short.post(
        f"/api/author/gaps/{gap['id']}",
        json={"text": FAQ_TEXT, "member_text": FAQ_MEMBER},
    )
    assert edited.status_code == 200, edited.text
    match = next(item for item in edited.json()["edits"]["gaps"] if item["id"] == gap["id"])
    assert match["status"] == "in_review"
    assert match["can_send"] is True

    sent = short.post(f"/api/author/gaps/{gap['id']}/send", json={})
    assert sent.status_code == 200, sent.text
    unit_id = f"U-GAP-{gap['id']}"
    assert sent.json()["unit_id"] == unit_id
    assert sent.json()["queue"] == "Knowledge Ops approvals"
    assert sent.json()["gap"]["status"] == "in_review"
    assert sent.json()["gap"]["unit_id"] == unit_id
    author_ids = [item["unit_id"] for item in short.get("/api/author/queue").json()["waiting"]]
    legal_ids = [item["unit_id"] for item in short.get("/api/legal/queue").json()["waiting"]]
    assert unit_id in author_ids
    assert unit_id not in legal_ids
    still = short.post(f"/api/author/gaps/{gap['id']}", json={"text": FAQ_TEXT, "member_text": FAQ_MEMBER})
    assert still.status_code == 400
    assert still.json()["error"] == "This draft was already sent to approval."

    approved = short.post("/api/author/approve", json={"unit_id": unit_id})
    assert approved.status_code == 200, approved.text
    assert approved.json()["message"] == f"Approved {unit_id}."
    closed = next(item for item in short.get("/api/gaps").json()["gaps"] if item["id"] == gap["id"])
    assert closed["status"] == "closed"

    answered = short.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": PRIOR_AUTH, "record": True},
    ).json()["result"]
    assert answered["abstained"] is False
    assert answered["unit"]["unit_id"] == unit_id
    assert answered["unit"]["text"] == FAQ_TEXT
    assert answered["ai_source"] == "closed_gap"
    member = short.get(
        "/api/portal/answers",
        params={"world": "guided", "role": "Member", "member_id": "HBR-20418", "question": PRIOR_AUTH},
    ).json()
    assert member["kind"] == "out_of_scope"
    assert member["text"].startswith("I can help with your Harbor plan")
    assert member["illustrative"] is True
    assert "price" not in member
    assert "unit_id" not in member
    insurance = short.post(
        "/api/search",
        json={"role": "Insurance advocate", "query": PRIOR_AUTH, "record": False},
    ).json()["result"]
    if not insurance["abstained"]:
        assert insurance["unit"]["unit_id"] != unit_id


def test_drift_loop(client):
    client.post("/api/session/reset", json={"mode": "jump"})
    client.post("/api/demo/confirm-tags", json={})
    before = client.get("/api/channels").json()["live"]
    assert before["channels"] == FOUR
    assert before["stale"] is False
    queue_before = client.get("/api/legal/queue").json()["count"]

    material = client.post("/api/drift", json={"kind": "material"})
    assert material.status_code == 200, material.text
    assert material.json()["drift"]["stale"] is True
    assert client.get("/api/legal/drift").json()["count"] == 0

    sent = client.post("/api/drift/send", json={})
    assert sent.status_code == 200, sent.text
    assert sent.json()["drift"]["sent"] is True
    waiting = client.get("/api/legal/drift").json()
    assert waiting["count"] == 1
    assert waiting["items"][0]["unit_id"] == before["unit_id"]
    assert client.get("/api/legal/queue").json()["count"] == queue_before
    assert client.get("/api/channels").json()["live"]["version"] == before["version"]
    assert "31-day" not in client.get("/api/channels").json()["live"]["text"]

    approved = client.post("/api/legal/drift/approve", json={})
    assert approved.status_code == 200, approved.text
    live = client.get("/api/channels").json()["live"]
    assert live["version"] == before["version"] + 1
    assert live["stale"] is False
    assert "31-day" in live["text"]
    assert "31-day" in live["member_text"]
    assert live["channels"] == FOUR
    previous = client.get("/api/channels").json()["previous"]
    assert previous["version"] == before["version"]
    assert previous["status"] == "superseded"
    assert client.get("/api/legal/drift").json()["count"] == 0
    assert client.get(f"/api/portal/units/{PRICING}", params={"world": "guided"}).json()["unit"]["channels"] == FOUR
