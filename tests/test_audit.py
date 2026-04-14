"""Tests for `brain audit` against fixture projects."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Ensure cli/ is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.audit import audit  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


class TestAuditClean(unittest.TestCase):
    def test_clean_fixture_scores_100(self):
        r = audit(FIXTURES / "clean")
        self.assertIsNotNone(r)
        self.assertEqual(r.score, 100)
        self.assertEqual(r.summary, "clean")
        self.assertEqual(r.layout, "project")
        self.assertEqual(r.brain_version, 1)
        self.assertTrue(r.has_marker)
        self.assertEqual(r.orphans, [])
        self.assertEqual(r.dead_links, [])
        self.assertEqual(r.naming_violations, [])
        self.assertEqual(r.missing_sections, [])
        self.assertEqual(r.missing_files, [])


class TestAuditBroken(unittest.TestCase):
    def setUp(self):
        self.r = audit(FIXTURES / "broken")
        self.assertIsNotNone(self.r)

    def test_score_below_50(self):
        self.assertLess(self.r.score, 50)

    def test_no_marker(self):
        self.assertFalse(self.r.has_marker)

    def test_finds_orphan(self):
        self.assertEqual(len(self.r.orphans), 1)
        self.assertIn("bad_name.md", self.r.orphans[0].path)

    def test_finds_dead_link(self):
        self.assertEqual(len(self.r.dead_links), 1)
        self.assertEqual(self.r.dead_links[0].path, "docs/MISSING-FILE.md")

    def test_finds_naming_violation(self):
        self.assertEqual(len(self.r.naming_violations), 1)
        self.assertIn("bad_name.md", self.r.naming_violations[0].path)

    def test_missing_sections(self):
        self.assertIn("Writing Rules", self.r.missing_sections)
        self.assertIn("Sensitive Files", self.r.missing_sections)

    def test_missing_readme(self):
        self.assertIn("README.md", self.r.missing_files)


class TestAuditNoBrain(unittest.TestCase):
    def test_returns_none_for_non_project_folder(self):
        # Use the cli/ folder itself - no CLAUDE.md there
        self.assertIsNone(audit(ROOT / "cli"))


if __name__ == "__main__":
    unittest.main()
