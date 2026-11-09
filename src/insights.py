"""Knowledge insights: the Knowledge owner's weekly view (EXPERIENCE_SPEC.md section 6).

One page answers "what should we fix first": the top unanswered questions ranked by demand, drift waiting for
Legal, units past their review date, and retrieval quality. Each item links to where it can be acted on.
"""

from __future__ import annotations

import streamlit as st

from src.components import callout, esc, metric_tile, muted, show
from src.engine import drift_state, expired_units, gaps, quality_report

INSIGHTS_CSS = """
<style>
.rank { display:grid; grid-template-columns: minmax(0, 1fr) 160px 48px; gap:8px; align-items:center; padding:6px 0;
  border-bottom:1px solid #E3E6EA; font-size:17px; }
.rank .bar { height:14px; background:#0B3A6A; border-radius:2px; }
.rank .bar-bg { background:#E7EEF6; border-radius:2px; }
.rank .count { text-align:right; font-variant-numeric: tabular-nums; font-weight:700; }
.rank .sub { font-size:16px; color:#4A4F55; }
.digest { border:1px solid #C9CED4; border-radius:8px; padding:10px 14px; background:#F4F6F8; font-size:17px; }
</style>
"""

TILE_LABELS = {
    "hit_at_1": "Right answer first",
    "over_abstain": "Wrong no-answers",
    "leaks": "Cross-role leaks",
}


def page_insights(conn, role: str, go_page) -> None:
    show(INSIGHTS_CSS)
    rows = list(gaps(conn))
    open_gaps = [row for row in rows if row["status"] == "proposed"]
    state = drift_state(conn)
    expired = list(expired_units(conn))
    report = quality_report(conn)
    held = report["golden_table"]["held_out"]
    held_pass = sum(1 for row in held if row["Result"] == "Pass")

    drift_waiting = 1 if state["material"] and not state["sent"] else 0
    def count(number: int, one: str, many: str) -> str:
        return f"{number} {one if number == 1 else many}"

    show(
        f'<div class="digest"><strong>This week:</strong> {count(len(open_gaps), "unanswered question cluster", "unanswered question clusters")}, '
        f'{count(drift_waiting, "source change", "source changes")} waiting for Legal, '
        f'{count(len(expired), "unit", "units")} past the review date. Illustrative, made-up data.</div>'
    )

    tiles = [tile for tile in report["tiles"] if tile["key"] in TILE_LABELS]
    columns = st.columns(len(tiles) + 1)
    for column, tile in zip(columns, tiles):
        with column:
            metric_tile(TILE_LABELS[tile["key"]], tile["display"], tile["detail"])
    with columns[-1]:
        metric_tile("Held-out questions", f"{held_pass} of {len(held)}", "pass, written before tuning")

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        show('<h2 class="section-heading">Top unanswered questions</h2>')
        muted("Ranked by how often advocates and members asked. Each one has an AI draft waiting for a decision.")
        if not open_gaps:
            callout("No open gaps. Every logged question has a decision.", "approved")
        top = max([row["search_count"] for row in open_gaps] or [1])
        for row in open_gaps[:6]:
            width = max(4, int(100 * row["search_count"] / top))
            show(
                f'<div class="rank"><div>{esc(row["cluster"])}<div class="sub">{esc(row["roles"])}</div></div>'
                f'<div class="bar-bg"><div class="bar" style="width:{width}%"></div></div>'
                f'<div class="count">{esc(row["search_count"])}</div></div>'
            )
        if open_gaps:
            st.button("Decide on the top gaps", key="x-ins-gaps", type="primary", on_click=go_page, args=("Gaps",))
    with right:
        show('<h2 class="section-heading">Needs attention</h2>')
        if drift_waiting:
            callout("<strong>1 source change waiting for Legal.</strong> The approved version stays live until Legal decides.", "review")
            st.button("Open drift", key="x-ins-drift", on_click=go_page, args=("Drift",))
        elif state["material"]:
            muted("The source change was sent to Legal.")
        else:
            muted("No source change is waiting.")
        if expired:
            names = ", ".join(row["title"] for row in expired)
            noun = "unit" if len(expired) == 1 else "units"
            callout(f"<strong>{len(expired)} {noun} past the review date:</strong> {esc(names)}. It stays live and is flagged for its owner.", "review")
        else:
            muted("No unit is past its review date.")
        st.button("Open quality details", key="x-ins-quality", on_click=go_page, args=("Quality",))
    from src.feedback_ui import insights_panel

    insights_panel(conn)
