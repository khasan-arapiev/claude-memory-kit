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

## 2. Stop — prompt to sync when session looks un-synced

**Purpose:** After a work turn, if the session looks like it produced brain-worthy work but no `/ProjectSync` has run yet, print a reminder. This is a **prompt, not an auto-run** — extracting the right insights is a judgment call.

**The subtle bit:** `/ProjectSync` already commits its work atomically, so the naive check of "are there uncommitted changes under `docs/`?" reports false right after a sync. Instead, check two things: (a) there are pending items the user hasn't merged yet, OR (b) no `sync:` commit has touched this repo in the last hour despite activity.

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "test -f CLAUDE.md || exit 0; python \"$HOME/.claude/skills/project-brain/cli/run.py\" pending list . --json 2>/dev/null | python -c 'import json,sys,subprocess; d=json.load(sys.stdin); n=len(d.get(\"items\",[])); recent=subprocess.run([\"git\",\"log\",\"--since=1 hour ago\",\"--grep=^sync:\",\"--oneline\"],capture_output=True,text=True).stdout.strip(); print(\"Brain reminder: \"+str(n)+\" pending item(s). Run /ProjectSync.\") if (n>0 or not recent) else None' 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

Single-line because Claude Code hooks run one shell command. If you prefer readability, save the logic as a script and have the hook call the script.

### Alternative: simpler but noisier

If the above is too clever, this simpler variant fires whenever pending is non-empty (including right after a merge_first Sync that legitimately left items staged for another session):

```json
{
  "type": "command",
  "command": "test -f CLAUDE.md && python \"$HOME/.claude/skills/project-brain/cli/run.py\" pending list . 2>/dev/null | grep -q 'Pending items:' && echo 'Pending items staged. Run /ProjectSync when ready.' || true"
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
