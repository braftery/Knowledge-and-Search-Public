"""Call wrap-ups and change acknowledgements on the engine tables."""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.pop("ANTHROPIC_API_KEY", None)

from src.engine import (
    acknowledgement_overview,
    acknowledge_change,
    activity,
    build_database,
    connect,
    is_acknowledged,
    list_wrapups,
    publish_revision,
    record_wrapup,
    revisions_for_role,
    wrapup_summary,
)

PRICING = "U-RX-EDU-001-09"


def _explore():
    folder = tempfile.mkdtemp()
    path = str(Path(folder) / "explore.sqlite")
    build_database(path, mode="explore")
    return connect(path)


class CallRecordTests(unittest.TestCase):
    def test_wrapup_table_redacts_and_counts(self):
        conn = _explore()
        saved = record_wrapup(
            conn,
            "Pharmacy advocate",
            "drug-price",
            "Drug price question",
            [PRICING, "U-NO-SUCH"],
            True,
            "resolved",
            "member id H12345678 please call back",
        )
        self.assertEqual(saved["id"], "W-1")
        self.assertEqual(saved["unit_ids"], [PRICING])
        self.assertEqual(saved["note"], "[redacted] please call back")
        self.assertTrue(saved["read_verbatim"])
        summary = wrapup_summary(conn)
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["verbatim_required"], 1)
        self.assertEqual(summary["verbatim_confirmed"], 1)
        self.assertEqual(summary["follow_ups"], 0)
        self.assertEqual(list_wrapups(conn)[0]["id"], "W-1")
        logged = " ".join(row["message"] for row in activity(conn, 20))
        self.assertIn("Read the approved wording word for word: yes.", logged)
        self.assertNotIn("H12345678", logged)

        with self.assertRaises(ValueError) as refused:
            record_wrapup(conn, "Member", "x", "reason", [], None, "resolved", "")
        self.assertEqual(str(refused.exception), "Only an advocate can wrap up a call.")

    def test_acknowledgement_table_is_scoped_and_idempotent(self):
        conn = _explore()
        publish_revision(conn)
        pharmacy = revisions_for_role(conn, "Pharmacy advocate")
        self.assertEqual([row["unit_id"] for row in pharmacy], [PRICING])
        insurance = revisions_for_role(conn, "Insurance advocate")
        self.assertNotIn(PRICING, [row["unit_id"] for row in insurance])
        with self.assertRaises(ValueError) as unknown:
            revisions_for_role(conn, "Not a role")
        self.assertEqual(str(unknown.exception), "Unknown role.")

        message, created = acknowledge_change(conn, "Pharmacy advocate", PRICING, 2)
        self.assertTrue(created)
        self.assertEqual(message, "Acknowledged version 2 of Pricing estimate disclaimer.")
        self.assertTrue(is_acknowledged(conn, "Pharmacy advocate", PRICING, 2))
        again, created_again = acknowledge_change(conn, "Pharmacy advocate", PRICING, 2)
        self.assertFalse(created_again)
        self.assertEqual(again, message)
        lines = [
            row["message"]
            for row in activity(conn, 40)
            if row["message"] == "Pharmacy advocate acknowledged version 2 of Pricing estimate disclaimer."
        ]
        self.assertEqual(len(lines), 1)

        overview = acknowledgement_overview(conn)
        item = next(row for row in overview if row["unit_id"] == PRICING)
        self.assertEqual(item["acknowledged_by"], ["Pharmacy advocate"])
        self.assertNotIn("Insurance advocate", item["pending"])
        self.assertNotIn("Insurance advocate", item["acknowledged_by"])

        with self.assertRaises(LookupError):
            acknowledge_change(conn, "Pharmacy advocate", PRICING, 9)
        with self.assertRaises(ValueError) as role:
            acknowledge_change(conn, "Legal approver", PRICING, 2)
        self.assertEqual(str(role.exception), "Only an advocate can acknowledge a change.")
