"""One test per endpoint, against the real engine and saved model answers."""

from api.tests.conftest import session_dir


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["illustrative"] is True


def test_session(client):
    body = client.get("/api/session").json()
    assert body["guided"]["mode"] == "start"
    assert body["guided"]["step"] == 0
    assert body["explore"]["ready"] is False
    assert "harbor_session" in client.cookies


def test_session_reset(client):
    client.post("/api/session/jump-short")
    body = client.post("/api/session/reset", json={"mode": "start"}).json()
    assert body["demo"]["mode"] == "start"
    assert body["undo"]["available"] is True


def test_jump_short(client):
    body = client.post("/api/session/jump-short").json()
    assert body["demo"]["mode"] == "short"
    assert body["demo"]["short_path"] is True


def test_demo_get(short):
    body = short.get("/api/demo").json()
    assert body["step_name"] == "Today's problem"
    assert len(body["steps"]) == 9


def test_demo_step(short):
    body = short.post("/api/demo/step", json={"step": 4}).json()
    assert body["demo"]["step"] == 4
    assert body["undo"]["available"] is False


def test_settings_live(short):
    body = short.post("/api/settings/live", json={"enabled": True}).json()
    assert body["live_ai"] is True
    demo = short.get("/api/demo").json()
    assert demo["live_ai"] is True


def test_today_get_before_run(started):
    body = started.get("/api/demo/today").json()
    assert body["ran"] is False
    assert body["cards"] == []


def test_today_post(started):
    body = started.post("/api/demo/today", json={}).json()
    assert body["today"]["ran"] is True
    assert len(body["today"]["cards"]) == 3


def test_extraction_get(short):
    body = short.get("/api/demo/extraction").json()
    assert body["extracted"] is True
    assert body["unit_count"] > 0
    assert "body" in body["document"]


def test_extract_post(started):
    body = started.post("/api/demo/extract", json={}).json()
    assert body["extraction"]["extracted"] is True


def test_confirm_tags(short):
    body = short.post("/api/demo/confirm-tags", json={}).json()
    corrections = body["extraction"]["audience_corrections"]
    pricing = next(item for item in corrections if "Pricing" in item["title"] or item["ai_audience"] == "member")
    assert pricing["ai_audience"] == "member"
    assert pricing["audience"] == "advocate"
    assert pricing["applied"] is True


def test_copies_get(short):
    body = short.get("/api/demo/copies").json()
    assert body["ready"] is True
    assert body["counts"]["conflict"] >= 1
    assert body["pairs"]


def test_keep_canonical(started):
    started.post("/api/demo/extract", json={})
    body = started.post("/api/demo/keep-canonical", json={}).json()
    assert body["ok"] is True
    copies = started.get("/api/demo/copies").json()
    assert copies["canonical"] is True


def test_escalate(started):
    started.post("/api/demo/extract", json={})
    started.post("/api/demo/keep-canonical", json={})
    body = started.post("/api/demo/escalate", json={}).json()
    assert body["conflicts"]["count_open"] >= 1


def test_legal_queue(short):
    body = short.get("/api/legal/queue").json()
    assert body["count"] == 3
    assert body["waiting"][0]["if_you_approve"]["approved_by"] == "Legal approver"


def test_author_queue(started):
    started.post("/api/demo/extract", json={})
    started.post("/api/demo/keep-canonical", json={})
    started.post("/api/demo/escalate", json={})
    body = started.get("/api/author/queue").json()
    assert body["count"] >= 1
    assert body["waiting"][0]["requires_legal"] is False


def test_conflicts_get(short):
    body = short.get("/api/conflicts").json()
    assert any(plan["id"] == "mail-order" and plan["open"] for plan in body["plans"])


def test_legal_inbox(explore):
    body = explore.get("/api/legal/inbox").json()
    assert body["count"] >= 1
    assert body["items"][0]["kind"] in ("approval", "conflict")


def test_legal_approve(short):
    unit_id = short.get("/api/legal/queue").json()["waiting"][0]["unit_id"]
    body = short.post("/api/legal/approve", json={"unit_id": unit_id}).json()
    assert body["message"].startswith("Approved ")
    assert all(item["unit_id"] != unit_id for item in body["queue"]["waiting"])


def test_legal_approve_all(started):
    _ready_for_approval(started)
    started.post("/api/author/approve-all", json={})
    body = started.post("/api/legal/approve-all", json={}).json()
    assert "Demo shortcut" in body["message"]
    assert started.get("/api/legal/queue").json()["count"] == 0


def test_author_approve(started):
    _ready_for_approval(started)
    unit_id = started.get("/api/author/queue").json()["waiting"][0]["unit_id"]
    body = started.post("/api/author/approve", json={"unit_id": unit_id}).json()
    assert body["message"].startswith("Approved ")


def test_author_approve_all(started):
    _ready_for_approval(started)
    body = started.post("/api/author/approve-all", json={}).json()
    assert "demo shortcut" in body["message"].lower()
    assert started.get("/api/author/queue").json()["count"] == 0


def test_legal_decline(explore):
    explore.post("/api/explore/open", json={"role": "Legal approver"})
    waiting = explore.get("/api/legal/queue?world=explore").json()["waiting"]
    assert waiting
    body = explore.post(
        "/api/legal/decline",
        json={"world": "explore", "unit_id": waiting[0]["unit_id"], "reason": "The span is too wide."},
    ).json()
    assert body["message"].startswith("Returned ")


def test_resolve_conflict(short):
    plan = next(item for item in short.get("/api/conflicts").json()["plans"] if item["resolve_in_demo"])
    body = short.post(
        "/api/conflicts/resolve",
        json={"conflict_id": plan["id"], "reason": plan["reason_suggestion"]},
    ).json()
    assert body["message"].startswith("Kept ")
    again = next(item for item in body["conflicts"]["plans"] if item["id"] == plan["id"])
    assert again["open"] is False


def test_search_prompts(client):
    body = client.get("/api/search/prompts").json()
    assert body["cost"]
    assert "Pharmacy advocate" in body["roles"]


def test_search(short):
    _approve_short(short)
    body = short.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": "what do I say before I quote a cost", "record": True},
    ).json()
    assert body["result"]["abstained"] is False
    assert isinstance(body["result"]["unit"]["text"], str)
    assert body["result"]["searched"] == ["pharmacy", "shared-legal"]


def test_search_both(short):
    _approve_short(short)
    body = short.post("/api/search/both", json={"query": "what do I say before I quote a cost"}).json()
    ids = [item["unit"]["unit_id"] for item in body["results"]]
    assert len(set(ids)) == 2


def test_channels_get(short):
    _approve_short(short)
    body = short.get("/api/channels").json()
    assert body["ready"] is True
    assert body["live"]["version"] == 1
    assert body["revision_ready"] is True


def test_channels_publish(short):
    _approve_short(short)
    body = short.post("/api/channels/publish", json={}).json()
    assert body["channels"]["live"]["version"] == 2
    assert body["channels"]["previous"]["version"] == 1
    assert body["channels"]["advocate_diff"]


def test_units_expired(explore):
    body = explore.get("/api/units/expired?world=explore").json()
    assert body["count"] >= 1
    assert body["units"][0]["unit_id"]


def test_units_list(explore):
    body = explore.get("/api/units?world=explore&role=Pharmacy%20advocate").json()
    assert body["count"] >= 1
    assert all(item["status"] == "approved" for item in body["units"])


def test_unit_get(short):
    unit_id = short.get("/api/legal/queue").json()["waiting"][0]["unit_id"]
    body = short.get(f"/api/units/{unit_id}").json()
    assert body["unit"]["unit_id"] == unit_id


def test_versions(short):
    _approve_short(short)
    short.post("/api/channels/publish", json={})
    unit_id = short.get("/api/channels").json()["live"]["unit_id"]
    body = short.get(f"/api/units/{unit_id}/versions").json()
    assert [item["version"] for item in body["versions"]] == [1, 2]
    assert body["versions"][1]["diff_from_previous"]["advocate"]


def test_as_of(short):
    _approve_short(short)
    short.post("/api/channels/publish", json={})
    live = short.get("/api/channels").json()
    unit_id = live["live"]["unit_id"]
    missing = short.get(f"/api/units/{unit_id}/as-of", params={"timestamp": "2000-01-01"})
    assert missing.status_code == 404
    blank = short.get(f"/api/units/{unit_id}/as-of")
    assert blank.status_code == 400
    moment = live["live"]["effective_date"]
    body = short.get(f"/api/units/{unit_id}/as-of", params={"timestamp": moment}).json()
    assert body["version"] == live["live"]["version"]
    assert body["unit_id"] == unit_id
    assert body["text"]
    earlier = live["previous"]["effective_date"]
    earlier_body = short.get(f"/api/units/{unit_id}/as-of", params={"timestamp": earlier}).json()
    # A date with no clock means the end of that day. Two versions published in the
    # same minute share a timestamp, so the later version is the one that was live.
    if earlier < moment:
        assert earlier_body["version"] == live["previous"]["version"]
    else:
        assert earlier_body["version"] == live["live"]["version"]


def test_documents(short):
    body = short.get("/api/documents").json()
    assert len(body["documents"]) == 4


def test_document_get(short):
    body = short.get("/api/documents/SRC-RX-EDU-001").json()
    assert "Verbatim" in body["body"]
    assert body["units"]


def test_gaps_get(short):
    body = short.get("/api/gaps").json()
    assert body["count"] >= 1
    assert body["gaps"][0]["queries"]


def test_gap_act(short):
    gap = next(item for item in short.get("/api/gaps").json()["gaps"] if item["draft_text"])
    body = short.post(f"/api/gaps/{gap['id']}", json={"action": "write", "reason": "Asked with no approved answer."}).json()
    assert body["message"] == "Draft sent to the author."
    updated = next(item for item in body["gaps"]["gaps"] if item["id"] == gap["id"])
    assert updated["status"] == "in_review"


def test_drift_get(short):
    _approve_short(short)
    body = short.get("/api/drift").json()
    assert body["ready"] is True
    assert "cosmetic" in body["prepared"]
    assert "material" in body["prepared"]


def test_drift_post(short):
    _approve_short(short)
    body = short.post("/api/drift", json={"kind": "cosmetic"}).json()
    assert body["drift"]["cosmetic"] is True
    assert body["drift"]["stale"] is False


def test_drift_send(short):
    _approve_short(short)
    short.post("/api/drift", json={"kind": "material"})
    body = short.post("/api/drift/send", json={}).json()
    assert body["drift"]["sent"] is True
    assert body["drift"]["stale"] is True


def test_quality_get_before_score(short):
    body = short.get("/api/quality").json()
    assert body["scored"] is True
    assert body["score_counts"]["right_first"] == 8


def test_quality_score(explore):
    body = explore.post("/api/quality/score", json={"world": "explore"}).json()
    held = body["quality"]["golden_table"]["held_out"]
    assert sum(1 for row in held if row["Result"] == "Fail") == 1
    assert body["quality"]["note"] == "Illustrative, made-up data"


def test_feedback_post(explore):
    body = explore.post(
        "/api/feedback",
        json={
            "world": "explore",
            "source": "advocate",
            "role": "Pharmacy advocate",
            "kind": "confusing_wording",
            "question": "member id H12345678 what wording do I use",
            "note": "dob 01/02/1950",
            "unit_id": "U-RX-EDU-001-09",
        },
    ).json()
    assert "H12345678" not in body["feedback"]["question"]
    assert "[redacted]" in body["feedback"]["question"]
    assert "01/02/1950" not in body["feedback"]["note"]


def test_feedback_author(explore):
    body = explore.get("/api/feedback/author?world=explore").json()
    assert isinstance(body["groups"], list)


def test_feedback_product(explore):
    body = explore.get("/api/feedback/product?world=explore").json()
    assert body["total"] >= 1


def test_feedback_open(explore):
    body = explore.get("/api/feedback/open?route=author&world=explore").json()
    assert body["count"] >= 1
    assert body["items"][0]["status"] == "open"


def test_feedback_summary(explore):
    body = explore.get("/api/feedback/summary?world=explore").json()
    assert body["week_start"]
    assert body["by_kind"]


def test_feedback_resolve(explore):
    item = explore.get("/api/feedback/open?route=author&world=explore").json()["items"][0]
    body = explore.post(
        f"/api/feedback/{item['id']}/resolve",
        json={"world": "explore", "resolution": "Updated the wording and sent it to Legal."},
    ).json()
    assert body["feedback"]["status"] == "resolved"
    assert body["feedback"]["resolution"]


def test_activity(short):
    short.post("/api/demo/today", json={})
    body = short.get("/api/activity").json()
    assert body["events"]
    assert "Rx pricing disclaimer" in body["events"][0]["message"]


def test_undo_get(short):
    short.post("/api/demo/today", json={})
    body = short.get("/api/undo").json()
    assert body["available"] is True
    assert body["label"]


def test_undo_post(short):
    short.post("/api/demo/today", json={})
    body = short.post("/api/undo", json={"world": "guided"}).json()
    assert body["message"].startswith("Undid:")
    assert short.get("/api/demo/today").json()["ran"] is False


def test_explore_open(client):
    body = client.post("/api/explore/open", json={"role": "Legal approver"}).json()
    assert body["explore"]["role"] == "Legal approver"
    assert body["explore"]["page"] == "Review inbox"
    assert body["explore"]["ready"] is True


def test_explore_get(explore):
    body = explore.get("/api/explore").json()
    assert body["live_calls_cap"] == 20
    assert "Agent desktop" in body["pages"]


def test_explore_page(explore):
    body = explore.post("/api/explore/page", json={"page": "What I can read"}).json()
    assert body["explore"]["page"] == "What I can read"


def test_explore_reset(explore):
    explore.post("/api/explore/ask", json={"role": "Pharmacy advocate", "query": "what do I say before I quote a cost"})
    body = explore.post("/api/explore/reset").json()
    assert body["message"] == "Sandbox reset."
    assert body["undo"]["available"] is True


def test_explore_ask(explore):
    body = explore.post(
        "/api/explore/ask",
        json={"role": "Pharmacy advocate", "query": "what do I say before I quote a cost"},
    ).json()
    assert body["result"]["ai_source"] == "cached"
    assert body["result"]["abstained"] is False
    assert body["used_live"] is False


def test_explore_questions(client):
    client.post("/api/explore/open", json={"role": "Member"})
    body = client.get("/api/explore/questions", params={"role": "Member"}).json()
    assert body["questions"]


def test_explore_calls(client):
    client.post("/api/explore/open", json={"role": "Insurance advocate"})
    body = client.get("/api/explore/calls", params={"role": "Insurance advocate"}).json()
    assert body["calls"][0]["member"]
    assert body["calls"][0]["fictional"] is True


def test_explore_desk(explore):
    body = explore.post(
        "/api/explore/desk",
        json={
            "role": "Pharmacy advocate",
            "query": "what do I say before I quote a cost",
            "call_reason": "Drug price question",
        },
    ).json()
    assert body["searches_in_call"] == 1
    assert body["result"]["unit"]["unit_id"]


def test_explore_member(explore):
    body = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": "How much will my prescription cost?"}).json()
    assert body["kind"] == "clarify"
    assert body["reply"] == "Which drug? Here are the ones on your list."
    assert body["chips"]
    assert body["feedback_recorded"] is None
    assert "unit" not in body["reply"].lower()
    assert "U-" not in body["reply"]


def test_explore_member_helped(explore):
    explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": "How much will my prescription cost?"})
    body = explore.post(
        "/api/explore/member/helped",
        json={"helped": False, "question": "How much will my prescription cost?", "unit_id": ""},
    ).json()
    assert body["recorded"] is True
    assert body["feedback"]["kind"] == "not_helpful"


def test_member_topics(explore):
    body = explore.get("/api/explore/member/topics").json()
    assert len(body["topics"]) == 5
    priced = body["topics"][0]
    assert priced["citation"].startswith("Source: Harbor Health")
    assert "unit" not in priced["citation"].lower()


def test_my_work(explore):
    explore.post("/api/explore/open", json={"role": "Knowledge Ops author"})
    body = explore.get("/api/explore/my-work").json()
    assert "items" in body
    assert "groups" in body
    names = {item["group"] for item in body["groups"]}
    assert names <= {
        "Documents to review",
        "Unanswered questions",
        "Source changes",
        "Sent back by Legal",
    }


def test_insights(explore):
    body = explore.get("/api/explore/insights").json()
    assert body["tiles"]
    assert "held_out" in body
    assert body["illustrative"] is True


def test_scope(client):
    client.post("/api/explore/open", json={"role": "Insurance advocate"})
    body = client.get("/api/explore/scope", params={"role": "Insurance advocate"}).json()
    assert body["knowledge_bases"] == ["benefits", "shared-legal"]


def test_portal_quick_start(explore):
    body = explore.get("/api/portal/quick-start").json()
    assert body["sample_unit"]["unit_id"]
    assert body["sample_unit"]["citation"]


def test_portal_units(explore):
    body = explore.get("/api/portal/units", params={"channel": "member_chat"}).json()
    assert body["count"] >= 1
    assert "member_text" in body["units"][0]


def test_portal_unit(explore):
    unit_id = explore.get("/api/portal/quick-start").json()["sample_unit"]["unit_id"]
    body = explore.get(f"/api/portal/units/{unit_id}", params={"channel": "member_chat"}).json()
    assert body["unit"]["text"] == body["unit"]["member_text"]


def test_portal_events(explore):
    body = explore.get("/api/portal/events").json()
    assert "events" in body


def test_portal_answers(explore):
    body = explore.get(
        "/api/portal/answers",
        params={"role": "Pharmacy advocate", "question": "what do I say before I quote a cost"},
    ).json()
    assert body["abstained"] is False
    assert body["unit_id"]
    member = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": "Do specialty drugs go through mail order?"},
    ).json()
    assert "unit_id" not in member
    assert member["text"]


def _ready_for_approval(client):
    assert client.post("/api/demo/extract", json={}).status_code == 200
    assert client.post("/api/demo/confirm-tags", json={}).status_code == 200
    assert client.post("/api/demo/keep-canonical", json={}).status_code == 200
    assert client.post("/api/demo/escalate", json={}).status_code == 200


def _approve_short(client):
    queue = client.get("/api/legal/queue").json()["waiting"]
    for item in queue:
        response = client.post("/api/legal/approve", json={"unit_id": item["unit_id"]})
        assert response.status_code == 200, response.text


def test_evals_route_reports_when_no_run_exists(client):
    body = client.get("/api/evals").json()
    assert "available" in body
    assert body["illustrative"] is True
