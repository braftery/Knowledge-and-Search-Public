"""Human choices for near-duplicates, merged website units, and open conflicts."""

import tempfile
import unittest
from pathlib import Path

from src.engine import build_database, connect, open_conflicts, resolve_conflict


class HumanDecisionTests(unittest.TestCase):
    def test_jump_supersedes_near_duplicates_and_merges_website_units(self):
        folder = tempfile.mkdtemp()
        path = str(Path(folder) / "jump.sqlite")
        build_database(path, mode="jump")
        conn = connect(path)
        rows = {
            row["unit_id"]: row
            for row in conn.execute(
                "SELECT unit_id, status, search_visible, superseded_by FROM units WHERE version = 1"
            )
        }
        for unit_id, kept in (
            ("U-RX-EDU-002-04", "U-RX-EDU-001-05"),
            ("U-RX-EDU-002-06", "U-RX-EDU-001-08"),
            ("U-RX-EDU-002-07", "U-RX-EDU-001-09"),
            ("U-RX-EDU-002-13", "U-RX-EDU-001-16"),
        ):
            self.assertEqual(rows[unit_id]["status"], "superseded")
            self.assertEqual(rows[unit_id]["search_visible"], 0)
            self.assertEqual(rows[unit_id]["superseded_by"], kept)
            self.assertEqual(rows[kept]["status"], "approved")
        for unit_id in ("U-WEB-FAQ-01", "U-WEB-FAQ-02", "U-WEB-FAQ-03"):
            self.assertEqual(rows[unit_id]["status"], "merged")
            self.assertEqual(rows[unit_id]["search_visible"], 0)
            self.assertEqual(rows[unit_id]["superseded_by"], "U-RX-EDU-001-09")
        for unit_id in ("U-RX-EDU-002-11", "U-RX-EDU-002-12"):
            self.assertEqual(rows[unit_id]["status"], "proposed")
            self.assertEqual(rows[unit_id]["search_visible"], 0)

    def test_mail_order_resolution_leaves_the_other_conflicts_open(self):
        folder = tempfile.mkdtemp()
        path = str(Path(folder) / "jump.sqlite")
        build_database(path, mode="jump")
        conn = connect(path)
        self.assertEqual(
            [plan["id"] for plan in open_conflicts(conn)],
            ["greeting", "verification", "mail-order"],
        )
        self.assertEqual(resolve_conflict(conn, "   "), "A reason is required.")
        reason = next(plan["reason"] for plan in open_conflicts(conn) if plan["id"] == "mail-order")
        message = resolve_conflict(conn, reason)
        self.assertIn("U-RX-EDU-001-12", message)
        self.assertEqual([plan["id"] for plan in open_conflicts(conn)], ["greeting", "verification"])
        statuses = {
            row["unit_id"]: (row["status"], row["search_visible"])
            for row in conn.execute(
                """
                SELECT unit_id, status, search_visible FROM units
                WHERE unit_id IN (
                    'U-RX-EDU-001-12', 'U-RX-EDU-002-09', 'U-RX-EDU-002-10',
                    'U-RX-EDU-001-02', 'U-RX-EDU-002-01', 'U-RX-EDU-001-04', 'U-RX-EDU-002-03'
                ) AND version = 1
                """
            )
        }
        self.assertEqual(statuses["U-RX-EDU-001-12"], ("approved", 1))
        self.assertEqual(statuses["U-RX-EDU-002-09"], ("retired", 0))
        self.assertEqual(statuses["U-RX-EDU-002-10"], ("retired", 0))
        self.assertEqual(statuses["U-RX-EDU-001-02"], ("blocked_conflict", 0))
        self.assertEqual(statuses["U-RX-EDU-002-01"], ("blocked_conflict", 0))
        self.assertEqual(statuses["U-RX-EDU-001-04"], ("blocked_conflict", 0))
        self.assertEqual(statuses["U-RX-EDU-002-03"], ("blocked_conflict", 0))
        again = resolve_conflict(conn, reason)
        self.assertIn("once AI has marked the pair a conflict", again)


if __name__ == "__main__":
    unittest.main()
