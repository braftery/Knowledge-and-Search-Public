"""Screen copy and Explore fixtures mirrored from the Streamlit UI.

The Streamlit modules import the UI toolkit, so the API keeps its own copy of
the labels, call scripts, and member topics those screens show.
"""

SCREENS = [
    (0, "Today's problem"),
    (1, "Extract units"),
    (2, "Find copies"),
    (3, "Legal approves"),
    (4, "Search"),
    (5, "Every channel"),
    (6, "Gaps"),
    (7, "Drift"),
    (8, "Quality"),
]
STEP_NAMES = dict(SCREENS)
SHORT_DEMO = (0, 1, 3, 4, 5)

TITLES = {
    0: "Today: one disclaimer, three wordings",
    1: "AI turns a script into knowledge units",
    2: "AI finds copies and conflicts",
    3: "Legal approves units, not documents",
    4: "One question, two roles, scoped answers",
    5: "Author once, every channel updates",
    6: "Unanswered questions become the next units",
    7: "When the source changes, the unit is flagged",
    8: "We measure retrieval before we trust it",
}

CAPTIONS = {
    0: "An advocate searches for the Rx pricing disclaimer during a call.",
    1: "The line an advocate must read is buried in a long script.",
    2: "Copies of the same legal line have drifted apart across documents.",
    3: "Approval is on the unit. Legal approves regulated wording, and search sees nothing until it is approved.",
    4: "Each role gets the approved line it is allowed to read, or a clear no-answer.",
    5: "The advocate and the member read the same approved unit. A Legal edit publishes one new version to both.",
    6: "Questions with no approved answer become the next units to write.",
    7: "When a source document changes, the approved unit is flagged and a person decides.",
    8: "These claims only matter if we measure them. Every figure here is illustrative.",
}

SCREEN_ROLE = {
    0: "Pharmacy advocate",
    1: "Knowledge Ops author",
    2: "Knowledge Ops author",
    3: "Legal approver",
    4: "Pharmacy advocate",
    5: "Legal approver",
    6: "Knowledge owner",
    7: "Knowledge owner",
    8: "Knowledge owner",
}

DOC_NAMES = {
    "SRC-RX-EDU-001": "Rx education script v1",
    "SRC-RX-EDU-002": "Rx education script v2 (desk copy)",
    "SRC-WEB-FAQ": "Website FAQ",
    "SRC-BEN-COST-001": "Benefits cost guide",
    "SRC-SPEC-SOP-001": "Specialty pharmacy intake SOP",
    "SRC-PA-FAQ-001": "Prior authorization FAQ for advocates",
    "SRC-CALLBACK-001": "Member callback policy",
    "SRC-WEB-MAIL-001": "Member website: mail-order pharmacy page",
}

TODAY_QUERY = "Rx pricing disclaimer"
PHARMACY_ONLY_QUERY = "do specialty drugs stay at the specialty pharmacy"
SEARCH_ROLES = ("Pharmacy advocate", "Insurance advocate")

ROLE_PAGES = {
    "Knowledge Ops author": ["My work", "Library", "Source documents", "Copies and conflicts"],
    "Legal approver": ["Review inbox", "Revise wording", "Version history"],
    "Pharmacy advocate": ["Agent desktop", "What I can read"],
    "Insurance advocate": ["Agent desktop", "What I can read"],
    "Member": ["App chat", "Website", "Phone line"],
    "Knowledge owner": ["Insights", "Gaps", "Drift", "Quality"],
    "Channel and AI team": ["Quick start", "API reference", "Change events", "Product backlog"],
}

ROLE_INTRO = {
    "Knowledge Ops author": "Your workspace opens on what needs you now, with the first item already open.",
    "Legal approver": "A notification brings you here. Each item opens on one page with everything you need to decide.",
    "Pharmacy advocate": "You are on a live call. The knowledge panel already shows the approved answer for the call reason.",
    "Insurance advocate": "You are on a live call. The knowledge panel already shows the approved answer for the call reason.",
    "Member": "You never see the knowledge system. You see Harbor Health's app, website, and phone line, all saying the same thing.",
    "Knowledge owner": "Your weekly view: what people could not find, what changed, and how well retrieval works.",
    "Channel and AI team": "You build channels and AI features. You render approved units by reference through the API.",
}

QUESTION_BANK = {
    "Pharmacy advocate": [
        "what do I say before I quote a cost",
        "rx price disclamer",
        "how long does a part d prior auth take",
        "Do specialty drugs stay at the specialty pharmacy?",
        "When can I offer 90-day mail order for a maintenance drug?",
        "formulary tier, can I quote a price before I verify the member?",
        "What closing line do I read at the end of an Rx education call?",
        "Can I talk about the drug and the price when a caregiver has no authorization on the account?",
    ],
    "Insurance advocate": [
        "what do I say before I quote a cost",
        "What do I say before I quote a medical cost?",
        "Does a specialist visit on a Harbor Medicare Advantage HMO need a referral?",
        "What is the MOOP for this MA plan?",
        "Do specialty drugs stay at the specialty pharmacy?",
        "What closing line do I read at the end of an Rx education call?",
    ],
    "Member": [
        "How much will my prescription cost?",
        "Is the price I see a guarantee?",
        "Does my specialist visit need a referral?",
        "Do specialty drugs go through mail order?",
    ],
}

MEMBER_TOPICS = [
    {"label": "Drug price estimates", "anchor": "pricing", "unit_id": None, "question": "How much will my prescription cost?"},
    {"label": "Cost of a doctor visit", "anchor": None, "unit_id": "U-BEN-COST-001-02", "question": "What will my doctor visit cost?"},
    {"label": "Specialist referrals", "anchor": None, "unit_id": "U-BEN-COST-001-05", "question": "Do I need a referral to see a specialist?"},
    {"label": "Specialty pharmacy", "anchor": None, "unit_id": "U-RX-EDU-001-13", "question": "Can my specialty drug come by mail?"},
    {"label": "Someone calling for me", "anchor": None, "unit_id": "U-RX-EDU-001-05", "question": "Can my daughter call about my drugs?"},
]

CALLS = {
    "Pharmacy advocate": {
        "Drug price question": {
            "member": "Dana R.",
            "plan": "Harbor Medicare Advantage HMO",
            "detail": "Asking what a 30-day fill of a maintenance drug will cost at a retail pharmacy.",
            "verified": True,
            "questions": [
                "what do I say before I quote a cost",
                "formulary tier, can I quote a price before I verify the member?",
            ],
        },
        "Specialty drug": {
            "member": "Luis M.",
            "plan": "Harbor Medicare Advantage HMO",
            "detail": "Wants a specialty drug moved to mail order to save a trip.",
            "verified": True,
            "questions": ["Do specialty drugs stay at the specialty pharmacy?"],
        },
        "Mail-order request": {
            "member": "Grace T.",
            "plan": "Harbor Medicare Advantage HMO",
            "detail": "Asks for a 90-day mail-order supply of a maintenance drug on the first fill.",
            "verified": True,
            "questions": ["When can I offer 90-day mail order for a maintenance drug?"],
        },
        "Prior authorization status": {
            "member": "Ken W.",
            "plan": "Harbor Medicare Advantage HMO",
            "detail": "Asks how long a Part D prior authorization decision will take.",
            "verified": True,
            "questions": ["How long does a Part D prior authorization take?"],
        },
    },
    "Insurance advocate": {
        "Specialist visit cost": {
            "member": "Maria S.",
            "plan": "Harbor Medicare Advantage HMO",
            "detail": "Asks what a cardiology visit will cost and whether she needs anything first.",
            "verified": True,
            "questions": [
                "What do I say before I quote a medical cost?",
                "Does a specialist visit on a Harbor Medicare Advantage HMO need a referral?",
            ],
        },
        "Out-of-pocket maximum": {
            "member": "Robert A.",
            "plan": "Harbor Medicare Advantage HMO",
            "detail": "Asks for this year's maximum out-of-pocket amount.",
            "verified": True,
            "questions": ["What is the MOOP for this MA plan?"],
        },
        "Specialty drug (wrong queue)": {
            "member": "Ann P.",
            "plan": "Harbor Medicare Advantage HMO",
            "detail": "Transferred from the main line with a specialty pharmacy question.",
            "verified": True,
            "questions": ["Do specialty drugs stay at the specialty pharmacy?"],
        },
    },
}

KIND_LABELS = {
    "couldnt_find": "Could not find it",
    "hard_to_find": "Hard to find",
    "confusing_wording": "Wording confused the member",
    "wrong_or_outdated": "Looks wrong or out of date",
    "no_answer": "No approved answer",
    "not_helpful": "Member said it did not help",
    "clarified": "Bot had to ask a clarifying question",
    "handed_off": "Bot handed off to a person",
    "rephrased": "Member rephrased the question",
    "slow": "Slow to answer",
}

ADVOCATE_FLAG_KINDS = ["couldnt_find", "hard_to_find", "confusing_wording", "wrong_or_outdated"]

WORK_GROUPS = [
    "Sent back by Legal",
    "Waiting for your approval",
    "Flagged by advocates and channels",
    "New extractions to confirm",
    "Source changed",
    "Drafts assigned to you",
]

EXPLORE_LIVE_CAP = 20
MEMBER_CHANNELS = {"member_chat", "voice_bot", "website"}
ILLUSTRATIVE = "Illustrative, made-up data"

_STOP = set("a an the is are do does my i me to of for on in at it this that what how can will be with or and".split())
_SAME = {"price": "cost", "cost": "price", "prescription": "drug", "medicine": "drug", "drug": "prescription"}


def doc_name(doc_id: str) -> str:
    return DOC_NAMES.get(doc_id or "", doc_id or "")


def kind_label(kind: str) -> str:
    return KIND_LABELS.get(kind, (kind or "").replace("_", " ").capitalize())


def plain_title(title: str) -> str:
    return (title or "").replace(" (Legal verbatim)", "").replace(" (Legal)", "").lower()
