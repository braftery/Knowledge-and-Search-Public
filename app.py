"""Harbor Health knowledge demo. Cached answers are the default."""

import uuid
from pathlib import Path

import streamlit as st

from src.components import (
    scroll_to_top_on_step_change,
    undo_bar,
    TITLES,
    activity_bar,
    go_to,
    inject_css,
    render_next,
    render_screen_header,
    render_sidebar,
    render_top_strip,
)
from src.engine import build_database, connect
from src.explore import DEMO, explore_options, view_changed, view_label, render_explore, render_sidebar_explore, role_from_view
from src.screens import SCREENS_FN


def _fresh(mode: str) -> None:
    folder = Path("/tmp/harbor-demo")
    folder.mkdir(exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.sqlite"
    build_database(str(path), mode=mode)
    st.session_state.db_path = str(path)
    st.session_state.screen = 0
    st.session_state.persona = "Pharmacy advocate"
    st.session_state.role_menu = "Pharmacy advocate"
    st.session_state.confirm = None
    st.session_state.highlight = None
    st.session_state.open_gap = None
    st.session_state.scored = False
    st.session_state.drift_msg = ""
    st.session_state.undo = None
    for key in ("last_query", "query-box", "gap-pick", "approved_note", "conflict_message", "rendered_screen"):
        st.session_state.pop(key, None)
    st.session_state.live_ai = False
    st.session_state["live-toggle"] = False
    st.query_params["screen"] = "0"


def _reset() -> None:
    """Reset keeps the old demo state for one Undo (interaction-design 15.8: undo, not a warning)."""
    previous = {"path": st.session_state.db_path, "screen": st.session_state.screen}
    _fresh("start")
    st.session_state.undo = {
        "path": previous["path"],
        "label": "Demo reset to the start.",
        "screen": 0,
        "restore_screen": previous["screen"],
    }


def _open_linked_screen(raw) -> None:
    if raw in (None, ""):
        return
    try:
        number = int(raw)
    except (TypeError, ValueError):
        return
    if 0 <= number <= 8:
        go_to(number)


if "db_path" not in st.session_state:
    linked = st.query_params.get("screen")
    _fresh("start")
    _open_linked_screen(linked)

screen = st.session_state.screen
view = st.session_state.get("view", DEMO)
explore_role = role_from_view(view)
st.set_page_config(
    page_title=(f"Explore as {explore_role}" if explore_role else TITLES[screen]) + " | Harbor Health",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

if explore_role:
    # Explore mode: its own database and pages. The guided demo's state is not read or changed.
    with st.sidebar:
        st.selectbox("View", explore_options(), key="view", format_func=view_label, on_change=view_changed)
        render_sidebar_explore(explore_role)
    render_explore(explore_role)
    st.stop()

conn = connect(st.session_state.db_path)

st.markdown(
    '<a class="skip-link" href="#main-content">Skip to content</a>',
    unsafe_allow_html=True,
)

st.session_state.next_placed = False

with st.sidebar:
    st.selectbox("View", explore_options(), key="view", format_func=view_label, on_change=view_changed)
    render_sidebar(on_jump=lambda: _fresh("short"), conn=conn)

render_top_strip(on_reset=_reset)
render_screen_header()
undo_bar()
scroll_to_top_on_step_change()
SCREENS_FN[st.session_state.screen](conn)
render_next(conn)
activity_bar(conn)
