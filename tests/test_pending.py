"""Tests for `brain pending list` parser."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.pending import list_pending  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "pending"


class TestPendingList(unittest.TestCase):
    def setUp(self):
        self.items = list_pending(FIXTURES)
        self.assertIsNotNone(self.items)

    def test_finds_all_items(self):
        # 3 valid + 1 invalid across 2 files
        self.assertEqual(len(self.items), 4)

    def test_types_parsed(self):
        types = [it.type for it in self.items]
        self.assertEqual(types.count("rule"), 1)
        self.assertEqual(types.count("fact"), 1)
        self.assertEqual(types.count("decision"), 1)
        self.assertEqual(types.count("bogus"), 1)

    def test_targets_parsed(self):
        rule = next(it for it in self.items if it.type == "rule")
        self.assertEqual(rule.target, "docs/WRITING-RULES.md")

    def test_session_id_from_filename(self):
        self.assertTrue(any(it.session_id == "2026-04-14-1430-a3b9" for it in self.items))

    def test_invalid_item_has_three_issues(self):
        bogus = next(it for it in self.items if it.type == "bogus")
        # bad type, missing target, invalid confidence
        self.assertEqual(len(bogus.issues), 3)

    def test_valid_item_has_no_issues(self):
        rule = next(it for it in self.items if it.type == "rule")
        self.assertEqual(rule.issues, [])

    def test_body_extracted(self):
        rule = next(it for it in self.items if it.type == "rule")
        self.assertEqual(rule.content, "Never use em dashes in copy.")


class TestPendingEmpty(unittest.TestCase):
    def test_clean_fixture_has_no_pending(self):
        items = list_pending(ROOT / "tests" / "fixtures" / "clean")
        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
