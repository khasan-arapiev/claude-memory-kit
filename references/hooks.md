# Hook Setup

Two optional Claude Code hooks make `/ProjectSync` feel ambient without surrendering any of its safety guarantees. Both are additive — the skill works without them.

Both live in `~/.claude/settings.json` under the `hooks` key.

## 1. SessionStart — show brain health as you open a project

**Purpose:** Run `brain audit` and `brain drift` the moment a session opens, so you see orphans, dead links, and drifted docs immediately — no "remember to run audit" discipline required.

**Cost:** Two fast CLI calls. Silent if the brain is clean.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "test -f CLAUDE.md && python \"$HOME/.claude/skills/claude-memory-kit/cli/run.py\" audit . 2>/dev/null | head -20 || true"
          },
          {
            "type": "command",
            "command": "test -f CLAUDE.md && python \"$HOME/.claude/skills/claude-memory-kit/cli/run.py\" drift . 2>/dev/null | head -10 || true"
          }
        ]
      }
    ]
  }
}
```

The `test -f CLAUDE.md` guard means the hook only fires in claude-memory-kit-managed folders. Elsewhere it's a no-op.

**Windows note:** these use bash syntax. Git Bash handles them; PowerShell does not. If your Claude Code install uses PowerShell, replace `test -f CLAUDE.md && ... || true` with the PowerShell equivalent, or point the hook at the `stop-prompt.py` pattern below (Python is the same on every OS).

## 2. Stop — prompt to sync when the session looks un-synced

**Purpose:** After a work turn, print a one-line reminder if (a) pending items are staged or (b) the session made commits but no `/ProjectSync` ran. This is a prompt, not an auto-run — extracting the right insights is a judgment call.

**Implementation:** a small Python script ships with the skill at `hooks/stop-prompt.py`. Python is the same on Windows, macOS, and Linux, which makes the hook work identically across platforms without the bash-in-JSON one-liners of earlier versions.

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$HOME/.claude/skills/claude-memory-kit/hooks/stop-prompt.py\""
          }
        ]
      }
    ]
  }
}
```

The script:
- Exits silently when there's no `CLAUDE.md` in the current directory.
- Prints `Brain: N pending item(s) staged. Run /ProjectSync when ready.` when pending is non-empty.
- Otherwise prints a nudge only if the session made commits but none of them were `sync:` commits in the last hour.
- Never raises: bugs in the hook don't break Claude.

Read or modify the script at `~/.claude/skills/claude-memory-kit/hooks/stop-prompt.py`. It's ~70 lines of stdlib Python, no dependencies.

## Manual install

```bash
# Ensure settings exists
test -f "$HOME/.claude/settings.json" || echo '{}' > "$HOME/.claude/settings.json"
# Then hand-merge the hook blocks above into it. Use jq or edit manually.
```

## Disabling

Remove whichever hook blocks you don't want from `~/.claude/settings.json`. The 3 slash commands (`/ProjectNewSetup`, `/ProjectSetupFix`, `/ProjectSync`) continue to work with zero hooks installed.
