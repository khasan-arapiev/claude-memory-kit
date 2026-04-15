"""Tests for `brain.git.inspect` — detached HEAD, unborn branch, branch named HEAD."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.git import inspect  # noqa: E402


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def _init_repo(path: Path) -> None:
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")


class TestGitInspect(unittest.TestCase):
    def test_no_git_reports_uninitialised(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = inspect(Path(tmp))
            self.assertFalse(g.initialised)
            self.assertFalse(g.detached)
            self.assertFalse(g.unborn)
            self.assertIsNone(g.branch)

    def test_unborn_branch_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            _init_repo(p)
            g = inspect(p)
            self.assertTrue(g.initialised)
            self.assertTrue(g.unborn, "fresh repo with no commits must set unborn=True")
            self.assertFalse(g.detached)
            self.assertEqual(g.branch, "main")

    def test_detached_head_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            _init_repo(p)
            (p / "f.txt").write_text("a", encoding="utf-8")
            _git(p, "add", "f.txt")
            _git(p, "commit", "-q", "-m", "first")
            # Detach to the current commit
            rev = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=str(p),
                capture_output=True, text=True,
            ).stdout.strip()
            _git(p, "checkout", "-q", "--detach", rev)
            g = inspect(p)
            self.assertTrue(g.initialised)
            self.assertTrue(g.detached, "checked-out commit must set detached=True")
            self.assertFalse(g.unborn)
            self.assertIsNone(g.branch, "detached HEAD has no branch name")

    def test_clean_repo_on_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            _init_repo(p)
            (p / "f.txt").write_text("a", encoding="utf-8")
            _git(p, "add", "f.txt")
            _git(p, "commit", "-q", "-m", "first")
            g = inspect(p)
            self.assertTrue(g.clean)
            self.assertFalse(g.detached)
            self.assertFalse(g.unborn)
            self.assertEqual(g.branch, "main")
            self.assertEqual(g.dirty_paths, [])
            self.assertEqual(g.untracked_paths, [])

    def test_untracked_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            _init_repo(p)
            (p / "tracked.txt").write_text("a", encoding="utf-8")
            _git(p, "add", "tracked.txt")
            _git(p, "commit", "-q", "-m", "init")
            (p / "new.txt").write_text("b", encoding="utf-8")
            g = inspect(p)
            self.assertIn("new.txt", g.untracked_paths)
            self.assertFalse(g.clean)


if __name__ == "__main__":
    unittest.main()
