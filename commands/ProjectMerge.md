---
description: Sweep all docs/.pending/ files into real docs, deduplicate, resolve conflicts, auto-grow new files
---

You are running the `ProjectMerge` command from the `project-brain` skill.

## Your job

Apply every item staged in `docs/.pending/` to the real brain (`CLAUDE.md` and `docs/`). Resolve conflicts with the user. Delete pending files after they're applied. Make every change as an atomic git commit.

## Required references

- `~/.claude/skills/project-brain/references/quality-rules.md` — naming, size caps, self-growing schema rules
- `~/.claude/skills/project-brain/templates/ADR-TEMPLATE.md` — for new decision items

## Step 1 — Get the deterministic plan

Don't parse `.pending/*.md` yourself. Call the CLI:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" pending list "<project path>" --json
```

You get back a JSON object with two arrays:

```json
{
  "items": [
    {
      "id": "2026-04-14-1430-a3b9::0",
      "session_id": "2026-04-14-1430-a3b9",
      "type": "rule",
      "target": "docs/strategy/WRITING-RULES.md",
      "confidence": "high",
      "content": "Never use em dashes in copy.",
      "source_file": "docs/.pending/2026-04-14-1430-a3b9.md",
      "issues": []
    }
  ],
  "conflicts": [
    {
      "target": "docs/decisions/2026-04-14-LANGUAGE-CHOICE.md",
      "type": "decision",
      "item_ids": ["2026-04-14-1730-ddd4::0", "2026-04-14-1731-eee5::0"],
      "reason": "2 decision items target the same file with different content"
    }
  ]
}
```

If `items` is empty, tell the user "No pending updates" and stop.

## Step 2 — Resolve detected conflicts FIRST

If `conflicts` is non-empty, surface every conflict to the user before doing any merging. For each conflict:

1. Print the target file, the conflicting item ids, and each item's body.
2. Ask the user which item wins.
3. The losing item gets captured in the winning ADR's "Alternatives considered" section so the rejected reasoning isn't lost.
4. Mark losing items to be skipped during the apply step.

The CLI flags conflicts deterministically (multiple decision items at the same target with different bodies). It does NOT detect semantic conflicts in `rule` or `fact` items — you still need to scan those by reading the contents during Step 3.

## Step 3 — Surface validation issues

Any item with non-empty `issues` is malformed. Show the user the issues and ask whether to skip those items or fix the source pending file before continuing.

## Step 4 — Group, dedup, detect remaining conflicts

Group items by `target`. Within each target:

- **Exact duplicates** (identical `content`): keep one, drop the rest, prefer high confidence.
- **Near-duplicates** (paraphrase of an existing item or another pending item): show both to the user, ask which to keep or whether to merge.
- **Semantic contradictions in non-decision types** (e.g. two rules saying opposite things): show both, ask which wins.

## Step 5 — Apply per target, one commit each

For each target file:

1. **If the target exists:** run `brain query "<topic of items>"` to find the right section, then Edit-tool an append or update.
2. **If the target does not exist (self-growing schema):**
   - For `decision` items: create as ADR using `ADR-TEMPLATE.md`, filename `YYYY-MM-DD-KEBAB-TITLE.md` under `docs/decisions/`.
   - For `rule` items: place under `docs/strategy/` or `docs/workflows/` based on scope.
   - For `fact` items: place under `docs/reference/` or `docs/context/`.
   - For `correction` items: edit wherever the original incorrect statement lives (use `brain query` to find it).
   - After creating any new file, add a routing entry to `CLAUDE.md` (must respect the 200-line cap).
3. Commit each target's changes as one atomic git commit: `merge: <type> -> <relative-path>`.

## Step 6 — Delete merged pending files

Once every item from a pending file has been applied (or skipped), delete the pending file. Commit the deletion separately: `merge: clear pending <session-id>`.

## Step 7 — Re-audit and report

After merging, run `brain audit` again to catch new orphans / oversize / dead-link issues introduced by the merge. Then summarize:

```
Merged 7 items across 4 docs.
Created 1 new file (docs/decisions/2026-04-14-USE-MARKDOWN-PENDING.md).
Resolved 1 conflict.
Cleared 2 pending sessions.
Brain health: 96% (was 91%).
```

## Pending file format

Pending files are plain markdown (not YAML), one file per session. Each item is an H2 with metadata fields and a body:

```markdown
# Pending updates - 2026-04-14-1430-a3b9

## rule
**target:** docs/strategy/WRITING-RULES.md
**confidence:** high

Never use em dashes in copy.

## fact
**target:** docs/reference/EXTERNAL-SYSTEMS.md
**confidence:** high

Meta Pixel ID: 0000000000000000
```

Valid types: `rule`, `fact`, `decision`, `correction`. Valid confidence: `high`, `medium`, `low`.

## Error cases

- No CLAUDE.md: tell user to run `/ProjectNewSetup` first.
- All items have validation issues: don't proceed; report issues and ask user to fix the pending files first.
- CLI unavailable: fall back to manual scan of `docs/.pending/` but warn the user that conflict detection will be less reliable.
