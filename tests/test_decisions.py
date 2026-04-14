"""Tests for `brain decisions` against the decisions fixture."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.decisions import list_decisions, search_decisions  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "decisions"


class TestDecisionsList(unittest.TestCase):
    def setUp(self):
        self.decisions = list_decisions(FIXTURES)
        self.assertIsNotNone(self.decisions)
        self.by_id = {d.id: d for d in self.decisions}

    def test_finds_three_decisions(self):
        self.assertEqual(len(self.decisions), 3)

    def test_sorted_newest_first(self):
        dates = [d.date for d in self.decisions]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_supersede_chain(self):
        bootstrap = self.by_id["2026-01-12-USE-BOOTSTRAP"]
        tailwind = self.by_id["2026-03-08-SWITCH-TO-TAILWIND"]
        # Tailwind supersedes Bootstrap
        self.assertEqual(tailwind.supersedes, "2026-01-12-USE-BOOTSTRAP")
        # Bootstrap should be auto-marked as superseded
        self.assertEqual(bootstrap.status, "superseded")
        self.assertEqual(bootstrap.superseded_by, "2026-03-08-SWITCH-TO-TAILWIND")

    def test_legacy_status_normalized(self):
        # Postgres ADR uses legacy "**Status:** Accepted" -> should map to "active"
        postgres = self.by_id["2026-04-01-USE-POSTGRES"]
        self.assertEqual(postgres.status, "active")

    def test_topics_extracted(self):
        tailwind = self.by_id["2026-03-08-SWITCH-TO-TAILWIND"]
        self.assertIn("frontend", tailwind.topics)
        self.assertIn("css", tailwind.topics)


class TestDecisionsSearch(unittest.TestCase):
    def test_search_by_title(self):
        results = search_decisions(FIXTURES, "tailwind")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "2026-03-08-SWITCH-TO-TAILWIND")

    def test_search_by_topic(self):
        results = search_decisions(FIXTURES, "css")
        self.assertEqual(len(results), 2)  # bootstrap + tailwind both tagged css

    def test_search_by_body(self):
        results = search_decisions(FIXTURES, "JSONB")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "2026-04-01-USE-POSTGRES")

    def test_search_no_matches(self):
        results = search_decisions(FIXTURES, "xyznomatch")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
