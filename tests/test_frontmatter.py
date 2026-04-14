"""Tests for the stdlib frontmatter parser."""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.frontmatter import parse  # noqa: E402


class TestFrontmatter(unittest.TestCase):
    def test_no_frontmatter_returns_empty(self):
        fm = parse("# Just a heading\n\nBody.\n")
        self.assertEqual(fm.data, {})
        self.assertIn("Just a heading", fm.body)

    def test_simple_keys(self):
        fm = parse("---\nstatus: active\ntitle: Hello\n---\nbody")
        self.assertEqual(fm.get("status"), "active")
        self.assertEqual(fm.get("title"), "Hello")
        self.assertEqual(fm.body, "body")

    def test_iso_date_coerced(self):
        fm = parse("---\nlast-synced: 2026-04-14\n---\n")
        self.assertEqual(fm.get("last-synced"), date(2026, 4, 14))

    def test_int_coerced(self):
        fm = parse("---\nversion: 2\n---\n")
        self.assertEqual(fm.get("version"), 2)

    def test_bool_coerced(self):
        fm = parse("---\nactive: true\narchived: no\n---\n")
        self.assertTrue(fm.get("active"))
        self.assertFalse(fm.get("archived"))

    def test_quoted_string(self):
        fm = parse('---\nname: "Hello World"\n---\n')
        self.assertEqual(fm.get("name"), "Hello World")

    def test_list_of_strings(self):
        fm = parse("---\ndescribes:\n  - one.js\n  - two.js\n---\n")
        self.assertEqual(fm.list_of("describes"), ["one.js", "two.js"])

    def test_empty_supersedes(self):
        fm = parse("---\nstatus: active\nsupersedes:\n---\n")
        self.assertEqual(fm.get("supersedes"), "")


if __name__ == "__main__":
    unittest.main()
