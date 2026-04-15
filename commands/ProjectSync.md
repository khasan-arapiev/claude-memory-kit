---
description: One-stop brain sync — extracts insights, stages them, merges when safe, refuses when unsafe. Replaces /ProjectSave, /ProjectMerge, /ProjectUpdate.
---

You are running the `ProjectSync` command from the `project-brain` skill.

## Your job

Bring the project brain up to date in one command. You handle the judgment half (what from this conversation is worth saving); the CLI handles the state half (what's already staged, what conflicts exist, whether a merge is safe right now). Pick the right action based on state — don't ask the user to pick between save / merge / update like the old three-command model.

## Required references

- `~/.claude/skills/project-brain/references/extraction-rubric.md` — what to save vs ignore
- `~/.claude/skills/project-brain/references/quality-rules.md` — naming, size caps, self-growing schema
- `~/.claude/skills/project-brain/templates/ADR-TEMPLATE.md` — for new decision items

## Step 1 — Verify project-brain managed

Check current directory for `CLAUDE.md` with `<!-- project-brain: managed -->`. If absent, abort: "Not a project-brain managed project. Run `/ProjectNewSetup` first."

## Step 2 — Generate a session id

```bash
session_id="$(date +%Y-%m-%d-%H%M)-$(head -c 4 /dev/urandom 2>/dev/null | base64 | tr -dc 'a-z0-9' | head -c 4)"
[ -z "$session_id" ] && session_id="$(date +%Y-%m-%d-%H%M)-$(echo $RANDOM | md5sum 2>/dev/null | head -c 4)"
```

Hold this value for the rest of the run.

## Step 3 — Ask the CLI what mode to run

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" sync plan "$(pwd)" --session-id "$session_id" --json
```

The JSON tells you which of four modes applies:

| Mode | Meaning | What you do |
|---|---|---|
| `empty` | Nothing staged anywhere | Extract insights from this session. If none, stop. Otherwise go straight to step 5 (apply directly, commit each). |
| `quick` | Only this session staged, no conflicts | Extract insights (they may add to the staged ones). Then apply all and commit. |
| `merge_first` | Other sessions have staged items | Extract and stage this session's insights to `docs/.pending/${session_id}.md`. **Do not merge.** Tell the user which other sessions exist and that you're stopping for their review. |
| `resolve_conflicts` | Pending items contradict each other | Surface every conflict (the JSON lists target + item ids). Ask the user which wins. Record the losing item in the winning ADR's "Alternatives considered" section. Then continue into the apply step. |

Trust the CLI. Do not recount pending files yourself.

## Step 4 — Extract insights from this session

Apply the extraction rubric to the whole current conversation. For each keeper, classify:

- `rule` — reusable guidance ("always", "never", "must")
- `fact` — concrete data (name, path, id, url, number)
- `decision` — a chosen approach with reasoning
- `correction` — "that earlier assumption was wrong, here's the right one"

Skip: conversation narrative, ephemeral state, anything already in the code or docs (run `brain query "<topic>"` to spot-check), raw credential values, vague impressions.

For each keeper, pick a target:

- `brain query "<topic>"` to find the closest existing doc section.
- If nothing fits and it's a `decision`, propose `docs/decisions/{{date}}-KEBAB-TITLE.md` (the placeholder expands at write time to today's ISO date).
- Otherwise propose a new file under `docs/strategy/`, `docs/reference/`, `docs/workflows/`, or `docs/context/` per the quality rules.

Valid placeholders in `target:` fields: `{{date}}`, `{{project-slug}}`, `{{slug}}`. Anything else will be flagged as an unknown placeholder by the CLI — fix before proceeding.

If extraction would produce more than 50 items, ask the user: "Found <N>. That's unusual — save all or cap at 20?"

## Step 5 — Stage or apply based on mode

### Mode: `merge_first`

Write the items to `docs/.pending/${session_id}.md` using the format below. Do not apply them. Report:

```
Staged <N> insights to docs/.pending/${session_id}.md
Other sessions have <M> pending items I won't touch:
  - <session-id>: <summary from brain pending list>
Run /ProjectSync again once those are reviewed and merged.
```

### Mode: `empty`, `quick`, or `resolve_conflicts` (after conflicts resolved)

Merge everything (any pre-existing pending plus this session's new items) directly into the brain. Use the unified pipeline:

1. Pull the full item set: `brain pending list "$(pwd)" --json`. Combine with the session's in-memory items.
2. Group by target, dedup identical bodies, surface paraphrase/semantic clashes to the user.
3. For each target:
   - Existing file: `brain query "<topic>"` → find the right section → Edit-tool append or update.
   - Missing file: create it. Add a routing entry to `CLAUDE.md` (respect the token cap).
   - Missing ADR: use `ADR-TEMPLATE.md`; filename `YYYY-MM-DD-KEBAB-TITLE.md` under `docs/decisions/`.
4. Commit each target atomically: `sync: <type> -> <relative-path>`.
5. Delete any pending files whose items have all been applied. Commit: `sync: clear pending <session-id>`.
6. Run `brain audit "$(pwd)"` and include the delta in the final report.

## Step 6 — Report

Pick the format based on the path taken:

**Staged only (merge_first):**
```
Staged <N> insights. Other sessions blocking merge: <ids>
```

**Merged:**
```
Synced <N> items across <M> docs in <K> commits.
  + <new> new file(s)
  ~ <upd> existing file(s) updated
Cleared pending: <session-ids>
Brain health: <new>% (was <old>%)
```

## Pending file format

Plain markdown, one file per session. Each item is an H2 for the type plus metadata fields and a body. Unknown placeholders in `target:` will be flagged by the CLI.

```markdown
# Pending updates - 2026-04-15-0900-ab12

## rule
**target:** docs/strategy/WRITING-RULES.md
**confidence:** high

Never use em dashes in copy.

## decision
**target:** docs/decisions/{{date}}-CHOSEN-LANG.md
**confidence:** high

Use Python for the CLI. TypeScript rejected because...
```

Valid types: `rule`, `fact`, `decision`, `correction`. Valid confidence: `high`, `medium`, `low`.

After writing any pending file, confirm it parses:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" pending list "$(pwd)" --json
```

Every item should appear with empty `issues`. Fix any flagged item before continuing.

## Error cases

- No CLAUDE.md → tell user to run `/ProjectNewSetup`.
- CLI unavailable → you can still stage to `docs/.pending/`, but do NOT attempt a merge without the CLI (conflict detection is the safety net).
- All items have validation issues → don't proceed; report them and ask the user whether to fix the source or drop those items.
