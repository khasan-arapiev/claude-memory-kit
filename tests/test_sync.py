"""Tests for `brain sync plan` state-aware routing."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.sync import sync_plan  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


class TestSyncClean(unittest.TestCase):
    def test_empty_fixture_returns_empty_mode(self):
        p = sync_plan(FIXTURES / "clean", session_id="any")
        self.assertIsNotNone(p)
        self.assertEqual(p.mode, "empty")
        self.assertEqual(p.pending_total, 0)


class TestSyncConflict(unittest.TestCase):
    def test_conflicts_force_resolve_mode(self):
        p = sync_plan(FIXTURES / "pending", session_id="2026-04-14-1430-a3b9")
        self.assertIsNotNone(p)
        self.assertEqual(p.mode, "resolve_conflicts")
        self.assertEqual(len(p.conflicts), 1)


class TestSyncQuick(unittest.TestCase):
    """When only the current session has staged items and nothing conflicts,
    sync should return `quick` — the old ProjectUpdate safe-fast path."""

    def test_quick_when_only_this_session(self):
        # Copy the clean fixture and stage a single-session pending file in it.
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            shutil.copytree(FIXTURES / "clean", proj)
            pending = proj / "docs" / ".pending"
            pending.mkdir(parents=True, exist_ok=True)
            (pending / "2026-04-15-0900-xyzz.md").write_text(
                "# Pending updates - 2026-04-15-0900-xyzz\n\n"
                "## rule\n"
                "**target:** docs/WRITING-RULES.md\n"
                "**confidence:** high\n\n"
                "Short sentences only.\n",
                encoding="utf-8",
            )
            p = sync_plan(proj, session_id="2026-04-15-0900-xyzz")
            self.assertIsNotNone(p)
            self.assertEqual(p.mode, "quick")
            self.assertEqual(p.pending_this_session, 1)
            self.assertEqual(p.pending_other_sessions, 0)


class TestSyncMergeFirst(unittest.TestCase):
    """Other sessions staged -> merge_first (don't quick-merge)."""

    def test_merge_first_when_foreign_session_present(self):
        # The pending fixture has 3 session files. Pretend we are a 4th, brand-new session.
        p = sync_plan(FIXTURES / "pending", session_id="2026-04-20-9999-zzzz")
        self.assertIsNotNone(p)
        # Conflicts take precedence over merge_first in our ordering, so this
        # fixture surfaces conflicts. Use a copy without the conflict pair:
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            shutil.copytree(FIXTURES / "clean", proj)
            pending = proj / "docs" / ".pending"
            pending.mkdir(parents=True, exist_ok=True)
            (pending / "2026-04-10-0800-aaaa.md").write_text(
                "# Pending updates - 2026-04-10-0800-aaaa\n\n"
                "## fact\n"
                "**target:** docs/reference/FACTS.md\n"
                "**confidence:** high\n\n"
                "Pi is 3.14159\n",
                encoding="utf-8",
            )
            plan = sync_plan(proj, session_id="2026-04-15-0900-newbie")
            self.assertEqual(plan.mode, "merge_first")
            self.assertIn("2026-04-10-0800-aaaa", plan.other_session_ids)


if __name__ == "__main__":
    unittest.main()
