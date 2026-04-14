"""Tests for `brain query` retrieval ranking."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.query import _chunk_doc, query  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "searchable"


class TestChunking(unittest.TestCase):
    def test_chunks_at_h2(self):
        chunks = _chunk_doc(FIXTURES / "docs" / "HOSTING.md", FIXTURES)
        # Expect: pre-H1 (none) + intro (H1 only) + 3 H2 sections
        # Intro chunk holds the H1, then FTP Access / SSL Certificates / DNS
        headings = [c.heading for c in chunks if c.heading]
        self.assertIn("FTP Access", headings)
        self.assertIn("SSL Certificates", headings)
        self.assertIn("DNS", headings)

    def test_line_starts_are_one_based(self):
        chunks = _chunk_doc(FIXTURES / "docs" / "HOSTING.md", FIXTURES)
        for c in chunks:
            self.assertGreaterEqual(c.line_start, 1)


class TestQueryRanking(unittest.TestCase):
    def test_ftp_query_finds_ftp_section(self):
        hits = query(FIXTURES, "FTP password", top_n=3)
        self.assertIsNotNone(hits)
        self.assertTrue(hits, "expected at least one hit")
        top = hits[0]
        self.assertIn("HOSTING.md", top.doc_path)
        self.assertEqual(top.heading, "FTP Access")

    def test_stripe_query_finds_stripe_section(self):
        hits = query(FIXTURES, "stripe webhook", top_n=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0].heading, "Stripe Integration")
        self.assertIn("PAYMENTS.md", hits[0].doc_path)

    def test_unrelated_query_returns_no_hits(self):
        hits = query(FIXTURES, "kubernetes orchestration", top_n=3)
        self.assertEqual(hits, [])

    def test_top_n_respected(self):
        hits = query(FIXTURES, "the and a", top_n=2)
        # All-stopwords query: tokenizer drops them, expect zero hits
        self.assertEqual(hits, [])

    def test_heading_match_outranks_body_match(self):
        # "DNS" appears only in the DNS heading + one body line
        hits = query(FIXTURES, "DNS records", top_n=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0].heading, "DNS")

    def test_returns_none_for_non_project(self):
        self.assertIsNone(query(ROOT / "cli", "anything"))


if __name__ == "__main__":
    unittest.main()
