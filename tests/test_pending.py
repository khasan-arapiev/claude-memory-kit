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


class TestPlaceholderValidation(unittest.TestCase):
    """Unknown {{...}} tokens and single-brace typos flag as validation issues."""

    def _parse(self, body: str):
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            shutil.copytree(ROOT / "tests" / "fixtures" / "clean", proj)
            pending = proj / "docs" / ".pending"
            pending.mkdir(parents=True, exist_ok=True)
            (pending / "2026-04-15-0900-xxxx.md").write_text(body, encoding="utf-8")
            return list_pending(proj)

    def test_known_placeholder_is_clean(self):
        items = self._parse(
            "# Pending\n\n"
            "## decision\n"
            "**target:** docs/decisions/{{date}}-FOO.md\n"
            "**confidence:** high\n\n"
            "Body.\n"
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].issues, [])

    def test_unknown_double_brace_token_flags(self):
        items = self._parse(
            "# Pending\n\n"
            "## rule\n"
            "**target:** docs/{{unknown}}-FOO.md\n"
            "**confidence:** high\n\n"
            "Body.\n"
        )
        self.assertEqual(len(items), 1)
        self.assertTrue(any("unknown placeholder" in i for i in items[0].issues))

    def test_single_brace_typo_flags(self):
        items = self._parse(
            "# Pending\n\n"
            "## rule\n"
            "**target:** docs/{date}-FOO.md\n"
            "**confidence:** high\n\n"
            "Body.\n"
        )
        self.assertEqual(len(items), 1)
        self.assertTrue(any("single-brace" in i for i in items[0].issues))


class TestConflictWithBodyIssue(unittest.TestCase):
    """A valid item contradicting an item-with-body-issue must still be flagged.

    Regression for a bug where any `issues` entry excluded the item from
    conflict keying — so `[valid A] vs [B with empty body]` silently merged.
    """

    def test_body_issue_does_not_hide_conflict(self):
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            shutil.copytree(ROOT / "tests" / "fixtures" / "clean", proj)
            pending = proj / "docs" / ".pending"
            pending.mkdir(parents=True, exist_ok=True)

            # Item A: valid
            (pending / "2026-04-15-0900-aaaa.md").write_text(
                "# Pending\n\n"
                "## decision\n"
                "**target:** docs/decisions/2026-04-15-CHOICE.md\n"
                "**confidence:** high\n\n"
                "Use Python.\n",
                encoding="utf-8",
            )
            # Item B: bad confidence (body issue) but SAME target
            (pending / "2026-04-15-0901-bbbb.md").write_text(
                "# Pending\n\n"
                "## decision\n"
                "**target:** docs/decisions/2026-04-15-CHOICE.md\n"
                "**confidence:** weird\n\n"
                "Use TypeScript.\n",
                encoding="utf-8",
            )
            items = list_pending(proj)
            self.assertEqual(len(items), 2)
            conflicts = detect_conflicts(items)
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(
                conflicts[0].target,
                "docs/decisions/2026-04-15-CHOICE.md",
            )


class TestPendingArchive(unittest.TestCase):
    def test_archive_moves_only_old_files(self):
        import os
        import shutil
        import tempfile
        import time
        from brain.pending import archive_old  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            shutil.copytree(ROOT / "tests" / "fixtures" / "clean", proj)
            pending = proj / "docs" / ".pending"
            pending.mkdir(parents=True, exist_ok=True)

            old = pending / "2020-01-01-0000-oooo.md"
            old.write_text("# Old\n\n## fact\n**target:** x.md\n**confidence:** high\n\nX\n", encoding="utf-8")
            # Backdate mtime by 30 days
            past = time.time() - 30 * 86400
            os.utime(old, (past, past))

            fresh = pending / "2026-04-15-0900-ffff.md"
            fresh.write_text("# Fresh\n\n## fact\n**target:** y.md\n**confidence:** high\n\nY\n", encoding="utf-8")

            result = archive_old(proj, days=14, dry_run=False)
            self.assertEqual(result["scanned"], 2)
            self.assertEqual(result["archived"], 1)
            self.assertEqual(result["kept"], 1)
            self.assertFalse(old.exists())
            self.assertTrue((pending / "archive" / old.name).exists())
            self.assertTrue(fresh.exists())

    def test_dry_run_does_not_move(self):
        import os, shutil, tempfile, time
        from brain.pending import archive_old  # noqa: E402
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            shutil.copytree(ROOT / "tests" / "fixtures" / "clean", proj)
            pending = proj / "docs" / ".pending"
            pending.mkdir(parents=True, exist_ok=True)
            old = pending / "2020-01-01-0000-oooo.md"
            old.write_text("# Old\n\n## fact\n**target:** x.md\n**confidence:** high\n\nX\n", encoding="utf-8")
            past = time.time() - 30 * 86400
            os.utime(old, (past, past))

            result = archive_old(proj, days=14, dry_run=True)
            self.assertEqual(result["archived"], 1)
            self.assertTrue(old.exists(), "dry-run must not move files")


if __name__ == "__main__":
    unittest.main()
