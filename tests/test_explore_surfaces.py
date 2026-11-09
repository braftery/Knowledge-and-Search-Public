"""Explore surface questions keep a saved answer in each sandbox state."""

import os
import unittest

os.environ.pop("ANTHROPIC_API_KEY", None)

import src.ai as ai
from src.ai import MISSING_CAPTION
from src.demo_paths import explore_surface_queries, walk_explore_surface_states
from src.engine import member_answer, search, set_live


def _refuse(*_args, **_kwargs):
    raise AssertionError("cached mode called the model")


class ExploreSurfaceCacheTests(unittest.TestCase):
    def test_surface_questions_do_not_miss_the_cache(self):
        ai.call_model = _refuse
        misses = []
        questions = explore_surface_queries()
        self.assertGreaterEqual(len(questions), 10)
        roles = {role for role, _question in questions}
        self.assertIn("Pharmacy advocate", roles)
        self.assertIn("Insurance advocate", roles)
        self.assertIn("Member", roles)
        self.assertIn(
            ("Pharmacy advocate", "whats the rx pricing disclamer i have to read"),
            questions,
        )
        for name, conn in walk_explore_surface_states():
            set_live(conn, False)
            for role, question in questions:
                if role == "Member":
                    found = member_answer(conn, question, record=False)
                else:
                    found = search(conn, role, question, record=False)
                note = found.get("note") or ""
                if note == MISSING_CAPTION or found.get("ai_source") == "missing":
                    misses.append(f"{name} | {role} | {question}")
        self.assertEqual(misses, [])
