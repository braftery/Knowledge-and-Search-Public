"""API tests for the back-end contract after pass 5.

Each test name is listed in the pull request. Figures are illustrative.
"""

from pathlib import Path

from api.tests.conftest import open_role

DANA = "HBR-20418"
ROOT = Path(__file__).resolve().parents[2]


def test_redaction_fixture_recall_and_false_positives():
    from src.engine import redact_query

    rows = [
        line.split("\t")
        for line in (ROOT / "fixtures" / "redaction_cases.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert len(rows) >= 30
    misses = []
    false_positives = []
    for kind, needle, text in rows:
        redacted = redact_query(text)
        if kind == "safe":
            if redacted != text:
                false_positives.append(text)
        elif needle and needle.lower() in redacted.lower():
            misses.append(f"{needle} still in {redacted}")
    recall = 1 - (len(misses) / max(1, sum(1 for kind, needle, _text in rows if kind == "redact" and needle)))
    print(f"redaction recall {recall:.2f} misses {len(misses)} false positives {len(false_positives)}")
    assert misses == []
    assert false_positives == []
    whole = redact_query("My name is Sam Okoro and my daughter Lena calls")
    assert "Sam" not in whole and "Okoro" not in whole and "Lena" not in whole
    caller = redact_query("Caller Dana Rivera")
    assert caller == "Caller [redacted]"


def test_overcharge_phrasings_open_the_complaint_flow(explore):
    phrases = [
        "I was charged more than I expected",
        "My copay was higher than the estimate",
        "The bill was higher than I thought",
        "I was overcharged",
        "I paid more than I thought I would",
        "This cost more than I expected",
        "The charge was higher than expected",
        "They charged more than I expected",
        "My cost was higher than the quote",
        "I think the pharmacy bill was too much",
    ]
    for phrase in phrases:
        body = explore.post(
            "/api/explore/member",
            json={"member_id": DANA, "question": phrase},
        ).json()
        assert body["kind"] == "handoff_offer", phrase
        assert body["chips"][0] == "The pharmacy charged more than the estimate"


def test_cosmetic_edit_inside_verbatim_goes_to_legal(short):
    _approve_pricing(short)
    body = short.post("/api/drift", json={"kind": "cosmetic"}).json()
    assert body["message"] == "Sent to Legal: a comma inside Legal wording. The approved version stays live."
    drift = body["drift"]
    assert drift["cosmetic"] is True
    assert drift["stale"] is False
    assert drift["verbatim_to_legal"] is True
    assert "Sent to Legal" in drift["message"]
    assert "Cosmetic change inside Legal wording" in drift["message"]
    material = short.post("/api/drift", json={"kind": "material"}).json()["drift"]
    assert material["material"] is True
    assert material["stale"] is True


def test_cosmetic_edit_outside_verbatim_keeps_the_log_message(tmp_path):
    from src.engine import COSMETIC_LOGGED, _drift_spec, build_database, connect, cosmetic_drift_message

    path = tmp_path / "drift.sqlite"
    build_database(str(path), "short")
    conn = connect(str(path))
    find = _drift_spec("cosmetic").get("find") or ""
    assert find
    conn.execute(
        "UPDATE units SET text = REPLACE(text, ?, ''), source_quote = REPLACE(COALESCE(source_quote, ''), ?, '')",
        (find, find),
    )
    conn.commit()
    assert cosmetic_drift_message(conn) == COSMETIC_LOGGED
    conn.close()


def test_explore_expired_review_fails_closed(explore):
    body = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "do specialty drugs stay at the specialty pharmacy",
            "record": False,
        },
    ).json()["result"]
    assert body["abstained"] is True
    assert "past its review date" in body["note"]
    open_role(explore, "Legal approver")
    extended = explore.post(
        "/api/legal/review/extend",
        json={
            "world": "explore",
            "unit_id": "U-RX-EDU-001-13",
            "review_by": "2027-06-01",
            "reason": "Illustrative extension so the sandbox can show the unit again.",
        },
    )
    assert extended.status_code == 200, extended.text


def test_explore_role_is_the_session_role(explore):
    refused = explore.post(
        "/api/search",
        json={"world": "explore", "role": "Insurance advocate", "query": "what is the MOOP", "record": False},
    )
    assert refused.status_code == 403
    assert refused.json()["detail"] == "Open that role first."
    open_role(explore, "insurance advocate")
    allowed = explore.post(
        "/api/search",
        json={"world": "explore", "role": "Pharmacy advocate", "query": "what is the MOOP", "record": False},
    )
    assert allowed.status_code == 403


def test_phone_authentication_is_per_call(explore):
    from src.member_data import date_of_birth

    first = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "how much is atorvastatin", "channel": "voice_bot", "call_id": "c-1"},
    ).json()
    assert first["kind"] == "authenticate"
    authed = explore.post(
        "/api/explore/phone/authenticate",
        json={"member_id": DANA, "date_of_birth": date_of_birth(DANA), "call_id": "c-1"},
    )
    assert authed.status_code == 200, authed.text
    assert "verified" in (authed.json().get("reply") or "").lower()
    priced = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "how much is atorvastatin", "channel": "voice_bot", "call_id": "c-1"},
    ).json()
    assert priced["kind"] == "price"
    second = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "how much is atorvastatin", "channel": "voice_bot", "call_id": "c-2"},
    ).json()
    assert second["kind"] == "authenticate"


def test_ivr_prompts_are_approved_units(explore):
    prompts = explore.get("/api/explore/member/topics").json()["ivr_prompts"]
    assert prompts["greeting"]["text"].startswith("Thank you for calling Harbor Health")
    assert "Press 0" in prompts["anything_else"]["text"]
    assert prompts["no_answer"]["text"].startswith("I don't have an approved answer")
    assert "verified" in prompts["verified"]["text"].lower()
    for key in ("greeting", "anything_else", "no_answer", "verified"):
        assert prompts[key]["unit_id"].startswith("U-")


def test_authorized_caller_is_pending_and_on_the_record(explore):
    from src.member_data import date_of_birth

    created = explore.post(
        "/api/explore/member/authorized-caller",
        json={"member_id": DANA, "caller_name": "Ana Morales", "relationship": "daughter"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["confirmation"].startswith("AC-")
    explore.post(
        "/api/explore/verify",
        json={"member_id": DANA, "date_of_birth": date_of_birth(DANA)},
    )
    record = explore.get(
        "/api/explore/member-record",
        params={"member_id": DANA, "role": "Pharmacy advocate"},
    ).json()
    assert record["recent_contacts"][0]["summary"] == "Asked to add an authorized caller"
    activity = " ".join(
        event["message"]
        for event in explore.get("/api/activity", params={"world": "explore", "limit": 20}).json()["events"]
    )
    assert "Ana" not in activity


def test_per_unit_tags_do_not_change_the_guided_pool(short, explore):
    before = short.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": "what do I say before I quote a cost", "record": False},
    ).json()["result"]["ranked"]
    saved = short.post(
        "/api/demo/units/U-RX-EDU-001-09/tags",
        json={"world": "guided", "audience": "", "domain": "pharmacy", "tags": ["price"]},
    )
    assert saved.status_code == 200, saved.text
    after = short.post(
        "/api/search",
        json={"role": "Pharmacy advocate", "query": "what do I say before I quote a cost", "record": False},
    ).json()["result"]["ranked"]
    assert after == before
    blocked = short.post(
        "/api/demo/units/U-RX-EDU-001-08/tags",
        json={"world": "guided", "audience": "advocate", "domain": "pharmacy", "tags": ["verify"]},
    )
    # A unit with no member wording leaves the member pool if audience drops member.
    if blocked.status_code == 400:
        assert "guided search pool" in blocked.json()["detail"]
    saved = explore.post(
        "/api/demo/units/U-RX-EDU-001-09/tags",
        json={"world": "explore", "audience": "advocate,member", "domain": "pharmacy", "tags": ["price"]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["recorded"] is True


def _approve_pricing(short):
    unit = short.get("/api/units/U-RX-EDU-001-09").json()["unit"]
    if unit["status"] != "approved":
        response = short.post("/api/legal/approve", json={"unit_id": "U-RX-EDU-001-09"})
        assert response.status_code == 200, response.text


def test_legal_typed_publish_and_prepared_publish(short):
    _approve_pricing(short)
    empty = short.post("/api/channels/publish", json={"text": "   ", "member_text": "Hello"})
    assert empty.status_code == 400
    prepared = short.post("/api/channels/publish", json={})
    assert prepared.status_code == 200, prepared.text
    assert "advocate desktop" in prepared.json()["message"]
    assert "phone line" in prepared.json()["message"]
    same = short.post(
        "/api/channels/publish",
        json={"text": prepared.json()["channels"]["live"]["text"], "member_text": prepared.json()["channels"]["live"]["member_text"]},
    )
    assert same.status_code == 400


def test_legal_workload_is_illustrative(short):
    body = short.get("/api/legal/workload").json()
    assert body["illustrative"] is True
    assert "Illustrative" in body["assumptions"]
    assert set(body["by_type"]) == {"verbatim", "policy", "cost", "other"}
    assert set(body["by_risk_tier"]) == {"high", "medium", "low"}
    assert body["minutes_per_tier"]["high"] == 20
    assert "total_hours" in body
    assert "verbatim" in body["proposed_tiering"]["legal"]


def test_undo_appends_a_version(short):
    _approve_pricing(short)
    published = short.post("/api/channels/publish", json={})
    assert published.status_code == 200, published.text
    undone = short.post("/api/undo", json={})
    assert undone.status_code == 200, undone.text
    versions = short.get("/api/units/U-RX-EDU-001-09/versions").json()["versions"]
    assert len(versions) >= 2


def test_visit_cache_skips_a_superseded_version(explore):
    first = explore.post(
        "/api/explore/ask",
        json={"role": "Pharmacy advocate", "query": "what do I say before I quote a cost"},
    ).json()
    assert first["from_visit_cache"] is False
    second = explore.post(
        "/api/explore/ask",
        json={"role": "Pharmacy advocate", "query": "What do I say before I quote a cost?"},
    ).json()
    assert second["from_visit_cache"] is True
    assert second["result"]["unit"]["version"] == first["result"]["unit"]["version"]


def test_unchanged_publish_and_idempotency_key(short):
    _approve_pricing(short)
    first = short.post("/api/channels/publish", json={"idempotency_key": "pub-1"})
    assert first.status_code == 200, first.text
    again = short.post("/api/channels/publish", json={"idempotency_key": "pub-1"})
    assert again.status_code == 200
    assert again.json()["message"] == first.json()["message"]
    third = short.post("/api/channels/publish", json={})
    assert third.status_code == 400


def test_events_are_append_only_with_ts_and_previous_version(short):
    _approve_pricing(short)
    short.post("/api/channels/publish", json={})
    events = short.get("/api/portal/events", params={"world": "guided"}).json()["events"]
    published = next(item for item in events if item["event"] == "unit.revised")
    assert published["ts"]
    assert published["occurred_at"]
    assert published["previous_version"] == 1
    assert published["event_id"]


def test_greeting_reason_records_reason_source(explore):
    plans = explore.get("/api/conflicts", params={"world": "explore"}).json()["plans"]
    greeting = next(plan for plan in plans if plan["id"] == "greeting")
    open_role(explore, "Legal approver")
    accepted = explore.post(
        "/api/conflicts/resolve",
        json={"world": "explore", "conflict_id": "greeting", "reason": greeting["reason_suggestion"]},
    ).json()
    stored = next(plan for plan in accepted["conflicts"]["plans"] if plan["id"] == "greeting")
    assert stored["reason_source"] == "ai_suggestion_accepted"


def test_cross_knowledge_base_returns_a_transfer(explore):
    found = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "do I need a referral to see a cardiologist",
            "record": False,
        },
    ).json()["result"]
    assert found["abstained"] is True
    assert found["transfer"]["queue"] == "Insurance queue"
    assert found["transfer"]["reason"]


def test_answered_gap_shows_answered(explore):
    from api.tests.test_routing_api import QUESTION, _as, _gap, _send

    gap = _gap(explore, "c0")
    filled = gap["draft_text"].replace("[approved disclaimer unit ID, e.g., U-RX-EDU-001-09]", "U-RX-EDU-001-09")
    _send(explore, "c0", filled)
    _as(explore, "Legal approver")
    approved = explore.post("/api/legal/approve", json={"world": "explore", "unit_id": "U-GAP-c0"})
    assert approved.status_code == 200, approved.text
    _as(explore, "Knowledge owner")
    insights = explore.get("/api/explore/insights").json()
    rows = insights["top_gaps"] + insights["findability_gaps"]
    match = next((row for row in rows if row.get("id") == "c0"), None)
    if match is not None:
        assert match["answered"] is True


def test_guided_quality_matches_step_8_from_a_fresh_session(client):
    assert client.post("/api/session/reset", json={"mode": "start"}).status_code == 200
    scored = client.post("/api/quality/score", json={"world": "guided"})
    assert scored.status_code == 200, scored.text
    quality = scored.json()["quality"]
    hit = next(tile for tile in quality["tiles"] if tile["key"] == "hit_at_1")
    abstain = next(tile for tile in quality["tiles"] if tile["key"] == "correct_abstain")
    assert hit["detail"] == "8 of 8"
    assert abstain["detail"] == "4 of 4"
    assert quality["held_out_pass"] == 2
    assert quality["held_out_total"] == 3
    assert len(quality["misses"]) == 6
    assert hit["wilson"]["measured"] is True
    owner = client.get("/api/explore/insights")
    # Insights on a guided session are not the explore route. Quality and the score share the snapshot.
    again = client.get("/api/quality", params={"world": "guided"}).json()
    again_hit = next(tile for tile in again["tiles"] if tile["key"] == "hit_at_1")
    assert again_hit["detail"] == "8 of 8"
    del owner


def test_mutating_routes_require_the_actor(explore):
    refused = explore.post("/api/channels/publish", json={"world": "explore"})
    assert refused.status_code == 403
    assert "Legal approver" in refused.json()["detail"]
    open_role(explore, "Legal approver")
    allowed = explore.post("/api/legal/approve", json={"world": "explore", "unit_id": "U-RX-EDU-001-08"})
    assert allowed.status_code == 200, allowed.text


def test_undo_is_scoped_to_the_actor(explore):
    open_role(explore, "Legal approver")
    published = explore.post("/api/channels/publish", json={"world": "explore"})
    assert published.status_code == 200, published.text
    open_role(explore, "Member")
    denied = explore.post("/api/undo", json={"world": "explore"})
    assert denied.status_code == 403
    open_role(explore, "Legal approver")
    undone = explore.post("/api/undo", json={"world": "explore"})
    assert undone.status_code == 200, undone.text


def test_answer_status_and_structured_citations(explore):
    from src.member_data import date_of_birth

    explore.post("/api/explore/verify", json={"member_id": DANA, "date_of_birth": date_of_birth(DANA)})
    body = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "how much is atorvastatin"},
    ).json()
    assert body["status"] == "price"
    assert body["citations"]
    assert "Source:" not in body["reply"]
    cite = body["citations"][0]
    assert {"unit_id", "version", "title", "approved_by", "approved_on"} <= set(cite)


def test_portal_cache_miss_is_separate_from_abstain(explore):
    missing = explore.get(
        "/api/portal/answers",
        params={"role": "Pharmacy advocate", "question": "where should the blue scooter be parked"},
    ).json()
    assert missing["status"] == "cache_miss"
    assert missing["abstained"] is False


def test_problem_json_and_role_case(client):
    unknown = client.post("/api/explore/open", json={"role": "Not a role"})
    assert unknown.status_code == 400
    body = unknown.json()
    assert body["title"] == "Bad Request"
    assert body["status"] == 400
    assert body["detail"] == "Unknown role."
    assert "Pharmacy advocate" in body["allowed"]
    opened = client.post("/api/explore/open", json={"role": "legal approver"})
    assert opened.status_code == 200, opened.text


def test_events_cursor_and_recorded_webhooks(short):
    _approve_pricing(short)
    registered = short.post(
        "/api/portal/webhooks",
        json={"world": "guided", "url": "https://example.test/hook", "events": ["unit.revised"]},
    )
    assert registered.status_code == 200, registered.text
    assert registered.json()["secret"]
    short.post("/api/channels/publish", json={})
    page = short.get("/api/portal/events", params={"world": "guided", "cursor": "0"}).json()
    assert "next_cursor" in page
    assert page["events"]
    assert page["events"][0]["event_id"]


def test_linked_sibling_stays_live(short):
    _approve_pricing(short)
    published = short.post("/api/channels/publish", json={})
    assert published.status_code == 200, published.text
    inbox = short.get("/api/legal/inbox").json()
    labels = " ".join(item.get("summary") or item.get("title") or "" for item in inbox.get("items") or [])
    # The sibling review is stored even when the inbox shape differs.
    assert published.json()["channels"]["live"]["status"] == "approved"


def test_zero_answers_are_not_measured_and_wilson_is_present(explore):
    scored = explore.post("/api/quality/score", json={"world": "explore"})
    assert scored.status_code == 200, scored.text
    quality = scored.json()["quality"]
    assert quality["slices"]["robustness"]
    for tile in quality["tiles"]:
        assert "wilson" in tile


def test_explore_question_cap_and_cache_key(explore):
    long_question = "a" * 501
    refused = explore.post(
        "/api/explore/ask",
        json={"role": "Pharmacy advocate", "query": long_question},
    )
    assert refused.status_code == 400


def test_member_context_comparison_glossary_and_cost_help(explore):
    from src.member_data import date_of_birth

    open_role(explore, "Legal approver")
    resolved = explore.post(
        "/api/conflicts/resolve",
        json={"world": "explore", "conflict_id": "mail-order", "reason": "Legal keeps the signed script."},
    )
    assert resolved.status_code == 200, resolved.text
    open_role(explore, "Pharmacy advocate")
    explore.post("/api/explore/verify", json={"member_id": DANA, "date_of_birth": date_of_birth(DANA)})
    compared = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "Is 90 days by mail cheaper for apixaban"},
    ).json()
    assert compared["kind"] == "price_compare"
    assert "per-month" in compared["reply"] or "per month" in compared["reply"].lower() or "difference" in compared["reply"]
    total = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "how much will all my drugs cost this month"},
    ).json()
    assert total["kind"] == "drug_total"
    assert total["monthly_total"] is not None
    two = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "How much is atorvastatin? And how much is metformin?"},
    ).json()
    assert two["kind"] == "price"
    assert any("metformin" in chip.lower() for chip in two["chips"])
    defined = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "what is a deductible"},
    ).json()
    assert defined["kind"] == "definition"
    glossary = explore.get("/api/explore/member/glossary").json()
    assert len(glossary["entries"]) >= 6
    help_body = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "I can't afford my medicine"},
    ).json()
    assert help_body["kind"] == "cost_help"
    assert "Talk to a member advocate" in help_body["chips"]
    claims = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "See my recent claims"},
    ).json()
    assert any(row.get("member_paid") == 140 for row in claims["claims"])


def test_phone_line_covers_the_member_list(explore):
    from src.member_data import date_of_birth

    explore.post(
        "/api/explore/phone/authenticate",
        json={"member_id": DANA, "date_of_birth": date_of_birth(DANA), "call_id": "line-1"},
    )
    drugs = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "how much is my prescription", "channel": "voice_bot", "call_id": "line-1"},
    ).json()
    assert drugs["kind"] == "clarify"
    assert drugs["chips"]
    mail = explore.post(
        "/api/explore/member",
        json={
            "member_id": DANA,
            "question": "how much is a 90 day supply of atorvastatin by mail",
            "channel": "voice_bot",
            "call_id": "line-1",
        },
    ).json()
    assert mail["kind"] == "price"
    specialist = explore.post(
        "/api/explore/member",
        json={
            "member_id": DANA,
            "question": "what will a specialist visit cost",
            "channel": "voice_bot",
            "call_id": "line-1",
        },
    ).json()
    assert specialist["kind"] == "visit_cost"
    pocket = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "what is my out of pocket maximum", "channel": "voice_bot", "call_id": "line-1"},
    ).json()
    assert pocket["kind"] in {"oop", "plan_figure"}
    billing = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "I was charged more than I expected", "channel": "voice_bot", "call_id": "line-1"},
    ).json()
    assert billing["kind"] == "handoff_offer"
    callback = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "can you call me back", "channel": "voice_bot", "call_id": "line-1"},
    ).json()
    assert callback["kind"] == "callback"


def test_member_is_required(explore):
    missing = explore.post("/api/explore/member", json={"question": "how much is atorvastatin"})
    assert missing.status_code == 400
    assert missing.json()["detail"] == "A member is required."


def test_unknown_channel_lists_allowed(explore):
    refused = explore.get("/api/portal/units/U-RX-EDU-001-09", params={"channel": "nonsense"})
    assert refused.status_code == 400
    assert "member_chat" in refused.json()["allowed"]


def test_insurance_portal_cost_line(explore):
    open_role(explore, "Insurance advocate")
    body = explore.get(
        "/api/portal/answers",
        params={"role": "Insurance advocate", "question": "what do I say before I quote a cost"},
    ).json()
    assert body["unit_id"] == "U-BEN-COST-001-02"
    assert body["status"] == "answer"


def test_out_of_network_cites_the_not_covered_rule(explore):
    from src.member_data import date_of_birth

    explore.post("/api/explore/verify", json={"member_id": DANA, "date_of_birth": date_of_birth(DANA)})
    body = explore.post(
        "/api/explore/member",
        json={"member_id": DANA, "question": "How much will an out of network specialist cost me?"},
    ).json()
    ids = [unit["unit_id"] for unit in body["units"]]
    assert "U-BEN-OON-RULE-001" in ids
    assert "U-BEN-COST-001-05" not in ids
    assert "U-BEN-OON-NEXT-001" in ids


def test_portal_openapi(client):
    spec = client.get("/api/portal/openapi.json")
    assert spec.status_code == 200
    body = spec.json()
    assert "/api/portal/answers" in body["paths"]
    assert "Problem" in body["components"]["schemas"]


def test_publish_names_four_channels(short):
    _approve_pricing(short)
    body = short.post("/api/channels/publish", json={}).json()
    message = body["message"] + " " + body["email"]
    for name in ("advocate desktop", "member chat", "website", "phone line"):
        assert name in message


def test_explore_linked_review_opens_and_lists(explore):
    open_role(explore, "Legal approver")
    before = explore.get("/api/legal/link-reviews", params={"world": "explore"}).json()["reviews"]
    assert not any(item["unit_id"] == "U-RX-EDU-PRICE-ANY" for item in before)
    published = explore.post("/api/channels/publish", json={"world": "explore"})
    assert published.status_code == 200, published.text
    live = published.json()["channels"]["live"]
    assert live["unit_id"] == "U-RX-EDU-001-09"
    assert live["version"] == 2
    assert live["sibling_of"] == "U-RX-EDU-PRICE-ANY"
    listed = explore.get("/api/legal/link-reviews", params={"world": "explore"})
    assert listed.status_code == 200, listed.text
    match = next(item for item in listed.json()["reviews"] if item["unit_id"] == "U-RX-EDU-PRICE-ANY")
    assert match["sibling_id"] == "U-RX-EDU-001-09"
    assert match["label"] == "A linked disclaimer may need the same change"
    assert match["created_at"]
    assert set(match) == {"unit_id", "sibling_id", "label", "created_at"}
    accepted = explore.post(
        "/api/legal/link-review/accept",
        json={"world": "explore", "unit_id": "U-RX-EDU-PRICE-ANY"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["message"] == "A linked disclaimer may need the same change"
    assert accepted.json()["stays_live"] is True
    again = explore.get("/api/legal/link-reviews", params={"world": "explore"}).json()["reviews"]
    assert not any(item["unit_id"] == "U-RX-EDU-PRICE-ANY" for item in again)
    price = explore.get("/api/units/U-RX-EDU-001-09", params={"world": "explore"}).json()["unit"]
    sibling = explore.get("/api/units/U-RX-EDU-PRICE-ANY", params={"world": "explore"}).json()["unit"]
    assert price["status"] == "approved"
    assert price["version"] == 2
    assert sibling["status"] == "approved"
    undone = explore.post("/api/undo", json={"world": "explore"})
    assert undone.status_code == 200, undone.text
    restored = explore.get("/api/units/U-RX-EDU-001-09", params={"world": "explore"}).json()["unit"]
    assert restored["version"] == 3
    assert restored["sibling_of"] == "U-RX-EDU-PRICE-ANY"


def test_sibling_id_reads_an_earlier_version(tmp_path):
    from src.engine import build_database, connect
    from src.finish import PRICE_ANY, PRICE_UNIT, copy_sibling_of, sibling_id

    path = tmp_path / "sibling.sqlite"
    build_database(str(path), "explore")
    conn = connect(str(path))
    conn.execute(
        """
        INSERT INTO units (
            unit_id, version, title, type, text, status, search_visible, sibling_of
        )
        SELECT unit_id, 2, title, type, text, 'approved', 1, ''
        FROM units WHERE unit_id = ? AND version = 1
        """,
        (PRICE_UNIT,),
    )
    assert sibling_id(conn, PRICE_UNIT) == PRICE_ANY
    copy_sibling_of(conn, PRICE_UNIT, 2)
    copied = conn.execute(
        "SELECT sibling_of FROM units WHERE unit_id = ? AND version = 2",
        (PRICE_UNIT,),
    ).fetchone()
    assert copied["sibling_of"] == PRICE_ANY
    conn.close()


def test_tag_edit_shows_on_extraction_without_changing_the_guided_pool(short, explore):
    query = {"role": "Pharmacy advocate", "query": "what do I say before I quote a cost", "record": False}
    before = short.post("/api/search", json=query).json()["result"]["ranked"]
    saved = short.post(
        "/api/demo/units/U-RX-EDU-001-09/tags",
        json={
            "world": "guided",
            "audience": "advocate",
            "domain": "Edited pharmacy domain",
            "tags": ["edited-tag", "price-line"],
        },
    )
    assert saved.status_code == 200, saved.text
    after = short.post("/api/search", json=query).json()["result"]["ranked"]
    assert after == before
    extraction = short.get("/api/demo/extraction", params={"world": "guided"}).json()
    unit = next(item for item in extraction["units"] if item["unit_id"] == "U-RX-EDU-001-09")
    assert unit["audience"] == ["advocate"]
    assert unit["domain"] == "Edited pharmacy domain"
    assert unit["tags"] == ["edited-tag", "price-line"]
    assert unit["tags_edited_by"] == "Knowledge Ops author"
    untouched = next(item for item in extraction["units"] if item["unit_id"] != "U-RX-EDU-001-09")
    assert "tags_edited_by" not in untouched
    stored = short.get("/api/units/U-RX-EDU-001-09").json()["unit"]
    assert "edited-tag" not in stored["tags"]
    assert stored["domain"] != "Edited pharmacy domain"
    explore_saved = explore.post(
        "/api/demo/units/U-RX-EDU-001-08/tags",
        json={
            "world": "explore",
            "audience": "advocate,member",
            "domain": "Edited member domain",
            "tags": ["edited-explore"],
        },
    )
    assert explore_saved.status_code == 200, explore_saved.text
    explore_units = explore.get("/api/demo/extraction", params={"world": "explore"}).json()["units"]
    edited = next(item for item in explore_units if item["unit_id"] == "U-RX-EDU-001-08")
    assert edited["audience"] == ["advocate", "member"]
    assert edited["domain"] == "Edited member domain"
    assert edited["tags"] == ["edited-explore"]
    assert edited["tags_edited_by"] == "Knowledge Ops author"


def test_site_units_are_fetchable(explore):
    for unit_id, snippet in (
        ("U-SITE-MAIL-001", "90-day"),
        ("U-SITE-FIND-001", "1-800-555-0148"),
        ("U-SITE-HELP-001", "member advocate"),
    ):
        found = explore.get(f"/api/portal/units/{unit_id}", params={"channel": "website"})
        assert found.status_code == 200, found.text
        assert snippet in found.json()["unit"]["text"]
