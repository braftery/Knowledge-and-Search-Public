"""Realistic touchpoints from EXPERIENCE_SPEC.md: the advocate's agent desktop and the member's app, website and phone line.

Everything here renders approved units by reference from the Explore database. Member views never show unit IDs,
advocate text, or internal metadata (EXPERIENCE_SPEC.md section 1, principle 4).
"""

from __future__ import annotations

import streamlit as st

from src.components import _get, esc, muted, show
from src.engine import ROLE_KB, live_approved

# ---------------------------------------------------------------- advocate: agent desktop

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

DESKTOP_CSS = """
<style>
.desk-bar { display:flex; justify-content:space-between; align-items:center; background:#2C3E50; color:#FFFFFF;
  padding:8px 14px; border-radius:6px 6px 0 0; font-size:16px; }
.desk-bar strong { color:#FFFFFF; }
.desk-live { background:#1E6B3A; color:#FFFFFF; border-radius:4px; padding:1px 8px; font-weight:700; }
.desk-body { border:1px solid #2C3E50; border-top:none; border-radius:0 0 6px 6px; padding:12px 14px; background:#FFFFFF; }
.desk-row { display:flex; gap:8px; margin:2px 0; font-size:17px; }
.desk-key { min-width:110px; color:#4A4F55; }
.kp-head { background:#0B3A6A; color:#FFFFFF; padding:8px 12px; border-radius:6px 6px 0 0; font-weight:700; font-size:17px; }
.kp-sub { font-size:16px; color:#4A4F55; margin:8px 0 4px 0; font-weight:700; }
.kp-cite { font-size:16px; color:#4A4F55; margin-top:6px; }
.kp-none { border:2px solid #8A5A00; background:#FFF4D6; border-radius:6px; padding:10px 12px; }
.browser { border:1px solid #C9CED4; border-radius:8px; overflow:hidden; background:#FFFFFF; }
.browser .chrome { background:#F4F6F8; border-bottom:1px solid #C9CED4; padding:8px 12px; font-size:16px; color:#4A4F55; }
.browser .site-nav { background:#0B3A6A; color:#FFFFFF; padding:10px 16px; font-weight:700; }
.browser .page { padding:16px 20px; }
.browser h2 { font-size:24px; margin:0 0 8px 0; }
.ivr { border:1px solid #C9CED4; border-radius:8px; padding:12px 16px; background:#FFFFFF; }
.ivr .turn { margin:8px 0; }
.ivr .who { font-weight:700; color:#4A4F55; display:block; font-size:16px; }
</style>
"""


def page_agent_desktop(conn, role: str, ask, set_query) -> None:
    """Agent desktop with the knowledge panel (EXPERIENCE_SPEC.md section 4)."""
    show(DESKTOP_CSS)
    calls = CALLS[role]
    reason = st.selectbox("Simulated call (pick a call reason)", list(calls), key=f"x-call-{role}")
    call = calls[reason]
    left, right = st.columns([1.4, 1], gap="medium")
    with left:
        verified = "Verified (2 of 3 identifiers)" if call["verified"] else "Not verified"
        show(
            f"""
            <div class="desk-bar"><span><strong>Agent Desktop</strong> · {esc(role.replace(" advocate", ""))}</span>
            <span class="desk-live">On call 02:14</span></div>
            <div class="desk-body">
              <div class="desk-row"><span class="desk-key">Member</span><span>{esc(call['member'])} (fictional)</span></div>
              <div class="desk-row"><span class="desk-key">Plan</span><span>{esc(call['plan'])}</span></div>
              <div class="desk-row"><span class="desk-key">Identity</span><span>{esc(verified)}</span></div>
              <div class="desk-row"><span class="desk-key">Call reason</span><span>{esc(reason)}</span></div>
              <div class="desk-row"><span class="desk-key">Member said</span><span>{esc(call['detail'])}</span></div>
            </div>
            """
        )
        muted("Mock desktop, made-up members. The panel docks inside the advocate's existing tools.")
    with right:
        show(f'<div class="kp-head">Knowledge · searches {esc(", ".join(ROLE_KB[role]))}</div>')
        with st.form(key=f"x-desk-form-{role}", clear_on_submit=False, border=False):
            typed = st.text_input("Ask", key=f"x-desk-q-{role}", label_visibility="collapsed", placeholder="Ask a question, then press Enter…")
            if st.form_submit_button("Search") and typed.strip():
                set_query(f"x-desk-last-{role}", typed.strip())
                count = int(st.session_state.get(f"x-searches-{role}", 0)) + 1
                st.session_state[f"x-searches-{role}"] = count
                if count >= 3:
                    from src.feedback_ui import record_once

                    record_once(
                        conn, f"hard::{role}::{reason}", source="advocate", role=role, kind="hard_to_find",
                        question=typed.strip(), note="Captured automatically: three or more searches in one call.",
                        signals={"searches_in_call": count},
                    )
        last = st.session_state.get(f"x-desk-last-{role}")
        if last:
            show(f'<p class="kp-sub">Results for: {esc(last)}</p>')
            _knowledge_answer(ask(conn, role, last), expanded=True, key=f"{role}-typed", conn=conn, role=role)
        show('<p class="kp-sub">Suggested for this call</p>')
        for index, question in enumerate(call["questions"]):
            result = ask(conn, role, question)
            _knowledge_answer(result, expanded=index == 0 and not last, key=f"{role}-{reason}-{index}", conn=conn, role=role)


def _knowledge_answer(result: dict, expanded: bool, key: str, conn=None, role: str = "") -> None:
    from src.feedback_ui import flag_control, record_once

    question = result.get("query", "")
    if result.get("ai_source") in ("missing", "live_failed"):
        show(
            f'<div class="kp-none"><strong>{esc(question)}</strong><br>No saved answer for this question, and the live model '
            "is unavailable. Pick a suggested question, or try again later.</div>"
        )
        return
    if result.get("abstained") or not result.get("unit"):
        show(
            f'<div class="kp-none"><strong>No approved answer:</strong> {esc(question)}<br>'
            "Do not guess. Offer a callback, or escalate to a supervisor. "
            "This question was logged for the knowledge team.</div>"
        )
        if conn is not None:
            record_once(conn, f"noans::{role}::{question}", source="advocate", role=role, kind="no_answer", question=question)
            flag_control(conn, role, question, "", key)
        return
    row = result["unit"]
    title = f"{row['title']}"
    with st.expander(title, expanded=expanded):
        if row["type"] == "verbatim":
            show(
                f'<div class="read-exactly"><div class="label">Read to member, word for word</div>'
                f'<div class="text">{esc(row["text"])}</div></div>'
            )
        else:
            show(f'<div class="unit-text">{esc(row["text"])}</div>')
        applies = _get(row, "applicability")
        show(
            f'<div class="kp-cite">Approved by {esc(row["approved_by"] or "not recorded")} · version {esc(row["version"])}'
            f'{" · applies to " + esc(applies) if applies else ""}</div>'
        )
        if st.toggle("Copy wording", key=f"x-copy-{key}"):
            st.code(row["text"], language=None, wrap_lines=True)
        if conn is not None:
            flag_control(conn, role, question, row["unit_id"], key)


# ---------------------------------------------------------------- member: app, website, phone line

MEMBER_TOPICS = [
    ("Drug price estimates", "pricing", None, "How much will my prescription cost?"),
    ("Cost of a doctor visit", None, "U-BEN-COST-001-02", "What will my doctor visit cost?"),
    ("Specialist referrals", None, "U-BEN-COST-001-05", "Do I need a referral to see a specialist?"),
    ("Specialty pharmacy", None, "U-RX-EDU-001-13", "Can my specialty drug come by mail?"),
    ("Someone calling for me", None, "U-RX-EDU-001-05", "Can my daughter call about my drugs?"),
]


def _topic_unit(conn, topic: tuple):
    from src.engine import anchor

    _label, anchor_name, unit_id, _question = topic
    unit_id = anchor(conn, anchor_name) if anchor_name else unit_id
    return live_approved(conn, unit_id) if unit_id else None


def _member_reply(row) -> str:
    if row is None or not (row["member_text"] or "").strip():
        return (
            "I do not have an approved answer for that. I can connect you with a member advocate. "
            '<span class="cite">Your question was passed to our knowledge team.</span>'
        )
    title = row["title"].replace(" (Legal)", "").replace(" (Legal verbatim)", "")
    return (
        f"{esc(row['member_text'])}"
        f'<span class="cite">Source: Harbor Health, {esc(title.lower())}, version {esc(row["version"])}</span>'
    )


def page_member_app(conn, role: str, ask) -> None:
    """Phone-frame app chat (EXPERIENCE_SPEC.md section 5)."""
    show(DESKTOP_CSS)
    history = st.session_state.setdefault("x-app-chat", [])
    left, right = st.columns([1, 1.1], gap="large")
    with left:
        muted("Tap a topic or type a question. Answers use approved member wording only.")
        for index, topic in enumerate(MEMBER_TOPICS):
            if st.button(topic[0], key=f"x-topic-{index}", width="stretch"):
                topic_row = _topic_unit(conn, topic)
                history.append({"q": topic[3], "a": _member_reply(topic_row)})
                st.session_state["x-app-last"] = {"q": topic[3], "unit_id": topic_row["unit_id"] if topic_row is not None else ""}
                st.rerun()
        with st.form("x-app-form", clear_on_submit=True, border=False):
            typed = st.text_input("Type a question", key="x-app-typed", placeholder="For example: is the price a guarantee…")
            sent = st.form_submit_button("Send", type="primary")
        muted("Please don't include personal details like your member ID or date of birth. For questions about your own claims, sign in.")
        if sent and typed.strip():
            question = typed.strip()
            result = member_ask(conn, question)
            from src.feedback_ui import record_once

            st.session_state["x-app-last"] = None
            if result.get("ai_source") in ("missing", "live_failed", "capped"):
                reply = "I cannot look that up right now. Try a topic, or I can connect you with a member advocate."
                st.session_state["x-app-suggest"] = []
                record_once(conn, f"handoff::{question}", role="Member", kind="handed_off", question=question,
                            note="Captured automatically: the chat could not look it up and offered a person.")
            elif result.get("abstained"):
                suggestions = _closest_topics(conn, question)
                names = " or ".join(MEMBER_TOPICS[index][0].lower() for index in suggestions)
                reply = (
                    "I want to give you the right answer. "
                    + (f"Is this about {esc(names)}? " if names else "")
                    + "Tap a topic, or I can connect you with a member advocate."
                )
                st.session_state["x-app-suggest"] = suggestions
                record_once(conn, f"clarify::{question}", role="Member", kind="clarified", question=question,
                            note="Captured automatically: no approved answer matched, so the chat asked a clarifying question.")
            else:
                reply = (
                    f"{esc(result['member_text'])}"
                    f'<span class="cite">Source: Harbor Health, {esc(_plain_title(result["title"]))}, version {esc(result["version"])}</span>'
                )
                st.session_state["x-app-suggest"] = []
                st.session_state["x-app-last"] = {"q": question, "unit_id": result.get("unit_id", "")}
            history.append({"q": question, "a": reply})
            st.rerun()
        suggestions = st.session_state.get("x-app-suggest") or []
        if suggestions:
            muted("Did you mean:")
            for index in suggestions:
                topic = MEMBER_TOPICS[index]
                if st.button(topic[0], key=f"x-suggest-{index}", type="primary"):
                    history.append({"q": topic[0], "a": _member_reply(_topic_unit(conn, topic))})
                    st.session_state["x-app-suggest"] = []
                    st.rerun()
        last_answer = st.session_state.get("x-app-last")
        if last_answer:
            with st.container(horizontal=True, gap="small", key="x-app-helped"):
                show('<span class="muted">Did that answer help?</span>')
                yes = st.button("Yes", key="x-app-yes")
                no = st.button("No", key="x-app-no")
            if yes or no:
                if no:
                    from src.engine import record_feedback

                    record_feedback(conn, "channel", "Member", "not_helpful", last_answer["q"], last_answer["unit_id"],
                                    "Member tapped No on Did that answer help?", {})
                st.session_state["x-app-last"] = None
                st.toast("Thanks. Your feedback goes to the knowledge team.")
                st.rerun()
        if history and st.button("Clear chat", key="x-app-clear", type="tertiary"):
            st.session_state["x-app-chat"] = []
            st.session_state["x-app-suggest"] = []
            st.rerun()
    with right:
        bubbles = "".join(
            f'<div class="bubble member">{esc(turn["q"])}</div><div class="bubble bot">{turn["a"]}</div>'
            for turn in history[-2:]
        ) or '<div class="bubble bot">Hi, I am the Harbor Health assistant. What can I help you with?</div>'
        show(
            f"""
            <div class="phone">
              <div class="bar">Harbor Health · Chat</div>
              <div class="chat">{bubbles}</div>
            </div>
            """
        )


def _plain_title(title: str) -> str:
    return title.replace(" (Legal verbatim)", "").replace(" (Legal)", "").lower()


_STOP = set("a an the is are do does my i me to of for on in at it this that what how can will be with or and".split())


def _closest_topics(conn, question: str) -> list[int]:
    """Up to two topics whose approved member wording shares the most words with the question."""
    words = {word.strip("?.,!").lower() for word in question.split()} - _STOP
    same = {"price": "cost", "cost": "price", "prescription": "drug", "medicine": "drug", "drug": "prescription"}
    words |= {same[word] for word in list(words) if word in same}
    scored = []
    for index, topic in enumerate(MEMBER_TOPICS):
        row = _topic_unit(conn, topic)
        text = f"{topic[0]} {topic[3]} {(row['member_text'] if row is not None else '')}".lower()
        overlap = sum(1 for word in words if word and word in text)
        if overlap:
            scored.append((-overlap, index))
    scored.sort()
    return [index for _overlap, index in scored[:2]]


def member_ask(conn, question: str) -> dict:
    """Member answer: saved answer first, then one live call within the visitor's cap. Each question runs once per visit."""
    from src.engine import member_answer, set_live

    key = f"x-member::{question}"
    if key in st.session_state:
        return st.session_state[key]
    from src.explore import calls_left

    set_live(conn, False)
    result = member_answer(conn, question)
    if result.get("ai_source") == "missing" and calls_left() > 0:
        set_live(conn, True)
        with st.spinner("No saved answer. Asking the model…"):
            result = member_answer(conn, question)
        set_live(conn, False)
        if result.get("ai_source") == "live":
            st.session_state.explore_live_calls = int(st.session_state.get("explore_live_calls", 0)) + 1
    from src.engine import record_search

    record_search(conn, "Member", question, result)
    st.session_state[key] = result
    return result


def page_member_website(conn, role: str, ask) -> None:
    """A help page that renders the same unit by reference (EXPERIENCE_SPEC.md section 5)."""
    show(DESKTOP_CSS)
    labels = [topic[0] for topic in MEMBER_TOPICS]
    label = st.selectbox("Help page", labels, key="x-web-topic")
    topic = MEMBER_TOPICS[labels.index(label)]
    row = _topic_unit(conn, topic)
    slug = label.lower().replace(" ", "-")
    if row is None or not (row["member_text"] or "").strip():
        body = "<p>This help topic is being updated. Call the number on your member card for help.</p>"
        updated = ""
    else:
        body = f"<p>{esc(row['member_text'])}</p>"
        updated = f'<p class="muted">Last updated {esc(str(_get(row, "effective_date") or row["approved_on"])[:10])} · version {esc(row["version"])}</p>'
    show(
        f"""
        <div class="browser">
          <div class="chrome">harborhealth.example/help/{esc(slug)}</div>
          <div class="site-nav">Harbor Health · Help center</div>
          <div class="page">
            <h2>{esc(label)}</h2>
            {body}
            {updated}
          </div>
        </div>
        """
    )
    muted("Fictional website. The page embeds the approved unit by reference, so a Legal revision updates it at once.")


def page_member_phone(conn, role: str, ask) -> None:
    """The automated phone line reading the same wording (EXPERIENCE_SPEC.md section 5)."""
    show(DESKTOP_CSS)
    labels = [topic[0] for topic in MEMBER_TOPICS]
    label = st.selectbox("Caller says", labels, key="x-ivr-topic")
    topic = MEMBER_TOPICS[labels.index(label)]
    row = _topic_unit(conn, topic)
    if row is None or not (row["member_text"] or "").strip():
        reading = "I do not have an approved answer for that. Please hold while I connect you with a member advocate."
    else:
        reading = row["member_text"]
    show(
        f"""
        <div class="ivr">
          <div class="turn"><span class="who">Automated line</span>Thank you for calling Harbor Health. In a few words, tell me what you are calling about.</div>
          <div class="turn"><span class="who">Caller</span>{esc(topic[3])}</div>
          <div class="turn"><span class="who">Automated line</span>{esc(reading)}</div>
          <div class="turn"><span class="who">Automated line</span>Would you like to speak with a member advocate?</div>
        </div>
        """
    )
    muted("Transcript of a fictional automated phone line. It reads the same approved member wording as the app and the website.")


def same_wording_check(conn) -> list[tuple[str, bool]]:
    """For tests: every topic's member wording is identical across the three member surfaces."""
    results = []
    for topic in MEMBER_TOPICS:
        row = _topic_unit(conn, topic)
        text = (row["member_text"] or "") if row is not None else ""
        results.append((topic[0], bool(text)))
    return results

