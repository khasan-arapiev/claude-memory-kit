"""Tests for `brain pending list` parser and conflict detection."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.pending import detect_conflicts, list_pending  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "pending"


class TestPendingList(unittest.TestCase):
    def setUp(self):
        self.items = list_pending(FIXTURES)
        self.assertIsNotNone(self.items)

    def test_finds_all_items(self):
        # 3 valid + 1 invalid + 2 conflicting decisions = 6 items across 3 files
        self.assertEqual(len(self.items), 6)

    def test_types_parsed(self):
        types = [it.type for it in self.items]
        self.assertEqual(types.count("rule"), 1)
        self.assertEqual(types.count("fact"), 1)
        self.assertEqual(types.count("decision"), 3)  # 1 from session1 + 2 conflicting
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


class TestConflictDetection(unittest.TestCase):
    def setUp(self):
        self.items = list_pending(FIXTURES)
        self.conflicts = detect_conflicts(self.items)

    def test_conflict_detected_for_two_decisions_same_target(self):
        self.assertEqual(len(self.conflicts), 1)
        c = self.conflicts[0]
        self.assertEqual(c.target, "docs/decisions/2026-04-14-LANGUAGE-CHOICE.md")
        self.assertEqual(c.type, "decision")
        self.assertEqual(len(c.item_ids), 2)
        self.assertIn("decision", c.reason)

    def test_no_conflict_when_only_one_decision_per_target(self):
        # The original decision (USE-MARKDOWN-PENDING) only has one item, no conflict
        decision_targets = [c.target for c in self.conflicts]
        self.assertNotIn("docs/decisions/2026-04-14-USE-MARKDOWN-PENDING.md", decision_targets)

    def test_invalid_items_excluded_from_conflict_detection(self):
        # The "bogus" item has no target and validation issues, must not appear in any conflict
        all_ids_in_conflicts = {iid for c in self.conflicts for iid in c.item_ids}
        for it in self.items:
            if it.type == "bogus":
                self.assertNotIn(it.id, all_ids_in_conflicts)

    def test_identical_decision_bodies_not_flagged(self):
        # If two decision items had the same body, that's a duplicate not a conflict.
        # We don't have such a fixture pair, so this just confirms detect_conflicts
        # never returns conflicts with all-identical bodies. Verify by inspection:
        for c in self.conflicts:
            ids_in_conflict = set(c.item_ids)
            bodies = {it.content.strip() for it in self.items if it.id in ids_in_conflict}
            self.assertGreater(len(bodies), 1, "conflict reported but bodies are identical")


if __name__ == "__main__":
    unittest.main()
