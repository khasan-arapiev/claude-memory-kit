---
description: Sweep all docs/.pending/ files into real docs, deduplicate, resolve conflicts, auto-grow new files
---

You are running the `ProjectMerge` command from the `project-brain` skill.

## Your job

Read all pending files, intelligently reconcile them, and write the result into real docs. Resolve conflicts by asking the user only about contradictions. Self-grow new doc files when needed and auto-wire them into CLAUDE.md.

## Required references

Load these files from the project-brain skill:
- `~/.claude/skills/project-brain/references/quality-rules.md` (for self-growing schema rules)
- `~/.claude/skills/project-brain/references/extraction-rubric.md`
- `~/.claude/skills/project-brain/templates/ADR-TEMPLATE.md`

## Steps

### 1. Verify project-brain managed

Check current directory for `CLAUDE.md` with `<!-- project-brain: managed -->` marker. If absent, abort.

### 2. List pending files

```bash
ls docs/.pending/*.md 2>/dev/null
```

If no pending files, output `Nothing to merge.` and exit.

### 3. Parse all pending files

For each file, parse YAML frontmatter and collect all items into a flat list with source filename tracked.

### 4. Deduplicate

Group items by `(type, target, content)`. If two items match exactly, keep one (prefer high confidence). Record the dedup count.

### 5. Detect conflicts

Group items by `target`. For each target, check if any items contradict each other (e.g., one says "always do X", another says "never do X" on the same target).

For each conflict:
- Surface both versions to the user
- Ask: "Conflict on `<target>`. Version A: `<A>`. Version B: `<B>`. Which wins? (A/B/skip)"
- Record user's choice

### 6. Apply self-growing schema

For each unique item, decide where it goes:

**Existing target check:**
```bash
test -f "<item.target>" && echo "EXISTS"
```

**If exists:**
- Read the file
- Find an appropriate section (or create a new section)
- Append the item content
- Track for commit

**If does not exist:**
Apply self-growing schema from `quality-rules.md`:
1. Determine appropriate folder based on item type
2. Generate filename in SCREAMING-KEBAB-CASE.md
3. For `decision` type, use ADR template
4. For others, create plain markdown with title + content
5. **Create the parent folder if missing:** `mkdir -p "$(dirname <item.target>)"` — the target may name a folder like `docs/strategy/` that doesn't exist yet
6. Write the file
7. Add a routing entry to CLAUDE.md under the appropriate "Working on..." section

### 7. Update CLAUDE.md routing

For every new file created, add a routing line under the appropriate section. Lines look like:
```markdown
### Working on <topic>
1. Read `docs/<category>/<NEW-FILE>.md`
```

If no section exists for the topic, create one before the `<!-- AUTO-GROWN ROUTES BELOW THIS LINE -->` marker.

### 8. Verify CLAUDE.md size

After all updates, check CLAUDE.md line count.

```bash
lines=$(wc -l < CLAUDE.md)
if [ "$lines" -gt 200 ]; then
  echo "WARNING: CLAUDE.md now $lines lines, exceeds cap. Suggesting lift in summary."
fi
```

If over 200, identify the largest non-routing section and propose lifting it (do not auto-lift, just suggest in the summary).

### 9. Commit each doc update atomically

For each doc that was modified or created:
```bash
git add "<doc-path>"
git add CLAUDE.md  # only if a route was added
git -c user.name="<identity>" -c user.email="<identity>" commit -m "docs(project-brain): merge <item-summary> into <doc-path>"
```

One commit per doc keeps history surgical and reverts trivial.

### 10. Delete merged pending files

```bash
rm docs/.pending/*.md
git add docs/.pending/
git -c user.name="<identity>" -c user.email="<identity>" commit -m "chore(project-brain): clear merged pending files"
```

### 11. Report

Output a structured summary:
```
Merged <X> items into <Y> docs.
  - <Z> conflicts resolved
  - <N> new files created
  - <M> existing files updated
  - <K> pending files cleared

CLAUDE.md size: <lines>/200
```

If CLAUDE.md is approaching the cap, add:
```
WARNING: CLAUDE.md at <lines>/200. Consider lifting these sections to dedicated docs:
  - <section name> (~<line count> lines)
  - ...
```

## Errors

- If a pending file has malformed YAML, skip it and report at the end: "Skipped <file> due to malformed YAML."
- If git commits fail due to missing identity, report and ask user.
