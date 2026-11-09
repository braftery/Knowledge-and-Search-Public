"""Legal routing for a gap draft or a unit Legal sent back."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.engine import (
    approve_by_author,
    approve_one,
    author_queue,
    build_database,
    connect,
    decline_unit,
    edit_gap_draft,
    edit_returned_unit,
    search,
    send_gap_to_approval,
    send_returned_to_approval,
    waiting_units,
)

QUOTE = "Routed to Legal: quotes approved verbatim wording from Pricing estimate disclaimer (Legal)."
COST = "Routed to Legal: mentions cost."
TYPE = "Routed to Legal: policy or verbatim type."
AUTHOR = "Routed to Knowledge Ops approvals: procedure or FAQ with no verbatim or cost wording."
RETURNED = "Routed to Legal: Legal sent it back, so Legal approves the change."
PLACEHOLDER = "[approved disclaimer unit ID, e.g., U-RX-EDU-001-09]"
QUESTION = "whats the rx pricing disclamer i have to read"
NEUTRAL = "Open the member record and confirm the spelling of the name before the script."


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


def _reason(conn, unit_id: str) -> str:
    row = conn.execute(
        "SELECT routing_reason, requires_legal FROM units WHERE unit_id = ? AND version = 1",
        (unit_id,),
    ).fetchone()
    return row


class LegalRoutingTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp()
        self.path = str(Path(folder) / "route.sqlite")
        build_database(self.path, mode="explore")
        self.conn = connect(self.path)

    def _send_gap(self, gap_id: str, text: str, member_text: str = "", draft_type: str | None = None):
        if draft_type:
            self.conn.execute("UPDATE gaps SET draft_type = ? WHERE id = ?", (draft_type, gap_id))
            self.conn.commit()
        self.assertEqual(edit_gap_draft(self.conn, gap_id, text, member_text), "")
        before = _snapshot(self.conn)
        self.assertEqual(send_gap_to_approval(self.conn, gap_id), "")
        return before

    def _assert_queue(self, unit_id: str, legal: bool):
        legal_ids = [row["unit_id"] for row in waiting_units(self.conn)]
        author_ids = [row["unit_id"] for row in author_queue(self.conn)]
        if legal:
            self.assertIn(unit_id, legal_ids)
            self.assertNotIn(unit_id, author_ids)
        else:
            self.assertIn(unit_id, author_ids)
            self.assertNotIn(unit_id, legal_ids)

    def _undo_send(self, before: str, unit_id: str, gap_id: str, status: str = "proposed"):
        _restore(self.conn, before)
        self.assertIsNone(
            self.conn.execute("SELECT 1 FROM units WHERE unit_id = ?", (unit_id,)).fetchone()
        )
        gap = self.conn.execute("SELECT status, unit_id FROM gaps WHERE id = ?", (gap_id,)).fetchone()
        self.assertEqual(gap["unit_id"], "")
        self.assertEqual(gap["status"], status)

    def test_gap_c0_quotes_approved_verbatim_and_legal_closes_it(self):
        row = self.conn.execute("SELECT draft_text, queries FROM gaps WHERE id = 'c0'").fetchone()
        self.assertIn(PLACEHOLDER, row["draft_text"])
        self.assertIn(QUESTION, row["queries"])
        filled = row["draft_text"].replace(PLACEHOLDER, "U-RX-EDU-001-09")
        self.assertNotIn("[", filled)
        before = self._send_gap("c0", filled)
        unit_id = "U-GAP-c0"
        stored = _reason(self.conn, unit_id)
        self.assertEqual(stored["routing_reason"], QUOTE)
        self.assertEqual(stored["requires_legal"], 1)
        self._assert_queue(unit_id, legal=True)
        logged = self.conn.execute(
            "SELECT role, message FROM activity ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(logged["role"], "Knowledge Ops author")
        self.assertEqual(logged["message"], QUOTE)
        self._undo_send(before, unit_id, "c0", "in_review")

        self.assertEqual(send_gap_to_approval(self.conn, "c0"), "")
        self.assertEqual(approve_by_author(self.conn, unit_id), "Legal approves this unit.")
        self.assertEqual(approve_one(self.conn, unit_id), f"Approved {unit_id}.")
        closed = self.conn.execute("SELECT status, unit_id FROM gaps WHERE id = 'c0'").fetchone()
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["unit_id"], unit_id)
        hit = search(self.conn, "Pharmacy advocate", QUESTION)
        self.assertFalse(hit["abstained"])
        self.assertEqual(hit["ai_source"], "closed_gap")
        self.assertEqual(hit["unit"]["unit_id"], unit_id)
        self.assertIn("The price I quote is an estimate", hit["unit"]["text"])

    def test_cost_words_match_whole_words_only(self):
        cases = [
            ("The training card shows $35.", COST, True),
            ("The training card shows $1,200.00.", COST, True),
            ("Ask whether the member already paid the copay at the desk.", COST, True),
            ("Ask whether the member already paid the copayment at the desk.", COST, True),
            ("Ask whether the member already paid the copays at the desk.", COST, True),
            ("The plan MOOP is listed on the card for this call.", COST, True),
            ("The plan lists an out-of-pocket limit for this call.", COST, True),
            ("The costume for the fair is priceless to the team that made it.", AUTHOR, False),
        ]
        for text, reason, legal in cases:
            with self.subTest(text=text):
                before = self._send_gap("c9", text)
                stored = _reason(self.conn, "U-GAP-c9")
                self.assertEqual(stored["routing_reason"], reason)
                self.assertEqual(stored["requires_legal"], 1 if legal else 0)
                self._assert_queue("U-GAP-c9", legal=legal)
                self._undo_send(before, "U-GAP-c9", "c9")

    def test_procedure_without_verbatim_or_cost_stays_with_the_author(self):
        before = self._send_gap("c1", NEUTRAL)
        stored = _reason(self.conn, "U-GAP-c1")
        self.assertEqual(stored["routing_reason"], AUTHOR)
        self.assertEqual(stored["requires_legal"], 0)
        self._assert_queue("U-GAP-c1", legal=False)
        self._undo_send(before, "U-GAP-c1", "c1")

    def test_type_wins_over_a_quote_and_a_cost_word(self):
        disclaimer = self.conn.execute(
            "SELECT text FROM units WHERE unit_id = 'U-RX-EDU-001-09'"
        ).fetchone()["text"]
        before = self._send_gap("c8", disclaimer, draft_type="policy")
        stored = _reason(self.conn, "U-GAP-c8")
        self.assertEqual(stored["routing_reason"], TYPE)
        self._assert_queue("U-GAP-c8", legal=True)
        self._undo_send(before, "U-GAP-c8", "c8")

    def test_quote_match_needs_a_sentence_and_folds_quotes(self):
        self.conn.execute(
            """
            INSERT INTO units (
                unit_id, version, title, type, text, status, search_visible, requires_legal
            ) VALUES
                ('U-TEST-FEW', 1, 'Few words', 'verbatim', 'Read the callback script.', 'approved', 1, 1),
                ('U-TEST-LINE', 1, 'Harbor callback script', 'verbatim', 'Read the harbor callback script.', 'approved', 1, 1)
            """
        )
        self.conn.commit()
        few = "Read the callback script. Then continue the education call with the member."
        before = self._send_gap("c9", few)
        self.assertEqual(_reason(self.conn, "U-GAP-c9")["routing_reason"], AUTHOR)
        self._undo_send(before, "U-GAP-c9", "c9")

        line = "Read the harbor callback script. Then continue the education call with the member."
        before = self._send_gap("c9", line)
        self.assertEqual(
            _reason(self.conn, "U-GAP-c9")["routing_reason"],
            "Routed to Legal: quotes approved verbatim wording from Harbor callback script.",
        )
        self._undo_send(before, "U-GAP-c9", "c9")

        raw = self.conn.execute(
            "SELECT text FROM units WHERE unit_id = 'U-RX-EDU-001-09'"
        ).fetchone()["text"]
        curly = raw.replace("'", "\u2019").replace(" today. ", "  today.\n\n")
        draft = f"Read this disclaimer exactly as written:\n\n\u201c{curly}\u201d"
        before = self._send_gap("c9", draft)
        self.assertEqual(_reason(self.conn, "U-GAP-c9")["routing_reason"], QUOTE)
        self._undo_send(before, "U-GAP-c9", "c9")

        before = self._send_gap("c9", NEUTRAL, raw)
        self.assertEqual(_reason(self.conn, "U-GAP-c9")["routing_reason"], QUOTE)
        self._undo_send(before, "U-GAP-c9", "c9")

        fragment = "Ask about the 30-day supply window for this member before the call."
        before = self._send_gap("c9", fragment)
        self.assertEqual(_reason(self.conn, "U-GAP-c9")["routing_reason"], AUTHOR)
        self._undo_send(before, "U-GAP-c9", "c9")

    def test_returned_unit_never_drops_below_legal(self):
        """A unit Legal sent back goes back to Legal even when its new wording would not trigger the rule."""
        self.assertTrue(decline_unit(self.conn, "U-RX-EDU-001-08", "Needs a plainer line.").startswith("Returned"))
        self.assertEqual(edit_returned_unit(self.conn, "U-RX-EDU-001-08", NEUTRAL, ""), "")
        self.assertEqual(send_returned_to_approval(self.conn, "U-RX-EDU-001-08"), "")
        stored = _reason(self.conn, "U-RX-EDU-001-08")
        self.assertEqual(stored["requires_legal"], 1)
        self.assertEqual(stored["routing_reason"], RETURNED)
        self._assert_queue("U-RX-EDU-001-08", legal=True)

    def test_returned_unit_follows_the_same_rule(self):
        self.assertTrue(decline_unit(self.conn, "U-RX-EDU-001-08", "Needs a plainer line.").startswith("Returned"))
        disclaimer = self.conn.execute(
            "SELECT text FROM units WHERE unit_id = 'U-RX-EDU-001-09'"
        ).fetchone()["text"]
        cases = [
            (NEUTRAL, "", "procedure", RETURNED, True),
            ("The training card shows $35.", "", "faq", COST, True),
            ("Ask whether the member already paid the copay at the desk.", "", "faq", COST, True),
            (disclaimer, "", "procedure", QUOTE, True),
            (NEUTRAL, "", "policy", TYPE, True),
        ]
        for text, member, draft_type, reason, legal in cases:
            with self.subTest(reason=reason, draft_type=draft_type):
                self.conn.execute(
                    "UPDATE units SET type = ? WHERE unit_id = ? AND version = 1",
                    (draft_type, "U-RX-EDU-001-08"),
                )
                self.conn.commit()
                self.assertEqual(edit_returned_unit(self.conn, "U-RX-EDU-001-08", text, member), "")
                before = _snapshot(self.conn)
                self.assertEqual(send_returned_to_approval(self.conn, "U-RX-EDU-001-08"), "")
                stored = _reason(self.conn, "U-RX-EDU-001-08")
                self.assertEqual(stored["routing_reason"], reason)
                self.assertEqual(stored["requires_legal"], 1 if legal else 0)
                self._assert_queue("U-RX-EDU-001-08", legal=legal)
                notes = self.conn.execute(
                    "SELECT notes, status FROM units WHERE unit_id = ? AND version = 1",
                    ("U-RX-EDU-001-08",),
                ).fetchone()
                self.assertEqual(notes["status"], "proposed")
                self.assertIn("plainer line", notes["notes"])
                logged = self.conn.execute(
                    "SELECT role, message FROM activity ORDER BY id DESC LIMIT 1"
                ).fetchone()
                self.assertEqual(logged["role"], "Knowledge Ops author")
                self.assertEqual(logged["message"], reason)
                _restore(self.conn, before)
                restored = self.conn.execute(
                    "SELECT status, requires_legal, routing_reason FROM units WHERE unit_id = ? AND version = 1",
                    ("U-RX-EDU-001-08",),
                ).fetchone()
                self.assertEqual(restored["status"], "returned")
                self.assertEqual(restored["requires_legal"], 1)
                self.assertEqual(restored["routing_reason"], "")


if __name__ == "__main__":
    unittest.main()
