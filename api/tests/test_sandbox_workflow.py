"""Explore sandbox: Knowledge Ops review, grounded gaps, and source changes.

Each numbered test covers one item in the authoring workflow. The guided
world, its candidate pool, and its saved answers stay as they were.
"""

from api.tests.conftest import open_role

PA_TIME = (
    "A standard prior authorization decision takes 4 business days after Harbor receives a complete request. "
    "An expedited request takes 24 hours. These figures are illustrative."
)
HOUR_OLD = (
    "Offer a Harbor callback window on weekdays from 8:00 a.m. to 5:00 p.m. Eastern. "
    "These hours are illustrative."
)
HOUR_NEW = (
    "Offer a Harbor callback window on weekdays from 8:00 a.m. to 6:00 p.m. Eastern. "
    "These hours are illustrative."
)
NOTE_OLD = "Write the callback reason in the desk note before you end the conversation."
NOTE_NEW = "Write the callback reason in the desk note before you end the call."
DUPLICATE = (
    "Specialty drugs stay at Harbor Specialty Pharmacy and are not converted to mail order on this call."
)
SANDBOX_DOCS = ("SRC-SPEC-SOP-001", "SRC-PA-FAQ-001", "SRC-CALLBACK-001")
SEEDED_LEGAL = "U-RX-EDU-001-08"


def _ko(explore):
    return open_role(explore, "Knowledge Ops author")


def _unit(explore, unit_id):
    body = explore.get(f"/api/units/{unit_id}", params={"world": "explore"})
    assert body.status_code == 200, body.text
    return body.json()["unit"]


def test_sandbox_documents_wait_for_knowledge_ops(explore):
    """Item 1. Three explore documents are already extracted and waiting."""
    guided = explore.get("/api/documents/SRC-SPEC-SOP-001", params={"world": "guided"})
    assert guided.status_code == 404

    for doc_id in SANDBOX_DOCS:
        body = explore.get(f"/api/documents/{doc_id}", params={"world": "explore"})
        assert body.status_code == 200, body.text
        document = body.json()
        assert document["body"]
        assert "illustrative" in document["body"].lower()
        assert document["units"]
        for unit in document["units"]:
            assert unit["status"]
            assert unit["routing_reason"]
            assert unit["source_span"]
            if unit["unit_id"] == "U-CB-NUMBER":
                # Seeded drift case: this sentence was deleted from the source on purpose.
                assert unit["source_span"] not in document["body"]
                continue
            assert unit["source_span"] in document["body"]
            assert unit["span_start"] >= 0
            assert unit["span_end"] == unit["span_start"] + len(unit["source_span"])

    sop = explore.get("/api/documents/SRC-SPEC-SOP-001", params={"world": "explore"}).json()
    by_id = {unit["unit_id"]: unit for unit in sop["units"]}
    procedures = ["U-SOP-REFERRAL", "U-SOP-RECORD", "U-SOP-SEND"]
    for unit_id in procedures:
        assert by_id[unit_id]["status"] == "extracted"
        assert by_id[unit_id]["type"] == "procedure"
        assert by_id[unit_id]["routing_owner"] == "knowledge_ops"
        assert by_id[unit_id]["search_visible"] is False
    assert "$40" in by_id["U-SOP-COPAY"]["text"]
    assert by_id["U-SOP-COPAY"]["routing_owner"] == "legal"
    assert "Cost statement" in by_id["U-SOP-COPAY"]["routing_reason"]
    assert by_id["U-SOP-DUPLICATE"]["text"] == DUPLICATE
    assert by_id["U-SOP-DUPLICATE"]["routing_owner"] == "knowledge_ops"
    assert by_id["U-SOP-DUPLICATE"]["duplicate_of"]
    assert "reject" in by_id["U-SOP-DUPLICATE"]["routing_reason"].lower()

    faq = explore.get("/api/documents/SRC-PA-FAQ-001", params={"world": "explore"}).json()
    faqs = {unit["unit_id"]: unit for unit in faq["units"]}
    assert len(faqs) == 5
    for unit_id in ("U-PA-START", "U-PA-ATTACH", "U-PA-TIMING", "U-PA-TELL"):
        assert faqs[unit_id]["type"] == "faq"
        assert faqs[unit_id]["status"] == "extracted"
        assert faqs[unit_id]["routing_owner"] == "knowledge_ops"
    assert faqs["U-PA-TIMING"]["source_span"] == PA_TIME
    assert "4 business days" in faqs["U-PA-TIMING"]["text"]
    assert faqs["U-PA-CLINICAL"]["routing_owner"] == "legal"
    assert "Clinical" in faqs["U-PA-CLINICAL"]["routing_reason"]

    callback = explore.get("/api/documents/SRC-CALLBACK-001", params={"world": "explore"}).json()
    assert callback["kb"] == "benefits,pharmacy"
    calls = {unit["unit_id"]: unit for unit in callback["units"]}
    assert len(calls) == 4
    for unit_id in ("U-CB-HOURS", "U-CB-NOTE", "U-CB-NUMBER"):
        assert calls[unit_id]["type"] == "procedure"
        assert calls[unit_id]["status"] == "approved"
        assert calls[unit_id]["search_visible"] is True
    assert calls["U-CB-HOURS"]["text"] == HOUR_OLD
    assert calls["U-CB-HOURS"]["source_span"] == HOUR_NEW
    assert calls["U-CB-HOURS"]["stale"] is True
    assert calls["U-CB-NOTE"]["text"] == NOTE_OLD
    assert calls["U-CB-NOTE"]["source_span"] == NOTE_NEW
    assert calls["U-CB-NOTE"]["stale"] is True  # the AI is unsure the change is cosmetic, so it waits for Knowledge Ops
    assert calls["U-CB-VERBATIM"]["status"] == "extracted"
    assert calls["U-CB-VERBATIM"]["type"] == "verbatim"
    assert calls["U-CB-VERBATIM"]["routing_owner"] == "legal"
    assert "6:00 p.m." in callback["body"]
    assert NOTE_NEW in callback["body"]


def test_knowledge_ops_review_actions(explore):
    """Item 2. Approve, send to Legal, edit, and reject, each recorded."""
    refused = explore.post(
        "/api/author/units/U-SOP-REFERRAL/review",
        json={"world": "explore", "action": "approve"},
    )
    assert refused.status_code == 403
    assert refused.json()["error"] == "Only the Knowledge Ops author can do this."
    guided = explore.post(
        "/api/author/units/U-SOP-REFERRAL/review",
        json={"world": "guided", "action": "approve"},
    )
    assert guided.status_code == 400
    assert guided.json()["error"] == "This route is for the explore sandbox."

    _ko(explore)
    other = explore.post(
        "/api/author/units/U-RX-EDU-001-01/review",
        json={"world": "explore", "action": "approve"},
    )
    assert other.status_code == 400
    assert other.json()["error"] == "That unit is not in the sandbox queue."

    blocked = explore.post(
        "/api/author/units/U-SOP-COPAY/review",
        json={"world": "explore", "action": "approve"},
    )
    assert blocked.status_code == 400
    assert blocked.json()["error"] == (
        "This unit goes to Legal: Cost statement. Legal approves cost wording."
    )
    clinical = explore.post(
        "/api/author/units/U-PA-CLINICAL/review",
        json={"world": "explore", "action": "approve"},
    )
    assert clinical.status_code == 400
    assert clinical.json()["error"].startswith("This unit goes to Legal:")
    verbatim = explore.post(
        "/api/author/units/U-CB-VERBATIM/review",
        json={"world": "explore", "action": "approve"},
    )
    assert verbatim.status_code == 400
    assert verbatim.json()["error"].startswith("This unit goes to Legal:")

    short = explore.post(
        "/api/author/units/U-SOP-DUPLICATE/review",
        json={"world": "explore", "action": "reject", "reason": "duplicate line"},
    )
    assert short.status_code == 400
    assert short.json()["error"] == "A rejection needs a reason of at least four words."
    rejected = explore.post(
        "/api/author/units/U-SOP-DUPLICATE/review",
        json={
            "world": "explore",
            "action": "reject",
            "reason": "This sentence duplicates an approved unit.",
        },
    )
    assert rejected.status_code == 200, rejected.text
    decision = rejected.json()["decision"]
    assert decision["actor"] == "Knowledge Ops author"
    assert decision["action"] == "reject"
    assert decision["ts"]
    assert decision["reason"] == "This sentence duplicates an approved unit."
    gone = _unit(explore, "U-SOP-DUPLICATE")
    assert gone["status"] == "rejected"
    assert gone["search_visible"] is False

    edited = explore.post(
        "/api/author/units/U-SOP-RECORD/review",
        json={"world": "explore", "action": "edit", "tags": ["intake", "prescriber", "reviewed"]},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "extracted"
    assert edited.json()["decision"]["action"] == "edit"
    assert edited.json()["decision"]["actor"] == "Knowledge Ops author"
    assert "reviewed" in edited.json()["unit"]["tags"]

    approved = explore.post(
        "/api/author/units/U-SOP-REFERRAL/review",
        json={"world": "explore", "action": "approve"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["decision"]["action"] == "approve"
    assert approved.json()["unit"]["search_visible"] is True
    open_role(explore, "Pharmacy advocate")
    before = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "Record the prescriber name and the medicine name on the intake form before you save it.",
            "record": False,
        },
    ).json()["result"]
    assert "U-SOP-RECORD" not in [row["unit_id"] for row in before["ranked"]]
    found = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "Confirm the specialty referral is on the account before you open an intake.",
            "record": False,
        },
    ).json()["result"]
    assert "U-SOP-REFERRAL" in [row["unit_id"] for row in found["ranked"]]
    duplicate = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": DUPLICATE,
            "record": False,
        },
    ).json()["result"]
    assert "U-SOP-DUPLICATE" not in [row["unit_id"] for row in duplicate["ranked"]]


def test_legal_sees_only_what_knowledge_ops_sent(explore):
    """Item 3. Legal reviews sent units, and a return comes back for a resend."""
    open_role(explore, "Legal approver")
    seeded = [item["unit_id"] for item in explore.get("/api/legal/queue", params={"world": "explore"}).json()["waiting"]]
    assert SEEDED_LEGAL in seeded
    assert "U-SOP-COPAY" not in seeded
    assert "U-PA-CLINICAL" not in seeded

    _ko(explore)
    optional = explore.post(
        "/api/author/units/U-SOP-SEND/review",
        json={"world": "explore", "action": "send_to_legal"},
    )
    assert optional.status_code == 200, optional.text
    assert optional.json()["status"] == "with_legal"
    assert optional.json()["decision"]["action"] == "send_to_legal"
    sent = explore.post(
        "/api/author/units/U-PA-CLINICAL/review",
        json={"world": "explore", "action": "send_to_legal"},
    )
    assert sent.status_code == 200, sent.text
    assert "Clinical" in sent.json()["unit"]["routing_reason"]

    open_role(explore, "Legal approver")
    waiting = [item["unit_id"] for item in explore.get("/api/legal/queue", params={"world": "explore"}).json()["waiting"]]
    assert SEEDED_LEGAL in waiting
    assert "U-SOP-SEND" in waiting
    assert "U-PA-CLINICAL" in waiting
    returned = explore.post(
        "/api/legal/decline",
        json={
            "world": "explore",
            "unit_id": "U-PA-CLINICAL",
            "reason": "Name the clinical owner before this line is approved.",
        },
    )
    assert returned.status_code == 200, returned.text
    back = _unit(explore, "U-PA-CLINICAL")
    assert back["status"] == "returned"
    assert "clinical owner" in back["notes"]

    _ko(explore)
    work = explore.get("/api/explore/my-work").json()
    sent_back = [item for item in work["items"] if item["group"] == "Sent back by Legal"]
    assert any(item["unit"]["unit_id"] == "U-PA-CLINICAL" for item in sent_back)
    edited = explore.post(
        "/api/author/units/U-PA-CLINICAL/review",
        json={"world": "explore", "action": "edit", "tags": ["clinical", "reviewed"]},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "returned"
    resent = explore.post(
        "/api/author/units/U-PA-CLINICAL/review",
        json={"world": "explore", "action": "send_to_legal"},
    )
    assert resent.status_code == 200, resent.text
    assert resent.json()["status"] == "with_legal"
    open_role(explore, "Legal approver")
    again = [item["unit_id"] for item in explore.get("/api/legal/queue", params={"world": "explore"}).json()["waiting"]]
    assert "U-PA-CLINICAL" in again
    _ko(explore)
    cleared = explore.get("/api/explore/my-work").json()
    assert all(
        item.get("unit", {}).get("unit_id") != "U-PA-CLINICAL"
        for item in cleared["items"]
        if item["group"] == "Sent back by Legal"
    )


def test_document_lists_follow_the_role(explore):
    """Item 4. Knowledge Ops and Legal each see the documents that still need them."""
    denied = explore.get("/api/author/documents", params={"world": "explore"})
    assert denied.status_code == 403
    _ko(explore)
    listed = explore.get("/api/author/documents", params={"world": "explore"}).json()
    by_id = {row["doc_id"]: row for row in listed["documents"]}
    assert set(SANDBOX_DOCS) <= set(by_id)
    assert "SRC-RX-EDU-001" not in by_id
    for doc_id in SANDBOX_DOCS:
        for key in ("waiting_for_ko", "with_legal", "sent_back", "approved", "rejected", "blocked"):
            assert key in by_id[doc_id]
    assert by_id["SRC-SPEC-SOP-001"]["waiting_for_ko"] == 5
    assert by_id["SRC-PA-FAQ-001"]["waiting_for_ko"] == 5
    assert by_id["SRC-CALLBACK-001"]["waiting_for_ko"] == 1
    assert by_id["SRC-CALLBACK-001"]["approved"] == 3
    everyone = explore.get("/api/author/documents", params={"world": "explore", "all": "true"}).json()
    assert "SRC-RX-EDU-001" in {row["doc_id"] for row in everyone["documents"]}

    legal_denied = explore.get("/api/legal/documents", params={"world": "explore"})
    assert legal_denied.status_code == 403
    assert legal_denied.json()["error"] == "Only the Legal approver can do this."
    open_role(explore, "Legal approver")
    legal = explore.get("/api/legal/documents", params={"world": "explore"}).json()
    assert "SRC-SPEC-SOP-001" not in {row["doc_id"] for row in legal["documents"]}
    _ko(explore)
    explore.post(
        "/api/author/units/U-SOP-COPAY/review",
        json={"world": "explore", "action": "send_to_legal"},
    )
    open_role(explore, "Legal approver")
    after = {
        row["doc_id"]: row
        for row in explore.get("/api/legal/documents", params={"world": "explore"}).json()["documents"]
    }
    assert after["SRC-SPEC-SOP-001"]["waiting"] == 1
    guided = explore.get("/api/author/documents", params={"world": "guided"})
    assert guided.status_code == 400
    assert guided.json()["error"] == "This route is for the explore sandbox."


def test_gap_draft_needs_a_source_before_it_can_be_sent(explore):
    """Item 5. A placeholder with no source cannot become a unit."""
    _ko(explore)
    drafts = explore.get("/api/explore/my-work").json()
    titles = [item["title"] for item in drafts["items"] if item["group"] == "Unanswered questions"]
    assert "How long does a standard prior authorization decision take?" in titles
    assert "Can I get a 90-day insulin supply by mail?" in titles
    assert "Can Harbor arrange a ride to my appointment?" in titles

    early = explore.post("/api/author/gaps/gap-pa-time/send", json={"world": "explore"})
    assert early.status_code == 400
    explore.post(
        "/api/author/gaps/gap-pa-time",
        json={
            "world": "explore",
            "text": "A standard prior authorization decision takes 4 business days. These figures are illustrative.",
            "member_text": "A standard prior authorization decision takes 4 business days.",
        },
    )
    unsourced = explore.post("/api/author/gaps/gap-pa-time/send", json={"world": "explore"})
    assert unsourced.status_code == 400
    assert unsourced.json()["error"] == "Ground and fill every placeholder before sending this draft."

    missing = explore.post(
        "/api/author/gaps/gap-insulin-mail/placeholders/0/source",
        json={"world": "explore", "kind": "document", "ref": "SRC-PA-FAQ-001", "quote": "nine business days"},
    )
    assert missing.status_code == 400
    assert missing.json()["error"] == "That passage is not in the source."
    unapproved = explore.post(
        "/api/author/gaps/gap-insulin-mail/placeholders/0/source",
        json={"world": "explore", "kind": "unit", "ref": "U-PA-TIMING", "quote": PA_TIME},
    )
    assert unapproved.status_code == 400
    assert unapproved.json()["error"] == "That passage is not in the source."


def test_prior_authorization_gap_uses_the_faq_document(explore):
    """Item 5. The timing draft is grounded in SRC-PA-FAQ-001 and Legal sees the source."""
    _ko(explore)
    grounded = explore.post(
        "/api/author/gaps/gap-pa-time/placeholders/0/source",
        json={"world": "explore", "kind": "document", "ref": "SRC-PA-FAQ-001", "quote": PA_TIME},
    )
    assert grounded.status_code == 200, grounded.text
    slot = grounded.json()["placeholders"][0]
    assert slot["kind"] == "document"
    assert slot["ref"] == "SRC-PA-FAQ-001"
    bad_fill = explore.post(
        "/api/author/gaps/gap-pa-time/placeholders/0/fill",
        json={"world": "explore", "text": "9 business days"},
    )
    assert bad_fill.status_code == 400
    assert bad_fill.json()["error"] == "That fact is not in the cited source."
    filled = explore.post(
        "/api/author/gaps/gap-pa-time/placeholders/0/fill",
        json={"world": "explore", "text": "4  Business Days"},
    )
    assert filled.status_code == 200, filled.text
    assert filled.json()["placeholders"][0]["filled"] is True
    sent = explore.post("/api/author/gaps/gap-pa-time/send", json={"world": "explore"})
    assert sent.status_code == 200, sent.text
    assert sent.json()["queue"] == "Legal"
    sources = sent.json()["unit"]["sources"]
    assert sources[0]["ref"] == "SRC-PA-FAQ-001"
    assert sources[0]["quote"] == PA_TIME
    open_role(explore, "Legal approver")
    waiting = explore.get("/api/legal/queue", params={"world": "explore"}).json()["waiting"]
    match = next(item for item in waiting if item["unit_id"] == "U-GAP-gap-pa-time")
    assert match["sources"][0]["ref"] == "SRC-PA-FAQ-001"


def test_owner_statement_becomes_an_attested_source(explore):
    """Item 5. Pharmacy Operations attests a fact, and the draft can then be filled."""
    _ko(explore)
    asked = explore.post(
        "/api/author/gaps/gap-insulin-mail/placeholders/0/source",
        json={
            "world": "explore",
            "kind": "request",
            "owner_role": "Pharmacy Operations",
            "question": "Is a 90-day insulin supply available by mail?",
        },
    )
    assert asked.status_code == 200, asked.text
    request_id = asked.json()["placeholders"][0]["request_id"]
    listed = explore.get("/api/explore/source-requests", params={"world": "explore"}).json()
    pending = next(item for item in listed["requests"] if item["id"] == request_id)
    assert pending["status"] == "pending"
    assert pending["owner_role"] == "Pharmacy Operations"
    statement = (
        "A 90-day insulin supply by mail is available after two retail fills. "
        "This figure is illustrative."
    )
    answered = explore.post(
        f"/api/explore/source-requests/{request_id}/answer",
        json={"world": "explore", "statement": statement, "signer": "Riley Chen"},
    )
    assert answered.status_code == 200, answered.text
    assert answered.json()["message"] == "Simulated owner reply."
    assert answered.json()["request"]["mark"] == "Simulated owner reply"
    doc_id = answered.json()["request"]["doc_id"]
    assert doc_id == "SRC-ATTEST-1"
    document = explore.get(f"/api/documents/{doc_id}", params={"world": "explore"}).json()
    assert document["statement"] == statement
    assert document["signer"] == "Riley Chen"
    assert document["owner_role"] == "Pharmacy Operations"
    assert document["attested_on"]
    assert statement in document["body"]
    assert "Simulated owner reply" in document["body"]
    filled = explore.post(
        "/api/author/gaps/gap-insulin-mail/placeholders/0/fill",
        json={"world": "explore", "text": "available after two retail fills"},
    )
    assert filled.status_code == 200, filled.text
    sent = explore.post("/api/author/gaps/gap-insulin-mail/send", json={"world": "explore"})
    assert sent.status_code == 200, sent.text
    assert sent.json()["unit"]["sources"][0]["ref"] == doc_id
    assert "available after two retail fills" in sent.json()["unit"]["text"]


def test_a_gap_with_no_owner_returns_to_the_knowledge_owner(explore):
    """Item 5. No owner means a process gap, and the advocate still has the follow-up."""
    _ko(explore)
    closed = explore.post(
        "/api/author/gaps/gap-ride/no-source",
        json={"world": "explore", "reason": "No team owns appointment transportation."},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "process_gap"
    assert closed.json()["label"] == "The business has no answer yet"
    gaps = explore.get("/api/gaps", params={"world": "explore"}).json()["gaps"]
    ride = next(item for item in gaps if item["id"] == "gap-ride")
    assert ride["label"] == "The business has no answer yet"
    insights = explore.get("/api/explore/insights").json()
    assert any(item["id"] == "gap-ride" for item in insights["process_gaps"])
    work = explore.get("/api/explore/my-work").json()
    assert all(item["id"] != "gap-gap-ride" for item in work["items"])
    open_role(explore, "Pharmacy advocate")
    found = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "Can Harbor arrange a ride to my appointment?",
            "record": False,
        },
    ).json()["result"]
    assert found["abstained"] is True
    assert found["follow_up"] == "The business has no answer yet. Follow up with the knowledge owner."
    assert "The business has no answer yet" in found["note"]


def test_drift_routes_to_the_role_that_approved_the_unit(explore):
    """Item 6. Legal keeps the 30-day case. Knowledge Ops gets the callback hours."""
    _ko(explore)
    listed = explore.get("/api/author/drift", params={"world": "explore"}).json()
    assert [item["unit_id"] for item in listed["items"]] == ["U-CB-HOURS", "U-CB-NOTE", "U-CB-NUMBER"]
    assert [item["kind"] for item in listed["items"]] == ["material", "uncertain", "removed"]
    assert "6:00 p.m." in listed["items"][0]["new_wording"]
    assert "5:00 p.m." in listed["items"][0]["old_wording"]
    assert listed["items"][0]["queue"] == "Knowledge Ops"
    assert [item["unit_id"] for item in listed["automatic"]] == ["U-RX-EDU-001-14"]
    assert listed["automatic"][0]["automatic"] is True
    note = _unit(explore, "U-CB-NOTE")
    assert note["text"] == NOTE_OLD
    assert note["stale"] is True
    price = _unit(explore, "U-RX-EDU-001-09")
    assert "31-day" not in price["text"]
    assert price["stale"] is True
    script = explore.get("/api/documents/SRC-RX-EDU-001", params={"world": "explore"}).json()
    assert "31-day" in script["body"]

    short = explore.post(
        "/api/author/drift/1",
        json={"world": "explore", "action": "keep_current", "reason": "too soon"},
    )
    assert short.status_code == 400
    assert short.json()["error"] == "A reason of at least four words is required."
    blank = explore.post(
        "/api/author/drift/1",
        json={"world": "explore", "action": "edit_and_accept"},
    )
    assert blank.status_code == 400
    assert blank.json()["error"] == "Write the wording before accepting this fix."

    open_role(explore, "Legal approver")
    legal = explore.get("/api/legal/drift", params={"world": "explore"}).json()
    legal_item = next(item for item in legal["items"] if item["unit_id"] == "U-RX-EDU-001-09")
    assert "31-day" in legal_item["new_wording"]
    assert "31-day" not in legal_item["old_wording"]
    assert "U-CB-HOURS" not in [item["unit_id"] for item in legal["items"]]


def test_knowledge_ops_can_accept_or_keep_a_source_change(explore):
    """Item 6. Accept publishes a new version. Keep current records a reason."""
    _ko(explore)
    kept = explore.post(
        "/api/author/drift/1",
        json={
            "world": "explore",
            "action": "keep_current",
            "reason": "The 5:00 p.m. window stays in force.",
        },
    )
    assert kept.status_code == 200, kept.text
    live = _unit(explore, "U-CB-HOURS")
    assert live["stale"] is False
    assert live["text"] == HOUR_OLD
    assert live["version"] == 1
    remaining = explore.get("/api/author/drift", params={"world": "explore"}).json()
    assert "U-CB-HOURS" not in [item["unit_id"] for item in remaining["items"]]
    assert remaining["automatic"]

    reset = explore.post("/api/explore/reset")
    assert reset.status_code == 200, reset.text
    accepted = explore.post(
        "/api/author/drift/1",
        json={"world": "explore", "action": "accept_fix"},
    )
    assert accepted.status_code == 200, accepted.text
    current = _unit(explore, "U-CB-HOURS")
    assert current["version"] == 2
    assert current["status"] == "approved"
    assert current["search_visible"] is True
    assert current["text"] == HOUR_NEW
    versions = explore.get("/api/units/U-CB-HOURS/versions", params={"world": "explore"}).json()["versions"]
    by_version = {row["version"]: row for row in versions}
    assert by_version[1]["status"] == "superseded"
    assert by_version[1]["text"] == HOUR_OLD
    assert by_version[1]["search_visible"] is False

    reset = explore.post("/api/explore/reset")
    assert reset.status_code == 200, reset.text
    custom = "Offer a Harbor callback window on weekdays from 8:00 a.m. to 4:00 p.m. Eastern. These hours are illustrative."
    edited = explore.post(
        "/api/author/drift/1",
        json={"world": "explore", "action": "edit_and_accept", "text": custom},
    )
    assert edited.status_code == 200, edited.text
    published = _unit(explore, "U-CB-HOURS")
    assert published["version"] == 2
    assert published["text"] == custom
    history = explore.get("/api/units/U-CB-HOURS/versions", params={"world": "explore"}).json()["versions"]
    first = next(row for row in history if row["version"] == 1)
    assert first["status"] == "superseded"
    assert first["text"] == HOUR_OLD


def test_knowledge_ops_my_work_has_four_groups(explore):
    """Item 7. Flags stay in Insights and the feedback list."""
    denied = explore.get("/api/explore/my-work")
    assert denied.status_code == 403
    _ko(explore)
    body = explore.get("/api/explore/my-work").json()
    names = [group["group"] for group in body["groups"]]
    assert names == [
        "Documents to review",
        "Unanswered questions",
        "Source changes",
    ]
    assert set(names) <= {
        "Documents to review",
        "Unanswered questions",
        "Source changes",
        "Sent back by Legal",
    }
    assert "Flagged by advocates and channels" not in names
    blob = " ".join(item["title"] for item in body["items"])
    assert "where is the prior authorization turnaround time" not in blob
    assert "does the price include my deductible" not in blob
    feedback = explore.get("/api/feedback/author", params={"world": "explore"}).json()
    examples = []
    for group in feedback["groups"]:
        examples.extend(group.get("examples") or [])
    assert any("prior authorization turnaround" in question for question in examples)
    insights = explore.get("/api/explore/insights").json()
    assert "feedback" in insights
    assert "by_kind" in insights["feedback"]


def test_existing_answers_and_step_8_stay_put(explore, client):
    """Guided step 8 and the explore member, advocate, and channel answers stay put."""
    pharmacy = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "what do I say before I quote a cost",
            "record": False,
        },
    ).json()["result"]
    assert pharmacy["unit"]["unit_id"] == "U-RX-EDU-001-09"
    prior = explore.post(
        "/api/search",
        json={
            "world": "explore",
            "role": "Pharmacy advocate",
            "query": "how long does a part d prior auth take",
            "record": False,
        },
    ).json()["result"]
    assert prior["abstained"] is True
    member = explore.post(
        "/api/explore/member",
        json={"member_id": "HBR-20418", "question": "how much is my atorvastatin"},
    ).json()
    portal = explore.get(
        "/api/portal/answers",
        params={"role": "Member", "member_id": "HBR-20418", "question": "how much is my atorvastatin"},
    ).json()
    assert member["units"][0]["unit_id"] == portal["units"][0]["unit_id"] == "U-RX-EDU-001-09"
    open_role(explore, "Insurance advocate")
    insurance = explore.get(
        "/api/portal/answers",
        params={"role": "Insurance advocate", "question": "what do I say before I quote a cost"},
    ).json()
    assert insurance["unit_id"] == "U-BEN-COST-001-02"

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
    guided_docs = [row["doc_id"] for row in client.get("/api/documents", params={"world": "guided"}).json()["documents"]]
    assert "SRC-SPEC-SOP-001" not in guided_docs
    script = client.get("/api/documents/SRC-RX-EDU-001", params={"world": "guided"}).json()["body"]
    assert "31-day" not in script


def test_each_gap_shows_what_the_ai_found(explore):
    """Each seeded question carries the AI's candidate source and how far to trust it."""
    _ko(explore)
    gaps = {item["id"]: item for item in explore.get("/api/author/edits", params={"world": "explore"}).json()["gaps"]}
    pa = gaps["gap-pa-time"]["candidate"]
    assert pa["ref"] == "SRC-PA-FAQ-001" and pa["trust"] == "review_backlog" and pa["fill"] == "4 business days"
    insulin = gaps["gap-insulin-mail"]["candidate"]
    assert insulin["ref"] == "SRC-WEB-MAIL-001" and insulin["trust"] == "unreviewed"
    web = explore.get("/api/documents/SRC-WEB-MAIL-001", params={"world": "explore"}).json()
    assert insulin["quote"] in web["body"]
    assert gaps["gap-ride"]["candidate"]["trust"] == "none" and not gaps["gap-ride"]["candidate"]["ref"]
    assert "candidate" in gaps["c0"] and gaps["c0"]["candidate"] is None

    # The suggested passage grounds and fills the placeholder.
    ground = explore.post(
        "/api/author/gaps/gap-pa-time/placeholders/0/source",
        json={"world": "explore", "kind": "document", "ref": pa["ref"], "quote": pa["quote"]},
    )
    assert ground.status_code == 200, ground.text
    fill = explore.post("/api/author/gaps/gap-pa-time/placeholders/0/fill", json={"world": "explore", "text": pa["fill"]})
    assert fill.status_code == 200, fill.text


def test_owner_can_reply_that_no_policy_exists(explore):
    """The subject expert says the company has no answer, so the question becomes a process gap."""
    _ko(explore)
    asked = explore.post(
        "/api/author/gaps/gap-ride/placeholders/0/source",
        json={"world": "explore", "kind": "request", "owner_role": "Care Coordination", "question": "Can Harbor arrange a ride?"},
    )
    assert asked.status_code == 200, asked.text
    request_id = explore.get("/api/explore/source-requests", params={"world": "explore"}).json()["requests"][-1]["id"]
    answer = explore.post(
        f"/api/explore/source-requests/{request_id}/answer",
        json={"world": "explore", "statement": "Harbor has no transportation benefit or policy today.", "signer": "Jordan Lee", "no_policy": True},
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["request"]["outcome"] == "no_policy"
    assert not answer.json()["request"]["doc_id"]
    gaps = {item["id"] for item in explore.get("/api/author/edits", params={"world": "explore"}).json()["gaps"]}
    assert "gap-ride" not in gaps
    open_role(explore, "Knowledge owner")
    insights = explore.get("/api/explore/insights").json()
    assert any("ride" in (item.get("cluster") or item.get("question") or "").lower() for item in insights.get("process_gaps", []))


def test_a_gap_can_be_dismissed_with_a_reason(explore):
    _ko(explore)
    short = explore.post("/api/author/gaps/gap-ride/dismiss", json={"world": "explore", "kind": "out_of_scope", "reason": "not ours"})
    assert short.status_code == 400
    missing = explore.post(
        "/api/author/gaps/gap-ride/dismiss",
        json={"world": "explore", "kind": "already_answered", "reason": "An approved unit already covers this", "unit_id": "U-NOPE"},
    )
    assert missing.status_code == 400
    ok = explore.post(
        "/api/author/gaps/gap-ride/dismiss",
        json={"world": "explore", "kind": "out_of_scope", "reason": "Harbor does not offer transportation in this plan"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "dismissed"
    gaps = {item["id"] for item in explore.get("/api/author/edits", params={"world": "explore"}).json()["gaps"]}
    assert "gap-ride" not in gaps


def test_knowledge_ops_can_add_a_unit_the_ai_missed(explore):
    _ko(explore)
    doc = explore.get("/api/documents/SRC-SPEC-SOP-001", params={"world": "explore"}).json()
    sentence = "Ask the member where they want the medicine delivered, and whether someone will be home to sign for a refrigerated package."
    assert sentence in doc["body"]
    added = explore.post(
        "/api/author/documents/SRC-SPEC-SOP-001/units",
        json={"world": "explore", "span": sentence, "title": "Ask about delivery", "type": "procedure", "audience": ["advocate"], "tags": ["delivery"]},
    )
    assert added.status_code == 200, added.text
    unit_id = added.json()["unit_id"]
    assert unit_id.startswith("U-KO-") and not added.json()["requires_legal"]
    unit = _unit(explore, unit_id)
    assert unit["status"] == "extracted" and unit["source_quote"] == sentence and not unit["search_visible"]
    again = explore.post("/api/author/documents/SRC-SPEC-SOP-001/units", json={"world": "explore", "span": sentence})
    assert again.status_code == 400 and "already unit" in again.text
    missing = explore.post("/api/author/documents/SRC-SPEC-SOP-001/units", json={"world": "explore", "span": "This sentence is not in the document at all."})
    assert missing.status_code == 400
    approve = explore.post(f"/api/author/units/{unit_id}/review", json={"world": "explore", "action": "approve"})
    assert approve.status_code == 200, approve.text
    assert _unit(explore, unit_id)["status"] == "approved"
    cost = explore.post(
        "/api/author/documents/SRC-SPEC-SOP-001/units",
        json={"world": "explore", "span": "Quote cost only with the approved pricing disclaimer, and only after the benefit check is complete.", "type": "policy"},
    )
    assert cost.status_code == 200 and cost.json()["requires_legal"]
    open_role(explore, "Legal approver")
    blocked = explore.post("/api/author/documents/SRC-SPEC-SOP-001/units", json={"world": "explore", "span": sentence})
    assert blocked.status_code in (400, 403)


def test_knowledge_ops_confirms_or_retires_the_other_source_changes(explore):
    _ko(explore)
    items = {item["kind"]: item for item in explore.get("/api/author/drift", params={"world": "explore"}).json()["items"]}
    unsure, removed = items["uncertain"], items["removed"]
    wrong = explore.post(f"/api/author/drift/{removed['id']}", json={"world": "explore", "action": "accept_fix"})
    assert wrong.status_code == 400
    short = explore.post(f"/api/author/drift/{removed['id']}", json={"world": "explore", "action": "retire", "reason": "gone"})
    assert short.status_code == 400
    retired = explore.post(
        f"/api/author/drift/{removed['id']}",
        json={"world": "explore", "action": "retire", "reason": "The policy no longer has this step"},
    )
    assert retired.status_code == 200, retired.text
    number = explore.get("/api/units/U-CB-NUMBER", params={"world": "explore"}).json()["unit"]
    assert number["status"] == "retired" and not number["search_visible"]
    confirmed = explore.post(f"/api/author/drift/{unsure['id']}", json={"world": "explore", "action": "confirm_cosmetic"})
    assert confirmed.status_code == 200, confirmed.text
    note = _unit(explore, "U-CB-NOTE")
    assert note["text"] == NOTE_OLD and note["stale"] is False


def test_legal_sees_three_source_changes_and_decides_each(explore):
    open_role(explore, "Legal approver")
    listed = explore.get("/api/legal/source-changes", params={"world": "explore"}).json()
    kinds = {item["unit_id"]: item["kind"] for item in listed["items"]}
    assert kinds == {"U-RX-EDU-001-09": "material", "U-RX-EDU-001-07": "material", "U-BEN-COST-001-02": "cosmetic_verbatim"}
    by_unit = {item["unit_id"]: item for item in listed["items"]}
    assert "deductible" in by_unit["U-RX-EDU-001-07"]["new_wording"]
    accept = explore.post(f"/api/legal/source-changes/{by_unit['U-RX-EDU-001-07']['id']}", json={"world": "explore", "action": "accept_fix"})
    assert accept.status_code == 200, accept.text
    policy = explore.get("/api/units/U-RX-EDU-001-07", params={"world": "explore"}).json()["unit"]
    assert "deductible" in policy["text"] and policy["version"] == 2
    cosmetic = explore.post(f"/api/legal/source-changes/{by_unit['U-BEN-COST-001-02']['id']}", json={"world": "explore", "action": "confirm_cosmetic"})
    assert cosmetic.status_code == 200, cosmetic.text
    legacy = explore.post(
        f"/api/legal/source-changes/{by_unit['U-RX-EDU-001-09']['id']}",
        json={"world": "explore", "action": "accept_fix"},
    )
    assert legacy.status_code == 200, legacy.text
    price = explore.get("/api/units/U-RX-EDU-001-09", params={"world": "explore"}).json()["unit"]
    assert "31-day" in price["text"]
    assert explore.get("/api/legal/source-changes", params={"world": "explore"}).json()["items"] == []
    _ko(explore)
    blocked = explore.post(f"/api/legal/source-changes/{by_unit['U-RX-EDU-001-07']['id']}", json={"world": "explore", "action": "accept_fix"})
    assert blocked.status_code in (400, 403)

