---
description: Checkpoint current session insights to docs/.pending/ for later merging
---

You are running the `ProjectSave` command from the `project-brain` skill.

## Your job

Scan the current conversation for high-signal insights (rules, facts, decisions, corrections) and write them to a single timestamped pending file. Silent operation, no prompts.

## Required references

Load these files from the project-brain skill:
- `~/.claude/skills/project-brain/references/extraction-rubric.md` — what to save vs ignore

## Steps

### 1. Verify project-brain managed

Check current directory for `CLAUDE.md` with `<!-- project-brain: managed -->` marker. If absent, abort with: "Not in a project-brain managed project. Run `/ProjectNewSetup` first."

### 2. Determine pending folder

`<project-root>/docs/.pending/` — create if missing.

### 3. Apply extraction rubric

Review the entire current conversation. For each user message and assistant response, identify items matching the SAVE criteria from `extraction-rubric.md`:

- New facts (names, paths, IDs, URLs, numbers)
- New rules
- Decisions with reasoning
- Corrections to prior assumptions

Skip items matching the IGNORE criteria:
- Conversation narrative
- Ephemeral state
- Patterns already visible in code
- Duplicates of existing docs (read CLAUDE.md routing and spot-check target docs)
- Vague impressions
- Raw credential values

### 4. Generate session id

```bash
session_id="$(date +%Y-%m-%d-%H%M)-$(head -c 4 /dev/urandom | base64 | tr -dc 'a-z0-9' | head -c 4)"
```

If `/dev/urandom` is not available (Windows bash), use:
```bash
session_id="$(date +%Y-%m-%d-%H%M)-$(echo $RANDOM | md5sum | head -c 4)"
```

### 5. Build pending file (plain markdown, not YAML)

For each extracted item, write an H2 section with metadata fields and a body. Format:

```markdown
# Pending updates - <session_id>

## <type>
**target:** <relative path to target doc>
**confidence:** <high|medium|low>

<body content here, multiple lines OK>
```

Valid `type` values: `rule`, `fact`, `decision`, `correction`.
Valid `confidence`: `high`, `medium`, `low`.

Determine `target` per item:
- Run `brain query "<topic>"` to find the closest existing doc section
- If no existing doc fits, propose a new path under `docs/<category>/` (the merge command will create it)
- For `decision` items with no existing target, propose `docs/decisions/<session-date>-KEBAB-TITLE.md`

### 6. Write pending file

```bash
mkdir -p docs/.pending
# Write the markdown content built in step 5 to:
#   docs/.pending/${session_id}.md
```

Use the actual extracted items, not placeholders. After writing, verify the file parses cleanly:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" pending list . --json
```

Confirm every item you wrote appears with empty `issues`. If any item shows issues, fix the file before committing.

### 7. Commit silently

```bash
git add "docs/.pending/${session_id}.md"
git -c user.name="<from-recent-commits>" -c user.email="<from-recent-commits>" commit -m "chore(project-brain): save session ${session_id} insights"
```

If git is not initialized, skip the commit but keep the file.

### 8. Output

If invoked manually, output one line:
```
Saved <N> items to docs/.pending/<session_id>.md
```

If invoked silently (e.g. by SessionEnd hook), output nothing.

## Special case: nothing to save

If no high-signal items were found, do not create an empty pending file. Output:
```
Nothing significant to save from this session.
```

## Errors

- If extraction would save more than 50 items in one session, that is unusual. Surface to user: "I found <N> items. That seems high. Should I save them all or only the top <N>?" Wait for user choice.
