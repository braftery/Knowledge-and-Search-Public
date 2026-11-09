"""Every query the demo issues must have a cached model answer."""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("ANTHROPIC_API_KEY", None)

import src.ai as ai
from src.demo_paths import REDACT_QUERY, UNCLUSTERED_QUERY, walk_demo_paths
from src.engine import (
    UNCLUSTERED_LABEL,
    activity,
    drift_events,
    expired_units,
    gaps,
    presenter_unit_ids,
    search,
    waiting_units,
)


def _refuse(*_args, **_kwargs):
    raise AssertionError("cached mode called the model")


class DemoPathTests(unittest.TestCase):
    def test_demo_paths_have_cached_answers(self):
        ai.call_model = _refuse
        missing = []
        for name, conn, queries in walk_demo_paths():
            for role, query in queries:
                found = search(conn, role, query, record=False)
                if found["ai_source"] == "missing":
                    missing.append(f"{name} | {role} | {query}")
            if name.startswith("after-") or "-after-" in name:
                events = list(drift_events(conn))
                if not events:
                    missing.append(f"{name} | drift | no event")
                elif events[-1]["ai_source"] == "missing":
                    missing.append(f"{name} | drift | missing")
            if name == "short-partial":
                waiting = [row["unit_id"] for row in waiting_units(conn)]
                if waiting != presenter_unit_ids(conn):
                    missing.append(f"short queue {waiting}")
                authors = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM units
                    WHERE approver_role = 'Knowledge Ops'
                       OR approved_by = 'Knowledge Ops author'
                       OR approved_by = 'Sam Patel (Knowledge Ops)'
                    """
                ).fetchone()["n"]
                if authors < 1:
                    missing.append("short demo did not approve author units")
            if name == "jump":
                expired = [row["unit_id"] for row in expired_units(conn)]
                if expired != ["U-RX-EDU-001-13"]:
                    missing.append(f"expired {expired}")
            if name == "full-author":
                authors = conn.execute(
                    "SELECT COUNT(*) AS n FROM units WHERE approved_by = 'Knowledge Ops author' AND status = 'approved'"
                ).fetchone()["n"]
                if authors < 1:
                    missing.append("full path did not record author approvals")
            if name == "full-logged":
                logged = " ".join(row["message"] for row in activity(conn, 10))
                for secret in ("H12345678", "01/02/1950", "415-555-0199", "123456789"):
                    if secret in logged:
                        missing.append(f"logged secret {secret}")
                cluster = next((row for row in gaps(conn) if row["cluster"] == UNCLUSTERED_LABEL), None)
                if cluster is None or UNCLUSTERED_QUERY not in (cluster["queries"] or ""):
                    missing.append("unclustered question was dropped")
                if cluster is not None and int(cluster["search_count"] or 0) < 1:
                    missing.append("unclustered count is empty")
        if missing:
            self.fail(str(len(missing)) + " missing caches\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
