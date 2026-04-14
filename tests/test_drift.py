"""Tests for `brain drift` against fixture projects."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.drift import drift  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


class TestDrift(unittest.TestCase):
    def test_clean_fixture_has_no_tracked_docs(self):
        r = drift(FIXTURES / "clean")
        self.assertIsNotNone(r)
        self.assertEqual(r.tracked_docs, 0)
        self.assertEqual(r.drift, [])
        self.assertEqual(r.missing_files, [])

    def test_drifted_fixture_detects_drift(self):
        r = drift(FIXTURES / "drifted")
        self.assertIsNotNone(r)
        self.assertEqual(r.tracked_docs, 1)
        self.assertEqual(len(r.drift), 1)
        item = r.drift[0]
        self.assertIn("CHECKOUT-FLOW.md", item.doc)
        self.assertEqual(item.described_file, "project/checkout.js")
        self.assertGreater(item.days_behind, 0)


if __name__ == "__main__":
    unittest.main()
