"""Smoke tests for the CLI binding layer (cli.main).

These don't re-prove what the unit tests cover; they just confirm that
argparse wiring, exit codes, and the _guard decorator behave as advertised
for each subcommand on a known-good fixture.
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.cli import main  # noqa: E402

CLEAN = str(ROOT / "tests" / "fixtures" / "clean")
BROKEN = str(ROOT / "tests" / "fixtures" / "broken")
PENDING = str(ROOT / "tests" / "fixtures" / "pending")


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestCLIExitCodes(unittest.TestCase):
    def test_audit_clean_exits_zero(self):
        code, _, _ = _run(["audit", CLEAN])
        self.assertEqual(code, 0)

    def test_audit_broken_exits_one(self):
        code, _, _ = _run(["audit", BROKEN])
        self.assertEqual(code, 1)

    def test_audit_missing_project_exits_one(self):
        # cli/ has no CLAUDE.md
        code, _, err = _run(["audit", str(ROOT / "cli")])
        self.assertEqual(code, 1)
        self.assertIn("No CLAUDE.md", err)

    def test_pending_list_with_issues_exits_nonzero(self):
        code, _, _ = _run(["pending", "list", PENDING])
        self.assertIn(code, (1,))  # either conflicts or issues triggers 1

    def test_pending_list_clean_exits_zero(self):
        code, _, _ = _run(["pending", "list", CLEAN])
        self.assertEqual(code, 0)

    def test_sync_plan_empty_exits_zero(self):
        code, _, _ = _run(["sync", "plan", CLEAN, "--session-id", "test"])
        self.assertEqual(code, 0)

    def test_sync_plan_conflict_exits_one(self):
        code, _, _ = _run(["sync", "plan", PENDING, "--session-id", "2026-04-14-1430-a3b9"])
        self.assertEqual(code, 1)

    def test_new_session_id_emits_valid_format(self):
        code, out, _ = _run(["sync", "new-session-id"])
        self.assertEqual(code, 0)
        self.assertRegex(out.strip(), r"^\d{4}-\d{2}-\d{2}-\d{4}-[a-z0-9]{4}$")

    def test_new_session_id_json(self):
        import json as _json
        code, out, _ = _run(["sync", "new-session-id", "--json"])
        self.assertEqual(code, 0)
        self.assertIn("session_id", _json.loads(out))


class TestGuardScope(unittest.TestCase):
    """_guard must not swallow programmer errors (ValueError)."""

    def test_value_error_not_caught(self):
        from brain.cli import _guard

        @_guard
        def raises(*_a, **_k):
            raise ValueError("boom")

        # ValueError bubbles up — _guard only catches OSError.
        with self.assertRaises(ValueError):
            raises()


if __name__ == "__main__":
    unittest.main()
