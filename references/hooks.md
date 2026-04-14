# Hook Setup

The project-brain skill uses one Claude Code hook: `SessionEnd`.

## SessionEnd hook

**Purpose:** Auto-run `ProjectSave` when a session closes, so insights from the session are preserved without the user remembering.

**Location:** `~/.claude/settings.json`

**Hook entry:**

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Project brain: SessionEnd hook fired. Run /ProjectSave manually next session if not auto-detected.'"
          }
        ]
      }
    ]
  }
}
```

**Important:** Claude Code's `SessionEnd` hook runs shell commands, not Claude prompts. The hook above just echoes a marker. To actually run `ProjectSave`, the next session's startup must check for an unfinished session and offer to save it.

**Implementation note:** Because `SessionEnd` hooks cannot directly invoke Claude commands, the project-brain skill uses a session-start safety check instead:

1. At the start of every session in a managed project, the command preamble checks `docs/.pending/` for files
2. It also checks the most recent commit in the project — if there is no recent `ProjectSave` commit but there are recent code/doc changes, it offers to run `ProjectSave` retroactively for the previous session

This achieves the same outcome as a true SessionEnd hook without depending on hooks firing reliably.

## Manual install

Run this command once after installing the project-brain skill (or have `ProjectNewSetup` install it during first run):

```bash
# Verify settings.json exists
test -f "$HOME/.claude/settings.json" || echo '{}' > "$HOME/.claude/settings.json"

# The actual hook addition is done by the project-brain skill the first time
# any project-brain command runs. The skill checks settings.json for the hook
# entry and adds it if missing.
```

## Disabling

To disable the auto-save behavior, remove the `SessionEnd` hook entry from `~/.claude/settings.json`. The 5 slash commands continue to work manually.
