"""Live abstentions draft their own gap. Cached mode stays unclustered."""

import hashlib
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import src.ai as ai
from src.engine import (
    ABSTAIN_QUERY,
    UNCLUSTERED_ID,
    build_database,
    connect,
    gaps,
    redact_query,
    record_search,
    search,
    send_gap_to_approval,
    set_live,
)

NOVEL = "what time does the clinic mailbox get painted"
EMAIL_Q = "email pat@example.com what time does the clinic mailbox get painted"
DRAFT = {
    "title": "Clinic mailbox paint visits",
    "type": "faq",
    "draft_text": "Paint visits happen during [clinic hours]. The illustrative count is 1000001.",
    "placeholders": ["[clinic hours]"],
    "author_checklist": ["Replace the clinic hours placeholder."],
    "suggested_kb": "pharmacy",
}


def _live_id(question: str) -> str:
    safe = redact_query(question)
    digest = hashlib.sha256(safe.encode("utf-8")).hexdigest()[:8]
    return f"live-{digest}"


def _gap_for(conn, question: str):
    needle = redact_query(question).strip().lower()
    for row in gaps(conn):
        queries = [item.strip().lower() for item in (row["queries"] or "").split("\n") if item.strip()]
        if needle in queries:
            return row
    return None


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


class LiveGapTests(unittest.TestCase):
    def setUp(self):
        self._saved_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        self._saved_cap = os.environ.pop("HARBOR_LIVE_CAP_FILE", None)
        self._saved_call = ai.call_model
        self.folder = tempfile.mkdtemp()
        self.cap_path = Path(self.folder) / "cap.json"
        os.environ["HARBOR_LIVE_CAP_FILE"] = str(self.cap_path)
        self.calls = []

    def tearDown(self):
        ai.call_model = self._saved_call
        if self._saved_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = self._saved_key
        if self._saved_cap is None:
            os.environ.pop("HARBOR_LIVE_CAP_FILE", None)
        else:
            os.environ["HARBOR_LIVE_CAP_FILE"] = self._saved_cap

    def _database(self):
        path = str(Path(self.folder) / "live.sqlite")
        build_database(path, mode="jump")
        return connect(path)

    def _mock(self, draft=None):
        payload = DRAFT if draft is None else draft

        def fake(task, user_content, input_ref=""):
            self.calls.append((task, user_content))
            if task == "assess_sufficiency":
                return {"answer_unit_id": None, "reason": "No approved unit covers this question."}, {}
            if task == "draft_gap_unit":
                return payload, {}
            raise AssertionError(task)

        ai.call_model = fake

    def _draft_calls(self):
        return [user for task, user in self.calls if task == "draft_gap_unit"]

    def test_cached_mode_keeps_the_unclustered_bucket(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        self._mock()
        found = search(conn, "Pharmacy advocate", NOVEL, record=True)
        self.assertTrue(found["abstained"])
        self.assertEqual(self._draft_calls(), [])
        self.assertEqual(self.calls, [])
        row = _gap_for(conn, NOVEL)
        self.assertIsNotNone(row)
        self.assertEqual(row["id"], UNCLUSTERED_ID)
        self.assertEqual(row["cluster"], "New, not yet clustered")
        self.assertFalse(any(item["id"].startswith("live-") for item in gaps(conn)))

    def test_live_abstain_drafts_its_own_cluster(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        set_live(conn, True)
        self._mock()
        before = _snapshot(conn)
        found = search(conn, "Pharmacy advocate", NOVEL, record=True)
        self.assertTrue(found["abstained"])
        self.assertEqual(len(self._draft_calls()), 1)
        self.assertIn(NOVEL, self._draft_calls()[0])
        row = _gap_for(conn, NOVEL)
        self.assertEqual(row["id"], _live_id(NOVEL))
        self.assertEqual(row["cluster"], NOVEL)
        self.assertEqual(row["status"], "proposed")
        self.assertEqual(row["search_count"], 1)
        self.assertEqual(row["roles"], "Pharmacy advocate")
        self.assertEqual(row["draft_title"], DRAFT["title"])
        self.assertIn("[clinic hours]", row["draft_text"])
        self.assertIn("[clinic hours]", row["placeholders"])
        self.assertIn("1000001", row["invented_figures"])
        self.assertEqual(row["draft_type"], "faq")
        blocked = send_gap_to_approval(conn, row["id"])
        self.assertIn("Replace every bracketed placeholder", blocked)
        logged = conn.execute(
            "SELECT role, message FROM activity WHERE message LIKE ? ORDER BY id DESC LIMIT 1",
            (f"%{row['id']}%",),
        ).fetchone()
        self.assertEqual(logged["role"], "Pharmacy advocate")
        self.assertIn(NOVEL, logged["message"])
        unclustered = conn.execute("SELECT queries FROM gaps WHERE id = ?", (UNCLUSTERED_ID,)).fetchone()
        stored = unclustered["queries"] if unclustered else ""
        self.assertNotIn(NOVEL, stored or "")

        _restore(conn, before)
        self.assertIsNone(_gap_for(conn, NOVEL))

        self.calls.clear()
        search(conn, "Pharmacy advocate", NOVEL, record=True)
        self.assertEqual(len(self._draft_calls()), 1)
        again = search(conn, "Pharmacy advocate", NOVEL, record=True)
        self.assertTrue(again["abstained"])
        self.assertEqual(len(self._draft_calls()), 1)
        self.assertEqual(_gap_for(conn, NOVEL)["search_count"], 2)

    def test_recorded_result_drafts_when_live(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        set_live(conn, True)
        self._mock()
        record_search(
            conn,
            "Insurance advocate",
            NOVEL,
            {"abstained": True, "ai_source": "live"},
        )
        row = _gap_for(conn, NOVEL)
        self.assertEqual(row["id"], _live_id(NOVEL))
        self.assertEqual(row["roles"], "Insurance advocate")
        self.assertEqual(len(self._draft_calls()), 1)

    def test_unrecorded_search_does_not_draft(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        set_live(conn, True)
        self._mock()
        found = search(conn, "Pharmacy advocate", NOVEL, record=False)
        self.assertTrue(found["abstained"])
        self.assertEqual(self._draft_calls(), [])
        self.assertTrue(any(task == "assess_sufficiency" for task, _user in self.calls))
        self.assertIsNone(_gap_for(conn, NOVEL))

    def test_existing_cluster_is_counted_and_not_redrafted(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        set_live(conn, True)
        self._mock()
        before = _gap_for(conn, ABSTAIN_QUERY)
        self.assertIsNotNone(before)
        self.assertFalse(before["id"].startswith("live-"))
        search(conn, "Pharmacy advocate", ABSTAIN_QUERY, record=True)
        after = _gap_for(conn, ABSTAIN_QUERY)
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(after["search_count"], before["search_count"] + 1)
        self.assertEqual(self._draft_calls(), [])

    def test_no_api_key_keeps_the_unclustered_bucket(self):
        conn = self._database()
        set_live(conn, True)
        self._mock()
        search(conn, "Pharmacy advocate", NOVEL, record=True)
        self.assertEqual(self.calls, [])
        row = _gap_for(conn, NOVEL)
        self.assertEqual(row["id"], UNCLUSTERED_ID)

    def test_database_cap_keeps_the_unclustered_bucket(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        set_live(conn, True)
        conn.execute(
            "INSERT INTO meta(key, value) VALUES('live_call_count', '20') "
            "ON CONFLICT(key) DO UPDATE SET value = '20'"
        )
        conn.commit()
        self._mock()
        found = search(conn, "Pharmacy advocate", NOVEL, record=True)
        self.assertEqual(found["ai_source"], "capped")
        self.assertEqual(self.calls, [])
        self.assertEqual(_gap_for(conn, NOVEL)["id"], UNCLUSTERED_ID)
        self.assertFalse(any(item["id"].startswith("live-") for item in gaps(conn)))

    def test_daily_cap_keeps_the_unclustered_bucket(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        set_live(conn, True)
        today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        self.cap_path.write_text('{"date": "%s", "count": 300, "cap": 300}' % today)
        self._mock()
        found = search(conn, "Pharmacy advocate", NOVEL, record=True)
        self.assertEqual(found["ai_source"], "capped")
        self.assertEqual(self.calls, [])
        self.assertEqual(_gap_for(conn, NOVEL)["id"], UNCLUSTERED_ID)

    def test_failed_draft_keeps_the_unclustered_bucket(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        set_live(conn, True)
        self._mock(
            draft={
                "title": "Empty",
                "type": "faq",
                "draft_text": "  ",
                "placeholders": [],
                "author_checklist": [],
                "suggested_kb": "pharmacy",
            }
        )
        search(conn, "Pharmacy advocate", NOVEL, record=True)
        self.assertEqual(len(self._draft_calls()), 1)
        self.assertEqual(_gap_for(conn, NOVEL)["id"], UNCLUSTERED_ID)

    def test_draft_prompt_and_gap_row_drop_the_email(self):
        conn = self._database()
        os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"
        set_live(conn, True)
        self._mock()
        search(conn, "Pharmacy advocate", EMAIL_Q, record=True)
        self.assertTrue(self.calls)
        for _task, user in self.calls:
            self.assertNotIn("pat@example.com", user)
            self.assertIn("[redacted]", user)
        row = _gap_for(conn, EMAIL_Q)
        self.assertEqual(row["id"], _live_id(EMAIL_Q))
        self.assertNotIn("pat@example.com", row["cluster"])
        self.assertNotIn("pat@example.com", row["queries"])
        self.assertIn("[redacted]", row["cluster"])


if __name__ == "__main__":
    unittest.main()
