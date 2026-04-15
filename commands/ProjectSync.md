---
description: One-stop brain sync — extracts insights, stages them, merges when safe, refuses when unsafe. Replaces /ProjectSave, /ProjectMerge, /ProjectUpdate.
---

You are running the `ProjectSync` command from the `project-brain` skill.

## Your job

Bring the project brain up to date in one command. You handle the judgment half (what from this conversation is worth saving); the CLI handles the state half (git state, session id, pending files, conflicts, safe-to-proceed). Trust `brain sync preflight` — don't reimplement its checks in prose.

## Flags the user can pass

- `--dry-run` — print every write and commit that *would* happen; touch nothing on disk or in git. See the **Dry-run contract** section below for exactly which steps are skipped.
- `--include-wip` — proceed even if the git working tree has uncommitted or untracked changes. Only in-progress git operations (merge/rebase/cherry-pick/bisect) remain blockers — those represent broken states and would corrupt history if the Sync writes on top.

## Dry-run contract (single source of truth)

When the user passes `--dry-run`, preflight echoes `dry_run: true` in its JSON. Every write-shaped step below is **skipped**; only plan output and CLI reads run. Specifically:

- Step 6.1 (stage pending file) — **skipped**.
- Step 6.4 (Edit / create target files / update CLAUDE.md routing) — **skipped**; print what *would* be edited.
- Step 6.5 (commit each target) — **skipped**; print the intended commit message.
- Step 6.6 (delete pending, commit clear) — **skipped**.
- Step 7 (append to `rejected-*.md` via `brain pending reject`) — **skipped**; print the intended args.
- Step 6.7 (`brain audit` re-run) — **runs** (read-only).

At the end of a dry run, print: *"Dry run complete. No files or commits touched. Re-run without `--dry-run` to apply."*

## Required references

- `~/.claude/skills/project-brain/references/extraction-rubric.md` — what to save vs ignore
- `~/.claude/skills/project-brain/references/quality-rules.md` — naming, size caps, self-growing schema
- `~/.claude/skills/project-brain/templates/ADR-TEMPLATE.md` — for new decision items

## Step 1 — Verify project-brain managed

Check current directory for `CLAUDE.md` with `<!-- project-brain: managed -->`. If absent, abort:

> Not a project-brain managed project. Run `/ProjectNewSetup` first.

## Step 2 — Run preflight

One CLI call gives you session id, git state, and the sync plan:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" sync preflight "$(pwd)" --json \
  ${INCLUDE_WIP:+--include-wip} ${DRY_RUN:+--dry-run}
```

The JSON has:
- `ok` — true when it's safe to proceed.
- `session_id` — use this for the rest of the run. Do NOT generate your own.
- `dry_run` — echo of the flag so re-reads of the payload know the mode.
- `git.{initialised, clean, branch, detached, unborn, operation_in_progress, dirty_paths, untracked_paths}`
- `plan.{mode, pending_total, stale_pending_count, conflicts, ...}` — full `sync_plan` output.
- `blockers[]` — structured `{code, message, remedy}` per blocker.

If `ok: false`, print each blocker AND its `remedy` string to the user. The remedy tells them exactly what to do (e.g. `git stash` / `--include-wip` / abort the merge). Do not try to edit files to "work around" a blocker.

If `git.initialised: false`, `ok` can still be true — you'll stage files and skip commit steps later. Tell the user at the end so they can `git init` if they want history.

## Step 3 — Surface stale pending files

If `plan.stale_pending_count > 0`, tell the user once (before extracting) and offer to archive:

> `N` pending file(s) are older than 14 days. These often block `/ProjectSync` as `merge_first` forever. Archive them? (y/n)

If the user says **yes**: run `brain pending archive "$(pwd)" --days 14`. Then refresh the plan — but NOT the full preflight, because that would mint a new session id. Run only:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" sync plan "$(pwd)" --session-id "$session_id" --json
```

and use the new `plan.mode` for Step 4. Keep the original `session_id` from Step 2.

If the user says **no**: proceed with the existing plan (it will most likely be `merge_first`). The Step 4 `merge_first` branch explains what happens next.

## Step 4 — Act on the plan mode

`plan.mode` is one of four values:

| Mode | Meaning | What you do |
|---|---|---|
| `empty` | Nothing staged anywhere | Extract insights. If none, stop. Otherwise stage → merge (Step 6). |
| `quick` | Only this session is staged, zero conflicts | Extract insights (they add to whatever's already staged). Stage → merge. |
| `merge_first` | Other sessions have staged items | Extract and stage this session's insights only. **Do not merge.** |
| `resolve_conflicts` | Pending items contradict each other | Present conflicts (Step 7). Apply user's decisions. Then merge. |

Trust the CLI. Do not recount pending files yourself.

## Step 5 — Extract insights from this session

Apply `extraction-rubric.md` to the whole conversation. For each keeper, classify:

- `rule` — reusable guidance ("always", "never", "must")
- `fact` — concrete data (name, path, id, url, number)
- `decision` — a chosen approach with reasoning
- `correction` — "that earlier assumption was wrong; here's the right one"

Skip: conversation narrative, ephemeral state, anything already in the code or docs (spot-check with `brain query`), raw credential values, vague impressions.

Pick a `target:` per item:
- `brain query "<topic>"` to find the closest existing doc section.
- If nothing fits and it's a `decision`, propose `docs/decisions/{{date}}-KEBAB-TITLE.md`.
- Otherwise new file under `docs/strategy/`, `docs/reference/`, `docs/workflows/`, or `docs/context/`.

**Placeholder validation.** Valid: `{{date}}`, `{{project-slug}}`, `{{slug}}`. Anything else — including single-brace typos like `{date}` — will be flagged by the CLI. Fix before proceeding.

**Batch cap.** > 50 items extracted is unusual — ask the user whether to save all or cap at 20.

**Dedup cost cap.** Don't `brain query` every candidate. One query per distinct topic, reuse results.

## Step 6 — Stage or apply based on mode

### Mode: `merge_first`

Write items to `docs/.pending/${session_id}.md` using `templates/PENDING-FILE-TEMPLATE.md`. Do not apply them. Verify:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" pending list "$(pwd)" --json
```

Items from this session should have empty `issues`. Fix any flagged ones before finishing. Report:

```
Staged <N> insights to docs/.pending/${session_id}.md
Other sessions have <M> pending items I won't touch:
  - <session-id>: <N items across N targets>
Run /ProjectSync again once those are reviewed and merged.
```

Then stop.

### Mode: `empty`, `quick`, or `resolve_conflicts` (after conflicts resolved)

Full merge pipeline. Dry-run skip rules are defined once up front in the **Dry-run contract** section — follow those instead of scattered per-step caveats.

1. **Stage** — write `docs/.pending/${session_id}.md` with this session's items (if any).
2. **Pull full item set**: `brain pending list "$(pwd)" --json`.
3. **Group by target**, dedup identical bodies, surface paraphrase/semantic clashes to the user.
4. **For each target**:
   - Existing file: `brain query "<topic>"` → find the right section → Edit append/update.
   - Missing file: create it. Add a routing entry to `CLAUDE.md` (respect the 3000-token cap from `quality-rules.md`).
   - Missing ADR: use `ADR-TEMPLATE.md`; filename `YYYY-MM-DD-KEBAB-TITLE.md` under `docs/decisions/`.
5. **Commit each target**: `sync: <type> -> <relative-path>`.
6. **Delete ONLY the current session's pending file** once all its items have been applied:
   ```bash
   rm "docs/.pending/${session_id}.md"
   git rm "docs/.pending/${session_id}.md" 2>/dev/null
   ```
   Do NOT touch other sessions' pending files. Commit: `sync: clear pending ${session_id}`.
7. **Re-audit** (always runs): `brain audit "$(pwd)"` — include health score delta in the final report.

## Step 7 — Conflict resolution prompt

The CLI reports contradictions deterministically. Present each in a consistent format:

```
Conflict 1 of N — <target path>
  Type: <decision|rule|correction>

  [A] <item-id>
      <first 200 chars of body>

  [B] <item-id>
      <first 200 chars of body>

Pick: A, B, both, or skip.
```

- **A / B** — apply the chosen item, drop the other. Persist the losing item's full body (see below).
- **both** — apply both (only valid when you can see they're complementary, not contradictory).
- **skip** — defer both; they stay in pending for a future `/ProjectSync`.

### Losing items must not be silently lost

ADR targets have an "Alternatives considered" section — put the loser there in full.

For **non-ADR targets** (rules, corrections), the pending file will be deleted in Step 6.6, and a truncated commit message is not a safe home for the loser. Use the deterministic CLI helper — it appends to `docs/.pending/archive/rejected-${session_id}.md` with a consistent header format and exits non-zero on failure, so the loser is guaranteed persisted before you move on:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" pending reject "$(pwd)" \
  --session-id "$session_id" \
  --type "<rule|fact|decision|correction>" \
  --target "<target path>" \
  --winner-id "<winning item id>" \
  --body "$(cat <<'EOF'
<full loser body here, multi-line supported>
EOF
)"
```

Call this once per rejected loser, BEFORE Step 6.6 deletes the session's pending file. Under `--dry-run` skip the call and print the intended args instead.

The archive file is committed alongside the sync: `sync: archive rejected -> docs/.pending/archive/rejected-${session_id}.md`.

## Step 8 — Report

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
  × <rej> rejected alternative(s) archived
Cleared pending: ${session_id}
Brain health: <new>% (was <old>%)
```

## Pending file format

See `templates/PENDING-FILE-TEMPLATE.md`. Plain markdown, one file per session, H2 per item.

## Error cases

- No CLAUDE.md → tell user to run `/ProjectNewSetup`.
- Preflight reports blockers → print them, stop. User re-runs after resolving, or adds `--include-wip` if the blocker is intentional dirty work.
- CLI unavailable → you can still stage to `docs/.pending/`, but do NOT attempt a merge. Conflict detection is the safety net.
- All items have validation issues → don't proceed; ask whether to fix the source or drop those items.
- `plan.stale_pending_count > 0` → offer `brain pending archive --days 14` (Step 3).
