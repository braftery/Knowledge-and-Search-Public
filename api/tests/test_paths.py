"""Guided demo paths from DEMO.md, driven only through the API."""


def test_short_path(client):
    demo = client.post("/api/session/jump-short").json()["demo"]
    assert demo["mode"] == "short"
    assert [step["number"] for step in demo["steps"] if step["on_short_path"]] == [0, 1, 3, 4, 5]

    today = client.post("/api/demo/today", json={}).json()["today"]
    assert len(today["cards"]) == 3
    assert today["cards"][0]["text"] != today["cards"][1]["text"]

    extraction = client.post("/api/demo/confirm-tags", json={}).json()["extraction"]
    assert extraction["extracted"] is True
    corrected = next(item for item in extraction["audience_corrections"] if item["unit_id"] == "U-RX-EDU-001-09")
    assert corrected["ai_audience"] == "member"
    assert corrected["audience"] == "advocate"

    waiting = client.get("/api/legal/queue").json()["waiting"]
    assert [item["unit_id"] for item in waiting] == ["U-RX-EDU-001-09", "U-RX-EDU-001-07", "U-BEN-COST-001-02"]
    for item in waiting:
        assert client.post("/api/legal/approve", json={"unit_id": item["unit_id"]}).status_code == 200
    assert client.get("/api/legal/queue").json()["count"] == 0

    both = client.post(
        "/api/search/both",
        json={"query": "what do I say before I quote a cost", "record": True},
    ).json()["results"]
    assert both[0]["unit"]["unit_id"] != both[1]["unit"]["unit_id"]
    assert both[0]["searched"] == ["pharmacy", "shared-legal"]
    assert both[1]["searched"] == ["benefits", "shared-legal"]

    abstain = client.post(
        "/api/search/both",
        json={"query": "how long does a part d prior auth take", "record": True},
    ).json()["results"]
    assert all(item["abstained"] for item in abstain)

    pharmacy = client.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": "do specialty drugs stay at the specialty pharmacy", "record": False},
    ).json()["result"]
    insurance = client.post(
        "/api/search",
        json={"role": "Insurance advocate", "query": "do specialty drugs stay at the specialty pharmacy", "record": False},
    ).json()["result"]
    assert pharmacy["abstained"] is False
    assert insurance["abstained"] is True

    before = client.get("/api/channels").json()["live"]
    published = client.post("/api/channels/publish", json={}).json()["channels"]
    assert published["live"]["version"] == before["version"] + 1
    assert published["live"]["text"] != before["text"]
    assert published["previous"]["status"] == "superseded"
    history = client.get(f"/api/units/{published['live']['unit_id']}/versions").json()["versions"]
    assert history[0]["version"] == 1
    assert history[1]["status"] == "approved"

    done = {step["number"]: step["done"] for step in client.get("/api/demo").json()["steps"]}
    assert done[0] and done[1] and done[3] and done[4] and done[5]


def test_full_path(client):
    client.post("/api/session/reset", json={"mode": "start"})
    client.post("/api/demo/today", json={})
    client.post("/api/demo/extract", json={})
    client.post("/api/demo/confirm-tags", json={})
    client.post("/api/demo/keep-canonical", json={})
    client.post("/api/demo/escalate", json={})

    first = client.get("/api/legal/queue").json()["waiting"][0]
    assert client.post("/api/legal/approve", json={"unit_id": first["unit_id"]}).status_code == 200
    assert "Demo shortcut" in client.post("/api/legal/approve-all", json={}).json()["message"]
    assert client.post("/api/author/approve-all", json={}).status_code == 200
    plan = next(item for item in client.get("/api/conflicts").json()["plans"] if item["resolve_in_demo"])
    resolved = client.post(
        "/api/conflicts/resolve",
        json={"conflict_id": plan["id"], "reason": plan["reason_suggestion"]},
    ).json()
    assert resolved["message"].startswith("Kept ")

    both = client.post(
        "/api/search/both",
        json={"query": "what do I say before I quote a cost", "record": True},
    ).json()["results"]
    assert both[0]["abstained"] is False and both[1]["abstained"] is False
    assert both[0]["unit"]["unit_id"] != both[1]["unit"]["unit_id"]

    assert client.post("/api/channels/publish", json={}).json()["channels"]["live"]["version"] == 2

    gap = next(item for item in client.get("/api/gaps").json()["gaps"] if item["draft_text"] and item["status"] == "proposed")
    before = [item["id"] for item in client.get("/api/author/edits").json()["gaps"]]
    assert gap["id"] not in before
    acted = client.post(
        f"/api/gaps/{gap['id']}",
        json={"action": "write", "reason": f"Asked {gap['search_count']} times with no approved answer."},
    ).json()
    assert next(item for item in acted["gaps"]["gaps"] if item["id"] == gap["id"])["status"] == "in_review"
    after = [item["id"] for item in client.get("/api/author/edits").json()["gaps"]]
    assert gap["id"] in after

    cosmetic = client.post("/api/drift", json={"kind": "cosmetic"}).json()["drift"]
    assert cosmetic["cosmetic"] is True and cosmetic["stale"] is False
    material = client.post("/api/drift", json={"kind": "material"}).json()["drift"]
    assert material["material"] is True and material["stale"] is True
    sent = client.post("/api/drift/send", json={}).json()["drift"]
    assert sent["sent"] is True

    quality = client.post("/api/quality/score", json={}).json()["quality"]
    held = quality["golden_table"]["held_out"]
    assert sum(1 for row in held if row["Result"] == "Fail") == 1
    assert quality["golden_table"]["rows"]

    done = {step["number"]: step["done"] for step in client.get("/api/demo").json()["steps"]}
    assert all(done[number] for number in range(9))


def test_feedback_loop(client):
    client.post("/api/explore/open", json={"role": "Pharmacy advocate"})
    asked = client.post(
        "/api/explore/desk",
        json={
            "role": "Pharmacy advocate",
            "query": "what do I say before I quote a cost",
            "call_reason": "Drug price question",
        },
    ).json()
    unit_id = asked["result"]["unit"]["unit_id"]
    flagged = client.post(
        "/api/feedback",
        json={
            "world": "explore",
            "source": "advocate",
            "role": "Pharmacy advocate",
            "kind": "couldnt_find",
            "question": "member id H12345678 what do I say before I quote a cost",
            "unit_id": unit_id,
            "note": "phone 415-555-0199",
        },
    ).json()["feedback"]
    assert "H12345678" not in flagged["question"]
    assert "415-555-0199" not in flagged["note"]
    assert flagged["route"] == "author"

    client.post("/api/explore/open", json={"role": "Member"})
    reply = client.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "Is the price I see a guarantee?"},
    ).json()
    assert reply["kind"] == "clarify"
    assert reply["feedback_recorded"] == "clarified"
    assert reply["suggestions"]
    assert "U-" not in reply["reply"]
    client.post(
        "/api/explore/member/helped",
        json={"helped": False, "question": "Is the price I see a guarantee?", "unit_id": ""},
    )

    client.post("/api/explore/open", json={"role": "Knowledge Ops author"})
    open_items = client.get("/api/feedback/open?route=author&world=explore").json()["items"]
    match = next(item for item in open_items if item["kind"] == "couldnt_find" and "[redacted]" in item["question"])
    resolved = client.post(
        f"/api/feedback/{match['id']}/resolve",
        json={"world": "explore", "resolution": "Rewrote the member wording and sent it to Legal."},
    ).json()["feedback"]
    assert resolved["status"] == "resolved"

    client.post("/api/explore/open", json={"role": "Channel and AI team"})
    product = client.get("/api/feedback/product?world=explore").json()
    kinds = {group["kind"] for group in product["groups"]}
    assert "clarified" in kinds

    client.post("/api/explore/open", json={"role": "Knowledge owner"})
    summary = client.get("/api/feedback/summary?world=explore").json()
    assert any(item["count"] >= 1 for item in summary["by_kind"])


def test_undo_after_reset(client):
    client.post("/api/session/jump-short")
    client.post("/api/demo/today", json={})
    client.post("/api/session/reset", json={"mode": "start"})
    assert client.get("/api/demo").json()["mode"] == "start"
    assert client.get("/api/demo/today").json()["ran"] is False
    undone = client.post("/api/undo", json={"world": "guided"}).json()
    assert undone["demo"]["mode"] == "short"
    assert client.get("/api/demo/today").json()["ran"] is True
