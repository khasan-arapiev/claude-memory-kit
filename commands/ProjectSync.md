---
description: One-stop brain sync — extracts insights, stages them, merges when safe, refuses when unsafe. Replaces /ProjectSave, /ProjectMerge, /ProjectUpdate.
---

You are running the `ProjectSync` command from the `project-brain` skill.

## Your job

Bring the project brain up to date in one command. You handle the judgment half (what from this conversation is worth saving); the CLI handles the state half (what's already staged, what conflicts exist, whether a merge is safe right now). Pick the right action based on state — don't ask the user to pick between save / merge / update like the old three-command model.

## Flags the user can pass

- `--dry-run` — run every step that does not write to disk or git. Print the exact edits / commits that *would* happen. No files get modified. Use this when the user wants to preview a sync on a busy session.

## Required references

- `~/.claude/skills/project-brain/references/extraction-rubric.md` — what to save vs ignore
- `~/.claude/skills/project-brain/references/quality-rules.md` — naming, size caps, self-growing schema
- `~/.claude/skills/project-brain/templates/ADR-TEMPLATE.md` — for new decision items

## Step 1 — Verify project-brain managed

Check current directory for `CLAUDE.md` with `<!-- project-brain: managed -->`. If absent, abort:

> Not a project-brain managed project. Run `/ProjectNewSetup` first.

## Step 2 — Verify git working tree is clean (skip in `--dry-run`)

`/ProjectSync` makes commits. Interleaving those with unrelated uncommitted changes would pollute the history. Before doing anything else:

```bash
if git rev-parse --git-dir >/dev/null 2>&1; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    # Working tree is dirty. Tell the user, don't touch anything.
    exit 1
  fi
fi
```

If dirty, abort with a precise message:

> Git working tree has uncommitted changes. Commit or stash them before running /ProjectSync so brain commits stay atomic. (Or re-run with `--dry-run` to preview without committing.)

If git is not initialised at all, record that fact and continue — you'll stage files but skip the commit steps later.

## Step 3 — Generate a session id (via the CLI, not shell)

```bash
session_id=$(python "$HOME/.claude/skills/project-brain/cli/run.py" sync new-session-id)
```

This is stdlib Python — no `/dev/urandom`, no `md5sum`, works identically on Git Bash / macOS / Linux. Hold the value for the rest of the run.

## Step 4 — Ask the CLI what mode to run

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" sync plan "$(pwd)" --session-id "$session_id" --json
```

The JSON tells you which of four modes applies:

| Mode | Meaning | What you do |
|---|---|---|
| `empty` | Nothing staged anywhere | Extract insights from this session. If none, stop. Otherwise **write a pending file for this session, then immediately merge it** (see step 6). Never merge from in-memory state — the pending file is the audit trail. |
| `quick` | Only this session is staged, no conflicts | Extract new insights (they get added to the existing staged ones). Then apply all and commit. |
| `merge_first` | Other sessions have staged items | Extract and stage this session's insights to `docs/.pending/${session_id}.md`. **Do not merge.** Tell the user which other sessions exist and that you're stopping for their review. |
| `resolve_conflicts` | Pending items contradict each other | Surface every conflict (see step 7 for the prompt format). Apply the user's decisions, then continue into the apply step. |

Trust the CLI. Do not recount pending files yourself.

## Step 5 — Extract insights from this session

Apply the extraction rubric to the whole current conversation. For each keeper, classify:

- `rule` — reusable guidance ("always", "never", "must")
- `fact` — concrete data (name, path, id, url, number)
- `decision` — a chosen approach with reasoning
- `correction` — "that earlier assumption was wrong, here's the right one"

Skip: conversation narrative, ephemeral state, anything already in the code or docs (run `brain query "<topic>"` to spot-check), raw credential values, vague impressions.

For each keeper, pick a target:

- `brain query "<topic>"` to find the closest existing doc section.
- If nothing fits and it's a `decision`, propose `docs/decisions/{{date}}-KEBAB-TITLE.md` (placeholder expands to today's ISO date at write time).
- Otherwise propose a new file under `docs/strategy/`, `docs/reference/`, `docs/workflows/`, or `docs/context/` per the quality rules.

**Placeholder validation.** Valid tokens: `{{date}}`, `{{project-slug}}`, `{{slug}}`. Anything else (including single-brace typos like `{date}`) will be flagged as a validation issue by the CLI — fix before proceeding.

**Batch cap.** If extraction would produce more than 50 items, ask the user: *"Found <N>. That's unusual — save all or cap at 20?"*

**Dedup cost cap.** You do NOT need to `brain query` every candidate. Query once per distinct topic and reuse results within the session.

## Step 6 — Stage or apply based on mode

### Mode: `merge_first`

Write items to `docs/.pending/${session_id}.md` using the format in `templates/PENDING-FILE-TEMPLATE.md`. Do not apply them. Verify the file parses cleanly:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" pending list "$(pwd)" --json
```

Every item from your session should appear with empty `issues`. Report:

```
Staged <N> insights to docs/.pending/${session_id}.md
Other sessions have <M> pending items I won't touch:
  - <session-id>: <N items across N targets>
Run /ProjectSync again once those are reviewed and merged.
```

Then stop.

### Mode: `empty`, `quick`, or `resolve_conflicts` (after conflicts resolved)

Merge everything (any pre-existing pending plus this session's new items) into the brain.

1. **Stage first** (all modes) — write `docs/.pending/${session_id}.md` with this session's items (if any). This is your audit trail: every change must originate from a pending file.
2. **Pull full item set**: `brain pending list "$(pwd)" --json`. This now includes the file you just wrote.
3. **Group by target**, dedup identical bodies, surface paraphrase/semantic clashes to the user.
4. **For each target**:
   - Existing file: `brain query "<topic>"` → find the right section → Edit append/update.
   - Missing file: create it. Add a routing entry to `CLAUDE.md` (respect the token cap from `quality-rules.md`).
   - Missing ADR: use `ADR-TEMPLATE.md`; filename `YYYY-MM-DD-KEBAB-TITLE.md` under `docs/decisions/`.
5. **Commit each target atomically**: `sync: <type> -> <relative-path>` — in `--dry-run` print the intended message instead.
6. **Delete ONLY the current session's pending file** once all its items have been applied:
   ```bash
   rm "docs/.pending/${session_id}.md"
   git rm "docs/.pending/${session_id}.md" 2>/dev/null
   ```
   Do NOT touch other sessions' pending files, even if they were fully merged — that's their owner's job. Commit: `sync: clear pending ${session_id}`.
7. **Re-audit**: `brain audit "$(pwd)"` — include health score delta in the final report.

## Step 7 — Conflict resolution prompt (when mode is `resolve_conflicts`)

The CLI reports contradictions deterministically. Present them to the user in a consistent format:

```
Conflict 1 of N — <target path>
  Type: <decision|rule|correction>

  [A] <item-id>
      <first 200 chars of body>

  [B] <item-id>
      <first 200 chars of body>

Pick: A, B, both, or skip.
```

- **A / B** — apply the chosen item, drop the other.
- **both** — apply both (only valid when you can see they're complementary, not contradictory).
- **skip** — defer both; they stay in pending for the next /ProjectSync.

For targets that are ADRs, the losing item goes into the winner's "Alternatives considered" section.
For non-ADR targets (rules, corrections), the losing item is dropped — the rejection rationale lives in this session's commit message instead.

## Step 8 — Report

Pick the format based on the path taken:

**Staged only (`merge_first`):**
```
Staged <N> insights. Other sessions blocking merge: <ids>
```

**Dry run:**
```
Dry run — would sync <N> items across <M> docs in <K> commits.
No files changed.
```

**Merged:**
```
Synced <N> items across <M> docs in <K> commits.
  + <new> new file(s)
  ~ <upd> existing file(s) updated
Cleared pending: ${session_id}
Brain health: <new>% (was <old>%)
```

## Pending file format

Plain markdown, one file per session. Each item is an H2 for the type plus metadata fields and a body. See `templates/PENDING-FILE-TEMPLATE.md`.

```markdown
# Pending updates - 2026-04-15-0900-ab12

## rule
**target:** docs/strategy/WRITING-RULES.md
**confidence:** high

Never use em dashes in copy.
```

Valid types: `rule`, `fact`, `decision`, `correction`. Valid confidence: `high`, `medium`, `low`.

## Error cases

- No CLAUDE.md → tell user to run `/ProjectNewSetup`.
- Dirty git working tree → abort per Step 2.
- CLI unavailable → you can still stage to `docs/.pending/`, but do NOT attempt a merge without the CLI. Conflict detection is the safety net.
- All items have validation issues → don't proceed; report them and ask the user whether to fix the source or drop those items.
- No git initialised → stage files and skip commit steps. Tell the user at the end so they can `git init` if they want history.
- Stale pending files piling up → suggest `brain pending archive --days 14` to sweep abandoned pending into `docs/.pending/archive/` without deleting.
