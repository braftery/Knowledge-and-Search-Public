"""Checks the shell copy, the design-system CSS, and the short-demo preload."""

import tempfile
from pathlib import Path

from src.components import CSS, NEXT, SCREENS, SHORT_DEMO, TITLES
from src.engine import (
    COST_QUERY,
    activity,
    approve_one,
    build_database,
    connect,
    flag,
    presenter_unit_ids,
    search,
    step_done,
    waiting_units,
)

EXACT_BUTTON_CSS = """
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: #0B3A6A !important; color: #FFFFFF !important; border: none !important;
}
.stButton > button[kind="primary"] p { color: #FFFFFF !important; }
.stButton > button:disabled { opacity: .45; cursor: not-allowed; }
header [data-testid="stToolbar"] { display: none; }  /* hides Fork and GitHub icons (U17) */
"""


def main() -> None:
    labels = [name for _number, name in SCREENS]
    expected = [
        "Today's problem",
        "Extract units",
        "Find copies",
        "Legal approves",
        "Search",
        "Every channel",
        "Gaps",
        "Drift",
        "Quality",
    ]
    if labels != expected:
        raise SystemExit(f"sidebar labels {labels}")
    if SHORT_DEMO != (0, 1, 3, 4, 5):
        raise SystemExit(f"short demo {SHORT_DEMO}")
    if list(NEXT) != list(range(8)):
        raise SystemExit(f"next order {list(NEXT)}")
    if 8 in NEXT:
        raise SystemExit("step 8 should not have a Next target")
    if set(TITLES) != set(range(9)):
        raise SystemExit("every step needs a title")
    for token in (
        "--ink: #1A1A1A",
        "--ink-muted: #4A4F55",
        "--surface: #FFFFFF",
        "--surface-alt: #F4F6F8",
        "--line: #C9CED4",
        "--primary: #0B3A6A",
        "--approved: #1E6B3A",
        "--approved-bg: #E6F2EA",
        "--review: #8A5A00",
        "--review-bg: #FFF4D6",
        "--blocked: #9B1C1C",
        "--blocked-bg: #FBEAEA",
        "--diff-del: #FBEAEA",
        "--diff-add: #E6F2EA",
    ):
        if token not in CSS:
            raise SystemExit(f"missing token {token}")
    normalized = "\n".join(line.strip() for line in CSS.splitlines())
    exact = "\n".join(line.strip() for line in EXACT_BUTTON_CSS.splitlines() if line.strip())
    if exact not in normalized:
        raise SystemExit("section 6 button CSS is missing")
    if "stBaseButton-primary" not in CSS:
        raise SystemExit("verified Streamlit button selector is missing")
    folder = tempfile.mkdtemp()
    path = str(Path(folder) / "short.sqlite")
    build_database(path, mode="short")
    conn = connect(path)
    for key in ("extracted", "canonical", "escalated", "website_merged"):
        if not flag(conn, key):
            raise SystemExit(f"short demo missing {key}")
    if flag(conn, "approved"):
        raise SystemExit("short demo must leave the three units unapproved")
    ids = presenter_unit_ids(conn)
    if ids != ["U-RX-EDU-001-09", "U-RX-EDU-001-07", "U-BEN-COST-001-02"]:
        raise SystemExit(f"presenter units {ids}")
    waiting = [row["unit_id"] for row in waiting_units(conn)]
    if waiting != ids:
        raise SystemExit(f"queue order {waiting}")
    approved = conn.execute("SELECT COUNT(*) AS n FROM units WHERE status = 'approved'").fetchone()["n"]
    if approved != 28:
        raise SystemExit(f"preapproved {approved}")
    blocked = conn.execute("SELECT unit_id, status FROM units WHERE status = 'blocked_conflict'").fetchall()
    if any(row["status"] == "approved" for row in blocked):
        raise SystemExit("a blocked unit was approved")
    latest = activity(conn, 1)[0]["message"]
    if latest != "Legal approved 18 units earlier this week. Illustrative.":
        raise SystemExit(f"short log {latest}")
    earlier = " ".join(row["message"] for row in activity(conn, 4))
    if "Knowledge Ops author approved 9 units earlier this week." not in earlier:
        raise SystemExit(f"author log missing {earlier}")
    if step_done(conn, 3):
        raise SystemExit("step 3 is not done until the three units are approved")
    for unit_id in ids:
        approve_one(conn, unit_id)
    if not step_done(conn, 3):
        raise SystemExit("step 3 should be done after the three approvals")
    pharmacy = search(conn, "Pharmacy advocate", COST_QUERY)
    insurance = search(conn, "Insurance advocate", COST_QUERY)
    if pharmacy["abstained"] or pharmacy["unit"]["unit_id"] != ids[0]:
        raise SystemExit(f"pharmacy answer {pharmacy}")
    if insurance["abstained"] or insurance["unit"]["unit_id"] != ids[2]:
        raise SystemExit(f"insurance answer {insurance}")
    print("shell ok")


if __name__ == "__main__":
    main()
