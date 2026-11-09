"""Explore routes that pair mock plan data with approved wording."""

from __future__ import annotations

from api.catalog import ILLUSTRATIVE, plain_title
from api.errors import APIError
from src.compliance import (
    CLAIMS_ID,
    DEDUCT_ID,
    ER_ID,
    IVR_ADD_ID,
    IVR_ADVOCATE_ID,
    IVR_AUTH_ID,
    IVR_BEFORE_ID,
    MAIL_RULE_ID,
    MAIL_WITHHELD,
    NOT_ON_LIST_ID,
    OON_RULE_ID,
    OON_VISIT_ID,
    OOP_ID,
    PERSON_ID,
    READ_ORDER,
    SAFE_ID,
    UC_ID,
    text_has_amount,
)
from src.engine import live_approved, open_conflicts, wording_title
from src.member_data import (
    ADVOCATE_RECORD_ROLES,
    CLARIFY_DRUG_REPLY,
    CLARIFY_VISIT_REPLY,
    DAY_OPTIONS,
    HANDOFF_OFFER_CHIPS,
    HANDOFF_OFFER_REPLY,
    OUT_OF_SCOPE_REPLY,
    PERSON_CHIPS,
    PHARMACIES,
    SPECIALTY_NOTE,
    VISITS,
    NETWORKS,
    drug_by_id,
    drug_clarify_chips,
    drug_quote,
    find_member,
    price_chips,
    price_comparison,
    price_reply,
    profile_payload,
    visit_chips,
    visit_quote,
    visit_reply,
)

COMPARE_PHARMACIES = ("preferred_retail", "standard_retail", "mail_order")

PRICING_DISCLAIMER = "U-RX-EDU-001-09"
PRICE_ANY = "U-RX-EDU-PRICE-ANY"
COST_DISCLAIMER = "U-BEN-COST-001-02"
REFERRAL_RULE = "U-BEN-COST-001-05"
SPECIALTY_RULE = "U-RX-EDU-001-13"
UNVERIFIED_TITLE = "No coverage details to unverified callers"
PRICE_WITHHELD = "Prices appear once Legal approves the pricing disclaimer."
COST_WITHHELD = "Costs appear once Legal approves the cost disclaimer."
UNVERIFIED_FALLBACK = "Coverage details stay hidden until Legal approves the unverified-caller rule."


def price_disclaimer_id(pharmacy: str, days: int) -> str:
    """30-day preferred retail uses the signed 30-day wording. Every other quote uses the any-supply unit."""
    if pharmacy == "preferred_retail" and int(days) == 30:
        return PRICING_DISCLAIMER
    return PRICE_ANY


def _unit_ref(conn, unit_id: str, *, advocate: bool, search_visible: bool = True) -> dict | None:
    if search_visible:
        row = live_approved(conn, unit_id)
    else:
        row = conn.execute(
            """
            SELECT * FROM units
            WHERE unit_id = ? AND status = 'approved'
            ORDER BY version DESC
            LIMIT 1
            """,
            (unit_id,),
        ).fetchone()
    if row is None:
        return None
    return _ref_from_row(row, advocate=advocate)


def _ref_from_row(row, *, advocate: bool) -> dict | None:
    text = ((row["text"] if advocate else row["member_text"]) or "").strip()
    if not text:
        return None
    return {
        "unit_id": row["unit_id"],
        "version": row["version"],
        "title": wording_title(row["title"]),
        "text": text,
        "approved_by": row["approved_by"] or "",
        "approved_on": row["approved_on"] or "",
        "citation": f"Source: Harbor Health, {plain_title(row['title'])}, version {row['version']}",
        "type": row["type"] or "",
    }


def _approved_title(conn, title: str):
    return conn.execute(
        """
        SELECT * FROM units
        WHERE title = ? AND status = 'approved' AND search_visible = 1
        ORDER BY version DESC
        LIMIT 1
        """,
        (title,),
    ).fetchone()


def _attach(
    conn,
    payload,
    gate_id: str,
    extra_ids: list[str],
    *,
    advocate: bool,
    withheld: str,
    amount_key: str,
    display_key: str,
    gate_search_visible: bool = True,
) -> dict:
    gate = _unit_ref(conn, gate_id, advocate=advocate, search_visible=gate_search_visible)
    if gate is None:
        payload["available"] = False
        payload[amount_key] = None
        payload[display_key] = ""
        payload["withheld_reason"] = withheld
        payload["units"] = []
        return payload
    units = [gate]
    for unit_id in extra_ids:
        ref = _unit_ref(conn, unit_id, advocate=advocate)
        if ref is None:
            ref = _unit_ref(conn, unit_id, advocate=advocate, search_visible=False)
        if ref is not None:
            units.append(ref)
    payload["units"] = units
    return payload


def _require_member(member_id: str) -> str:
    member_id = (member_id or "").strip()
    if not member_id:
        raise APIError("A member is required.")
    if find_member(member_id) is None:
        raise APIError(f"No member {member_id}.", 404)
    return member_id


def _hidden_refs(conn, unit_ids: list[str], *, advocate: bool) -> list[dict]:
    refs = []
    for unit_id in unit_ids:
        ref = _unit_ref(conn, unit_id, advocate=advocate, search_visible=False)
        if ref is None:
            ref = _unit_ref(conn, unit_id, advocate=advocate)
        if ref is not None:
            refs.append(ref)
    return refs


def _strip_unverified_profile(payload: dict) -> dict:
    """Drop coverage details an unverified caller must not receive."""
    payload.pop("drugs", None)
    payload.pop("recent_contacts", None)
    payload.pop("claims", None)
    payload.pop("oop", None)
    payload.pop("coverage_stage", None)
    payload.pop("drug_deductible", None)
    plan = payload.get("plan") or {}
    payload["plan"] = {
        "name": plan.get("name") or "",
        "nurse_line": plan.get("nurse_line") or "",
        "nurse_line_note": plan.get("nurse_line_note") or "",
    }
    payload["verified"] = False
    return payload


def member_profile_view(conn, member_id: str, *, verified: bool = False) -> dict:
    member_id = _require_member(member_id)
    payload = profile_payload(member_id)
    payload["illustrative"] = True
    payload["note"] = ILLUSTRATIVE
    payload["verified"] = bool(verified)
    if not verified:
        return _strip_unverified_profile(payload)
    figures = _hidden_refs(conn, [OOP_ID, CLAIMS_ID, ER_ID, UC_ID, OON_RULE_ID], advocate=False)
    by_id = {item["unit_id"]: item for item in figures}
    if OOP_ID not in by_id:
        payload.pop("oop", None)
        plan = payload.get("plan") or {}
        plan.pop("out_of_pocket_maximum", None)
        payload["plan"] = plan
    if CLAIMS_ID not in by_id:
        payload.pop("claims", None)
    if ER_ID not in by_id:
        payload.get("plan", {}).pop("emergency", None)
    if UC_ID not in by_id:
        payload.get("plan", {}).pop("urgent_care", None)
    payload["figure_units"] = figures
    return payload


def mail_rule_open(conn) -> bool:
    return any(plan.get("id") == "mail-order" for plan in open_conflicts(conn))


def _withhold_mail(quote: dict) -> dict:
    quote["available"] = False
    quote["price"] = None
    quote["price_display"] = ""
    quote["withheld_reason"] = MAIL_WITHHELD
    quote["units"] = []
    quote["note"] = ""
    return quote


def drug_price_view(
    conn, member_id: str, drug_id: str, pharmacy: str, days: int, *, advocate: bool = False
) -> dict:
    member_id = _require_member(member_id)
    drug_id = (drug_id or "").strip()
    pharmacy = (pharmacy or "preferred_retail").strip()
    if not drug_id:
        raise APIError("A drug_id is required.")
    if drug_by_id(drug_id) is None:
        raise APIError(f"No drug {drug_id}.", 404)
    if pharmacy not in PHARMACIES:
        raise APIError("Unknown pharmacy.")
    if days not in DAY_OPTIONS:
        raise APIError("Days must be 30 or 90.")
    quote = drug_quote(member_id, drug_id, pharmacy, days)
    if pharmacy == "mail_order" and quote.get("available") and mail_rule_open(conn):
        quote["illustrative"] = True
        return _withhold_mail(quote)
    extra = [SPECIALTY_RULE] if quote["note"] == SPECIALTY_NOTE else []
    if quote.get("coverage_stage") == "Deductible":
        extra = [DEDUCT_ID, *extra]
    _attach(
        conn,
        quote,
        price_disclaimer_id(pharmacy, days),
        extra,
        advocate=advocate,
        withheld=PRICE_WITHHELD,
        amount_key="price",
        display_key="price_display",
        gate_search_visible=False,
    )
    quote["illustrative"] = True
    return quote


def price_options_view(conn, member_id: str, drug_id: str, *, advocate: bool = False) -> list[dict]:
    """30-day and 90-day prices at preferred retail, standard retail, and mail order."""
    options = []
    for pharmacy in COMPARE_PHARMACIES:
        for days in DAY_OPTIONS:
            options.append(
                drug_price_view(conn, member_id, drug_id, pharmacy, days, advocate=advocate)
            )
    return options


def visit_cost_view(conn, member_id: str, visit: str, network: str, *, advocate: bool = False) -> dict:
    member_id = _require_member(member_id)
    visit = (visit or "").strip()
    network = (network or "in").strip()
    if not visit:
        raise APIError("A visit is required.")
    if visit not in VISITS:
        raise APIError("Unknown visit.")
    if network not in NETWORKS:
        raise APIError("Network must be in or out.")
    quote = visit_quote(member_id, visit, network)
    if not quote["available"]:
        units = []
        rule = _unit_ref(conn, OON_RULE_ID, advocate=advocate, search_visible=False)
        if rule is not None:
            units.append(rule)
            quote["note"] = rule["text"]
        if visit == "specialist":
            next_step = _unit_ref(conn, "U-BEN-OON-NEXT-001", advocate=advocate, search_visible=False)
            if next_step is not None:
                units.append(next_step)
        quote["units"] = units
        quote["illustrative"] = True
        return quote
    extra = [REFERRAL_RULE] if visit == "specialist" else []
    gate = COST_DISCLAIMER
    gate_visible = True
    if network == "out" and visit in ("urgent_care", "emergency"):
        gate = OON_VISIT_ID
        gate_visible = False
    elif visit == "urgent_care":
        gate = UC_ID
        gate_visible = False
    elif visit == "emergency":
        gate = ER_ID
        gate_visible = False
    _attach(
        conn,
        quote,
        gate,
        extra,
        advocate=advocate,
        withheld=COST_WITHHELD,
        amount_key="cost",
        display_key="cost_display",
        gate_search_visible=gate_visible,
    )
    quote["illustrative"] = True
    return quote


def _priced_row(conn, member_id: str, drug: dict) -> dict:
    quote = drug_quote(member_id, drug["drug_id"], "preferred_retail", 30)
    _attach(
        conn,
        quote,
        price_disclaimer_id("preferred_retail", 30),
        [],
        advocate=True,
        withheld=PRICE_WITHHELD,
        amount_key="price",
        display_key="price_display",
        gate_search_visible=False,
    )
    return {
        "drug_id": drug["drug_id"],
        "pharmacy": "preferred_retail",
        "days": 30,
        "available": quote["available"],
        "price": quote["price"],
        "price_display": quote["price_display"],
        "tier_label": quote["tier_label"],
        "note": quote["note"],
        "withheld_reason": quote["withheld_reason"],
    }


def member_record_view(conn, member_id: str, role: str, verified: bool) -> dict:
    role = (role or "").strip()
    if role not in ADVOCATE_RECORD_ROLES:
        raise APIError("Unknown role.")
    member_id = _require_member(member_id)
    payload = profile_payload(member_id)
    payload["role"] = role
    payload["verified"] = bool(verified)
    payload["illustrative"] = True
    payload["note"] = ILLUSTRATIVE
    if not verified:
        _strip_unverified_profile(payload)
        payload["role"] = role
        payload["verified"] = False
        row = _approved_title(conn, UNVERIFIED_TITLE)
        ref = _ref_from_row(row, advocate=True) if row is not None else None
        if ref is None:
            payload["withheld_reason"] = UNVERIFIED_FALLBACK
            payload["units"] = []
        else:
            payload["withheld_reason"] = ref["text"]
            payload["units"] = [ref]
        return payload
    prices = [_priced_row(conn, member_id, drug) for drug in payload["drugs"]]
    payload["prices"] = prices
    payload["withheld_reason"] = ""
    gate = _unit_ref(conn, price_disclaimer_id("preferred_retail", 30), advocate=True, search_visible=False)
    units = []
    if gate is not None:
        units.append(gate)
        if any(item["note"] == SPECIALTY_NOTE for item in prices):
            specialty = _unit_ref(conn, SPECIALTY_RULE, advocate=True)
            if specialty is not None:
                units.append(specialty)
    payload["units"] = units
    from src.finish import authorized_contacts

    extra = authorized_contacts(conn, member_id)
    if extra:
        payload["recent_contacts"] = extra + list(payload.get("recent_contacts") or [])
    return payload


def advocate_plan_fields(conn, member_id: str, question: str, intent: dict) -> dict:
    """Advocate wording and plan figures for a verified price or visit question."""
    fields_read = {"read_order": list(READ_ORDER)}
    if intent.get("intent") == "price":
        quote = drug_price_view(
            conn,
            member_id,
            intent["drug_id"],
            intent["pharmacy"],
            intent["days"],
            advocate=True,
        )
        fields = {"kind": "price", "price": quote, "units": quote["units"], **fields_read}
        if price_comparison(question):
            fields["price_options"] = price_options_view(
                conn, member_id, intent["drug_id"], advocate=True
            )
        return fields
    quote = visit_cost_view(
        conn, member_id, intent["visit"], intent["network"], advocate=True
    )
    return {"kind": "visit_cost", "visit_cost": quote, "units": quote["units"], **fields_read}


def unverified_rule(conn) -> dict:
    """The approved advocate rule, with no plan figures."""
    row = _approved_title(conn, UNVERIFIED_TITLE)
    ref = _ref_from_row(row, advocate=True) if row is not None else None
    if ref is None:
        return {"text": UNVERIFIED_FALLBACK, "units": []}
    return {"text": ref["text"], "units": [ref]}


def _chat_base(question: str) -> dict:
    return {
        "abstained": False,
        "reply": "",
        "member_text": "",
        "citation": "",
        "title": "",
        "version": None,
        "unit_id": "",
        "question": question,
        "suggestions": [],
        "chips": [],
        "units": [],
        "show_unit_id": False,
        "illustrative": True,
    }


def _unit_answer(conn, body: dict, unit_id: str) -> dict:
    """Member wording for one approved unit, cited, with no advocate script."""
    ref = _unit_ref(conn, unit_id, advocate=False)
    body["kind"] = "answer"
    body["abstained"] = False
    body["show_unit_id"] = False
    if ref is None:
        body["abstained"] = True
        body["kind"] = "handoff"
        body["reply"] = "I cannot look that up right now. Try a topic, or I can connect you with a member advocate."
        return body
    body["reply"] = f"{ref['text']} {ref['citation']}".strip()
    body["member_text"] = ref["text"]
    body["citation"] = ref["citation"]
    body["title"] = ref["title"]
    body["version"] = ref["version"]
    body["unit_id"] = ref["unit_id"]
    body["units"] = [ref]
    return body


def _hidden_member(conn, unit_id: str) -> dict | None:
    return _unit_ref(conn, unit_id, advocate=False, search_visible=False)


def _record_safety(conn, question: str) -> None:
    from src.engine import now_et, redact_query

    conn.execute(
        """
        INSERT INTO safety_signals (ts, question, unit_id, channel)
        VALUES (?, ?, ?, 'member')
        """,
        (now_et(), redact_query(question or ""), SAFE_ID),
    )
    conn.commit()


def _fill_unit(body: dict, ref: dict | None, kind: str) -> dict:
    body["kind"] = kind
    body["show_unit_id"] = False
    if ref is None:
        body["kind"] = "handoff"
        body["abstained"] = True
        body["reply"] = "I cannot look that up right now. Try a topic, or I can connect you with a member advocate."
        return body
    body["abstained"] = False
    body["reply"] = ref["text"]
    body["member_text"] = ref["text"]
    body["citation"] = ref["citation"]
    body["title"] = ref["title"]
    body["version"] = ref["version"]
    body["unit_id"] = ref["unit_id"]
    body["units"] = [ref]
    return body


def ivr_prompt_map(conn) -> dict:
    prompts = {}
    for key, unit_id in (
        ("authenticate", IVR_AUTH_ID),
        ("before_amount", IVR_BEFORE_ID),
        ("advocate", IVR_ADVOCATE_ID),
        ("add_caller", IVR_ADD_ID),
        ("greeting", "U-IVR-GREETING-001"),
        ("anything_else", "U-IVR-ANYTHING-001"),
        ("no_answer", "U-IVR-NOANSWER-001"),
        ("verified", "U-IVR-VERIFIED-001"),
    ):
        ref = _hidden_member(conn, unit_id)
        if ref is not None:
            prompts[key] = ref
    return prompts


def _oop_reply(conn, body: dict, member_id: str) -> dict:
    ref = _hidden_member(conn, OOP_ID)
    body["read_order"] = list(READ_ORDER)
    if ref is None:
        body["kind"] = "handoff"
        body["abstained"] = True
        body["withheld_reason"] = "The out-of-pocket figure stays hidden until Legal approves its disclaimer."
        body["reply"] = body["withheld_reason"]
        return body
    profile = profile_payload(member_id)
    oop = profile["oop"]
    body["kind"] = "plan_figure"
    body["abstained"] = False
    body["reply"] = (
        f"Your out-of-pocket maximum is {oop['limit_display']}. You have spent {oop['spent_display']}."
    )
    body["plan_figure"] = {"name": "out_of_pocket", **oop}
    body["units"] = [ref]
    _cite_template(conn, body, "U-TPL-OOP-001")
    body["member_text"] = ref["text"]
    body["citation"] = ref["citation"]
    body["title"] = ref["title"]
    body["version"] = ref["version"]
    body["unit_id"] = ref["unit_id"]
    return body


def _overcharge_reply(conn, body: dict, choice: str) -> dict:
    unit_id = {
        "estimate": "U-RX-OVER-ESTIMATE-001",
        "supply": "U-RX-OVER-SUPPLY-001",
        "deductible": "U-RX-OVER-DEDUCT-001",
        "not_on_list": "U-RX-OVER-LIST-001",
    }.get(choice, "")
    if not unit_id:
        body["kind"] = "handoff"
        body["abstained"] = True
        body["reply"] = "I cannot look that up right now. Try a topic, or I can connect you with a member advocate."
        return body
    ref = _hidden_member(conn, unit_id) or _unit_ref(conn, unit_id, advocate=False, search_visible=False)
    return _fill_unit(body, ref, "answer")


def _cite_template(conn, body: dict, unit_id: str) -> None:
    ref = _hidden_member(conn, unit_id)
    if ref is None:
        return
    units = list(body.get("units") or [])
    units.append(ref)
    body["units"] = units


def _price_compare(conn, body: dict, member_id: str, intent: dict) -> dict:
    from src.member_data import drug_by_id, money

    retail = drug_price_view(conn, member_id, intent["drug_id"], "preferred_retail", 30)
    mail = drug_price_view(conn, member_id, intent["drug_id"], "mail_order", 90)
    body["kind"] = "price_compare"
    body["read_order"] = list(READ_ORDER)
    body["price_options"] = [
        {"pharmacy": "preferred_retail", "days": 30, "price": retail.get("price"), "price_display": retail.get("price_display"), "available": retail.get("available")},
        {"pharmacy": "mail_order", "days": 90, "price": mail.get("price"), "price_display": mail.get("price_display"), "available": mail.get("available")},
    ]
    units = []
    for quote in (retail, mail):
        for unit in quote.get("units") or []:
            if unit not in units:
                units.append(unit)
    body["units"] = units
    retail_month = retail.get("price")
    mail_month = None
    if isinstance(mail.get("price"), int):
        mail_month = mail["price"] // 3
    difference = None
    if isinstance(retail_month, int) and isinstance(mail_month, int):
        difference = retail_month - mail_month
    drug = drug_by_id(intent["drug_id"]) or {}
    name = drug.get("name") or "This drug"
    body["per_month"] = {
        "preferred_retail_30": retail_month,
        "mail_order_90": mail_month,
        "difference": difference,
        "illustrative": True,
    }
    if difference is None:
        body["reply"] = f"{name}: one of these prices is waiting on an approved rule."
        body["abstained"] = True
    else:
        body["abstained"] = False
        body["reply"] = (
            f"{name}: a 30-day supply at a preferred pharmacy is {retail.get('price_display') or 'unavailable'} a month. "
            f"A 90-day mail supply is {mail.get('price_display') or 'unavailable'}, "
            f"about {money(mail_month)} a month. "
            f"The per-month difference is {money(abs(difference))}. These figures are illustrative."
        )
    body["ivr_prompts"] = ivr_prompt_map(conn)
    _cite_template(conn, body, "U-TPL-PRICE-001")
    return body


def _drug_total(conn, body: dict, member_id: str) -> dict:
    from src.member_data import member_drugs, money

    rows = []
    total = 0
    units = []
    missing = False
    for drug in member_drugs(member_id, include_tier=False):
        quote = drug_price_view(conn, member_id, drug["drug_id"], "preferred_retail", 30)
        amount = quote.get("price")
        if not isinstance(amount, int):
            missing = True
            amount_display = ""
        else:
            total += amount
            amount_display = quote.get("price_display") or money(amount)
        for unit in quote.get("units") or []:
            if unit not in units:
                units.append(unit)
        rows.append({
            "drug_id": drug["drug_id"],
            "name": drug["name"],
            "price": amount if isinstance(amount, int) else None,
            "price_display": amount_display,
            "disclaimer_unit_id": (quote.get("units") or [{}])[0].get("unit_id") if quote.get("units") else "",
            "illustrative": True,
        })
    body["kind"] = "drug_total"
    body["read_order"] = list(READ_ORDER)
    body["drugs"] = rows
    body["monthly_total"] = None if missing else total
    body["monthly_total_display"] = "" if missing else money(total)
    body["units"] = units
    body["abstained"] = missing
    if missing:
        body["reply"] = "One of these drugs is waiting on an approved price rule, so there is no monthly total yet."
    else:
        names = ", ".join(f"{row['name']} {row['price_display']}" for row in rows)
        body["reply"] = (
            f"This month at a preferred pharmacy, 30-day supplies: {names}. "
            f"The monthly total is {money(total)}. Each figure is illustrative and uses its disclaimer."
        )
    _cite_template(conn, body, "U-TPL-PRICE-001")
    return body


def chat_intent_view(conn, member_id: str, question: str, intent: dict) -> dict:
    kind = intent["intent"]
    body = _chat_base(question)
    if kind == "safety":
        _record_safety(conn, question)
        return _fill_unit(body, _hidden_member(conn, SAFE_ID), "safety")
    if kind == "out_of_scope":
        body["kind"] = "out_of_scope"
        body["abstained"] = True
        body["reply"] = OUT_OF_SCOPE_REPLY
        return body
    if kind == "oop":
        return _oop_reply(conn, body, member_id)
    if kind == "overcharge_reason":
        return _overcharge_reply(conn, body, intent.get("choice") or "")
    if kind == "handoff_offer":
        body["kind"] = "handoff_offer"
        body["abstained"] = False
        if intent.get("person"):
            ref = _unit_ref(conn, PERSON_ID, advocate=False, search_visible=False)
            body["reply"] = ref["text"] if ref else HANDOFF_OFFER_REPLY
            body["units"] = [ref] if ref else []
            body["chips"] = list(PERSON_CHIPS)
            if ref:
                body["unit_id"] = ref["unit_id"]
                body["member_text"] = ref["text"]
                body["citation"] = ref["citation"]
                body["title"] = ref["title"]
                body["version"] = ref["version"]
        else:
            body["reply"] = HANDOFF_OFFER_REPLY
            body["chips"] = list(HANDOFF_OFFER_CHIPS)
        return body
    if kind == "definition":
        from src.finish import GLOSSARY_IDS

        return _fill_unit(body, _hidden_member(conn, GLOSSARY_IDS.get(intent.get("key") or "", "")), "definition")
    if kind == "cost_help":
        filled = _fill_unit(body, _hidden_member(conn, "U-BEN-COST-HELP-001"), "cost_help")
        filled["chips"] = ["Talk to a member advocate"]
        return filled
    if kind == "callback":
        return _fill_unit(body, _hidden_member(conn, "U-IVR-CALLBACK-001"), "callback")
    if kind == "grievance":
        filled = _fill_unit(body, _hidden_member(conn, "U-BEN-GRIEVANCE-001"), "grievance")
        filled["chips"] = ["Talk to a member advocate"]
        return filled
    if kind == "claims":
        from src.member_data import profile_payload

        profile = profile_payload(member_id) or {}
        body["kind"] = "claims"
        body["abstained"] = False
        body["reply"] = "Here are the recent claims on the plan record. Figures are illustrative."
        body["claims"] = profile.get("claims") or []
        ref = _hidden_member(conn, CLAIMS_ID)
        if ref is not None:
            body["units"] = [ref]
            body["unit_id"] = ref["unit_id"]
        return body
    if kind == "drug_total":
        return _drug_total(conn, body, member_id)
    if kind == "price_compare":
        return _price_compare(conn, body, member_id, intent)
    if kind in ("referral", "authorized_caller"):
        return _unit_answer(conn, body, intent.get("unit_id") or "")
    if kind == "clarify_drug":
        body["kind"] = "clarify"
        body["abstained"] = True
        body["reply"] = CLARIFY_DRUG_REPLY
        body["chips"] = drug_clarify_chips(member_id)
        return body
    if kind == "clarify_visit":
        body["kind"] = "clarify"
        body["abstained"] = True
        body["reply"] = CLARIFY_VISIT_REPLY
        body["chips"] = visit_chips()
        return body
    if kind == "price":
        quote = drug_price_view(conn, member_id, intent["drug_id"], intent["pharmacy"], intent["days"])
        body["kind"] = "price"
        body["read_order"] = list(READ_ORDER)
        body["reply"] = price_reply(quote, covered=bool(intent.get("covered")))
        body["price"] = quote
        body["units"] = quote["units"]
        body["chips"] = price_chips(quote)
        body["ivr_prompts"] = ivr_prompt_map(conn)
        if quote["units"]:
            body["citation"] = quote["units"][0]["citation"]
        _cite_template(conn, body, "U-TPL-PRICE-001")
        return body
    if kind == "visit_cost":
        quote = visit_cost_view(conn, member_id, intent["visit"], intent["network"])
        body["kind"] = "visit_cost"
        body["read_order"] = list(READ_ORDER)
        body["reply"] = visit_reply(quote)
        body["visit_cost"] = quote
        body["units"] = quote["units"]
        body["chips"] = visit_chips(intent["visit"])
        body["ivr_prompts"] = ivr_prompt_map(conn)
        if quote["units"]:
            body["citation"] = quote["units"][0]["citation"]
        _cite_template(conn, body, "U-TPL-VISIT-001")
        if intent.get("visit") == "specialist":
            _cite_template(conn, body, "U-TPL-REFERRAL-NOTE-001")
        return body
    raise APIError("Unknown intent.")
