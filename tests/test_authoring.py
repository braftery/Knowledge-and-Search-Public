"""Author edit, placeholder block, approval routing, and the closed-gap answer."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.engine import (
    activity,
    approve_by_author,
    approve_one,
    author_queue,
    build_database,
    connect,
    decline_unit,
    edit_gap_draft,
    edit_returned_unit,
    live_approved,
    member_answer,
    search,
    send_gap_to_approval,
    send_returned_to_approval,
    waiting_units,
)

FAQ_TEXT = (
    "A standard Part D prior authorization decision is made within 7 calendar days "
    "after Harbor Health receives a complete request. An expedited request is decided within 72 hours."
)
FAQ_MEMBER = (
    "A standard prior authorization decision takes 7 calendar days. An expedited request takes 72 hours."
)
POLICY_TEXT = (
    "For a maintenance drug, Harbor Health offers a 90-day mail order supply only after "
    "two retail fills of that drug in the current calendar year."
)
POLICY_MEMBER = "A 90-day mail order supply is available after two retail fills of the same drug this year."


def _gap(conn, draft_type, needle):
    rows = conn.execute("SELECT * FROM gaps WHERE draft_type = ?", (draft_type,)).fetchall()
    for row in rows:
        blob = f"{row['draft_title']} {row['cluster']}"
        if needle.lower() in blob.lower():
            return row
    raise AssertionError(f"no {draft_type} gap matching {needle}")


def _lines(stored):
    return [line.strip() for line in (stored or "").split("\n") if line.strip()]


def _messages(conn):
    return list(conn.execute("SELECT role, message FROM activity ORDER BY id").fetchall())


def _snapshot(conn) -> str:
    """Same sqlite backup the presenter undo checkpoint uses."""
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


class GapAuthoringTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp()
        self.path = str(Path(folder) / "author.sqlite")
        build_database(self.path, mode="jump")
        self.conn = connect(self.path)

    def test_placeholder_blocks_send_and_approval_closes_the_loop(self):
        faq = _gap(self.conn, "faq", "prior authorization")
        # Seeded drafts are procedure or faq. Mark one policy to exercise the Legal gate.
        policy = _gap(self.conn, "procedure", "mail order")
        self.conn.execute("UPDATE gaps SET draft_type = 'policy' WHERE id = ?", (policy["id"],))
        self.conn.commit()
        policy = _gap(self.conn, "policy", "mail order")
        self.assertIn("[", faq["draft_text"])
        blocked = send_gap_to_approval(self.conn, faq["id"])
        self.assertIn("Replace every bracketed placeholder", blocked)
        self.assertIn("Still open:", blocked)
        self.assertEqual(
            edit_gap_draft(self.conn, faq["id"], FAQ_TEXT, "[plan name]"),
            "",
        )
        member_blocked = send_gap_to_approval(self.conn, faq["id"])
        self.assertIn("[plan name]", member_blocked)
        self.assertEqual(edit_gap_draft(self.conn, faq["id"], FAQ_TEXT, FAQ_MEMBER), "")
        self.assertEqual(send_gap_to_approval(self.conn, faq["id"]), "")
        self.assertEqual(
            edit_gap_draft(self.conn, faq["id"], FAQ_TEXT, FAQ_MEMBER),
            "This draft was already sent to approval.",
        )
        authored = [row["unit_id"] for row in author_queue(self.conn)]
        legal = [row["unit_id"] for row in waiting_units(self.conn)]
        self.assertIn(f"U-GAP-{faq['id']}", authored)
        self.assertNotIn(f"U-GAP-{faq['id']}", legal)
        faq_unit = self.conn.execute(
            "SELECT type, requires_legal, member_text, origin, channels, search_visible FROM units WHERE unit_id = ?",
            (f"U-GAP-{faq['id']}",),
        ).fetchone()
        self.assertEqual(faq_unit["type"], "faq")
        self.assertEqual(faq_unit["requires_legal"], 0)
        self.assertEqual(faq_unit["member_text"], FAQ_MEMBER)
        self.assertEqual(faq_unit["origin"], f"gap:{faq['id']}")
        self.assertIn("member_chat", faq_unit["channels"])
        self.assertEqual(faq_unit["search_visible"], 0)

        question = _lines(faq["queries"])[0]
        before = search(self.conn, "Pharmacy advocate", question)
        self.assertTrue(before["abstained"])
        self.assertNotEqual(before["ai_source"], "missing")

        self.assertEqual(approve_by_author(self.conn, f"U-GAP-{faq['id']}"), f"Approved U-GAP-{faq['id']}.")
        again = approve_by_author(self.conn, f"U-GAP-{faq['id']}")
        self.assertEqual(again, "This unit stays unapproved.")
        closed = self.conn.execute("SELECT status, unit_id FROM gaps WHERE id = ?", (faq["id"],)).fetchone()
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["unit_id"], f"U-GAP-{faq['id']}")
        live = live_approved(self.conn, f"U-GAP-{faq['id']}")
        self.assertEqual(live["text"], FAQ_TEXT)
        self.assertEqual(live["search_visible"], 1)
        self.assertEqual(
            edit_returned_unit(self.conn, f"U-GAP-{faq['id']}", "Changed after approval."),
            "An approved unit cannot be edited. A change publishes a new version.",
        )
        self.assertIn("can no longer be edited", edit_gap_draft(self.conn, faq["id"], "Later edit."))

        for original in _lines(faq["queries"]):
            hit = search(self.conn, "Pharmacy advocate", original)
            self.assertEqual(hit["unit"]["unit_id"], f"U-GAP-{faq['id']}", original)
            self.assertEqual(hit["ai_source"], "closed_gap")
            self.assertEqual(hit["unit"]["text"], FAQ_TEXT)
            other = search(self.conn, "Insurance advocate", original)
            if not other["abstained"]:
                self.assertNotEqual(other["unit"]["unit_id"], f"U-GAP-{faq['id']}")
            member = member_answer(self.conn, original)
            self.assertFalse(member["abstained"], original)
            self.assertEqual(member["member_text"], FAQ_MEMBER)
            self.assertNotIn("unit", member)
            self.assertIn("version 1", member["citation"])

        self.assertIn("[", policy["draft_text"])
        self.assertEqual(edit_gap_draft(self.conn, policy["id"], POLICY_TEXT, POLICY_MEMBER), "")
        self.assertEqual(send_gap_to_approval(self.conn, policy["id"]), "")
        policy_id = f"U-GAP-{policy['id']}"
        self.assertIn(policy_id, [row["unit_id"] for row in waiting_units(self.conn)])
        self.assertNotIn(policy_id, [row["unit_id"] for row in author_queue(self.conn)])
        self.assertEqual(approve_by_author(self.conn, policy_id), "Legal approves this unit.")
        self.assertEqual(approve_one(self.conn, policy_id), f"Approved {policy_id}.")
        self.assertEqual(approve_one(self.conn, policy_id), "This unit stays unapproved.")
        policy_gap = self.conn.execute("SELECT status FROM gaps WHERE id = ?", (policy["id"],)).fetchone()
        self.assertEqual(policy_gap["status"], "closed")
        policy_question = _lines(policy["queries"])[0]
        policy_hit = search(self.conn, "Pharmacy advocate", policy_question)
        self.assertEqual(policy_hit["unit"]["unit_id"], policy_id)
        self.assertEqual(policy_hit["unit"]["text"], POLICY_TEXT)

        logged = _messages(self.conn)
        edit_rows = [row for row in logged if row["message"].startswith("Edited the")]
        self.assertTrue(edit_rows)
        self.assertTrue(all(row["role"] == "Knowledge Ops author" for row in edit_rows))
        send_rows = [row for row in logged if row["message"].startswith("Sent U-GAP-")]
        self.assertTrue(any(row["message"].endswith("Knowledge Ops approvals.") for row in send_rows))
        self.assertTrue(any(row["message"].endswith("Legal.") for row in send_rows))
        self.assertTrue(all(row["role"] == "Knowledge Ops author" for row in send_rows))
        close_rows = [row for row in logged if row["message"].startswith("Closed the")]
        self.assertEqual(len(close_rows), 2)
        faq_close = next(row for row in close_rows if faq["cluster"] in row["message"])
        policy_close = next(row for row in close_rows if policy["cluster"] in row["message"])
        self.assertEqual(faq_close["role"], "Knowledge Ops author")
        self.assertEqual(policy_close["role"], "Legal approver")

    def test_undo_restores_each_authoring_step(self):
        faq = _gap(self.conn, "faq", "prior authorization")
        original = faq["draft_text"]
        before_edit = _snapshot(self.conn)
        self.assertEqual(edit_gap_draft(self.conn, faq["id"], FAQ_TEXT, FAQ_MEMBER), "")
        _restore(self.conn, before_edit)
        restored = self.conn.execute("SELECT draft_text FROM gaps WHERE id = ?", (faq["id"],)).fetchone()
        self.assertEqual(restored["draft_text"], original)

        self.assertEqual(edit_gap_draft(self.conn, faq["id"], FAQ_TEXT, FAQ_MEMBER), "")
        before_send = _snapshot(self.conn)
        self.assertEqual(send_gap_to_approval(self.conn, faq["id"]), "")
        _restore(self.conn, before_send)
        self.assertIsNone(
            self.conn.execute("SELECT 1 FROM units WHERE unit_id = ?", (f"U-GAP-{faq['id']}",)).fetchone()
        )
        self.assertEqual(
            self.conn.execute("SELECT unit_id FROM gaps WHERE id = ?", (faq["id"],)).fetchone()["unit_id"],
            "",
        )

        self.assertEqual(send_gap_to_approval(self.conn, faq["id"]), "")
        before_approval = _snapshot(self.conn)
        self.assertEqual(approve_by_author(self.conn, f"U-GAP-{faq['id']}"), f"Approved U-GAP-{faq['id']}.")
        _restore(self.conn, before_approval)
        unit = self.conn.execute(
            "SELECT status, search_visible FROM units WHERE unit_id = ?",
            (f"U-GAP-{faq['id']}",),
        ).fetchone()
        self.assertEqual(unit["status"], "proposed")
        self.assertEqual(unit["search_visible"], 0)
        self.assertEqual(
            self.conn.execute("SELECT status FROM gaps WHERE id = ?", (faq["id"],)).fetchone()["status"],
            "in_review",
        )

    def test_wrong_role_cannot_edit(self):
        faq = _gap(self.conn, "faq", "prior authorization")
        refused = edit_gap_draft(self.conn, faq["id"], FAQ_TEXT, role="Member")
        self.assertIn("Knowledge Ops author", refused)
        stored = self.conn.execute("SELECT draft_text FROM gaps WHERE id = ?", (faq["id"],)).fetchone()
        self.assertNotEqual(stored["draft_text"], FAQ_TEXT)


class ReturnedUnitTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp()
        self.path = str(Path(folder) / "returned.sqlite")
        build_database(self.path, mode="explore")
        self.conn = connect(self.path)
        self.unit_id = "U-RX-EDU-001-08"

    def test_returned_unit_is_edited_and_sent_back_to_legal(self):
        approved = edit_returned_unit(self.conn, "U-RX-EDU-001-09", "Do not edit the live disclaimer.")
        self.assertIn("approved unit cannot be edited", approved)
        self.assertTrue(decline_unit(self.conn, self.unit_id, "Needs a plain example. Illustrative.").startswith("Returned"))
        original = self.conn.execute(
            "SELECT text, notes FROM units WHERE unit_id = ? AND version = 1",
            (self.unit_id,),
        ).fetchone()
        self.assertIn("plain example", original["notes"])
        blocked = edit_returned_unit(self.conn, self.unit_id, "Read this [plain example] to the member.", "Member [plain example].")
        self.assertEqual(blocked, "")
        self.assertIn("Replace every bracketed placeholder", send_returned_to_approval(self.conn, self.unit_id))
        placeholder_text = "Read this [plain example] to the member."
        clean = original["text"] + " Here is the plain example the author added."
        member = "Here is the plain example for a member."
        before_edit = _snapshot(self.conn)
        self.assertEqual(edit_returned_unit(self.conn, self.unit_id, clean, member), "")
        _restore(self.conn, before_edit)
        rolled = self.conn.execute(
            "SELECT text FROM units WHERE unit_id = ? AND version = 1",
            (self.unit_id,),
        ).fetchone()
        self.assertEqual(rolled["text"], placeholder_text)

        self.assertEqual(edit_returned_unit(self.conn, self.unit_id, clean, member), "")
        before_send = _snapshot(self.conn)
        self.assertEqual(send_returned_to_approval(self.conn, self.unit_id), "")
        self.assertIn(self.unit_id, [row["unit_id"] for row in waiting_units(self.conn)])
        self.assertNotIn(self.unit_id, [row["unit_id"] for row in author_queue(self.conn) if row["status"] == "returned"])
        _restore(self.conn, before_send)
        self.assertEqual(
            self.conn.execute(
                "SELECT status FROM units WHERE unit_id = ? AND version = 1",
                (self.unit_id,),
            ).fetchone()["status"],
            "returned",
        )

        self.assertEqual(send_returned_to_approval(self.conn, self.unit_id), "")
        before_approval = _snapshot(self.conn)
        self.assertEqual(approve_one(self.conn, self.unit_id), f"Approved {self.unit_id}.")
        self.assertEqual(approve_one(self.conn, self.unit_id), "This unit stays unapproved.")
        live = live_approved(self.conn, self.unit_id)
        self.assertEqual(live["text"], clean)
        self.assertEqual(live["member_text"], member)
        self.assertEqual(live["search_visible"], 1)
        self.assertIn(
            "approved unit cannot be edited",
            edit_returned_unit(self.conn, self.unit_id, "Another edit."),
        )
        _restore(self.conn, before_approval)
        self.assertEqual(
            self.conn.execute(
                "SELECT status, search_visible FROM units WHERE unit_id = ? AND version = 1",
                (self.unit_id,),
            ).fetchone()["status"],
            "proposed",
        )
        logged = " ".join(f"{row['role']}: {row['message']}" for row in _messages(self.conn))
        self.assertIn("Knowledge Ops author: Edited U-RX-EDU-001-08", logged)
        self.assertIn("Knowledge Ops author: Sent U-RX-EDU-001-08 to Legal.", logged)
        # The restored snapshot is from before approval, so the approval log is gone.
        self.assertNotIn(f"Approved {self.unit_id}.", " ".join(row["message"] for row in activity(self.conn, 8)))


if __name__ == "__main__":
    unittest.main()
