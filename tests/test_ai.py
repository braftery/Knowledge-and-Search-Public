"""Checks for fixture replay and the verbatim guard. No model call."""

import tempfile
import unittest
from pathlib import Path

from src.ai import (
    assign_ids,
    candidate_pairs,
    check_unit,
    find_fixture,
    invented_figures,
    jaccard,
    kb_for,
    load_human_decisions,
    prepared_drift_edits,
    pricing_sentence,
    search_pool,
    sha256_text,
    write_fixture,
)


class AiFixtureTests(unittest.TestCase):
    def test_verbatim_guard_does_not_rewrite(self):
        document = "Verbatim (Legal): Say this exactly."
        flags = check_unit(document, {"type": "verbatim", "text": "Say this exactly.", "source_span": "Say this exactly."})
        self.assertFalse(flags["source_mismatch"])
        self.assertFalse(flags["verbatim_altered"])
        altered = check_unit(document, {"type": "verbatim", "text": "Say this loosely.", "source_span": "Say this exactly."})
        self.assertFalse(altered["source_mismatch"])
        self.assertTrue(altered["verbatim_altered"])
        missing = check_unit(document, {"type": "policy", "text": "Missing.", "source_span": "Not in the document."})
        self.assertTrue(missing["source_mismatch"])

    def test_ids_and_scope_come_from_the_decisions_file(self):
        document = "Verbatim (Legal): Thank you for calling Harbor Health."
        units = assign_ids(
            "SRC-RX-EDU-001",
            document,
            "pharmacy",
            0,
            [
                {
                    "title": "Closing",
                    "type": "verbatim",
                    "text": "Thank you for calling Harbor Health.",
                    "source_span": "Thank you for calling Harbor Health.",
                    "tags": ["closing"],
                    "domain": "shared",
                    "audience": "advocate",
                }
            ],
        )
        self.assertEqual(units[0]["unit_id"], "U-RX-EDU-001-01")
        self.assertEqual(units[0]["kb_scope"], ["pharmacy"])
        self.assertEqual(kb_for("U-RX-EDU-001-15", "pharmacy"), ["shared-legal"])
        self.assertEqual(kb_for("U-RX-EDU-002-12", "pharmacy"), ["shared-legal"])
        self.assertEqual(kb_for("U-RX-EDU-001-09", "pharmacy"), ["pharmacy"])
        self.assertFalse(units[0]["verbatim_altered"])
        decisions = load_human_decisions()
        from src.corpus import load_corpus

        extracted = {unit["unit_id"] for unit in load_corpus()["units"]}
        self.assertEqual(set(decisions["knowledge_bases"]), extracted)

    def test_conflict_blocks_both_and_exact_keeps_earlier(self):
        left = _unit("U-A", 0, 1)
        right = _unit("U-B", 1, 1)
        third = _unit("U-C", 2, 1, verbatim_altered=True)
        pool = search_pool(
            [left, right, third],
            [
                {"a_id": "U-A", "b_id": "U-B", "output": {"relation": "conflict"}},
            ],
        )
        self.assertEqual(pool, [])
        kept = search_pool(
            [left, right],
            [{"a_id": "U-A", "b_id": "U-B", "output": {"relation": "exact"}}],
        )
        self.assertEqual([unit["unit_id"] for unit in kept], ["U-A"])

    def test_fixture_index_sees_a_write_after_a_miss(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            user = "Document ID: SRC-INDEX\n\nHello"
            self.assertIsNone(find_fixture("extract_units", user, directory))
            write_fixture("extract_units", user, {"units": [{"title": "Hello"}]}, "data/test.md", directory)
            found = find_fixture("extract_units", user, directory)
            self.assertEqual(found["output"], {"units": [{"title": "Hello"}]})
            self.assertIsNone(find_fixture("extract_units", user + " changed", directory))

    def test_fixture_roundtrip_keeps_output(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            user = "Document ID: SRC-TEST\n\nHello"
            original = {"units": [{"title": "Hello", "text": "Hello"}]}
            write_fixture("extract_units", user, original, "data/test.md", directory)
            found = find_fixture("extract_units", user, directory)
            self.assertEqual(found["output"], original)
            self.assertEqual(found["input_sha256"], sha256_text(user))
            self.assertIsNone(find_fixture("extract_units", user + " changed", directory))

    def test_drift_edits_are_distinct(self):
        sentence = pricing_sentence(
            "Verbatim (Legal): The price I quote is an estimate for a 30-day supply at a preferred pharmacy."
        )
        edits = prepared_drift_edits(sentence, sentence)
        self.assertIn("31-day", edits[0]["new_span"])
        self.assertIn("supply, at", edits[1]["new_span"])
        self.assertNotEqual(edits[0]["new_span"], edits[1]["new_span"])

    def test_jaccard_threshold(self):
        self.assertGreater(jaccard("30 day supply preferred pharmacy", "30 day supply preferred pharmacy estimate"), 0.3)
        self.assertLess(jaccard("mail order specialty", "dental allowance maximum"), 0.3)

    def test_candidate_pairs_ignore_domain(self):
        shared = "offer a 90 day mail order supply after two retail fills this calendar year"
        left = _pair_unit("U-A", 0, 1, "policy", "Pharmacy education, Medicare Advantage", shared, "SRC-RX-EDU-001")
        right = _pair_unit("U-B", 1, 1, "policy", "pharmacy education", shared, "SRC-RX-EDU-002")
        pairs = [(item[0]["unit_id"], item[1]["unit_id"]) for item in candidate_pairs([left, right])]
        self.assertEqual(pairs, [("U-A", "U-B")])
        shifted = _pair_unit("U-B", 1, 1, "policy", "a completely different domain", shared, "SRC-RX-EDU-002")
        shifted_pairs = [(item[0]["unit_id"], item[1]["unit_id"]) for item in candidate_pairs([right, left])]
        self.assertEqual(
            [(item[0]["unit_id"], item[1]["unit_id"]) for item in candidate_pairs([left, shifted])],
            shifted_pairs,
        )
        self.assertEqual(candidate_pairs([shifted, left])[0][0]["unit_id"], "U-A")
        far = _pair_unit("U-C", 1, 1, "policy", left["domain"], "dental allowance maximum out of pocket", "SRC-RX-EDU-002")
        self.assertEqual(candidate_pairs([left, far]), [])
        same_doc = _pair_unit("U-D", 0, 2, "policy", left["domain"], shared, "SRC-RX-EDU-001")
        self.assertEqual(candidate_pairs([left, same_doc]), [])
        faq = _pair_unit("U-F", 1, 2, "faq", "other domain", shared, "SRC-RX-EDU-002")
        self.assertEqual(
            [(item[0]["unit_id"], item[1]["unit_id"]) for item in candidate_pairs([left, faq])],
            [("U-A", "U-F")],
        )
        verbatim = _pair_unit("U-V", 1, 3, "verbatim", left["domain"], shared, "SRC-RX-EDU-002")
        self.assertEqual(candidate_pairs([left, verbatim]), [])

    def test_website_pricing_pair_ignores_jaccard(self):
        pricing = _pair_unit(
            "U-P",
            0,
            1,
            "verbatim",
            "pharmacy",
            "An estimate for a 30-day supply at a preferred retail pharmacy.",
            "SRC-RX-EDU-001",
        )
        website = _pair_unit("U-W", 2, 1, "faq", "unrelated", "Office hours are weekdays.", "SRC-WEB-FAQ")
        self.assertLess(jaccard(pricing["text"], website["text"]), 0.3)
        pairs = candidate_pairs([website, pricing])
        self.assertEqual([(item[0]["unit_id"], item[1]["unit_id"]) for item in pairs], [("U-P", "U-W")])

    def test_conflict_status_blocks_both(self):
        from src.engine import _create_schema, apply_conflict_blocks, connect

        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "blocks.sqlite")
            conn = connect(path)
            _create_schema(conn)
            for unit_id in ("U-A", "U-B"):
                conn.execute(
                    """
                    INSERT INTO units (
                        unit_id, version, title, type, text, tags, tags_confirmed, domain,
                        kb_scope, audience, channels, status, search_visible, source_doc,
                        source_quote, approved_by, approved_on, stale, proposed_text,
                        requires_legal, conflicts_with, notes, source_mismatch, verbatim_altered
                    ) VALUES (?, 1, ?, 'policy', 'text', '', 0, 'd', 'pharmacy', 'advocate', '',
                              'proposed', 1, 'SRC', '', '', '', 0, '', 1, '', '', 0, 0)
                    """,
                    (unit_id, unit_id),
                )
            apply_conflict_blocks(
                conn,
                [{"a_id": "U-A", "b_id": "U-B", "output": {"relation": "conflict"}}],
            )
            rows = conn.execute(
                "SELECT status, search_visible FROM units ORDER BY unit_id"
            ).fetchall()
            self.assertEqual([(row["status"], row["search_visible"]) for row in rows], [("blocked_conflict", 0), ("blocked_conflict", 0)])
            visible = conn.execute(
                "SELECT unit_id FROM units WHERE status = 'approved' AND search_visible = 1"
            ).fetchall()
            self.assertEqual(list(visible), [])

    def test_invented_figure_flag(self):
        flagged = invented_figures(
            "The copay is $505 after 30 days.",
            ["how long is prior auth"],
            ["No numbers here"],
        )
        self.assertEqual(flagged, ["$505", "30"])
        cleared = invented_figures(
            "The copay is $505 after 30 days.",
            ["the $505 copay"],
            ["a 30-day supply"],
        )
        self.assertEqual(cleared, [])
        quoted = invented_figures(
            'Read "a 30-day supply" and see U-RX-EDU-001-09.',
            ["which disclaimer do I read"],
            ["The price I quote is an estimate for a 30-day supply at a preferred retail pharmacy."],
        )
        self.assertEqual(quoted, [])
        self.assertEqual(
            invented_figures("1. Open the record.\n2. Read the line.", ["where is the wording"], ["a 30-day supply"]),
            [],
        )
        self.assertEqual(invented_figures("Wait 3 days.", ["when"], ["a 30-day supply"]), ["3"])

    def test_fixture_provenance_is_optional(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            user = "Document ID: SRC-PROV\n\nHello"
            write_fixture(
                "extract_units",
                user,
                {"units": []},
                "data/prov.md",
                directory,
                provenance={
                    "response_id": "msg_test",
                    "stop_reason": "end_turn",
                    "input_tokens": 10,
                    "output_tokens": 4,
                    "prompt_sha256": "abc",
                },
            )
            found = find_fixture("extract_units", user, directory)
            self.assertEqual(found["response_id"], "msg_test")
            self.assertEqual(found["stop_reason"], "end_turn")
            self.assertEqual(found["usage"]["input_tokens"], 10)
            self.assertEqual(found["usage"]["output_tokens"], 4)
            self.assertEqual(found["prompt_sha256"], "abc")


def _pair_unit(unit_id, doc_index, index, unit_type, domain, text, source_doc):
    return {
        "unit_id": unit_id,
        "doc_index": doc_index,
        "index": index,
        "type": unit_type,
        "domain": domain,
        "text": text,
        "source_doc": source_doc,
        "source_mismatch": False,
        "verbatim_altered": False,
    }


def _unit(unit_id, doc_index, index, verbatim_altered=False):
    return {
        "unit_id": unit_id,
        "doc_index": doc_index,
        "index": index,
        "source_mismatch": False,
        "verbatim_altered": verbatim_altered,
        "kb_scope": ["pharmacy"],
        "audience_list": ["advocate"],
        "title": unit_id,
        "text": unit_id,
        "type": "policy",
        "domain": "pharmacy",
        "tags": [],
    }


if __name__ == "__main__":
    unittest.main()
