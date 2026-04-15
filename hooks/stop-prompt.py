#!/usr/bin/env python3
"""Stop-hook helper — nudge the user to run `/ProjectSync` when there's real work to sync.

Run by Claude Code's Stop hook (one shell command per hook, so a single
script file is both readable and cross-platform):

    settings.json -> hooks.Stop[*].hooks[0].command =
        "python \"$HOME/.claude/skills/project-brain/hooks/stop-prompt.py\""

Output:
  stdout:  a one-line reminder (or nothing if no nudge needed)
  stderr:  nothing in normal operation; tracebacks on bugs
  exit 0:  always (hooks shouldn't break Claude when they fail)

Logic:
  1. If the current directory has no CLAUDE.md, exit silently.
  2. If `brain pending list` reports any items, nudge. (Unambiguous signal.)
  3. Else, nudge ONLY when there's been a commit in the last hour that
     touched docs/ or CLAUDE.md but NO `sync:` commit covered it.
     Unrelated commits (feature work, typo fixes) do NOT trigger a nudge,
     so the hook doesn't become banner-blind noise.

Install path override:
  Set BRAIN_SKILL_DIR to point at the project-brain skill dir if you
  installed it somewhere other than ~/.claude/skills/project-brain.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CLAUDE_MD = Path("CLAUDE.md")

# Install path: default `~/.claude/skills/project-brain`, overridable via env.
BRAIN_SKILL_DIR = Path(
    os.environ.get(
        "BRAIN_SKILL_DIR",
        str(Path.home() / ".claude" / "skills" / "project-brain"),
    )
)
BRAIN_CLI = BRAIN_SKILL_DIR / "cli" / "run.py"


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


def _brain_touching_commits_last_hour() -> list[str]:
    """Return commit hashes from the last hour that changed docs/ or CLAUDE.md."""
    code, out = _quiet_run([
        "git", "log", "--since=1 hour ago", "--name-only", "--pretty=format:%H",
    ])
    if code != 0 or not out.strip():
        return []
    hashes: list[str] = []
    current_hash: str | None = None
    touched = False
    for line in out.splitlines():
        if not line.strip():
            if current_hash and touched:
                hashes.append(current_hash)
            current_hash = None
            touched = False
            continue
        if current_hash is None:
            current_hash = line.strip()
        else:
            if line.startswith("docs/") or line.strip() == "CLAUDE.md":
                touched = True
    if current_hash and touched:
        hashes.append(current_hash)
    return hashes


def _has_recent_sync_commit() -> bool:
    code, out = _quiet_run(["git", "log", "--since=1 hour ago", "--grep=^sync:", "--oneline"])
    return code == 0 and bool(out.strip())


def main() -> int:
    if not CLAUDE_MD.is_file():
        return 0

    pending = _pending_item_count()
    if pending > 0:
        print(f"Brain: {pending} pending item(s) staged. Run /ProjectSync when ready.")
        return 0

    # No pending — only nudge when recent work touched the brain AND no
    # sync: commit covers it. Filters out "I just fixed a typo in src/".
    brain_commits = _brain_touching_commits_last_hour()
    if brain_commits and not _has_recent_sync_commit():
        print("Brain: docs/ or CLAUDE.md changed this session but no /ProjectSync ran. "
              "Run /ProjectSync to capture insights.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never break Claude Code when the hook misbehaves.
        sys.exit(0)
