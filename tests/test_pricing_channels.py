"""The pricing unit is published to advocate guidance and the member channels."""

import tempfile
import unittest
from pathlib import Path

from src.ai import with_audience_override
from src.corpus import load_corpus
from src.engine import build_database, connect, live_approved, publish_revision
from src.portal import unit_payload

PRICING = "U-RX-EDU-001-09"
CLOSING = "U-RX-EDU-001-15"
EXPECTED = ["advocate_guidance", "member_chat", "voice_bot", "website"]


def _channels(row) -> list[str]:
    return [part.strip() for part in (row["channels"] or "").split(",") if part.strip()]


class PricingChannelTests(unittest.TestCase):
    def test_pricing_channels_include_the_member_surfaces(self):
        folder = tempfile.mkdtemp()
        path = str(Path(folder) / "channels.sqlite")
        build_database(path, mode="jump")
        conn = connect(path)
        live = live_approved(conn, PRICING)
        self.assertEqual(_channels(live), EXPECTED)
        self.assertEqual(unit_payload(live)["channels"], EXPECTED)
        closing = live_approved(conn, CLOSING)
        self.assertEqual(_channels(closing), ["advocate_guidance"])

        before = _channels(live)
        publish_revision(conn)
        revised = live_approved(conn, PRICING)
        self.assertEqual(revised["version"], live["version"] + 1)
        self.assertEqual(_channels(revised), before)
        self.assertEqual(unit_payload(revised)["channels"], EXPECTED)

    def test_in_memory_override_matches_the_stored_channels(self):
        units = {unit["unit_id"]: unit for unit in load_corpus()["units"]}
        self.assertEqual(with_audience_override(units[PRICING])["channels"], EXPECTED)
        self.assertEqual(with_audience_override(units[CLOSING])["channels"], ["advocate_guidance"])


if __name__ == "__main__":
    unittest.main()
