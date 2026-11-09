"""Call wrap-ups and change acknowledgements on the Explore database."""

PRICING = "U-RX-EDU-001-09"


def _wrap(client, **overrides):
    body = {
        "world": "explore",
        "role": "Pharmacy advocate",
        "call_id": "drug-price",
        "call_reason": "Drug price question",
        "unit_ids": [PRICING],
        "read_verbatim": True,
        "outcome": "resolved",
        "note": "",
    }
    body.update(overrides)
    return client.post("/api/explore/wrapup", json=body)


def test_wrapup_validation(explore):
    role = _wrap(explore, role="Legal approver")
    assert role.status_code == 400
    assert role.json()["error"] == "Only an advocate can wrap up a call."

    outcome = _wrap(explore, outcome="closed")
    assert outcome.status_code == 400
    assert outcome.json()["error"] == "Choose how the call ended."

    missing_flag = _wrap(explore, read_verbatim=None)
    assert missing_flag.status_code == 400
    assert missing_flag.json()["error"] == "Confirm whether you read the approved wording word for word."

    blank_note = _wrap(explore, unit_ids=[], read_verbatim=None, outcome="follow_up", note="   ")
    assert blank_note.status_code == 400
    assert blank_note.json()["error"] == "Add a note so the follow-up has what it needs."

    unknown = _wrap(explore, unit_ids=["U-NO-SUCH"], read_verbatim=None, outcome="resolved")
    assert unknown.status_code == 200, unknown.text
    assert unknown.json()["wrapup"]["unit_ids"] == []


def test_wrapup_is_listed_and_undo_removes_it(explore):
    saved = _wrap(explore)
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["message"] == "Wrap-up saved."
    assert body["undo"]["available"] is True
    assert body["undo"]["world"] == "explore"
    wrapup = body["wrapup"]
    assert wrapup["id"] == "W-1"
    assert wrapup["role"] == "Pharmacy advocate"
    assert wrapup["call_id"] == "drug-price"
    assert wrapup["unit_ids"] == [PRICING]
    assert wrapup["read_verbatim"] is True
    assert wrapup["outcome"] == "resolved"
    assert wrapup["created_at"]
    summary = body["summary"]
    assert summary == {"count": 1, "verbatim_required": 1, "verbatim_confirmed": 1, "follow_ups": 0}

    listed = explore.get("/api/explore/wrapups", params={"world": "explore"}).json()
    assert listed["summary"] == summary
    assert listed["items"][0]["id"] == "W-1"

    insights = explore.get("/api/explore/insights").json()
    assert insights["wrapups"] == summary

    activity = explore.get("/api/activity", params={"world": "explore", "limit": 20}).json()
    messages = [event["message"] for event in activity["events"]]
    assert (
        "Pharmacy advocate wrapped up a call about Drug price question. "
        "Read the approved wording word for word: yes."
    ) in messages

    undone = explore.post("/api/undo", json={"world": "explore"})
    assert undone.status_code == 200, undone.text
    after = explore.get("/api/explore/wrapups").json()
    assert after["summary"]["count"] == 0
    assert after["items"] == []
    assert explore.get("/api/explore/insights").json()["wrapups"]["count"] == 0


def test_follow_up_note_and_redaction(explore):
    saved = _wrap(
        explore,
        outcome="follow_up",
        note="member id H12345678 please call back",
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["wrapup"]["note"] == "[redacted] please call back"
    assert "H12345678" not in body["wrapup"]["note"]
    assert body["summary"]["follow_ups"] == 1
    activity = explore.get("/api/activity", params={"world": "explore", "limit": 20}).json()
    line = next(event["message"] for event in activity["events"] if "wrapped up" in event["message"])
    assert line.endswith("Follow-up needed.")
    assert "H12345678" not in line
    assert event_role(activity, line) == "Pharmacy advocate"


def event_role(activity, message):
    for event in activity["events"]:
        if event["message"] == message:
            return event["role"]
    return ""


def test_false_read_aloud_says_no(explore):
    saved = _wrap(explore, read_verbatim=False)
    assert saved.status_code == 200, saved.text
    assert saved.json()["wrapup"]["read_verbatim"] is False
    assert saved.json()["summary"]["verbatim_required"] == 1
    assert saved.json()["summary"]["verbatim_confirmed"] == 0
    activity = explore.get("/api/activity", params={"world": "explore", "limit": 10}).json()
    line = next(event["message"] for event in activity["events"] if "wrapped up" in event["message"])
    assert "Read the approved wording word for word: no." in line


def test_change_acknowledgement(explore):
    explore.post("/api/explore/open", json={"role": "Legal approver"})
    published = explore.post("/api/channels/publish", json={"world": "explore"})
    assert published.status_code == 200, published.text

    explore.post("/api/explore/open", json={"role": "Pharmacy advocate"})
    pharmacy = explore.get(
        "/api/explore/changes",
        params={"world": "explore", "role": "Pharmacy advocate"},
    ).json()
    assert pharmacy["pending"] == 1
    change = pharmacy["changes"][0]
    assert change["unit_id"] == PRICING
    assert change["version"] == 2
    assert change["previous_version"] == 1
    assert change["title"] == "Pricing estimate disclaimer"
    assert change["acknowledged"] is False
    assert change["approved_on"]
    assert change["approved_by"] == "Legal approver"
    assert any(part["kind"] in {"equal", "remove", "add"} for part in change["diff"])

    explore.post("/api/explore/open", json={"role": "Insurance advocate"})
    insurance = explore.get(
        "/api/explore/changes",
        params={"world": "explore", "role": "Insurance advocate"},
    ).json()
    assert PRICING not in [item["unit_id"] for item in insurance["changes"]]

    unknown = explore.get("/api/explore/changes", params={"role": "Not a role"})
    assert unknown.status_code == 400
    assert unknown.json()["error"] == "Unknown role."

    denied = explore.post(
        "/api/explore/changes/acknowledge",
        json={"world": "explore", "role": "Legal approver", "unit_id": PRICING, "version": 2},
    )
    assert denied.status_code == 400
    assert denied.json()["error"] == "Only an advocate can acknowledge a change."

    missing = explore.post(
        "/api/explore/changes/acknowledge",
        json={"world": "explore", "role": "Pharmacy advocate", "unit_id": PRICING, "version": 9},
    )
    assert missing.status_code == 404
    assert missing.json()["error"] == "That unit version does not exist."

    explore.post("/api/explore/open", json={"role": "Pharmacy advocate"})
    first = explore.post(
        "/api/explore/changes/acknowledge",
        json={"world": "explore", "role": "Pharmacy advocate", "unit_id": PRICING, "version": 2},
    )
    assert first.status_code == 200, first.text
    assert first.json()["message"] == "Acknowledged version 2 of Pricing estimate disclaimer."
    assert first.json()["undo"]["available"] is True
    assert first.json()["changes"]["pending"] == 0
    assert first.json()["changes"]["changes"][0]["acknowledged"] is True

    second = explore.post(
        "/api/explore/changes/acknowledge",
        json={"world": "explore", "role": "Pharmacy advocate", "unit_id": PRICING, "version": 2},
    )
    assert second.status_code == 200, second.text
    assert second.json()["message"] == first.json()["message"]

    activity = explore.get("/api/activity", params={"world": "explore", "limit": 40}).json()
    lines = [
        event["message"]
        for event in activity["events"]
        if event["message"] == "Pharmacy advocate acknowledged version 2 of Pricing estimate disclaimer."
    ]
    assert lines == ["Pharmacy advocate acknowledged version 2 of Pricing estimate disclaimer."]

    insights = explore.get("/api/explore/insights").json()
    item = next(row for row in insights["acknowledgements"] if row["unit_id"] == PRICING)
    assert item["version"] == 2
    assert item["acknowledged_by"] == ["Pharmacy advocate"]
    assert "Insurance advocate" not in item["pending"]
    assert "Insurance advocate" not in item["acknowledged_by"]


def test_null_read_aloud_omits_the_sentence(explore):
    saved = _wrap(explore, unit_ids=[], read_verbatim=None, outcome="transferred")
    assert saved.status_code == 200, saved.text
    assert saved.json()["wrapup"]["read_verbatim"] is None
    assert saved.json()["summary"]["verbatim_required"] == 0
    activity = explore.get("/api/activity", params={"world": "explore", "limit": 10}).json()
    line = next(event["message"] for event in activity["events"] if "wrapped up" in event["message"])
    assert line == "Pharmacy advocate wrapped up a call about Drug price question."
