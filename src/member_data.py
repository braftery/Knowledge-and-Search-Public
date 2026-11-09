"""Mock plan data for the Explore member and advocate views.

Figures are illustrative. The file is the only source of premiums, copays,
formulary rows, and member records. Wording that accompanies a number comes
from an approved unit, attached by the API, and is not written here.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "member_data.json"

DEFAULT_MEMBER_ID = "HBR-20418"
SIGNED_IN_MEMBER = DEFAULT_MEMBER_ID

PHARMACIES = ("preferred_retail", "standard_retail", "mail_order", "specialty")
DAY_OPTIONS = (30, 90)
VISITS = ("primary_care", "specialist", "urgent_care", "emergency")
NETWORKS = ("in", "out")
ADVOCATE_RECORD_ROLES = ("Pharmacy advocate", "Insurance advocate")

SPECIALTY_NOTE = "Specialty drugs fill at Harbor Specialty Pharmacy."
UNAVAILABLE_NOTE = "This supply is not available at that pharmacy."
OUT_OF_NETWORK_NOTE = "Out of network is not covered, except emergency and urgent care."
REFERRAL_NOTE = "You need a referral from your primary care doctor first."

CLARIFY_DRUG_REPLY = "Which drug? Here are the ones on your list."
CLARIFY_VISIT_REPLY = "What kind of visit?"
OUT_OF_SCOPE_REPLY = (
    "I can help with your Harbor plan: drug prices, visit costs, referrals and pharmacy questions, "
    "or I can connect you with a member advocate."
)
HANDOFF_OFFER_REPLY = "I'm sorry about that. A member advocate can look at your account with you."
HANDOFF_OFFER_CHIPS = [
    "The pharmacy charged more than the estimate",
    "This may be my deductible",
    "The supply was different",
    "A drug not on my list",
    "Talk to a member advocate",
    "See my recent claims",
]
PERSON_CHIPS = ["Talk to a member advocate"]
REFERRAL_UNIT = "U-BEN-COST-001-05"
CAREGIVER_UNIT = "U-RX-EDU-001-05"

VISIT_LABEL = {
    "primary_care": "primary care visit",
    "specialist": "specialist visit",
    "urgent_care": "urgent care visit",
    "emergency": "emergency room visit",
}
VISIT_QUESTION = {
    "primary_care": "What will a primary care visit cost?",
    "specialist": "What will a specialist visit cost?",
    "urgent_care": "What will an urgent care visit cost?",
    "emergency": "What will an emergency room visit cost?",
}
PHARMACY_PHRASE = {
    "preferred_retail": "at a preferred pharmacy",
    "standard_retail": "at a standard pharmacy",
    "mail_order": "by mail",
    "specialty": "at a specialty pharmacy",
}

_PLAN_WORDS = {
    "plan",
    "drug",
    "drugs",
    "medication",
    "medications",
    "prescription",
    "prescriptions",
    "pharmacy",
    "pharmacies",
    "refill",
    "refills",
    "price",
    "prices",
    "cost",
    "costs",
    "copay",
    "copays",
    "pay",
    "covered",
    "coverage",
    "doctor",
    "doctors",
    "visit",
    "visits",
    "specialist",
    "specialists",
    "referral",
    "referrals",
    "claim",
    "claims",
    "deductible",
    "deductibles",
    "insulin",
    "mail",
    "card",
    "cards",
    "benefit",
    "benefits",
}
_GENERIC_DRUG = {"prescription", "prescriptions", "drug", "drugs", "medication", "medications"}
_COST_TOKENS = {"cost", "costs", "price", "prices", "pay", "copay", "copays"}
_SPECIFIC_VISITS = {"primary_care", "specialist", "urgent_care", "emergency"}
_SPECIALIST_WORDS = {
    "specialist",
    "specialists",
    "cardiologist",
    "cardiologists",
    "cardiology",
    "dermatologist",
    "dermatologists",
}
_FAMILY_WORDS = {
    "daughter",
    "daughters",
    "son",
    "sons",
    "wife",
    "husband",
    "spouse",
    "partner",
    "caregiver",
    "caregivers",
    "family",
    "someone",
}
_COMPLAINT_WORDS = {
    "overcharged",
    "charged",
    "bill",
    "billing",
    "upset",
    "angry",
    "complaint",
    "complaints",
    "wrong",
    "refund",
    "refunds",
}
_CALL_WORDS = re.compile(r"\b(?:call|calling|talk)\b")
_REFER_WORDS = re.compile(r"\b(?:referral|referrals|refer)\b")


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(DATA_PATH.read_text())


def money(amount: int) -> str:
    return f"${amount:,}"


def _figure(amount: int) -> dict:
    return {"amount": amount, "display": money(amount)}


def date_of_birth(member_id: str) -> str:
    member = find_member(member_id)
    if member is None:
        return ""
    return str(member.get("date_of_birth") or "")


def identifiers_match(member_id: str, birth: str) -> bool:
    """Illustrative check: the member id and the date of birth on the plan file."""
    member = find_member(member_id)
    if member is None:
        return False
    stored = str(member.get("date_of_birth") or "").strip()
    given = (birth or "").strip()
    return bool(stored) and stored == given


def plan_payload() -> dict:
    plan = load()["plan"]
    pharmacies = []
    for item in load()["pharmacies"]:
        pharmacies.append({
            "name": item["name"],
            "network": item["network"],
            "city": item["city"],
            "display": item["network"].capitalize(),
        })
    return {
        "name": plan["name"],
        "premium": {"amount": plan["premium_monthly"], "display": f"{money(plan['premium_monthly'])} a month"},
        "primary_care": _figure(plan["primary_care"]),
        "specialist": _figure(plan["specialist"]),
        "urgent_care": _figure(plan["urgent_care"]),
        "emergency": _figure(plan["emergency"]),
        "out_of_network": {
            "display": plan["out_of_network"],
            "exceptions": list(plan["out_of_network_exceptions"]),
        },
        "medical_deductible": _figure(plan["medical_deductible"]),
        "out_of_pocket_maximum": _figure(plan["out_of_pocket_maximum"]),
        "part_d_deductible": {
            "amount": plan["part_d_deductible"],
            "display": money(plan["part_d_deductible"]),
            "note": plan["part_d_deductible_note"],
        },
        "pharmacies": pharmacies,
        "nurse_line": plan.get("nurse_line") or "",
        "nurse_line_note": plan.get("nurse_line_note") or "",
    }


def formulary() -> list[dict]:
    return list(load()["formulary"])


def drug_by_id(drug_id: str) -> dict | None:
    for drug in formulary():
        if drug["drug_id"] == drug_id:
            return drug
    return None


def find_member(member_id: str) -> dict | None:
    wanted = (member_id or "").strip()
    for member in load()["members"]:
        if member["member_id"] == wanted:
            return member
    return None


def member_ids() -> list[str]:
    return [member["member_id"] for member in load()["members"]]


def public_drug(drug: dict, *, include_tier: bool) -> dict:
    item = {
        "drug_id": drug["drug_id"],
        "name": drug["name"],
        "strength": drug["strength"],
        "specialty": bool(drug["specialty"]),
    }
    if include_tier:
        item["tier"] = drug["tier"]
    return item


def _claims(member: dict) -> list[dict]:
    rows = []
    for claim in member["claims"]:
        rows.append({
            "date": claim["date"],
            "provider_type": claim["provider_type"],
            "amount_billed": claim["amount_billed"],
            "amount_billed_display": money(claim["amount_billed"]),
            "plan_paid": claim["plan_paid"],
            "plan_paid_display": money(claim["plan_paid"]),
            "member_paid": claim["member_paid"],
            "member_paid_display": money(claim["member_paid"]),
            "status": claim["status"],
            "drug": claim.get("drug") or "",
            "note": claim.get("note") or "",
        })
    return rows


def profile_payload(member_id: str) -> dict | None:
    member = find_member(member_id)
    if member is None:
        return None
    plan = load()["plan"]
    drugs = []
    for drug_id in member["drug_ids"]:
        drug = drug_by_id(drug_id)
        if drug is not None:
            drugs.append(public_drug(drug, include_tier=True))
    return {
        "member": {
            "member_id": member["member_id"],
            "name": member["name"],
            "plan": plan["name"],
        },
        "plan": plan_payload(),
        "coverage_stage": member["coverage_stage"],
        "oop": {
            "limit": plan["out_of_pocket_maximum"],
            "spent": member["oop_spent"],
            "limit_display": money(plan["out_of_pocket_maximum"]),
            "spent_display": money(member["oop_spent"]),
        },
        "drug_deductible": {
            "amount": plan["part_d_deductible"],
            "met": bool(member["drug_deductible_met"]),
        },
        "drugs": drugs,
        "claims": _claims(member),
        "recent_contacts": [dict(item) for item in member["recent_contacts"]],
    }


def member_drugs(member_id: str, *, include_tier: bool) -> list[dict]:
    member = find_member(member_id)
    if member is None:
        return []
    rows = []
    for drug_id in member["drug_ids"]:
        drug = drug_by_id(drug_id)
        if drug is not None:
            rows.append(public_drug(drug, include_tier=include_tier))
    return rows


def _price_key(drug: dict) -> str:
    if drug.get("insulin"):
        return "insulin"
    return str(drug["tier"])


def _tier_label(drug: dict) -> str:
    return f"Tier {drug['tier']}"


def _table_amount(drug: dict, pharmacy: str, days: int):
    table = (load()["prices"].get(_price_key(drug)) or {})
    cell = table.get(pharmacy) or {}
    if str(days) not in cell or cell[str(days)] is None:
        return None, ""
    amount = int(cell[str(days)])
    note = ""
    if pharmacy == "specialty" and table.get("coinsurance_note"):
        note = table["coinsurance_note"]
    return amount, note


def drug_quote(member_id: str, drug_id: str, pharmacy: str, days: int) -> dict | None:
    """Price fields for one fill. None when the member or the drug is unknown.

    `available` is false when the table has no price, including a specialty
    drug asked for at another pharmacy. The caller attaches approved units
    and may withhold the number.
    """
    member = find_member(member_id)
    drug = drug_by_id(drug_id)
    if member is None or drug is None:
        return None
    if drug["specialty"] and pharmacy != "specialty":
        amount = None
        note = SPECIALTY_NOTE
        available = False
    else:
        amount, note = _table_amount(drug, pharmacy, days)
        if amount is None:
            note = UNAVAILABLE_NOTE
            available = False
        else:
            available = True
    stage = member["coverage_stage"]
    # Tier 3, other than insulin, is in the deductible until that deductible is met.
    if (
        available
        and int(drug.get("tier") or 0) >= 3
        and not drug.get("insulin")
        and not drug.get("specialty")
        and not member.get("drug_deductible_met")
    ):
        from src.compliance import DEDUCTIBLE_AMOUNT

        deductible_amount = DEDUCTIBLE_AMOUNT.get((pharmacy, days))
        if deductible_amount is not None:
            amount = deductible_amount
            stage = "Deductible"
    return {
        "drug": public_drug(drug, include_tier=True),
        "pharmacy": pharmacy,
        "days": days,
        "available": available,
        "price": amount if available else None,
        "price_display": money(amount) if available else "",
        "tier_label": _tier_label(drug),
        "coverage_stage": stage,
        "note": note,
        "withheld_reason": "",
    }


def visit_quote(member_id: str, visit: str, network: str) -> dict | None:
    member = find_member(member_id)
    if member is None:
        return None
    plan = load()["plan"]
    covered_out = set(plan["out_of_network_exceptions"])
    if network == "out" and visit not in covered_out:
        return {
            "visit": visit,
            "network": network,
            "available": False,
            "cost": None,
            "cost_display": "",
            "note": OUT_OF_NETWORK_NOTE,
            "withheld_reason": "",
        }
    amount = int(plan[visit])
    note = REFERRAL_NOTE if visit == "specialist" else ""
    return {
        "visit": visit,
        "network": network,
        "available": True,
        "cost": amount,
        "cost_display": money(amount),
        "note": note,
        "withheld_reason": "",
    }


def display_strength(strength: str) -> str:
    text = (strength or "").strip()
    if text.endswith(" tablet"):
        return text[: -len(" tablet")]
    return text


def price_reply(quote: dict, *, covered: bool) -> str:
    if quote.get("withheld_reason"):
        return quote["withheld_reason"]
    if not quote.get("available"):
        return quote.get("note") or UNAVAILABLE_NOTE
    drug = quote["drug"]
    strength = display_strength(drug["strength"])
    place = PHARMACY_PHRASE[quote["pharmacy"]]
    supply = f"{quote['days']}-day supply"
    if covered:
        return (
            f"{drug['name']} {strength}, tier {drug['tier']}, {supply} {place}: {quote['price_display']}."
        )
    return f"{drug['name']} {strength}, {supply} {place}: {quote['price_display']}."


def price_chips(quote: dict) -> list[str]:
    name = quote["drug"]["name"].lower()
    pharmacy = quote["pharmacy"]
    days = quote["days"]
    chips = []
    if not (pharmacy == "mail_order" and days == 90):
        chips.append(f"How much is a 90-day supply of {name} by mail?")
    if not (pharmacy == "preferred_retail" and days == 90):
        chips.append(f"How much is a 90-day supply of {name}?")
    if pharmacy != "standard_retail":
        chips.append(f"How much is a 30-day supply of {name} at a standard pharmacy?")
    return chips


def drug_clarify_chips(member_id: str) -> list[str]:
    chips = []
    for drug in member_drugs(member_id, include_tier=False):
        chips.append(f"How much is {drug['name'].lower()}?")
    return chips


def visit_reply(quote: dict) -> str:
    if quote.get("withheld_reason"):
        return quote["withheld_reason"]
    if not quote.get("available"):
        return quote.get("note") or OUT_OF_NETWORK_NOTE
    label = VISIT_LABEL[quote["visit"]]
    article = "An" if quote["visit"] in {"urgent_care", "emergency"} else "A"
    where = "in network" if quote["network"] == "in" else "out of network"
    sentence = f"{article} {label} {where}: {quote['cost_display']}."
    if quote.get("note"):
        return f"{sentence} {quote['note']}"
    return sentence


def visit_chips(current: str | None = None) -> list[str]:
    return [VISIT_QUESTION[visit] for visit in VISITS if visit != current]


def _normalize(question: str) -> str:
    text = (question or "").lower().replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _aliases(drug: dict) -> list[str]:
    names = {drug["name"].lower(), drug["drug_id"].replace("-", " ")}
    if drug.get("insulin"):
        names.add("insulin")
    for alias in drug.get("aliases") or []:
        cleaned = str(alias).strip().lower()
        if cleaned:
            names.add(cleaned)
    return sorted(names, key=len, reverse=True)


def _vocab_tokens() -> set[str]:
    tokens = set(_PLAN_WORDS)
    for drug in formulary():
        for alias in _aliases(drug):
            tokens.update(alias.split())
    return tokens


def _find_drug(text: str) -> dict | None:
    best = None
    best_at = None
    best_len = -1
    for drug in formulary():
        for alias in _aliases(drug):
            match = re.search(rf"\b{re.escape(alias)}\b", text)
            if match is None:
                continue
            at = match.start()
            length = len(alias)
            if best is None or at < best_at or (at == best_at and length > best_len):
                best = drug
                best_at = at
                best_len = length
    return best


def _find_visit(text: str) -> str | None:
    if re.search(r"\bprimary care\b", text):
        return "primary_care"
    if re.search(r"\b(specialist|cardiology|cardiologist)\b", text):
        return "specialist"
    if re.search(r"\burgent care\b|\burgent\b", text):
        return "urgent_care"
    if re.search(r"\bemergency\b|\ber\b", text):
        return "emergency"
    if re.search(r"\bdoctor\b", text):
        return "doctor"
    return None


def _has_cost(text: str, tokens: set[str]) -> bool:
    if "how much" in text or "cheaper" in tokens:
        return True
    if "mail" in tokens and "retail" in tokens:
        return True
    return bool(tokens & _COST_TOKENS)


def price_comparison(question: str) -> bool:
    """A question that compares mail order with retail, or asks which is cheaper."""
    text = _normalize(question)
    tokens = set(text.split())
    if "cheaper" in tokens:
        return True
    return "mail" in tokens and "retail" in tokens


def _pharmacy(text: str) -> str:
    if re.search(r"\bspecialty\b", text):
        return "specialty"
    if re.search(r"\bmail\b", text):
        return "mail_order"
    if re.search(r"\bstandard\b", text):
        return "standard_retail"
    return "preferred_retail"


def _days(text: str) -> int:
    if re.search(r"\b90\b", text):
        return 90
    return 30


def _network(text: str) -> str:
    if "out of network" in text:
        return "out"
    return "in"


def _in_scope(text: str, tokens: set[str]) -> bool:
    if tokens & _vocab_tokens():
        return True
    return _find_drug(text) is not None


def _referral_intent(text: str, tokens: set[str]) -> bool:
    if _REFER_WORDS.search(text):
        return True
    return bool(tokens & _SPECIALIST_WORDS)


def _caller_intent(text: str, tokens: set[str]) -> bool:
    if not (tokens & _FAMILY_WORDS):
        return False
    return _CALL_WORDS.search(text) is not None


def _glossary_key(text: str) -> str:
    if "out of pocket" in text and "my " not in text and any(word in text for word in ("what is", "what's", "define", "mean")):
        return "oop_max"
    if "what is a tier" in text or "what does tier" in text or text.strip() in {"tier", "what is tier"}:
        return "tier"
    if "coverage stage" in text and any(word in text for word in ("what", "mean", "define")):
        return "coverage_stage"
    if "what is a deductible" in text or "what does deductible" in text:
        return "deductible"
    if "preferred retail" in text and any(word in text for word in ("what", "mean", "define")):
        return "preferred_pharmacy"
    if text.strip() in {"what is mail order", "what does mail order mean"} or "what is mail order" in text:
        return "mail_order"
    return ""


def _cost_help(text: str) -> bool:
    phrases = (
        "can't afford",
        "cannot afford",
        "cant afford",
        "can t afford",
        "too expensive",
        "help paying",
        "can't pay",
        "cannot pay",
        "cost help",
    )
    return any(phrase in text for phrase in phrases)


def _callback(text: str) -> bool:
    return "call me back" in text or "callback" in text or "call me later" in text


def _grievance(text: str) -> bool:
    return "grievance" in text or "appeal" in text


def _all_drugs(text: str) -> bool:
    if "all my drug" in text or "all my medicine" in text or "all of my drug" in text:
        return True
    return "how much will all" in text and "drug" in text


def _complaint_intent(tokens: set[str]) -> bool:
    return bool(tokens & _COMPLAINT_WORDS)


def is_general_overcharge(text: str) -> bool:
    """A complaint about a higher charge, before the member picks a reason chip."""
    from src.compliance import overcharge_choice

    lowered = (text or "").lower()
    if overcharge_choice(lowered):
        return False
    phrases = (
        "charged more",
        "more than i expected",
        "more than expected",
        "higher than",
        "overcharg",
        "copay was higher",
        "cost more than",
        "paid more than",
        "bill was higher",
        "too much",
    )
    return any(phrase in lowered for phrase in phrases)


def _keeps_in_library(text: str, tokens: set[str]) -> bool:
    """Plan, billing, family, or complaint words stay out of the out-of-scope reply."""
    if _in_scope(text, tokens):
        return True
    if tokens & _FAMILY_WORDS or tokens & _COMPLAINT_WORDS:
        return True
    return False


def classify_member_question(question: str) -> dict | None:
    """A fixed intent, or None when the question stays on the knowledge path.

    No model call. Safety runs before every other intent. Out of scope is
    returned only when the question has no plan, billing, family, complaint,
    or person-request word.
    """
    from src.compliance import (
        is_fill_request,
        is_human_request,
        is_oop,
        is_safety,
        is_third_party,
        overcharge_choice,
    )

    text = _normalize(question)
    if not text:
        return None
    if is_safety(question) or is_safety(text):
        return {"intent": "safety"}
    choice = overcharge_choice(text)
    if choice:
        return {"intent": "overcharge_reason", "choice": choice}
    if is_general_overcharge(text):
        return {"intent": "handoff_offer", "overcharge": True}
    tokens = set(text.split())
    if _glossary_key(text):
        return {"intent": "definition", "key": _glossary_key(text)}
    if _cost_help(text):
        return {"intent": "cost_help"}
    if _callback(text):
        return {"intent": "callback"}
    if _grievance(text):
        return {"intent": "grievance"}
    if "see my recent claims" in text or "recent claims" in text:
        return {"intent": "claims"}
    if _all_drugs(text):
        return {"intent": "drug_total"}
    drug = _find_drug(text)
    generic_drug = drug is None and bool(tokens & _GENERIC_DRUG)
    visit = _find_visit(text)
    cost = _has_cost(text, tokens)
    covered = "covered" in tokens
    fill = drug is not None and is_fill_request(text)
    if is_oop(text):
        return {"intent": "oop"}
    if drug is not None and (cost or fill) and is_third_party(text):
        return {"intent": "authorized_caller", "unit_id": CAREGIVER_UNIT, "withhold_price": True}
    if drug is not None and covered:
        return {
            "intent": "price",
            "drug_id": drug["drug_id"],
            "pharmacy": "preferred_retail",
            "days": 30,
            "covered": True,
        }
    if drug is not None and (cost or fill):
        intent_name = "price_compare" if price_comparison(text) else "price"
        return {
            "intent": intent_name,
            "drug_id": drug["drug_id"],
            "pharmacy": _pharmacy(text),
            "days": _days(text),
            "covered": False,
        }
    if generic_drug and (cost or covered):
        return {"intent": "clarify_drug"}
    if visit in _SPECIFIC_VISITS and cost:
        return {"intent": "visit_cost", "visit": visit, "network": _network(text)}
    if visit == "doctor" and cost:
        return {"intent": "clarify_visit"}
    if not cost and _referral_intent(text, tokens):
        return {"intent": "referral", "unit_id": REFERRAL_UNIT}
    if is_human_request(text):
        return {"intent": "handoff_offer", "person": True}
    if _caller_intent(text, tokens):
        return {"intent": "authorized_caller", "unit_id": CAREGIVER_UNIT}
    if _complaint_intent(tokens):
        return {"intent": "handoff_offer"}
    if not _keeps_in_library(text, tokens):
        return {"intent": "out_of_scope"}
    return None
