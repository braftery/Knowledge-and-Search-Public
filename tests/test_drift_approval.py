"""Legal can approve or return a drift fix after it is sent."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.engine import (
    apply_prepared_drift,
    approve_drift_fix,
    build_database,
    connect,
    document_body,
    drift_state,
    legal_drift_items,
    live_approved,
    resolve_returned_drift,
    return_drift_fix,
    send_drift_to_legal,
)


def _database():
    folder = tempfile.mkdtemp()
    path = str(Path(folder) / "drift.sqlite")
    build_database(path, mode="jump")
    return connect(path)


def _snapshot(conn) -> str:
    folder = tempfile.mkdtemp()
    path = str(Path(folder) / "undo.sqlite")
    copy = sqlite3.connect(path)
    conn.commit()
    conn.backup(copy)
    copy.close()
    return path


def _restore(conn, path: str) -> None:
    saved = sqlite3.connect(path)
    saved.backup(conn)
    saved.close()


def _prepare(conn):
    message = apply_prepared_drift(conn, "material")
    if message:
        raise AssertionError(message)
    return send_drift_to_legal(conn)


class DriftApprovalTests(unittest.TestCase):
    def test_approval_publishes_the_next_version_to_every_channel(self):
        conn = _database()
        self.assertEqual(legal_drift_items(conn), [])
        self.assertEqual(_prepare(conn), "")
        before = live_approved(conn, "U-RX-EDU-001-09")
        state = drift_state(conn)
        items = legal_drift_items(conn)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["unit_id"], before["unit_id"])
        self.assertEqual(item["old_wording"], before["text"])
        self.assertEqual(item["new_wording"], state["proposed_text"])
        self.assertIn("31-day", item["new_wording"])
        self.assertNotIn("31-day", item["old_wording"])
        self.assertEqual(item["source_before"], "30-day supply")
        self.assertEqual(item["source_after"], "31-day supply")
        self.assertIn("30-day supply", item["member_text"])

        self.assertEqual(approve_drift_fix(conn, role="Pharmacy advocate"), "Only a Legal approver can approve a drift fix.")
        self.assertEqual(len(legal_drift_items(conn)), 1)
        before_publish = _snapshot(conn)
        self.assertEqual(approve_drift_fix(conn), "")
        _restore(conn, before_publish)
        self.assertEqual(len(legal_drift_items(conn)), 1)
        self.assertEqual(live_approved(conn, before["unit_id"])["version"], before["version"])

        self.assertEqual(approve_drift_fix(conn), "")
        self.assertEqual(approve_drift_fix(conn), "No drift fix is waiting for Legal.")
        self.assertEqual(legal_drift_items(conn), [])
        after = live_approved(conn, before["unit_id"])
        self.assertEqual(after["version"], before["version"] + 1)
        self.assertEqual(after["text"], item["new_wording"])
        self.assertEqual(after["channels"], before["channels"])
        self.assertEqual(after["stale"], 0)
        self.assertEqual(after["search_visible"], 1)
        self.assertIn("31-day supply", after["member_text"])
        self.assertNotIn("30-day supply", after["member_text"])
        old = conn.execute(
            "SELECT status, search_visible, text, stale FROM units WHERE unit_id = ? AND version = ?",
            (before["unit_id"], before["version"]),
        ).fetchone()
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(old["search_visible"], 0)
        self.assertNotIn("31-day", old["text"])
        self.assertIn("31-day", document_body(conn, "SRC-RX-EDU-001"))
        self.assertFalse(drift_state(conn)["stale"])
        logged = conn.execute(
            "SELECT role, message FROM activity ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(logged["role"], "Legal approver")
        self.assertIn(f"version {after['version']}", logged["message"])
        self.assertIn("Every channel now shows", logged["message"])

    def test_send_back_keeps_the_live_version_until_the_author_resolves_it(self):
        conn = _database()
        self.assertEqual(_prepare(conn), "")
        before = live_approved(conn, "U-RX-EDU-001-09")
        self.assertEqual(return_drift_fix(conn, "  "), "A reason is required.")
        self.assertEqual(
            resolve_returned_drift(conn, "Keep the approved days supply."),
            "No drift fix is waiting for the author.",
        )
        self.assertEqual(before["stale"], 1)
        before_return = _snapshot(conn)
        self.assertEqual(return_drift_fix(conn, "The 30-day supply is still the signed wording."), "")
        _restore(conn, before_return)
        self.assertEqual(len(legal_drift_items(conn)), 1)

        self.assertEqual(return_drift_fix(conn, "The 30-day supply is still the signed wording."), "")
        self.assertEqual(legal_drift_items(conn), [])
        live = live_approved(conn, before["unit_id"])
        self.assertEqual(live["version"], before["version"])
        self.assertEqual(live["text"], before["text"])
        self.assertEqual(live["stale"], 1)
        self.assertTrue(drift_state(conn)["stale"])
        self.assertEqual(resolve_returned_drift(conn, "  "), "A note is required.")
        self.assertEqual(resolve_returned_drift(conn, "Keep the signed 30-day wording.", role="Legal approver"), "Only a Knowledge Ops author can resolve a returned drift fix.")
        before_resolve = _snapshot(conn)
        self.assertEqual(resolve_returned_drift(conn, "Keep the signed 30-day wording."), "")
        _restore(conn, before_resolve)
        self.assertEqual(live_approved(conn, before["unit_id"])["stale"], 1)

        self.assertEqual(resolve_returned_drift(conn, "Keep the signed 30-day wording."), "")
        resolved = live_approved(conn, before["unit_id"])
        self.assertEqual(resolved["text"], before["text"])
        self.assertEqual(resolved["stale"], 0)
        self.assertEqual(resolved["search_visible"], 1)
        self.assertFalse(drift_state(conn)["stale"])
        self.assertIn("31-day", document_body(conn, "SRC-RX-EDU-001"))
        self.assertNotIn("31-day", resolved["text"])
        messages = list(conn.execute("SELECT role, message FROM activity ORDER BY id").fetchall())
        returned = next(row for row in messages if "Sent the drift fix" in row["message"])
        self.assertEqual(returned["role"], "Legal approver")
        self.assertIn("30-day supply is still the signed wording", returned["message"])
        done = next(row for row in messages if row["message"].startswith("Resolved the returned drift fix"))
        self.assertEqual(done["role"], "Knowledge Ops author")
        self.assertIn("Keep the signed 30-day wording", done["message"])

    def test_cosmetic_edit_inside_verbatim_goes_to_legal(self):
        conn = _database()
        before = live_approved(conn, "U-RX-EDU-001-09")["text"]
        self.assertEqual(apply_prepared_drift(conn, "cosmetic"), "")
        items = legal_drift_items(conn)
        self.assertEqual(len(items), 1)
        self.assertIn("Cosmetic change inside Legal wording", items[0]["summary"])
        self.assertEqual(live_approved(conn, "U-RX-EDU-001-09")["text"], before)
        self.assertEqual(send_drift_to_legal(conn), "No material change is waiting for Legal.")


if __name__ == "__main__":
    unittest.main()
