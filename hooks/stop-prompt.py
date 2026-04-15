#!/usr/bin/env python3
"""Stop-hook helper — decide whether to nudge the user to run `/ProjectSync`.

Run by Claude Code's Stop hook (one shell command per hook, so a single
script file is both readable and cross-platform):

    settings.json -> hooks.Stop[*].hooks[0].command =
        "python \"$HOME/.claude/skills/project-brain/hooks/stop-prompt.py\""

Output:
  stdout:  a one-line reminder (or nothing if no nudge needed)
  stderr:  nothing in normal operation; tracebacks on bugs
  exit 0:  always (hooks shouldn't break Claude when they fail)

Logic:
  - If the current directory has no CLAUDE.md, exit silently.
  - If `brain pending list` reports any items, nudge.
  - Else, if there's been no `sync:` commit in the last hour AND
    any commits happened in the last hour, nudge — on the assumption
    that the session produced work that hasn't been synced yet.
  - Else, silent.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CLAUDE_MD = Path("CLAUDE.md")
BRAIN_CLI = Path.home() / ".claude" / "skills" / "project-brain" / "cli" / "run.py"


def _quiet_run(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=8)
        return p.returncode, p.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def _pending_item_count() -> int:
    if not BRAIN_CLI.is_file():
        return 0
    code, out = _quiet_run([sys.executable, str(BRAIN_CLI), "pending", "list", ".", "--json"])
    if code not in (0, 1):  # 0 clean, 1 conflicts/issues — both valid payloads
        return 0
    try:
        return len(json.loads(out).get("items", []))
    except (json.JSONDecodeError, AttributeError):
        return 0


def _recent_sync_commit() -> bool:
    code, out = _quiet_run(["git", "log", "--since=1 hour ago", "--grep=^sync:", "--oneline"])
    return code == 0 and bool(out.strip())


def _recent_any_commit() -> bool:
    code, out = _quiet_run(["git", "log", "--since=1 hour ago", "--oneline"])
    return code == 0 and bool(out.strip())


def main() -> int:
    # Guard: only run in project-brain-managed folders.
    if not CLAUDE_MD.is_file():
        return 0

    pending = _pending_item_count()
    if pending > 0:
        print(f"Brain: {pending} pending item(s) staged. Run /ProjectSync when ready.")
        return 0

    # No pending — but if there's been session activity without a sync,
    # nudge once. (Skipped when the repo has no recent commits at all:
    # that just means the session hasn't produced anything yet.)
    if _recent_any_commit() and not _recent_sync_commit():
        print("Brain: session touched the repo but no /ProjectSync yet. "
              "Run /ProjectSync to capture insights.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never break Claude Code when the hook misbehaves.
        sys.exit(0)
