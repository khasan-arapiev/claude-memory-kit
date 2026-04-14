---
description: Solo-chat shortcut. Save and merge in one shot, skipping the pending folder. Use only when no other chats are working on the same project.
---

You are running the `ProjectUpdate` command from the `project-brain` skill.

## Your job

Run the equivalent of `ProjectSave` followed by `ProjectMerge`, but skip writing to `docs/.pending/`. Insights are extracted from the current session and written directly into real docs in one commit sequence.

## When to use vs ProjectSave + ProjectMerge

Use `ProjectUpdate` only when:
- You are the only chat working on this project
- No other sessions have unmerged pending files

If `docs/.pending/` already contains files from other sessions, **abort** and tell the user: "There are <N> pending files from other sessions. Run `/ProjectMerge` first to incorporate them, then re-run `/ProjectUpdate`."

## Required references

Same as `ProjectSave` and `ProjectMerge`:
- `~/.claude/skills/project-brain/references/extraction-rubric.md`
- `~/.claude/skills/project-brain/references/quality-rules.md`
- `~/.claude/skills/project-brain/templates/ADR-TEMPLATE.md`

## Steps

### 1. Verify project-brain managed

Check current directory for `CLAUDE.md` with `<!-- project-brain: managed -->` marker. If absent, abort.

### 2. Check for existing pending files

```bash
count=$(ls docs/.pending/*.md 2>/dev/null | wc -l)
if [ "$count" -gt 0 ]; then
  echo "ABORT: $count pending files exist. Run /ProjectMerge first."
  exit 1
fi
```

### 3. Extract insights from session

Apply the extraction rubric (`extraction-rubric.md`) to the current conversation. Build the same item list that `ProjectSave` would build, but keep it in memory rather than writing a pending file.

### 4. If nothing to save, exit

```
Nothing significant to update from this session.
```

### 5. Apply self-growing schema directly

For each item, follow the same logic as `ProjectMerge` step 6 (existing-target check, append or create new file, update CLAUDE.md routing).

### 6. Commit each doc atomically

Same as `ProjectMerge` step 9. One commit per doc.

### 7. Report

```
Updated <Y> docs in <commit-count> commits.
  - <N> new files created
  - <M> existing files updated

CLAUDE.md size: <lines>/200
```

## Errors

- Abort if pending files exist (see step 2)
- Same error handling as `ProjectMerge` for malformed data or git failures
