"""Tests for `brain sync plan`, `preflight`, and related helpers."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))
sys.path.insert(0, str(ROOT))  # tests._helpers

from brain.git import inspect as inspect_git  # noqa: E402
from brain.sync import preflight, sync_plan  # noqa: E402
from brain.session import new_session_id  # noqa: E402

from tests._helpers import clone_clean, stage_pending, minimal_item  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


class TestSyncClean(unittest.TestCase):
    def test_empty_fixture_returns_empty_mode(self):
        p = sync_plan(FIXTURES / "clean", session_id="any")
        self.assertIsNotNone(p)
        self.assertEqual(p.mode, "empty")
        self.assertEqual(p.pending_total, 0)
        self.assertEqual(p.stale_pending_count, 0)


class TestSyncConflict(unittest.TestCase):
    def test_conflicts_force_resolve_mode(self):
        p = sync_plan(FIXTURES / "pending", session_id="2026-04-14-1430-a3b9")
        self.assertEqual(p.mode, "resolve_conflicts")
        self.assertEqual(len(p.conflicts), 1)


class TestSyncQuick(unittest.TestCase):
    def test_quick_when_only_this_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))
            stage_pending(proj, "2026-04-15-0900-xyzz", minimal_item())
            p = sync_plan(proj, session_id="2026-04-15-0900-xyzz")
            self.assertEqual(p.mode, "quick")


class TestSyncMergeFirst(unittest.TestCase):
    def test_merge_first_when_foreign_session_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))
            stage_pending(proj, "2026-04-10-0800-aaaa", minimal_item(type_="fact", target="docs/reference/FACTS.md"))
            plan = sync_plan(proj, session_id="2026-04-15-0900-newbie")
            self.assertEqual(plan.mode, "merge_first")
            self.assertIn("2026-04-10-0800-aaaa", plan.other_session_ids)


class TestSyncEmptySessionId(unittest.TestCase):
    def test_empty_session_single_pending_session_is_quick(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))
            stage_pending(proj, "2026-04-10-0800-aaaa", minimal_item(type_="fact"))
            self.assertEqual(sync_plan(proj, session_id="").mode, "quick")

    def test_empty_session_multiple_pending_sessions_is_merge_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))
            stage_pending(proj, "2026-04-10-0800-aaaa", minimal_item(type_="fact", target="docs/reference/A.md"))
            stage_pending(proj, "2026-04-11-0900-bbbb", minimal_item(type_="fact", target="docs/reference/B.md"))
            plan = sync_plan(proj, session_id="")
            self.assertEqual(plan.mode, "merge_first")


class TestNewSessionId(unittest.TestCase):
    def test_format(self):
        sid = new_session_id()
        parts = sid.split("-")
        self.assertEqual(len(parts), 5)
        self.assertEqual(len(parts[4]), 4)
        self.assertTrue(parts[4].isalnum())

    def test_uniqueness(self):
        self.assertEqual(len({new_session_id() for _ in range(20)}), 20)


class TestInspectGit(unittest.TestCase):
    def test_no_git_is_uninitialised(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))  # not a git repo
            g = inspect_git(proj)
            self.assertFalse(g.initialised)
            self.assertTrue(g.clean)
            self.assertIsNone(g.operation_in_progress)


class TestPreflightBasics(unittest.TestCase):
    def test_preflight_on_clean_fixture_returns_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))
            pf = preflight(proj)
            self.assertIsNotNone(pf)
            self.assertTrue(pf.ok)
            self.assertIsNotNone(pf.plan)
            self.assertEqual(pf.plan.mode, "empty")
            self.assertTrue(pf.session_id)
            self.assertFalse(pf.dry_run)

    def test_preflight_dry_run_echoes_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))
            pf = preflight(proj, dry_run=True)
            self.assertTrue(pf.dry_run)

    def test_preflight_blockers_are_structured(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))
            # Make it a git repo with an untracked file
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(proj), check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(proj), check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=str(proj), check=True)
            (proj / "stray.txt").write_text("x", encoding="utf-8")
            pf = preflight(proj)
            self.assertFalse(pf.ok)
            # Each blocker is dict with code/message/remedy
            self.assertTrue(pf.blockers)
            for b in pf.blockers:
                self.assertIn("code", b)
                self.assertIn("message", b)
                self.assertIn("remedy", b)
            # Untracked file is a blocker by default
            codes = {b["code"] for b in pf.blockers}
            self.assertIn("untracked_files", codes)

    def test_include_wip_covers_untracked(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            proj = clone_clean(Path(tmp))
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(proj), check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(proj), check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=str(proj), check=True)
            (proj / "stray.txt").write_text("x", encoding="utf-8")
            pf = preflight(proj, include_wip=True)
            # include-wip must drop the untracked blocker (not just dirty)
            codes = {b["code"] for b in pf.blockers}
            self.assertNotIn("untracked_files", codes)
            self.assertNotIn("dirty_working_tree", codes)
            self.assertTrue(pf.ok)

    def test_preflight_on_missing_project_returns_none(self):
        self.assertIsNone(preflight(ROOT / "cli"))  # no CLAUDE.md there


if __name__ == "__main__":
    unittest.main()
