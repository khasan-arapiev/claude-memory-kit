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
            "command": "test -f CLAUDE.md && python \"$HOME/.claude/skills/project-brain/cli/run.py\" audit . 2>/dev/null | head -20 || true"
          },
          {
            "type": "command",
            "command": "test -f CLAUDE.md && python \"$HOME/.claude/skills/project-brain/cli/run.py\" drift . 2>/dev/null | head -10 || true"
          }
        ]
      }
    ]
  }
}
```

The `test -f CLAUDE.md` guard means the hook only fires in project-brain-managed folders. Elsewhere it's a no-op.

## 2. Stop — prompt to sync when brain docs were touched

**Purpose:** After a work turn, if any `docs/` or `CLAUDE.md` file was modified, print a reminder so the user can run `/ProjectSync` before losing the context. This is a **prompt, not an auto-run** — because extracting the right insights is a judgment call that needs Claude's attention, not a cron job.

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "git -C . diff --name-only HEAD 2>/dev/null | grep -qE '^(docs/|CLAUDE\\.md)' && echo 'Brain docs changed this session. Run /ProjectSync to stage + merge.' || true"
          }
        ]
      }
    ]
  }
}
```

## Why we don't auto-run `/ProjectSync` on hook fire

Claude Code hooks run shell commands, not Claude prompts. They can't invoke a slash command directly, and even if they could, auto-running a destructive-ish operation (writing to the brain, making commits) every time a session ends would be unsafe — you'd accumulate low-quality saves and lose the friction that makes the pending/merge boundary trustworthy.

The pattern that works is: **hooks report state, Claude does the writes.** SessionStart shows you what's drifted. Stop tells you there's work worth syncing. `/ProjectSync` is still a conscious command the user types — but with these hooks, they never forget.

## Manual install

```bash
# Ensure settings exists
test -f "$HOME/.claude/settings.json" || echo '{}' > "$HOME/.claude/settings.json"
# Then hand-merge the hook blocks above into it. JSON merging is fiddly; use a
# tool like `jq` or edit manually.
```

## Disabling

Remove whichever hook blocks you don't want from `~/.claude/settings.json`. The 3 slash commands (`/ProjectNewSetup`, `/ProjectSetupFix`, `/ProjectSync`) continue to work with zero hooks installed.
