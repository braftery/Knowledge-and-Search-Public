"""Pass 5 checks that stay deterministic: safety, cost language, time, and names.

Member-facing sentences live on approved units. This module only classifies
and redacts. It does not write reply wording.
"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

READ_ORDER = ["units", "reply"]

SAFE_ID = "U-SAFE-CRISIS-001"
OOP_ID = "U-BEN-OOP-001"
OON_RULE_ID = "U-BEN-OON-RULE-001"
OON_VISIT_ID = "U-BEN-OON-VISIT-001"
ER_ID = "U-BEN-ER-001"
UC_ID = "U-BEN-UC-001"
CLAIMS_ID = "U-BEN-CLAIMS-001"
DEDUCT_ID = "U-BEN-DEDUCT-001"
NOT_ON_LIST_ID = "U-RX-NOT-ON-LIST-001"
IVR_AUTH_ID = "U-IVR-AUTH-001"
IVR_BEFORE_ID = "U-IVR-BEFORE-001"
IVR_ADVOCATE_ID = "U-IVR-ADVOCATE-001"
IVR_ADD_ID = "U-IVR-ADD-001"
PERSON_ID = "U-HANDOFF-PERSON-001"

MAIL_RULE_ID = "U-RX-EDU-001-12"
CAREGIVER_ID = "U-RX-EDU-001-05"
SPECIALTY_REVIEW_ID = "U-RX-EDU-001-13"
REVIEW_EXTENSION = (
    "Extended through 2027-01-15 by Dana Okafor (Legal) while the review is open. Illustrative."
)

# Illustrative full cost while a tier 3 drug is still in the Part D deductible.
# Tiers 1 and 2, and insulin, keep the copay table.
DEDUCTIBLE_AMOUNT = {
    ("preferred_retail", 30): 180,
    ("preferred_retail", 90): 250,
    ("standard_retail", 30): 180,
    ("standard_retail", 90): 250,
    ("mail_order", 90): 200,
}

_SAFETY = re.compile(
    r"\b("
    r"chest pain|heart attack|can'?t breathe|cannot breathe|cant breathe|"
    r"shortness of breath|not breathing|stroke|overdose|overdosed|"
    r"suicid\w*|kill myself|killing myself|harm myself|harming myself|"
    r"hurt myself|hurting myself|end my life|want to die|unconscious|"
    r"severe bleeding|poisoned|poisoning"
    r")\b",
    re.IGNORECASE,
)
_HUMAN = re.compile(
    r"\b(real person|talk to someone|talk to a person|talk to an agent|"
    r"representative|operator)\b|\b(agent|human)\b",
    re.IGNORECASE,
)
_THIRD = re.compile(
    r"\b(caregiver|caregivers|daughter|daughters|son|sons|wife|husband|"
    r"spouse|partner|family)\b",
    re.IGNORECASE,
)
_FILL = re.compile(r"\b(90|supply|fill|mail)\b", re.IGNORECASE)
_OOP = re.compile(
    r"\b(out of pocket|oop|maximum out of pocket|out of pocket max|most i would pay|most you would pay)\b",
    re.IGNORECASE,
)
_NUMBER_WORD = (
    r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)"
)
_SPELLED_AMOUNT = re.compile(
    rf"\b{_NUMBER_WORD}(?:[-\s]{_NUMBER_WORD})+\b|\b{_NUMBER_WORD}\s+dollars?\b",
    re.IGNORECASE,
)
_EXTRA_COST = re.compile(
    r"\b(?:dollars?|cents?|free|guarantees?|guaranteed|covered|pay|coverage)\b|"
    r"\d+(?:\.\d+)?\s*(?:%|percent)\b",
    re.IGNORECASE,
)
_AMOUNT_IN_TEXT = re.compile(
    r"\$\s?\d|\b\d+(?:\.\d+)?\s*(?:%|percent)\b|\b(?:dollars?|cents?)\b",
    re.IGNORECASE,
)
_PHONE = re.compile(
    r"(?<!\w)(?:\+?1[\s.-]*)?(?:\(\s*\d{3}\s*\)|\d{3})[\s.-]*\d{3}[\s.-]*\d{4}\b"
)

STAFF_NAMES = (
    "Dana Okafor",
    "Sam Patel",
    "Riley Chen",
    "Alex Nguyen",
)
SESSION_LEGAL_NAME = "Dana Okafor (Legal)"
SESSION_AUTHOR_NAME = "Sam Patel (Knowledge Ops)"
OTHER_AUTHOR_NAME = "Alex Nguyen (Knowledge Ops)"

TIMESTAMP_ERROR = "Use a timestamp like 2026-09-24T10:00:00Z or 2026-09-24 10:00 ET."
MAIL_WITHHELD = "Mail-order prices stay hidden until Legal resolves the mail-order rule."
UNVERIFIED_GATE = "verified"


def is_safety(text: str) -> bool:
    return _SAFETY.search(text or "") is not None


def is_human_request(text: str) -> bool:
    return _HUMAN.search(text or "") is not None


def is_third_party(text: str) -> bool:
    return _THIRD.search(text or "") is not None


def is_fill_request(text: str) -> bool:
    return _FILL.search(text or "") is not None


def is_oop(text: str) -> bool:
    return _OOP.search(text or "") is not None


def mentions_expanded_cost(text: str) -> bool:
    chunk = text or ""
    if _SPELLED_AMOUNT.search(chunk) or _EXTRA_COST.search(chunk):
        return True
    return False


def text_has_amount(text: str) -> bool:
    return _AMOUNT_IN_TEXT.search(text or "") is not None


def overcharge_choice(text: str) -> str:
    """A reason chip the member can send back, or an empty string.

    A plain deductible question stays on the plan path. Only the chip, or a
    complaint that names the deductible, selects this reason.
    """
    lowered = (text or "").lower()
    if "not on my list" in lowered or "not on the list" in lowered:
        return "not_on_list"
    if "different supply" in lowered or "the supply was different" in lowered:
        return "supply"
    if "pharmacy charged more" in lowered or lowered.strip() == "the pharmacy charged more than the estimate":
        return "estimate"
    if "more than the estimate" in lowered and "charged more than i expected" not in lowered and "higher than" not in lowered:
        return "estimate"
    if "this may be my deductible" in lowered:
        return "deductible"
    return ""


def parse_timestamp(timestamp: str) -> datetime:
    """Naive America/New_York moment. A date alone means 23:59 that day.

    Accepts RFC 3339 and `YYYY-MM-DD HH:MM ET`. Raises ValueError on bad input.
    """
    raw = (timestamp or "").strip()
    if not raw:
        raise ValueError("A timestamp is required.")
    if raw.endswith(" ET"):
        raw = raw[: -len(" ET")].strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        parsed = datetime.strptime(raw, "%Y-%m-%d")
        return parsed.replace(hour=23, minute=59)
    iso = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso)
    except ValueError:
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(ET).replace(tzinfo=None)
        return parsed
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(TIMESTAMP_ERROR)


def redact_phones(text: str) -> str:
    return _PHONE.sub("[redacted]", text or "")


def person_names() -> list[str]:
    """Known fictional names, longest first, so a full name wins over a shorter one."""
    from src.member_data import load

    found = list(STAFF_NAMES)
    for member in load().get("members") or []:
        name = (member.get("name") or "").strip()
        if name:
            found.append(name)
            parts = name.split()
            if len(parts) >= 2:
                found.append(parts[0])
    unique = []
    seen = set()
    for name in found:
        key = name.lower()
        if key in seen or len(name) < 3:
            continue
        seen.add(key)
        unique.append(name)
    unique.sort(key=len, reverse=True)
    return unique


def _allow_phrases() -> set[str]:
    from src.member_data import formulary

    phrases = {
        "harbor health",
        "harbor medicare advantage",
        "harbor medicare advantage hmo",
        "harbor preferred pharmacy",
        "harbor specialty pharmacy",
        "preferred pharmacy",
        "specialty pharmacy",
        "medicare advantage",
        "part d",
        "initial coverage",
        "ozempic",
    }
    for drug in formulary():
        phrases.add(drug["name"].lower())
        for alias in drug.get("aliases") or []:
            phrases.add(str(alias).lower())
    return phrases


def _name_allowed(name: str, source: str) -> bool:
    cleaned = re.sub(r"\s+", " ", (name or "").strip()).lower()
    if not cleaned:
        return True
    allowed = _allow_phrases()
    if cleaned in allowed:
        return True
    source_l = source.lower()
    for phrase in allowed:
        if cleaned in phrase and phrase in source_l:
            return True
    return False


_CONTEXT_NAME = re.compile(
    r"(?i:\b(?:my name is|i am|i'm|this is|caller|name\s*:|for|"
    r"my (?:daughter|son|wife|husband|mother|father|caregiver))\s+)"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
)
_CAPS_RUN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")


def redact_names(text: str) -> str:
    """Redact a name from the roster, from a name cue, or from a capitalised run.

    Drug names, plan names, pharmacy names, and place names used in the product
    stay. A single capitalised word at the start of a sentence stays.
    """
    value = text or ""
    if not value:
        return value

    def context_sub(match):
        name = match.group(1)
        if _name_allowed(name, value):
            return match.group(0)
        return match.group(0)[: match.start(1) - match.start(0)] + "[redacted]"

    value = _CONTEXT_NAME.sub(context_sub, value)

    def run_sub(match):
        name = match.group(1)
        if _name_allowed(name, text or ""):
            return name
        start = match.start()
        source = text or ""
        at_sentence = start == 0 or (start >= 2 and source[start - 2 : start] in {". ", "! ", "? "})
        words = name.split()
        starters = {
            "Is", "The", "A", "An", "What", "How", "Can", "Do", "Does", "My",
            "This", "When", "Where", "Who", "Will", "Are", "Did", "If", "For",
        }
        if at_sentence and words and words[0] in starters:
            rest = " ".join(words[1:])
            if len(words) < 3 or _name_allowed(rest, source):
                return name
            return words[0] + " [redacted]"
        return "[redacted]"

    value = _CAPS_RUN.sub(run_sub, value)
    for name in person_names():
        value = re.sub(rf"\b{re.escape(name)}\b", "[redacted]", value, flags=re.IGNORECASE)
    return value


def caregiver_price_question(query: str) -> bool:
    """The known pharmacy miss: a caregiver with no authorization, and a price."""
    text = (query or "").lower()
    if "caregiver" not in text and "authorization" not in text:
        return False
    return any(word in text for word in ("price", "cost", "copay", "pay", "give"))
