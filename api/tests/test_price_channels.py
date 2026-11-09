"""Price disclaimers, portal intents, and verified advocate quotes."""

import os
import sqlite3

DANA = "HBR-20418"
PRICING = "U-RX-EDU-001-09"
PRICE_ANY = "U-RX-EDU-PRICE-ANY"
COST = "U-BEN-COST-001-02"
REFERRAL = "U-BEN-COST-001-05"
PRICE_WITHHELD = "Prices appear once Legal approves the pricing disclaimer."
SHIPPING = "member asked whether the 90-day mail price includes shipping"
OON_RULE = "U-BEN-OON-RULE-001"


def _verify(client, member_id: str = DANA) -> None:
    from src.member_data import date_of_birth

    response = client.post(
        "/api/explore/verify",
        json={"member_id": member_id, "date_of_birth": date_of_birth(member_id)},
    )
    assert response.status_code == 200, response.text


def _resolve_mail(client) -> None:
    opened = client.post("/api/explore/open", json={"role": "Legal approver"})
    assert opened.status_code == 200, opened.text
    response = client.post(
        "/api/conflicts/resolve",
        json={"world": "explore", "conflict_id": "mail-order", "reason": "Legal keeps the signed script."},
    )
    assert response.status_code == 200, response.text
    restored = client.post("/api/explore/open", json={"role": "Pharmacy advocate"})
    assert restored.status_code == 200, restored.text


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


def test_disclaimer_follows_the_supply_and_pharmacy(explore):
    _verify(explore)
    _resolve_mail(explore)
    preferred = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin"},
    ).json()
    assert preferred["units"][0]["unit_id"] == PRICING
    assert preferred["units"][0]["text"].startswith("These prices are estimates for a 30-day supply")
    mail = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin", "pharmacy": "mail_order", "days": 90},
    ).json()
    assert mail["available"] is True
    assert mail["price"] == 0
    assert mail["units"][0]["unit_id"] == PRICE_ANY
    assert mail["units"][0]["text"].startswith("This price is an estimate for the supply and the pharmacy shown")
    standard = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin", "pharmacy": "standard_retail", "days": 30},
    ).json()
    assert standard["units"][0]["unit_id"] == PRICE_ANY
    chat = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "how much is a 90 day supply of atorvastatin by mail"},
    ).json()
    assert chat["kind"] == "price"
    assert chat["units"][0]["unit_id"] == PRICE_ANY
    record = explore.get(
        "/api/explore/member-record",
        params={"member_id": DANA, "role": "Pharmacy advocate", "verified": True},
    ).json()
    assert record["prices"][0]["pharmacy"] == "preferred_retail"
    assert record["prices"][0]["days"] == 30
    assert record["units"][0]["unit_id"] == PRICING
    assert record["units"][0]["text"].startswith("The price I quote is an estimate for a 30-day supply")


def test_price_is_withheld_when_the_unit_in_use_is_unapproved(explore):
    _verify(explore)
    _resolve_mail(explore)
    _unapprove(explore, PRICE_ANY)
    mail = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin", "pharmacy": "mail_order", "days": 90},
    ).json()
    assert mail["available"] is False
    assert mail["price"] is None
    assert mail["price_display"] == ""
    assert mail["withheld_reason"] == PRICE_WITHHELD
    assert mail["units"] == []
    preferred = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin"},
    ).json()
    assert preferred["available"] is True
    assert preferred["price"] == 0
    assert preferred["units"][0]["unit_id"] == PRICING
    _unapprove(explore, PRICING)
    hidden = explore.get(
        "/api/explore/member/drug-price",
        params={"member_id": DANA, "drug_id": "atorvastatin"},
    ).json()
    assert hidden["available"] is False
    assert hidden["price"] is None
    assert hidden["withheld_reason"] == PRICE_WITHHELD
    assert hidden["units"] == []


def test_out_of_network_specialist_omits_the_cost_disclaimer(explore):
    _verify(explore)
    body = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "specialist", "network": "out"},
    ).json()
    assert body["available"] is False
    assert body["cost"] is None
    assert COST not in [unit["unit_id"] for unit in body["units"]]
    assert [unit["unit_id"] for unit in body["units"]] == [OON_RULE, "U-BEN-OON-NEXT-001"]
    covered = explore.get(
        "/api/explore/member/visit-cost",
        params={"member_id": DANA, "visit": "specialist", "network": "in"},
    ).json()
    assert covered["available"] is True
    assert [unit["unit_id"] for unit in covered["units"]] == [COST, REFERRAL]


def test_portal_member_intents_match_member_chat(explore):
    _resolve_mail(explore)
    question = "how much is my atorvastatin"
    chat = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": question}).json()
    portal = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": question},
    ).json()
    assert portal["kind"] == chat["kind"] == "price"
    assert portal["price"]["price"] == chat["price"]["price"] == 0
    assert portal["price"]["pharmacy"] == chat["price"]["pharmacy"]
    assert portal["text"] == chat["reply"]
    assert portal["units"][0]["unit_id"] == chat["units"][0]["unit_id"] == PRICING
    assert portal["illustrative"] is True
    mail = "how much is a 90 day supply of apixaban by mail"
    chat_mail = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": mail}).json()
    portal_mail = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": mail},
    ).json()
    assert portal_mail["kind"] == chat_mail["kind"] == "price"
    assert portal_mail["price"]["price"] == chat_mail["price"]["price"] == 200
    assert portal_mail["units"][0]["unit_id"] == PRICE_ANY
    referral = "do i need a referral for a cardiologist"
    chat_ref = explore.post("/api/explore/member", json={"member_id": "HBR-20418", "question": referral}).json()
    portal_ref = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": referral},
    ).json()
    assert portal_ref["kind"] == chat_ref["kind"] == "answer"
    assert portal_ref["units"][0]["unit_id"] == REFERRAL
    weather = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": "what is the weather"},
    ).json()
    assert weather["kind"] == "out_of_scope"
    assert "price" not in weather
    complaint = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": "I was overcharged"},
    ).json()
    chat_complaint = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "I was overcharged"},
    ).json()
    assert complaint["kind"] == chat_complaint["kind"] == "handoff_offer"
    assert complaint["text"] == chat_complaint["reply"]
    knowledge = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": "Do specialty drugs go through mail order?"},
    ).json()
    assert "kind" not in knowledge
    assert "abstained" in knowledge
    assert "unit_id" not in knowledge
    unknown = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "question": question, "member_id": "HBR-00000"},
    )
    assert unknown.status_code == 404


def test_verified_advocate_ask_returns_price_options(explore):
    _resolve_mail(explore)
    question = "is apixaban cheaper by mail"
    hidden = explore.post(
        "/api/explore/ask",
        json={
            "role": "Pharmacy advocate",
            "query": question,
            "member_id": DANA,
            "verified": True,
        },
    ).json()
    assert "price" not in hidden
    assert "price_options" not in hidden
    assert "visit_cost" not in hidden
    assert "result" not in hidden
    assert len(hidden["units"]) == 1
    assert hidden["units"][0]["title"] == "No coverage details to unverified callers"
    assert hidden["text"] == hidden["units"][0]["text"]
    assert "$" not in hidden["text"]
    _verify(explore)
    plain = explore.post(
        "/api/explore/ask",
        json={"role": "Pharmacy advocate", "query": question},
    ).json()
    assert "price_options" not in plain
    assert "kind" not in plain
    assert "result" in plain
    verified = explore.post(
        "/api/explore/ask",
        json={
            "role": "Pharmacy advocate",
            "query": question,
            "member_id": DANA,
            "verified": True,
        },
    ).json()
    assert verified["kind"] == "price"
    assert verified["result"]["query"] == question
    assert verified["units"][0]["unit_id"] == PRICE_ANY
    assert verified["units"][0]["text"].startswith(
        "The price I quote is an estimate for the supply and pharmacy we discussed"
    )
    options = {(item["pharmacy"], item["days"]): item for item in verified["price_options"]}
    assert set(options) == {
        ("preferred_retail", 30),
        ("preferred_retail", 90),
        ("standard_retail", 30),
        ("standard_retail", 90),
        ("mail_order", 30),
        ("mail_order", 90),
    }
    assert options[("preferred_retail", 30)]["price"] == 180
    assert options[("preferred_retail", 30)]["units"][0]["unit_id"] == PRICING
    assert options[("mail_order", 90)]["price"] == 200
    assert options[("mail_order", 90)]["units"][0]["unit_id"] == PRICE_ANY
    assert options[("mail_order", 30)]["available"] is False
    explore.post("/api/explore/open", json={"role": "Insurance advocate"})
    visit = explore.post(
        "/api/explore/ask",
        json={
            "role": "Insurance advocate",
            "query": "what will a specialist visit cost",
            "member_id": DANA,
            "verified": True,
        },
    ).json()
    assert visit["kind"] == "visit_cost"
    assert visit["visit_cost"]["cost"] == 35
    assert [unit["unit_id"] for unit in visit["units"]] == [COST, REFERRAL]
    assert visit["units"][0]["text"].startswith("The cost I quote")


def test_shipping_flag_replaces_the_shoe_size_flag(explore):
    items = explore.get(
        "/api/feedback/open",
        params={"route": "author", "world": "explore"},
    ).json()["items"]
    questions = [item["question"] for item in items]
    assert not any("shoe size" in question for question in questions)
    match = next(item for item in items if SHIPPING in item["question"])
    assert match["kind"] == "couldnt_find"
    assert match["kind_label"] == "Could not find it"


def test_price_any_stays_out_of_search(explore, client):
    unit = explore.get("/api/units/U-RX-EDU-PRICE-ANY", params={"world": "explore"}).json()["unit"]
    assert unit["status"] == "approved"
    assert unit["search_visible"] is False
    assert unit["type"] == "verbatim"
    assert unit["requires_legal"] is True
    assert unit["approved_by"] == "Dana Okafor (Legal)"
    assert unit["approved_on"].startswith("2026-09-23")
    assert unit["kb_scope"] == ["pharmacy"]
    assert set(unit["channels"]) == {"advocate_guidance", "member_chat", "website", "voice_bot"}
    found = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "what do I say before I quote a cost",
            "record": False,
        },
    ).json()
    ranked = [row["unit_id"] for row in found["result"]["ranked"]]
    assert PRICE_ANY not in ranked
    assert found["result"]["unit"]["unit_id"] == PRICING
    client.post("/api/session/reset", json={"mode": "jump"})
    guided = client.get("/api/units/U-RX-EDU-PRICE-ANY", params={"world": "guided"}).json()["unit"]
    assert guided["search_visible"] is False
    assert guided["status"] == "approved"
