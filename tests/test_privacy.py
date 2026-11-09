"""Redaction before a model prompt, and the identifier patterns from HIPAA finding H2."""

import csv
import os
import tempfile
import unittest
from pathlib import Path

os.environ.pop("ANTHROPIC_API_KEY", None)

import src.corpus as corpus
from src.ai import DEMO_QUERIES, gap_user, label_user, sufficiency_user
from src.corpus import decide, load_corpus
from src.engine import DATA, build_database, connect, member_answer, redact_query, search

ROOT = Path(__file__).resolve().parents[1]


class RedactionPatternTests(unittest.TestCase):
    def test_h2_examples_are_removed(self):
        samples = [
            ("MBI 1EG4-TE5-MK73 needs a refill", "1EG4-TE5-MK73"),
            ("MBI 1EG4TE5MK73 needs a refill", "1EG4TE5MK73"),
            ("mbi 1eg4-te5-mk73 needs a refill", "1eg4-te5-mk73"),
            ("write mary.johnson@example.com about the copay", "mary.johnson@example.com"),
            ("the pharmacy is in 02139", "02139"),
            ("the pharmacy is in 02139-1234", "02139-1234"),
            ("ship to 123 Main St today", "123 Main St"),
            ("ship to 45 Oak Ave today", "45 Oak Ave"),
            ("ship to 9 Pine Rd today", "9 Pine Rd"),
            ("ship to 10 Harbor Blvd today", "10 Harbor Blvd"),
            ("ship to 8 Clinic Dr today", "8 Clinic Dr"),
            ("ship to 22 Cedar Ln today", "22 Cedar Ln"),
            ("claim 1234567890 is still open", "1234567890"),
            ("reference 1234-5678-9012 is still open", "1234-5678-9012"),
        ]
        for query, secret in samples:
            redacted = redact_query(query)
            self.assertNotIn(secret, redacted, redacted)
            self.assertIn("[redacted]", redacted, redacted)

    def test_existing_identifier_patterns_still_match(self):
        samples = [
            ("member id H12345678 what is the shoe size", "H12345678"),
            ("dob 01/02/1950 what is the shoe size", "01/02/1950"),
            ("phone 415-555-0199 what is the shoe size", "415-555-0199"),
            ("number 123456789 what is the shoe size", "123456789"),
            ("ssn 123-45-6789 what is the shoe size", "123-45-6789"),
        ]
        for query, secret in samples:
            self.assertNotIn(secret, redact_query(query))

    def test_ordinary_questions_and_dollar_amounts_stay(self):
        unchanged = [
            "mail order refill timing",
            "copay for tier 2 drugs",
            "prior auth for Ozempic",
            "she has diabetes and takes insulin",
            "Harbor Medicare Advantage HMO copay",
            "the copay is $505 for Ozempic",
            "metformin costs $1,234.56 on this plan",
        ]
        for query in unchanged:
            self.assertEqual(redact_query(query), query, query)

    def test_a_person_name_is_removed_with_the_email(self):
        redacted = redact_query("Mary Johnson at mary.johnson@example.com asked about insulin")
        self.assertNotIn("Mary Johnson", redacted)
        self.assertIn("insulin", redacted)
        self.assertNotIn("mary.johnson@example.com", redacted)
        self.assertIn("[redacted]", redacted)


class PromptRedactionTests(unittest.TestCase):
    def test_sufficiency_gap_and_label_prompts_drop_the_identifier(self):
        question = "what is the copay for member 1EG4-TE5-MK73"
        prompt = sufficiency_user(question, "Pharmacy advocate", [])
        self.assertNotIn("1EG4-TE5-MK73", prompt)
        self.assertIn("[redacted]", prompt)
        self.assertIn("copay", prompt)
        gap = gap_user(
            "Copay",
            [{"query": question, "role": "Pharmacy advocate"}],
            [],
        )
        self.assertNotIn("1EG4-TE5-MK73", gap)
        labeled = label_user([{"id": "c9", "queries": [{"query": question, "role": "Member"}]}])
        self.assertNotIn("1EG4-TE5-MK73", labeled)

    def test_ranking_keeps_the_raw_question(self):
        seen = {}
        original = corpus.top_candidates

        def spy(query, role, pool, limit=3):
            seen["query"] = query
            return original(query, role, pool, limit=limit)

        corpus.top_candidates = spy
        try:
            question = "prior auth for Ozempic member 1EG4-TE5-MK73"
            decide(question, "Pharmacy advocate", load_corpus()["pool"], live=False)
        finally:
            corpus.top_candidates = original
        self.assertEqual(seen["query"], question)
        self.assertIn("1EG4-TE5-MK73", seen["query"])

    def test_search_logs_the_redacted_question_and_keeps_the_raw_one(self):
        folder = tempfile.mkdtemp()
        path = str(Path(folder) / "privacy.sqlite")
        build_database(path, mode="jump")
        conn = connect(path)
        question = "copay for Ozempic at 123 Main St 02139"
        found = search(conn, "Pharmacy advocate", question, record=True)
        self.assertEqual(found["query"], question)
        self.assertNotIn("123 Main St", found["logged_query"])
        self.assertNotIn("02139", found["logged_query"])
        self.assertIn("Ozempic", found["logged_query"])
        logged = " ".join(row["message"] for row in conn.execute("SELECT message FROM activity").fetchall())
        self.assertNotIn("123 Main St", logged)
        self.assertNotIn("02139", logged)

    def test_saved_answers_still_replay(self):
        """Demo questions have no identifiers, so redaction does not change their fixture hash."""
        misses = [item for item in load_corpus()["misses"] if "fixture missing" in item.lower()]
        self.assertEqual(misses, [])
        for filename in ("golden_set.csv", "search_log.csv", "question_bank.csv"):
            with (DATA / filename).open() as handle:
                for row in csv.DictReader(handle):
                    question = row.get("question") or row.get("query")
                    self.assertEqual(redact_query(question), question, question)
        for question, _role in DEMO_QUERIES:
            self.assertEqual(redact_query(question), question, question)
        folder = tempfile.mkdtemp()
        path = str(Path(folder) / "replay.sqlite")
        build_database(path, mode="jump")
        conn = connect(path)
        replayed = list(DEMO_QUERIES)
        with (DATA / "golden_set.csv").open() as handle:
            replayed.extend((row["question"], row["role"]) for row in csv.DictReader(handle))
        with (DATA / "question_bank.csv").open() as handle:
            replayed.extend(
                (row["question"], row["role"]) for row in csv.DictReader(handle) if row["role"] == "Member"
            )
        checked = set()
        for question, role in replayed:
            key = (question, role)
            if key in checked:
                continue
            checked.add(key)
            if role == "Member":
                found = member_answer(conn, question, record=False)
            else:
                found = search(conn, role, question, record=False)
            self.assertNotEqual(found["ai_source"], "missing", f"{role}: {question}")
        member_prompt = sufficiency_user("How much will my prescription cost?", "Member", [])
        self.assertIn("How much will my prescription cost?", member_prompt)


if __name__ == "__main__":
    unittest.main()
