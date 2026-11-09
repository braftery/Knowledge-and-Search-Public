"""Plan data, price and visit quotes, chat intents, and unclustered gaps."""

import os
import sqlite3

MEMBERS = [
    "HBR-20418",
    "HBR-22841",
    "HBR-23107",
    "HBR-24055",
    "HBR-25112",
    "HBR-26390",
    "HBR-27004",
]
DANA = "HBR-20418"
LUIS = "HBR-22841"
PRICING = "U-RX-EDU-001-09"
COST = "U-BEN-COST-001-02"
REFERRAL = "U-BEN-COST-001-05"
SPECIALTY = "U-RX-EDU-001-13"
PRICE_WITHHELD = "Prices appear once Legal approves the pricing disclaimer."
COST_WITHHELD = "Costs appear once Legal approves the cost disclaimer."
SPECIALTY_NOTE = "Specialty drugs fill at Harbor Specialty Pharmacy."
OON_RULE = "U-BEN-OON-RULE-001"


def _verify(client, member_id: str) -> None:
    from src.member_data import date_of_birth

    response = client.post(
        "/api/explore/verify",
        json={"member_id": member_id, "date_of_birth": date_of_birth(member_id)},
    )
    assert response.status_code == 200, response.text


def _resolve_mail(client) -> None:
    client.post("/api/explore/open", json={"role": "Legal approver"})
    response = client.post(
        "/api/conflicts/resolve",
        json={
            "world": "explore",
            "conflict_id": "mail-order",
            "reason": "Legal keeps the signed script.",
        },
    )
    assert response.status_code == 200, response.text
    client.post("/api/explore/open", json={"role": "Pharmacy advocate"})
OUT_OF_SCOPE = (
    "I can help with your Harbor plan: drug prices, visit costs, referrals and pharmacy questions, "
    "or I can connect you with a member advocate."
)


def _db(client) -> str:
    root = os.environ["HARBOR_API_SESSIONS"]
    return os.path.join(root, client.cookies["harbor_session"], "explore.sqlite")


def _unapprove(client, unit_id: str) -> None:
    conn = sqlite3.connect(_db(client))
    try:
        conn.execute(
            "UPDATE units SET status = 'proposed', search_visible = 0 WHERE unit_id = ?",
            (unit_id,),
        )
        conn.commit()
    finally:
        conn.close()


def _unit(ref: dict, unit_id: str) -> None:
    assert ref["unit_id"] == unit_id
    assert isinstance(ref["version"], int) and ref["version"] >= 1
    assert ref["title"]
    assert "(Legal)" not in ref["title"]
    assert ref["text"]
    assert ref["citation"].startswith("Source: Harbor Health, ")
    assert f"version {ref['version']}" in ref["citation"]
    assert "U-" not in ref["citation"]


def test_profile_shape(explore):
    missing = explore.get("/api/explore/member/profile")
    assert missing.status_code == 400
    unknown = explore.get("/api/explore/member/profile", params={"member_id": "HBR-00000"})
    assert unknown.status_code == 404
    for member_id in MEMBERS:
        _verify(explore, member_id)
        found = explore.get("/api/explore/member/profile", params={"member_id": member_id})
        assert found.status_code == 200, found.text
        body = found.json()
        assert body["member"]["member_id"] == member_id
        assert body["coverage_stage"] == "Initial coverage"
        assert len(body["drugs"]) >= 2
        expected_claims = 4 if member_id == DANA else 3
        assert len(body["claims"]) == expected_claims
        assert len(body["recent_contacts"]) == 3
        assert body["illustrative"] is True
    dana = explore.get("/api/explore/member/profile", params={"member_id": DANA}).json()
    assert dana["member"]["name"] == "Dana R."
    assert dana["member"]["plan"] == "Harbor Medicare Advantage HMO"
    assert dana["plan"]["premium"]["display"] == "$0 a month"
    assert dana["plan"]["primary_care"] == {"amount": 0, "display": "$0"}
    assert dana["plan"]["specialist"] == {"amount": 35, "display": "$35"}
    assert dana["plan"]["urgent_care"]["display"] == "$45"
    assert dana["plan"]["emergency"]["display"] == "$110"
    assert dana["plan"]["medical_deductible"]["display"] == "$0"
    assert dana["plan"]["out_of_pocket_maximum"] == {"amount": 4500, "display": "$4,500"}
    assert dana["plan"]["part_d_deductible"]["amount"] == 250
    assert "tiers 1 and 2" in dana["plan"]["part_d_deductible"]["note"]
    assert dana["plan"]["out_of_network"]["exceptions"] == ["emergency", "urgent_care"]
    assert len(dana["plan"]["pharmacies"]) == 3
    assert {item["network"] for item in dana["plan"]["pharmacies"]} <= {"preferred", "standard"}
    assert [drug["drug_id"] for drug in dana["drugs"]] == ["atorvastatin", "metformin", "apixaban"]
    assert dana["drugs"][2]["tier"] == 3
    assert dana["drugs"][2]["specialty"] is False
    assert dana["oop"] == {
        "limit": 4500,
        "spent": 1210,
        "limit_display": "$4,500",
        "spent_display": "$1,210",
    }
    assert dana["drug_deductible"] == {"amount": 250, "met": False}
    claim = dana["claims"][0]
    assert set(claim) >= {
        "date",
        "provider_type",
        "amount_billed",
        "amount_billed_display",
        "plan_paid",
        "plan_paid_display",
        "member_paid",
        "member_paid_display",
        "status",
    }
    contact = dana["recent_contacts"][0]
    assert set(contact) == {"date", "channel", "summary"}
    luis = explore.get("/api/explore/member/profile", params={"member_id": LUIS}).json()
    assert "adalimumab" in [drug["drug_id"] for drug in luis["drugs"]]


def test_profile_needs_an_open_sandbox(client):
    response = client.get("/api/explore/member/profile", params={"member_id": DANA})
    assert response.status_code == 400
    assert response.json()["error"] == "Open an Explore role before using the sandbox."


def test_drug_price_shape(explore):
    _verify(explore, DANA)
    _verify(explore, LUIS)
    _resolve_mail(explore)
    body = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin"},
    ).json()
    assert body["pharmacy"] == "preferred_retail"
    assert body["days"] == 30
    assert body["available"] is True
    assert body["price"] == 0
    assert body["price_display"] == "$0"
    assert body["tier_label"] == "Tier 1"
    assert body["coverage_stage"] == "Initial coverage"
    assert body["drug"]["name"] == "Atorvastatin"
    assert body["drug"]["strength"] == "20 mg tablet"
    assert body["note"] == ""
    assert body["withheld_reason"] == ""
    assert body["illustrative"] is True
    assert len(body["units"]) == 1
    _unit(body["units"][0], PRICING)
    assert body["units"][0]["title"] == "Pricing estimate disclaimer"
    assert body["units"][0]["text"].startswith("These prices are estimates")
    mail = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin", "pharmacy": "mail_order", "days": 90},
    ).json()
    assert mail["available"] is True
    assert mail["price"] == 0
    standard = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin", "pharmacy": "standard_retail", "days": 30},
    ).json()
    assert standard["price"] == 10
    insulin = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "insulin-glargine", "pharmacy": "preferred_retail", "days": 30},
    ).json()
    assert insulin["price"] == 35
    assert insulin["tier_label"] == "Tier 3"
    assert insulin["drug"]["specialty"] is False
    specialty = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": LUIS, "drug_id": "adalimumab", "pharmacy": "specialty", "days": 30},
    ).json()
    assert specialty["available"] is True
    assert specialty["price"] == 612
    assert specialty["price_display"] == "$612"
    assert specialty["note"] == "33% coinsurance, shown as $612."
    missing = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "not-a-drug"},
    )
    assert missing.status_code == 404
    bad_pharmacy = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin", "pharmacy": "retail"},
    )
    assert bad_pharmacy.status_code == 400
    assert bad_pharmacy.json()["error"] == "Unknown pharmacy."
    bad_days = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin", "days": 15},
    )
    assert bad_days.status_code == 400
    assert bad_days.json()["error"] == "Days must be 30 or 90."


def test_specialty_drug_refuses_mail_order(explore):
    _verify(explore, DANA)
    _verify(explore, LUIS)
    body = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": LUIS, "drug_id": "adalimumab", "pharmacy": "mail_order", "days": 90},
    ).json()
    assert body["available"] is False
    assert body["price"] is None
    assert body["note"] == SPECIALTY_NOTE
    assert body["withheld_reason"] == ""
    assert body["illustrative"] is True
    assert [unit["unit_id"] for unit in body["units"]] == ["U-RX-EDU-PRICE-ANY", SPECIALTY]
    _unit(body["units"][1], SPECIALTY)
    unavailable = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin", "pharmacy": "specialty", "days": 30},
    ).json()
    assert unavailable["available"] is False
    assert unavailable["price"] is None
    assert unavailable["note"] == "This supply is not available at that pharmacy."
    assert [unit["unit_id"] for unit in unavailable["units"]] == ["U-RX-EDU-PRICE-ANY"]


def test_price_withheld_until_the_disclaimer_is_approved(explore):
    _verify(explore, DANA)
    _unapprove(explore, PRICING)
    body = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin"},
    ).json()
    assert body["available"] is False
    assert body["price"] is None
    assert body["price_display"] == ""
    assert body["withheld_reason"] == PRICE_WITHHELD
    assert body["units"] == []
    assert body["illustrative"] is True
    visit = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "primary_care"},
    ).json()
    assert visit["available"] is True
    assert visit["cost"] == 0


def test_visit_cost_shape(explore):
    _verify(explore, DANA)
    specialist = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "specialist", "network": "in"},
    ).json()
    assert specialist["available"] is True
    assert specialist["cost"] == 35
    assert specialist["cost_display"] == "$35"
    assert specialist["note"] == "You need a referral from your primary care doctor first."
    assert specialist["withheld_reason"] == ""
    assert specialist["illustrative"] is True
    assert [unit["unit_id"] for unit in specialist["units"]] == [COST, REFERRAL]
    _unit(specialist["units"][0], COST)
    assert specialist["units"][0]["text"].startswith("This cost is an estimate")
    primary = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "primary_care"},
    ).json()
    assert primary["cost"] == 0
    assert [unit["unit_id"] for unit in primary["units"]] == [COST]
    outside = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "primary_care", "network": "out"},
    ).json()
    assert outside["available"] is False
    assert outside["cost"] is None
    assert outside["note"] == "Out of network is not covered, except emergency and urgent care."
    assert [unit["unit_id"] for unit in outside["units"]] == [OON_RULE]
    emergency = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "emergency", "network": "out"},
    ).json()
    assert emergency["available"] is True
    assert emergency["cost"] == 110
    urgent = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "urgent_care", "network": "out"},
    ).json()
    assert urgent["cost"] == 45
    specialist_out = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "specialist", "network": "out"},
    ).json()
    assert specialist_out["available"] is False
    assert specialist_out["cost"] is None
    assert [unit["unit_id"] for unit in specialist_out["units"]] == [OON_RULE, "U-BEN-OON-NEXT-001"]
    unknown = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "dentist"},
    )
    assert unknown.status_code == 400
    assert unknown.json()["error"] == "Unknown visit."


def test_visit_cost_withheld_until_the_disclaimer_is_approved(explore):
    _verify(explore, DANA)
    _unapprove(explore, COST)
    body = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "specialist"},
    ).json()
    assert body["available"] is False
    assert body["cost"] is None
    assert body["cost_display"] == ""
    assert body["withheld_reason"] == COST_WITHHELD
    assert body["units"] == []
    assert body["illustrative"] is True
    price = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin"},
    ).json()
    assert price["available"] is True
    assert price["price"] == 0


def test_member_record_for_a_verified_advocate(explore):
    _verify(explore, DANA)
    _verify(explore, "HBR-25112")
    _verify(explore, LUIS)
    denied = explore.get(
        "/api/explore/member-record",
        params={"member_id": DANA, "role": "Member", "verified": True},
    )
    assert denied.status_code == 400
    assert denied.json()["error"] == "Unknown role."
    body = explore.get(
        "/api/explore/member-record",
        params={"member_id": DANA, "role": "Pharmacy advocate", "verified": True},
    ).json()
    assert body["verified"] is True
    assert body["role"] == "Pharmacy advocate"
    assert body["illustrative"] is True
    assert body["oop"]["spent"] == 1210
    assert len(body["claims"]) == 4
    assert body["drugs"][0]["tier"] == 1
    by_drug = {item["drug_id"]: item for item in body["prices"]}
    assert by_drug["atorvastatin"]["price"] == 0
    assert by_drug["atorvastatin"]["pharmacy"] == "preferred_retail"
    assert by_drug["atorvastatin"]["days"] == 30
    assert by_drug["apixaban"]["price"] == 180
    assert body["withheld_reason"] == ""
    assert [unit["unit_id"] for unit in body["units"]] == [PRICING]
    assert body["units"][0]["text"].startswith("The price I quote")
    insurance = explore.get(
        "/api/explore/member-record",
        params={"member_id": "HBR-25112", "role": "Insurance advocate", "verified": True},
    )
    assert insurance.status_code == 200
    assert insurance.json()["member"]["name"] == "Maria S."
    luis = explore.get(
        "/api/explore/member-record",
        params={"member_id": LUIS, "role": "Pharmacy advocate", "verified": True},
    ).json()
    adalimumab = next(item for item in luis["prices"] if item["drug_id"] == "adalimumab")
    assert adalimumab["available"] is False
    assert adalimumab["price"] is None
    assert adalimumab["note"] == SPECIALTY_NOTE
    assert [unit["unit_id"] for unit in luis["units"]] == [PRICING, SPECIALTY]


def test_unverified_record_drops_prices(explore):
    body = explore.get(
        "/api/explore/member-record",
        params={"member_id": DANA, "role": "Pharmacy advocate", "verified": False},
    ).json()
    assert body["verified"] is False
    assert "prices" not in body
    assert "claims" not in body
    assert "oop" not in body
    assert "drugs" not in body
    assert "recent_contacts" not in body
    assert "coverage_stage" not in body
    assert "drug_deductible" not in body
    assert "primary_care" not in body.get("plan", {})
    assert len(body["units"]) == 1
    _unit(body["units"][0], body["units"][0]["unit_id"])
    assert body["units"][0]["title"] == "No coverage details to unverified callers"
    assert body["withheld_reason"] == body["units"][0]["text"]
    assert "unverified caller" in body["withheld_reason"]
    assert body["illustrative"] is True
    omitted = explore.get(
        "/api/explore/member-record",
        params={"member_id": DANA, "role": "Insurance advocate"},
    ).json()
    assert omitted["verified"] is False
    assert "prices" not in omitted


def test_chat_drug_and_visit_intents(explore):
    _resolve_mail(explore)
    atorvastatin = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "how much is atorvastatin"},
    ).json()
    assert atorvastatin["kind"] == "price"
    assert atorvastatin["reply"] == "Atorvastatin 20 mg, 30-day supply at a preferred pharmacy: $0."
    assert atorvastatin["price"]["price"] == 0
    assert atorvastatin["price"]["illustrative"] is True
    assert atorvastatin["feedback_recorded"] is None
    assert atorvastatin["illustrative"] is True
    assert "How much is a 90-day supply of atorvastatin by mail?" in atorvastatin["chips"]
    assert atorvastatin["units"][0]["unit_id"] == PRICING
    mail = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "how much is a 90 day supply of atorvastatin by mail"},
    ).json()
    assert mail["kind"] == "price"
    assert mail["reply"] == "Atorvastatin 20 mg, 90-day supply by mail: $0."
    assert mail["price"]["pharmacy"] == "mail_order"
    assert mail["price"]["days"] == 90
    specialist = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "what will a specialist visit cost"},
    ).json()
    assert specialist["kind"] == "visit_cost"
    assert specialist["visit_cost"]["cost"] == 35
    assert specialist["visit_cost"]["illustrative"] is True
    assert "You need a referral from your primary care doctor first." in specialist["reply"]
    assert [unit["unit_id"] for unit in specialist["units"]][:2] == [COST, REFERRAL]
    assert "U-TPL-VISIT-001" in [unit["unit_id"] for unit in specialist["units"]]
    clarify = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "how much is my prescription"},
    ).json()
    assert clarify["kind"] == "clarify"
    assert clarify["reply"] == "Which drug? Here are the ones on your list."
    assert "How much is atorvastatin?" in clarify["chips"]
    assert "How much is metformin?" in clarify["chips"]
    assert "How much is apixaban?" in clarify["chips"]
    assert clarify["feedback_recorded"] is None
    insulin = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "is my insulin covered"},
    ).json()
    assert insulin["kind"] == "price"
    assert insulin["price"]["drug"]["drug_id"] == "insulin-glargine"
    assert insulin["price"]["price"] == 35
    assert "tier 3" in insulin["reply"]
    assert "$35" in insulin["reply"]
    doctor = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "what will my doctor visit cost"},
    ).json()
    assert doctor["kind"] == "clarify"
    assert doctor["reply"] == "What kind of visit?"
    assert "What will a specialist visit cost?" in doctor["chips"]
    topic = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "topic": 0}).json()
    assert topic["kind"] == "clarify"
    assert topic["reply"] == "Which drug? Here are the ones on your list."
    assert topic["feedback_recorded"] is None
    visit_topic = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "topic": 1}).json()
    assert visit_topic["kind"] == "clarify"
    assert visit_topic["reply"] == "What kind of visit?"
    other = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "topic": 3}).json()
    assert other["kind"] == "topic"
    assert other["unit_id"] == SPECIALTY
    luis = explore.post(
        "/api/explore/member",
        json={"question": "how much is my prescription", "member_id": LUIS},
    ).json()
    assert "How much is adalimumab?" in luis["chips"]
    unknown = explore.post(
        "/api/explore/member",
        json={"question": "how much is atorvastatin", "member_id": "HBR-00000"},
    )
    assert unknown.status_code == 404


def test_weather_is_out_of_scope_and_not_logged(explore):
    before_gaps = explore.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    before_author = explore.get(
        "/api/feedback/open",
        params={"route": "author", "world": "explore"},
    ).json()["count"]
    before_product = explore.get("/api/feedback/product", params={"world": "explore"}).json()["total"]
    body = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": "what is the weather"}).json()
    assert body["kind"] == "out_of_scope"
    assert body["reply"] == OUT_OF_SCOPE
    assert body["feedback_recorded"] is None
    assert body["chips"] == []
    assert body["illustrative"] is True
    after_gaps = explore.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    assert after_gaps == before_gaps
    assert explore.get(
        "/api/feedback/open",
        params={"route": "author", "world": "explore"},
    ).json()["count"] == before_author
    assert explore.get("/api/feedback/product", params={"world": "explore"}).json()["total"] == before_product
    activity = " ".join(
        event["message"]
        for event in explore.get("/api/activity", params={"world": "explore", "limit": 20}).json()["events"]
    )
    assert "weather" not in activity.lower()


def test_knowledge_path_still_answers(explore):
    body = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "Do specialty drugs go through mail order?"},
    ).json()
    assert body["kind"] == "abstain"
    assert "past its review date" in body["reply"]
    assert body.get("feedback_recorded") in (None, "")


def test_unclustered_questions_are_flagged_and_refused(explore):
    fresh = explore.get("/api/explore/insights").json()
    assert fresh["new_questions"] == {"count": 0, "examples": []}
    explore.post("/api/settings/live", json={"enabled": False, "world": "explore"})
    question = "where should the blue scooter be parked"
    found = explore.post(
        "/api/search",
        json={"world": "explore", "role": "Pharmacy advocate", "query": question, "record": True},
    )
    assert found.status_code == 200, found.text
    assert found.json()["result"]["abstained"] is True
    gaps = explore.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    row = next(item for item in gaps if item["id"] == "new-unclustered")
    assert row["kind"] == "unclustered"
    assert row["cluster"] == "New, not yet clustered"
    assert question in row["queries"]
    assert all(item["kind"] == "cluster" for item in gaps if item["id"] != "new-unclustered")
    insights = explore.get("/api/explore/insights").json()
    assert all(item["id"] != "new-unclustered" for item in insights["top_gaps"])
    assert all(item["kind"] == "cluster" for item in insights["top_gaps"])
    assert insights["new_questions"]["count"] >= 1
    assert any(question in example for example in insights["new_questions"]["examples"])
    edits = explore.get("/api/author/edits", params={"world": "explore"}).json()["gaps"]
    assert all(item["id"] != "new-unclustered" for item in edits)
    explore.post("/api/explore/open", json={"role": "Knowledge Ops author"})
    refused = explore.post("/api/author/gaps/new-unclustered/send", json={"world": "explore"})
    assert refused.status_code == 400
    assert refused.json()["error"] == "Group these questions into a topic first."
