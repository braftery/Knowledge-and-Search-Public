"""Shared layout pieces and components for the demo (BUILD_EVALUATION.md sections 6 to 8)."""

from __future__ import annotations

import difflib
import html
import re

import streamlit as st

from src.engine import ROLE_KB, activity, document_body, live_enabled, mode_name, set_live, step_done

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

NEXT = {number: f"Next: {STEP_NAMES[number + 1]}" for number in range(8)}

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

ROLES = [
    "Knowledge Ops author",
    "Legal approver",
    "Pharmacy advocate",
    "Insurance advocate",
    "Member",
    "Knowledge owner",
]

DOC_NAMES = {
    "SRC-RX-EDU-001": "Rx education script v1",
    "SRC-RX-EDU-002": "Rx education script v2 (desk copy)",
    "SRC-WEB-FAQ": "Website FAQ",
    "SRC-BEN-COST-001": "Benefits cost guide",
}

CHANNEL_NAMES = {
    "advocate_guidance": "Advocate guidance",
    "member_chat": "Member chat",
    "website": "Website",
}

STATUS = {
    "proposed": ("Proposed", "review"),
    "in_review": ("In review", "review"),
    "approved": ("Approved", "approved"),
    "superseded": ("Superseded", "neutral"),
    "retired": ("Retired", "neutral"),
    "merged": ("Merged", "neutral"),
    "blocked_conflict": ("Blocked: conflict", "blocked"),
}


CSS = """
:root {
    --ink: #1A1A1A;
    --ink-muted: #4A4F55;
    --surface: #FFFFFF;
    --surface-alt: #F4F6F8;
    --line: #C9CED4;
    --primary: #0B3A6A;
    --approved: #1E6B3A;
    --approved-bg: #E6F2EA;
    --review: #8A5A00;
    --review-bg: #FFF4D6;
    --blocked: #9B1C1C;
    --blocked-bg: #FBEAEA;
    --diff-del: #FBEAEA;
    --diff-add: #E6F2EA;
}
html, body, .stApp { font-size: 18px; line-height: 1.5; color: var(--ink); background: var(--surface); }
.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] li,
.stApp label,
[data-testid="stWidgetLabel"] p { font-size: 18px; line-height: 1.5; color: var(--ink); }
[data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[data-testid="stMarkdownContainer"] p { margin-bottom: 0.4rem; }
[data-testid="stMarkdownContainer"] > p:last-child { margin-bottom: 0; }
.stTextInput input, .stTextArea textarea { font-size: 18px !important; color: var(--ink) !important; min-height: 48px; }
.stTextInput input:disabled, .stTextArea textarea:disabled {
    color: var(--ink) !important; -webkit-text-fill-color: var(--ink) !important; opacity: 1; background: var(--surface-alt) !important;
}
header[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; background: transparent !important; }
footer, [data-testid="stDecoration"], [data-testid="stHeaderActionElements"] { display: none !important; }
[data-testid="stStatusWidget"] { position: fixed; top: 8px; right: 16px; z-index: 1000; }
[data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"], [data-testid="stSidebarHeader"] { display: none !important; }
.block-container { padding: 16px 24px 24px 24px !important; max-width: 1180px; }
[data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: 12px; }

/* Section 6.4 required button CSS */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: #0B3A6A !important; color: #FFFFFF !important; border: none !important;
}
.stButton > button[kind="primary"] p { color: #FFFFFF !important; }
.stButton > button:disabled { opacity: .45; cursor: not-allowed; }
header [data-testid="stToolbar"] { display: none; }  /* hides Fork and GitHub icons (U17) */

/* Verified selectors for the installed Streamlit version */
.stButton > button { font-size: 18px !important; min-height: 48px; border-radius: 4px; padding: 8px 16px; }
.stButton button[data-testid="stBaseButton-primary"] { background: #0B3A6A !important; color: #FFFFFF !important; border: 1px solid #0B3A6A !important; }
.stButton button[data-testid="stBaseButton-primary"] p { color: #FFFFFF !important; font-weight: 700; }
.stButton button[data-testid="stBaseButton-primary"]:hover { background: #082C52 !important; }
.stButton button[data-testid="stBaseButton-secondary"] { background: #FFFFFF !important; color: var(--primary) !important; border: 1px solid var(--primary) !important; }
.stButton button[data-testid="stBaseButton-secondary"] p { color: var(--primary) !important; }
.stButton button[data-testid="stBaseButton-secondary"]:hover { background: #E7EEF6 !important; }
.stButton button[data-testid="stBaseButton-tertiary"] p { color: var(--primary) !important; text-decoration: underline; }
.stButton > button:focus-visible { outline: 3px solid #8A5A00 !important; outline-offset: 2px; }
[data-testid="stExpander"] summary p { font-size: 18px; font-weight: 700; }
[data-testid="stExpander"] details { border-color: var(--line); }

/* Sidebar */
section[data-testid="stSidebar"] { background: var(--surface-alt) !important; width: 272px !important; min-width: 272px !important; }
section[data-testid="stSidebar"] > div { width: 272px !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: 0 !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { width: 100% !important; max-width: 100% !important; box-sizing: border-box; padding: 20px 14px 16px 14px !important; margin: 0 !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div { width: 100% !important; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 3px !important; }
.brand { font-size: 20px; font-weight: 700; line-height: 1.3; margin: 0 0 4px 0; }
.brand-note, .muted { font-size: 16px; line-height: 1.5; color: var(--ink-muted); margin: 0; }
.side-heading { font-size: 16px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-muted); margin: 10px 0 2px 0; }
section[data-testid="stSidebar"] .stButton, section[data-testid="stSidebar"] .stButton > button { width: 100% !important; }
section[data-testid="stSidebar"] [class*="st-key-nav-"] .stButton > button {
    justify-content: flex-start !important; min-height: 38px; height: 38px; padding: 0 12px !important;
    background: transparent !important; border: 1px solid transparent !important; border-radius: 4px;
}
section[data-testid="stSidebar"] [class*="st-key-nav-"] .stButton > button > div { width: 100%; justify-content: flex-start !important; }
section[data-testid="stSidebar"] [class*="st-key-nav-"] .stButton > button p {
    color: var(--ink) !important; font-size: 17px !important; text-align: left !important; white-space: nowrap; width: 100%;
}
section[data-testid="stSidebar"] [class*="st-key-nav-"] .stButton > button:hover { background: #E7EEF6 !important; border-color: var(--line) !important; }
section[data-testid="stSidebar"] [class*="st-key-nav-"][class*="-current"] .stButton > button { background: var(--primary) !important; border-color: var(--primary) !important; }
section[data-testid="stSidebar"] [class*="st-key-nav-"][class*="-current"] .stButton > button p { color: #FFFFFF !important; font-weight: 700; }
section[data-testid="stSidebar"] [class*="st-key-nav-"][class*="-done"] .stButton > button::after {
    content: "Done"; margin-left: auto; font-size: 16px; font-weight: 700; color: var(--approved);
    background: var(--approved-bg); padding: 0 8px; border-radius: 4px; line-height: 24px;
}
section[data-testid="stSidebar"] [class*="st-key-nav-"][class*="-current"][class*="-done"] .stButton > button::after { color: var(--primary); background: #FFFFFF; }
section[data-testid="stSidebar"] [class*="st-key-nav-"],
section[data-testid="stSidebar"] [class*="st-key-nav-"] .stButton,
section[data-testid="stSidebar"] [class*="st-key-jump"],
section[data-testid="stSidebar"] [class*="st-key-jump"] .stButton { width: 100% !important; }
section[data-testid="stSidebar"] [class*="st-key-nav-"] .stButton > button,
section[data-testid="stSidebar"] [class*="st-key-jump"] .stButton > button { width: 100% !important; }
section[data-testid="stSidebar"] [class*="st-key-nav-"] .stButton > button > div { flex: 1 1 auto; }
section[data-testid="stSidebar"] [class*="st-key-nav-"][class*="-short"] .stButton > button { border-left: 4px solid var(--primary) !important; }
section[data-testid="stSidebar"] [class*="st-key-jump"] .stButton > button p { font-size: 16px !important; }

/* Top strip */
.topline { display: flex; align-items: baseline; gap: 20px; flex-wrap: wrap; }
.persona { font-size: 22px; font-weight: 700; line-height: 1.3; }
.chip { display: inline-block; font-size: 16px; font-weight: 700; padding: 2px 10px; border-radius: 4px; border: 1px solid var(--line); background: var(--surface-alt); color: var(--ink); white-space: nowrap; }
h1.screen-title { font-size: 30px !important; line-height: 1.25; font-weight: 700; margin: 4px 0 0 0 !important; padding: 0 !important; color: var(--ink); }
p.pain-caption { font-size: 18px !important; color: var(--ink-muted) !important; margin: 4px 0 4px 0 !important; }
h2.section-heading { font-size: 22px !important; font-weight: 700; line-height: 1.3; margin: 8px 0 0 0 !important; padding: 0 !important; }
p.sub-heading { font-size: 18px !important; font-weight: 700; line-height: 1.4; margin: 4px 0 2px 0 !important; padding: 0 !important; }

/* Badges */
.badge { display: inline-block; font-size: 16px; font-weight: 700; line-height: 1.4; padding: 1px 8px; border-radius: 4px; border: 1px solid transparent; margin: 0 6px 0 0; white-space: nowrap; vertical-align: middle; }
.badge.neutral { background: var(--surface-alt); color: var(--ink); border-color: var(--line); }
.badge.approved { background: var(--approved-bg); color: var(--approved); border-color: var(--approved); }
.badge.review { background: var(--review-bg); color: var(--review); border-color: var(--review); }
.badge.blocked { background: var(--blocked-bg); color: var(--blocked); border-color: var(--blocked); }

/* Cards */
.card { border: 1px solid var(--line); border-radius: 6px; background: var(--surface); padding: 14px 16px; margin: 0 0 4px 0; }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.card-title { font-size: 19px; font-weight: 700; line-height: 1.35; }
.card-num { display: inline-block; min-width: 26px; font-weight: 700; color: var(--ink-muted); }
.meta { font-size: 16px; color: var(--ink-muted); line-height: 1.5; margin-top: 8px; }
.read-exactly { border: 2px solid var(--ink); border-radius: 4px; padding: 10px 12px; margin-top: 10px; background: #FFFFFF; }
.read-exactly .label { font-size: 16px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-muted); }
.read-exactly .text { font-size: 20px; line-height: 1.5; }
.unit-text { margin-top: 10px; font-size: 18px; line-height: 1.5; }
.callout { margin: 0 0 4px 0; border-radius: 6px; padding: 12px 16px; border: 1px solid var(--line); background: var(--surface-alt); }
.callout.review { background: var(--review-bg); border-color: var(--review); }
.callout.blocked { background: var(--blocked-bg); border-color: var(--blocked); }
.callout.approved { background: var(--approved-bg); border-color: var(--approved); }
.callout strong { font-weight: 700; }
.preview { border-left: 4px solid var(--primary); background: #F3F6FA; padding: 10px 14px; margin-top: 10px; border-radius: 0 4px 4px 0; }
.preview .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 2px 16px; margin-top: 4px; }
.preview .row { display: flex; gap: 8px; }
.preview .key { min-width: 112px; color: var(--ink-muted); }

/* Diff */
.diff del { background: var(--diff-del); color: var(--blocked); text-decoration: line-through; padding: 0 2px; }
.diff ins { background: var(--diff-add); color: var(--approved); text-decoration: underline; padding: 0 2px; }
.legend { font-size: 16px; color: var(--ink-muted); }
.legend del { background: var(--diff-del); color: var(--blocked); padding: 0 4px; }
.legend ins { background: var(--diff-add); color: var(--approved); padding: 0 4px; text-decoration: underline; }

/* Source panel */
.source-panel { border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; height: 520px; overflow: auto; font-size: 17px; line-height: 1.55; background: #FFFFFF; }
.source-panel mark { background: #FFF3BF; color: var(--ink); padding: 0 2px; }
.source-panel .span-tag { display: inline-block; font-size: 16px; font-weight: 700; background: var(--primary); color: #FFFFFF; border-radius: 3px; padding: 0 5px; margin-right: 4px; vertical-align: 2px; }

/* Channel mockups */
.agent { border: 1px solid #2C3E50; border-radius: 8px; overflow: hidden; background: #FFFFFF; }
.agent .bar { background: #2C3E50; color: #FFFFFF; padding: 8px 14px; font-size: 16px; font-weight: 700; }
.agent .body { padding: 12px 14px; }
.phone { width: 340px; max-width: 100%; margin: 0 auto; border: 10px solid #1A1A1A; border-radius: 28px; background: #F4F6F8; overflow: hidden; }
.phone .bar { background: var(--primary); color: #FFFFFF; padding: 10px 14px; font-size: 16px; font-weight: 700; }
.phone .chat { padding: 10px; display: flex; flex-direction: column; gap: 8px; }
.bubble { padding: 10px 12px; border-radius: 14px; font-size: 16px; line-height: 1.45; max-width: 88%; }
.bubble.member { align-self: flex-end; background: var(--primary); color: #FFFFFF; border-bottom-right-radius: 4px; }
.bubble.bot { align-self: flex-start; background: #FFFFFF; border: 1px solid var(--line); border-bottom-left-radius: 4px; }
.bubble .cite { display: block; margin-top: 6px; font-size: 16px; color: var(--ink-muted); }
.changed { background: var(--diff-add); text-decoration: underline; }
.version-strip { font-size: 18px; font-weight: 700; padding: 8px 14px; border-radius: 6px; background: var(--approved-bg); border: 1px solid var(--approved); color: var(--approved); }

/* Metrics */
.tile { border: 1px solid var(--line); border-radius: 6px; padding: 12px 14px; }
.tile .num { font-size: 44px; font-weight: 700; line-height: 1.1; font-variant-numeric: tabular-nums; }
.tile .lbl { font-size: 16px; font-weight: 700; }
.tile .sub { font-size: 16px; color: var(--ink-muted); }

/* Undo bar and readable measure */
.done-note { font-size: 17px; font-weight: 700; color: var(--approved); background: var(--approved-bg); border: 1px solid var(--approved); border-radius: 4px; padding: 4px 10px; }
.unit-text, .meta, p.muted, .callout, .read-exactly .text, .preview { max-width: 80ch; }
.callout { max-width: none; }
.callout > *, .callout { line-height: 1.5; }
[class*="st-key-undo-bar"] .stButton > button { min-height: 36px; }
.field-error { color: var(--blocked); font-weight: 700; font-size: 17px; margin: 0; }
.chip-q { font-size: 16px; color: var(--ink-muted); margin: 2px 0 0 4px; }

/* Activity */
.activity-line { font-size: 16px; line-height: 1.5; color: var(--ink); background: var(--surface-alt); border: 1px solid var(--line); border-radius: 6px; padding: 8px 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.activity-line .who { font-weight: 700; }

.skip-link { position: absolute; left: 8px; top: 8px; background: var(--primary); color: #FFFFFF !important; padding: 8px 12px; z-index: 1000; transform: translateY(-200px); }
.skip-link:focus { transform: none; outline: 3px solid #8A5A00; }
[data-testid="stElementContainer"]:has(.skip-link) { height: 0; min-height: 0; margin: 0; }
@media (prefers-reduced-motion: reduce) { .stApp *, .stApp *::before, .stApp *::after { animation: none !important; transition: none !important; } }
"""


# ---------------------------------------------------------------- basics


def esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def show(markup: str) -> None:
    """Render one HTML fragment. Lines are joined so Markdown never treats indentation as code."""
    st.markdown(" ".join(line.strip() for line in markup.splitlines() if line.strip()), unsafe_allow_html=True)


def inject_css() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def heading(text: str) -> None:
    show(f'<h2 class="section-heading">{esc(text)}</h2>')


def subheading(text: str) -> None:
    show(f'<p class="sub-heading">{esc(text)}</p>')


def muted(text: str) -> None:
    show(f'<p class="muted">{esc(text)}</p>')


def callout(body_html: str, tone: str = "neutral") -> None:
    show(f'<div class="callout {tone}">{body_html}</div>')


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="badge {tone}">{esc(text)}</span>'


def status_badge(row) -> str:
    label, tone = STATUS.get(row["status"], (row["status"], "neutral"))
    if row["status"] == "approved" and _get(row, "stale"):
        return badge("Approved", "approved") + badge("Stale: source changed", "review")
    return badge(label, tone)


def type_badge(row) -> str:
    return badge(str(row["type"]).title(), "neutral")


def verbatim_badge(row) -> str:
    if row["type"] != "verbatim":
        return ""
    if _get(row, "source_mismatch") or _get(row, "verbatim_altered"):
        return badge("Differs from source", "blocked")
    return badge("Matches source exactly", "approved")


def _get(row, key, default=""):
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


def channel_list(row) -> list[str]:
    raw = _get(row, "channels")
    names = []
    for part in str(raw).split(","):
        part = part.strip()
        if part:
            names.append(CHANNEL_NAMES.get(part, part.replace("_", " ").capitalize()))
    return names


def doc_name(doc_id: str) -> str:
    return DOC_NAMES.get(doc_id, doc_id)


def short_date(stamp: str) -> str:
    return str(stamp or "")[:10]


# ---------------------------------------------------------------- navigation


def is_short(conn) -> bool:
    return mode_name(conn) == "short"


def go_to(number: int) -> None:
    st.session_state.undo = None
    st.session_state.screen = number
    st.session_state.persona = SCREEN_ROLE[number]
    st.session_state.role_menu = SCREEN_ROLE[number]
    st.session_state.confirm = None
    st.query_params["screen"] = str(number)


def next_step(conn, number: int):
    if is_short(conn) and number in SHORT_DEMO:
        index = SHORT_DEMO.index(number)
        return SHORT_DEMO[index + 1] if index + 1 < len(SHORT_DEMO) else None
    return number + 1 if number < 8 else None


def _on_role() -> None:
    st.session_state.persona = st.session_state.role_menu


def banner_role() -> str:
    number = st.session_state.screen
    if number == 4 and st.session_state.persona == SCREEN_ROLE[4]:
        return "Pharmacy and Insurance advocates"
    return st.session_state.persona


def render_sidebar(on_jump, conn) -> None:
    show(
        """
        <div class="brand">Harbor Health Knowledge</div>
        <p class="brand-note">Prototype. Illustrative, made-up data.</p>
        <p class="side-heading">The story</p>
        """
    )
    current = st.session_state.screen
    short = is_short(conn)
    for number, name in SCREENS:
        parts = [f"nav-{number}"]
        if number == current:
            parts.append("current")
        if step_done(conn, number):
            parts.append("done")
        if short and number in SHORT_DEMO:
            parts.append("short")
        st.button(
            f"{number}   {name}",
            key="-".join(parts),
            on_click=go_to,
            args=(number,),
            width="stretch",
        )
    show('<p class="side-heading">Demo controls</p>')
    muted("Short demo: steps 0, 1, 3, 4, 5 (blue edge).")
    st.button("Jump to short demo", key="jump-short", on_click=on_jump, width="stretch")
    st.session_state.live_ai = live_enabled(conn)
    st.session_state["live-toggle"] = st.session_state.live_ai
    with st.expander("Settings"):
        st.toggle("Live AI", key="live-toggle", on_change=_on_live, args=(conn,))
        if st.session_state.live_ai:
            if _has_key():
                muted("Live AI is on. New questions call the model. If a call fails, the saved answer is used.")
            else:
                show(
                    '<p class="field-error">No API key is set, so every answer falls back to the saved one.</p>'
                    '<p class="muted">Add ANTHROPIC_API_KEY in the app secrets to call the model.</p>'
                )
        else:
            muted("Saved answers are on, so every answer is repeatable. Each one came from a real model call.")


def _on_live(conn) -> None:
    set_live(conn, bool(st.session_state.get("live-toggle")))
    st.session_state.live_ai = bool(st.session_state.get("live-toggle"))


def _has_key() -> bool:
    try:
        from src.ai import resolve_api_key

        return bool(resolve_api_key())
    except Exception:
        return False


def render_top_strip(on_reset) -> None:
    number = st.session_state.screen
    mode = "Live AI" if st.session_state.get("live_ai") else "Saved AI answers"
    left, role_col, reset_col = st.columns([7, 1.3, 1.6], vertical_alignment="center")
    with left:
        show(
            f"""
            <div class="topline">
              <span class="persona">You are: {esc(banner_role())}</span>
              <span class="chip">Step {number} of 8</span>
              <span class="chip">{esc(mode)}</span>
            </div>
            """
        )
    with role_col:
        with st.popover("Role", width="stretch"):
            st.selectbox("Switch role", ROLES, key="role_menu", on_change=_on_role)
    with reset_col:
        st.button("Reset demo", key="reset", on_click=on_reset, type="tertiary", width="stretch")


def render_screen_header() -> None:
    number = st.session_state.screen
    show(
        f"""
        <h1 id="main-content" class="screen-title">{esc(TITLES[number])}</h1>
        <p class="pain-caption">{esc(CAPTIONS[number])}</p>
        """
    )


def action_row(conn, label: str | None = None, key: str | None = None, secondary: list | None = None) -> str | None:
    """One row: the primary action on the left, optional secondary actions, Next at the right edge.

    Returns the key of the clicked action, or None.
    """
    number = st.session_state.screen
    target = next_step(conn, number)
    secondary = secondary or []
    clicked = None
    align = "distribute" if (label or secondary) else "right"
    with st.container(horizontal=True, horizontal_alignment=align, vertical_alignment="center", key="action-row"):
        with st.container(horizontal=True, width="content", gap="small", key="action-left"):
            if label and st.button(label, key=key, type="primary"):
                clicked = key
            for sec_label, sec_key in secondary:
                if st.button(sec_label, key=sec_key):
                    clicked = sec_key
        with st.container(width="content", key="action-right"):
            if target is None:
                if is_short(conn):
                    st.button("Back to step 0", key="shell-next", on_click=go_to, args=(0,))
            else:
                st.button(
                    f"Next: {STEP_NAMES[target]}",
                    key="shell-next",
                    type="secondary" if label else "primary",
                    on_click=go_to,
                    args=(target,),
                )
    st.session_state.next_placed = True
    return clicked


def render_next(conn) -> None:
    if st.session_state.get("next_placed"):
        return
    action_row(conn)


def activity_bar(conn) -> None:
    rows = list(activity(conn, limit=20))
    if rows:
        latest = rows[0]
        text = (
            f'<span class="who">Latest activity</span> &nbsp; {esc(latest["ts"])} &nbsp; '
            f'<span class="who">{esc(latest["role"])}</span> &nbsp; {esc(latest["message"])}'
        )
    else:
        text = '<span class="who">Latest activity</span> &nbsp; Nothing is recorded yet.'
    show(f'<div class="activity-line" aria-live="polite">{text}</div>')
    with st.expander("Full activity log"):
        for row in rows:
            st.markdown(f"**{row['role']}** · {row['ts']}  \n{row['message']}")


# ---------------------------------------------------------------- diff


_WORDS = re.compile(r"\S+\s*")


def _chunks(old: str, new: str) -> list[tuple[str, str, str]]:
    """Word-level opcodes from difflib, with short equal runs folded into the changes around them.

    Returns (kind, old_text, new_text) where kind is "equal" or "change".
    """
    a = _WORDS.findall(old or "")
    b = _WORDS.findall(new or "")
    raw = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        raw.append(("equal" if op == "equal" else "change", "".join(a[i1:i2]), "".join(b[j1:j2])))
    merged: list[list[str]] = []
    for index, (kind, old_text, new_text) in enumerate(raw):
        short_bridge = (
            kind == "equal"
            and len(old_text.split()) <= 2
            and 0 < index < len(raw) - 1
            and raw[index - 1][0] == "change"
            and raw[index + 1][0] == "change"
        )
        if short_bridge:
            kind = "change"
        if merged and merged[-1][0] == kind == "change":
            merged[-1][1] += old_text
            merged[-1][2] += new_text
        else:
            merged.append([kind, old_text, new_text])
    return [tuple(item) for item in merged]


def diff_html(old: str, new: str) -> str:
    """Word-level diff from difflib. Removed words struck through, added words underlined."""
    out = []
    for kind, old_text, new_text in _chunks(old, new):
        if kind == "equal":
            out.append(esc(old_text))
            continue
        trail = " " if (old_text or new_text).endswith(" ") else ""
        if old_text.strip():
            out.append(f"<del>{esc(old_text.strip())}</del> ")
        if new_text.strip():
            out.append(f"<ins>{esc(new_text.strip())}</ins>{trail}")
    return f'<span class="diff">{"".join(out)}</span>'


def added_only_html(old: str, new: str) -> str:
    """The new text with added words highlighted, no strikethrough. Used inside channel mockups."""
    out = []
    for kind, _old_text, new_text in _chunks(old, new):
        if kind == "equal":
            out.append(esc(new_text))
        elif new_text.strip():
            trail = " " if new_text.endswith(" ") else ""
            out.append(f'<span class="changed">{esc(new_text.strip())}</span>{trail}')
    return "".join(out)


def side_by_side(old: str, new: str) -> tuple[str, str]:
    """Two columns for a conflict: the left marks what only the first wording says, the right what only the second says."""
    left, right = [], []
    for kind, old_text, new_text in _chunks(old, new):
        if kind == "equal":
            left.append(esc(old_text))
            right.append(esc(new_text))
            continue
        if old_text.strip():
            left.append(f"<del>{esc(old_text.strip())}</del> ")
        if new_text.strip():
            right.append(f"<ins>{esc(new_text.strip())}</ins> ")
    return f'<span class="diff">{"".join(left)}</span>', f'<span class="diff">{"".join(right)}</span>'


def diff_legend() -> str:
    return '<span class="legend">Legend: <del>removed</del> <ins>added</ins></span>'


# ---------------------------------------------------------------- unit cards


def _unit_body(row, text_html: str | None = None, label: str = "Read exactly") -> str:
    text = text_html if text_html is not None else esc(row["text"])
    if row["type"] == "verbatim":
        return (
            f'<div class="read-exactly"><div class="label">{esc(label)}</div>'
            f'<div class="text">{text}</div></div>'
        )
    return f'<div class="unit-text">{text}</div>'


def is_expired(row) -> bool:
    """A unit past its review_by date is flagged (SPEC.md: expiry is flagged, a person decides)."""
    import datetime

    review = str(_get(row, "review_by") or "")[:10]
    if not review or row["status"] != "approved":
        return False
    return review < datetime.date.today().isoformat()


def expiry_badge(row) -> str:
    return badge("Review overdue", "review") if is_expired(row) else ""


def scope_line(row) -> str:
    applies = _get(row, "applicability")
    review = str(_get(row, "review_by") or "")[:10]
    parts = []
    if applies:
        parts.append(f"Applies to: {esc(applies)}")
    if review:
        parts.append(f"Review by {esc(review)}")
    return " · ".join(parts)


def _meta_line(row) -> str:
    parts = [f"{esc(row['unit_id'])} v{esc(row['version'])}", esc(_get(row, "kb_scope") or "no knowledge base")]
    if _get(row, "approved_by"):
        parts.append(f"Approved by {esc(row['approved_by'])} {esc(short_date(row['approved_on']))}")
    else:
        parts.append("Not approved yet")
    return " · ".join(parts)


def unit_card(row, key: str, number: int | None = None, text_html: str | None = None, details: bool = True) -> None:
    """Compact unit card (section 8.1). Wording first, one metadata line, details on demand."""
    num = f'<span class="card-num">{number}</span>' if number is not None else ""
    used = channel_list(row)
    used_line = f"Used in: {esc(', '.join(used))}" if used else "Used in: no channel yet"
    linked = _get(row, "superseded_by")
    link_line = ""
    if linked and row["status"] in ("superseded", "merged"):
        verb = "Superseded by" if row["status"] == "superseded" else "Merged into"
        link_line = f"<div class=\"meta\">{verb} {esc(linked)}</div>"
    show(
        f"""
        <div class="card">
          <div class="card-head">
            <div class="card-title">{num}{esc(row['title'])}</div>
            <div>{type_badge(row)}{status_badge(row)}</div>
          </div>
          {_unit_body(row, text_html)}
          <div class="meta">{verbatim_badge(row)}{expiry_badge(row)}{_meta_line(row)}<br>{used_line}<br>{scope_line(row)}</div>
          {link_line}
        </div>
        """
    )
    if details:
        with st.expander(f"Details for {row['unit_id']}"):
            tag_label = "Tags" if _get(row, "tags_confirmed") else "Suggested tags (AI)"
            st.markdown(
                f"**{tag_label}:** {_get(row, 'tags')}  \n"
                f"**Domain:** {_get(row, 'domain')}  \n"
                f"**Audience:** {str(_get(row, 'audience')).replace(',', ', ')}  \n"
                f"**Source:** {doc_name(_get(row, 'source_doc'))}"
            )
            quote = _get(row, "source_quote")
            if quote:
                show(f'<div class="callout"><span class="muted">Source passage</span><br>{esc(quote)}</div>')
            if _get(row, "notes"):
                muted(str(row["notes"]))


def full_unit_card(conn, row, preview: dict) -> None:
    """Approve screen card (section 8.2). What Legal must check comes first: the verbatim check and the preview,
    then the wording and its source passage."""
    if row["type"] == "verbatim":
        if _get(row, "source_mismatch") or _get(row, "verbatim_altered"):
            callout(
                "<strong>Verbatim check: differs from source.</strong> This unit cannot be approved.",
                "blocked",
            )
        else:
            callout(
                "<strong>Verbatim check: matches source exactly,</strong> character for character.",
                "approved",
            )
    approval_preview(preview)
    unit_card(row, "full", details=False)
    quote = _get(row, "source_quote")
    if quote:
        body = esc(document_body(conn, row["source_doc"]))
        needle = esc(quote)
        start = body.find(needle)
        if start >= 0:
            before = body[max(0, start - 160):start]
            after = body[start + len(needle):start + len(needle) + 120]
            snippet = f"...{before}<mark>{needle}</mark>{after}..."
        else:
            snippet = f"<mark>{needle}</mark>"
        snippet = snippet.replace("## ", "")
        show(
            f'<div class="callout"><span class="muted">Source passage in {esc(doc_name(row["source_doc"]))}</span>'
            f'<div style="font-size:16px;margin-top:4px;">{snippet.replace(chr(10), " ")}</div></div>'
        )


def approval_preview(preview: dict) -> None:
    rows = "".join(
        f'<div class="row"><span class="key">{esc(key)}</span><span>{esc(value)}</span></div>'
        for key, value in preview["rows"]
    )
    show(f'<div class="preview"><strong>If you approve this unit</strong><div class="grid">{rows}</div></div>')


def compute_preview(conn, row) -> dict:
    kbs = {part.strip() for part in str(_get(row, "kb_scope")).split(",") if part.strip()}
    audience = str(_get(row, "audience"))
    readers = []
    for role in ("Pharmacy advocate", "Insurance advocate"):
        if kbs & set(ROLE_KB[role]):
            readers.append(role)
    if "member" in audience or "both" in audience:
        readers.append("Member chat")
    channels = channel_list(row)
    replaced = conn.execute(
        "SELECT unit_id, source_doc, status FROM units WHERE superseded_by = ? AND version = 1",
        (row["unit_id"],),
    ).fetchall()
    docs = sorted({doc_name(item["source_doc"]) for item in replaced})
    if replaced:
        replaces = f"{len(replaced)} other wordings in {', '.join(docs)}"
    else:
        replaces = "No other wording"
    return {
        "rows": [
            ("Searchable by", ", ".join(readers) or "No role yet"),
            ("Appears in", ", ".join(channels) or "No channel yet"),
            ("Replaces", replaces),
            ("Approved by", "Legal approver" if _get(row, "requires_legal") else "Knowledge Ops author"),
            ("Applies to", _get(row, "applicability") or "Not recorded"),
        ]
    }


# ---------------------------------------------------------------- search


def _source_line(source) -> str:
    return {
        "cached": "Saved model answer.",
        "live": "Live model answer.",
        "fallback": "Live call unavailable, so the saved model answer is shown.",
        "live_failed": "The live call failed and no saved answer exists.",
    }.get(source or "", "")


def answer_card(result: dict) -> None:
    role = result["role"]
    show(
        f"""
        <p class="sub-heading">Answer for: {esc(role)}</p>
        <p class="muted">Searched: {esc(', '.join(result.get('searched') or []) or 'nothing')}</p>
        """
    )
    if result.get("ai_source") == "missing":
        callout(
            "<strong>No saved answer for this question.</strong> The demo uses saved model answers. "
            "Choose one of the prepared questions below the search button.",
            "review",
        )
        return
    if result["abstained"]:
        why = result.get("note") or "No approved unit matched."
        callout(
            "<div class=\"card-title\">No approved answer</div>"
            "Nothing this role is allowed to read answers the question. The question was added to the "
            f"knowledge team's gap queue.<div class=\"meta\">Why (AI): {esc(why)}</div>",
            "neutral",
        )
        nearest = [unit_id for _rank, unit_id in (result.get("ranked") or [])][:2]
        if nearest:
            from src.corpus import load_corpus

            by_id = load_corpus()["by_id"]
            names = [f"{(by_id.get(unit_id) or {}).get('title', unit_id)} ({unit_id})" for unit_id in nearest]
            with st.expander("Closest approved units this role can read (not an answer)"):
                for name in names:
                    st.markdown(f"- {name}")
        return
    row = result["unit"]
    used = ", ".join(channel_list(row)) or "no channel yet"
    show(
        f"""
        <div class="card">
          {_unit_body(row)}
          <div class="meta"><strong>Source:</strong> {esc(row['unit_id'])} v{esc(row['version'])} · {esc(row['title'])} ·
          {esc(doc_name(row['source_doc']))}<br><strong>Applies to:</strong> {esc(_get(row, 'applicability') or 'not recorded')}
          {expiry_badge(row)}<br><strong>Approved by:</strong> {esc(_get(row, 'approved_by') or 'not recorded')}
          on {esc(_get(row, 'approved_on') or 'not recorded')}<br><strong>Used in:</strong> {esc(used)}</div>
          <div class="meta"><strong>Why this unit (AI):</strong> {esc(result.get('note') or '')}</div>
          <div class="meta">{esc(_source_line(result.get('ai_source')))}</div>
        </div>
        """
    )


# ---------------------------------------------------------------- channels


def agent_mockup(row, text_html: str | None = None) -> None:
    text = text_html if text_html is not None else esc(row["text"])
    show(
        f"""
        <div class="agent">
          <div class="bar">Agent Assist · Pricing the fill</div>
          <div class="body">
            <div class="muted">Member asked about a drug price. Read before quoting any amount.</div>
            <div class="read-exactly"><div class="label">Read to member</div><div class="text">{text}</div></div>
            <div class="meta">{esc(row['unit_id'])} v{esc(row['version'])} · approved by {esc(_get(row, 'approved_by') or 'Legal')}
            {esc(short_date(_get(row, 'approved_on')))}</div>
          </div>
        </div>
        """
    )


def member_mockup(row, text_html: str | None = None) -> None:
    member_text = _get(row, "member_text") or row["text"]
    text = text_html if text_html is not None else esc(member_text)
    show(
        f"""
        <div class="phone">
          <div class="bar">Harbor Health · Chat</div>
          <div class="chat">
            <div class="bubble member">How much will my prescription cost?</div>
            <div class="bubble bot">{text}
              <span class="cite">Source: Harbor Health pricing disclaimer, version {esc(row['version'])}</span>
            </div>
          </div>
        </div>
        """
    )


# ---------------------------------------------------------------- metrics


def metric_tile(label: str, value: str, sub: str) -> None:
    show(
        f"""
        <div class="tile">
          <div class="num">{esc(value)}</div>
          <div class="lbl">{esc(label)}</div>
          <div class="sub">{esc(sub)}</div>
        </div>
        """
    )


def source_panel(conn, doc_id: str, units: list) -> None:
    """The source document with each unit's span highlighted and numbered to match its card."""
    body = esc(document_body(conn, doc_id))
    for index, unit in enumerate(units, start=1):
        needle = esc(_get(unit, "source_quote"))
        if needle and needle in body:
            body = body.replace(
                needle,
                f'<span class="span-tag">{index}</span><mark>{needle}</mark>',
                1,
            )
    body = body.replace("\n", "<br>")
    st.markdown(f'<div class="source-panel">{body}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- undo and feedback (interaction-design 3.5, 3.6, 15.8)


def checkpoint(conn, done_label: str) -> None:
    """Save the demo state before an action so the presenter can undo it.

    Undo beats a confirmation dialog for reversible actions. One level is kept.
    """
    import sqlite3
    import uuid
    from pathlib import Path

    folder = Path("/tmp/harbor-demo")
    folder.mkdir(exist_ok=True)
    copy_path = folder / f"undo-{uuid.uuid4().hex}.sqlite"
    target = sqlite3.connect(str(copy_path))
    conn.commit()
    conn.backup(target)
    target.close()
    st.session_state.undo = {
        "path": str(copy_path),
        "label": done_label,
        "screen": st.session_state.screen,
    }


def _undo() -> None:
    undo = st.session_state.get("undo")
    if not undo:
        return
    screen = undo.get("restore_screen", undo["screen"])
    st.session_state.db_path = undo["path"]
    st.session_state.screen = screen
    st.session_state.persona = SCREEN_ROLE[screen]
    st.session_state.role_menu = SCREEN_ROLE[screen]
    st.query_params["screen"] = str(screen)
    for key in ("scored", "approved_note", "conflict_message"):
        st.session_state.pop(key, None)
    st.session_state.undo = None


def undo_bar() -> None:
    """A quiet confirmation of the last action with an Undo link, shown on the step where it happened."""
    undo = st.session_state.get("undo")
    if not undo or undo["screen"] != st.session_state.screen:
        return
    with st.container(horizontal=True, vertical_alignment="center", key="undo-bar", gap="small"):
        show(f'<div class="done-note" aria-live="polite">{esc(undo["label"])}</div>')
        st.button("Undo", key="undo-last", type="tertiary", on_click=_undo)


def scroll_to_top_on_step_change() -> None:
    """Return to the top when the step changes, so a new step never opens mid-page."""
    number = st.session_state.screen
    if st.session_state.get("rendered_screen") == number:
        return
    st.session_state.rendered_screen = number
    import streamlit.components.v1 as components

    # The step number makes each step's script unique, so the browser runs it again on every step change.
    components.html(
        f"""
        <script>
        // step {number}
        function toTop() {{
          const doc = window.parent.document;
          for (const sel of ['[data-testid="stMain"]', '[data-testid="stAppViewContainer"]', 'section.main']) {{
            const el = doc.querySelector(sel);
            if (el) {{ el.scrollTop = 0; }}
          }}
          window.parent.scrollTo(0, 0);
        }}
        toTop();
        setTimeout(toTop, 150);
        </script>
        """,
        height=0,
    )


def working(label: str = "Asking the model…"):
    """A spinner for slow work. Cached answers return at once, so only live calls show it (no flicker)."""
    from contextlib import nullcontext

    if st.session_state.get("live_ai"):
        return st.spinner(label)
    return nullcontext()
