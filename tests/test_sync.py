"""Tests for `brain sync plan` state-aware routing and helpers."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.sync import new_session_id, sync_plan  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def _stage_pending(proj: Path, session_id: str, body: str) -> None:
    """Helper: drop a pending file in a fixture copy."""
    pending = proj / "docs" / ".pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / f"{session_id}.md").write_text(body, encoding="utf-8")


def _clone_clean(tmp: Path) -> Path:
    proj = tmp / "proj"
    shutil.copytree(FIXTURES / "clean", proj)
    return proj


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
    def test_quick_when_only_this_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = _clone_clean(Path(tmp))
            _stage_pending(
                proj, "2026-04-15-0900-xyzz",
                "# Pending updates - 2026-04-15-0900-xyzz\n\n"
                "## rule\n"
                "**target:** docs/WRITING-RULES.md\n"
                "**confidence:** high\n\n"
                "Short sentences only.\n",
            )
            p = sync_plan(proj, session_id="2026-04-15-0900-xyzz")
            self.assertEqual(p.mode, "quick")
            self.assertEqual(p.pending_this_session, 1)
            self.assertEqual(p.pending_other_sessions, 0)


class TestSyncMergeFirst(unittest.TestCase):
    def test_merge_first_when_foreign_session_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = _clone_clean(Path(tmp))
            _stage_pending(
                proj, "2026-04-10-0800-aaaa",
                "# Pending updates - 2026-04-10-0800-aaaa\n\n"
                "## fact\n"
                "**target:** docs/reference/FACTS.md\n"
                "**confidence:** high\n\n"
                "Pi is 3.14159\n",
            )
            plan = sync_plan(proj, session_id="2026-04-15-0900-newbie")
            self.assertEqual(plan.mode, "merge_first")
            self.assertIn("2026-04-10-0800-aaaa", plan.other_session_ids)


class TestSyncEmptySessionId(unittest.TestCase):
    """Regression: running `brain sync plan` without --session-id should not
    flip everything to merge_first just because no session is claimed."""

    def test_empty_session_single_pending_session_is_quick(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = _clone_clean(Path(tmp))
            _stage_pending(
                proj, "2026-04-10-0800-aaaa",
                "# Pending updates - 2026-04-10-0800-aaaa\n\n"
                "## fact\n"
                "**target:** docs/reference/FACTS.md\n"
                "**confidence:** high\n\n"
                "Pi is 3.14159\n",
            )
            plan = sync_plan(proj, session_id="")
            self.assertEqual(plan.mode, "quick")

    def test_empty_session_multiple_pending_sessions_is_merge_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = _clone_clean(Path(tmp))
            _stage_pending(
                proj, "2026-04-10-0800-aaaa",
                "# Pending updates - 2026-04-10-0800-aaaa\n\n"
                "## fact\n"
                "**target:** docs/reference/A.md\n"
                "**confidence:** high\n\n"
                "A\n",
            )
            _stage_pending(
                proj, "2026-04-11-0900-bbbb",
                "# Pending updates - 2026-04-11-0900-bbbb\n\n"
                "## fact\n"
                "**target:** docs/reference/B.md\n"
                "**confidence:** high\n\n"
                "B\n",
            )
            plan = sync_plan(proj, session_id="")
            self.assertEqual(plan.mode, "merge_first")
            self.assertEqual(len(plan.other_session_ids), 2)


class TestNewSessionId(unittest.TestCase):
    def test_format(self):
        sid = new_session_id()
        # YYYY-MM-DD-HHMM-xxxx
        parts = sid.split("-")
        self.assertEqual(len(parts), 5)
        self.assertEqual(len(parts[0]), 4)   # year
        self.assertEqual(len(parts[1]), 2)   # month
        self.assertEqual(len(parts[2]), 2)   # day
        self.assertEqual(len(parts[3]), 4)   # HHMM
        self.assertEqual(len(parts[4]), 4)   # suffix
        self.assertTrue(parts[4].isalnum())

    def test_uniqueness_across_quick_calls(self):
        ids = {new_session_id() for _ in range(20)}
        # With 36^4 suffix space, 20 samples should never collide.
        self.assertEqual(len(ids), 20)


if __name__ == "__main__":
    unittest.main()
