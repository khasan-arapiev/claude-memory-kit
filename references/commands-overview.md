# Commands Overview

Three slash commands implement the project-brain system. Each lives in `~/.claude/commands/` as its own `.md` file.

## Quick reference

| Command | When to use | Writes where | Multi-chat safe |
|---|---|---|---|
| `ProjectNewSetup` | Brand new project from nothing | Creates whole project skeleton | N/A |
| `ProjectSetupFix` | Audit existing project structure | Fixes existing files in place | N/A |
| `ProjectSync` | Any time insights from this chat should enter the brain | `docs/.pending/` or `docs/` (real files) depending on state | Yes |

`ProjectSync` replaces the 0.1.x trio of `ProjectSave` / `ProjectMerge` / `ProjectUpdate`. It reads pending state from the CLI (`brain sync plan`) and automatically picks the right action — stage only (other sessions present), quick-merge (solo + no conflicts), or stop-and-ask (conflicts detected).

## Detailed behavior

### `ProjectNewSetup`

**Inputs from user:**
- Router level or project level?
- (If project) Project type: website, saas, ecommerce, client-work, tool, other
- Project name and slug
- One-paragraph description

**Steps:**
1. Walk up directory tree to find workspace root (folder containing `Security/`)
2. Create folder structure (`docs/`, `project/`, `assets/`, `tools/`, plus type-specific extras)
3. Create `CLAUDE.md` from template, populated with all known fields
4. Create `Security/<project-slug>.json` from template (empty values)
5. If workspace root has no `.gitignore`, add it from `GITIGNORE-TEMPLATE`
6. Inherit writing rules from parent `CLAUDE.md` if present
7. Commit scaffold as one atomic git commit

### `ProjectSetupFix`

**Inputs from user:** None (auto-detects level)

**Steps:**
1. Detect level: scan for `docs/` and `project/` (project level) or only sub-folders with CLAUDE.md (router level)
2. Run all quality checks from `quality-rules.md`:
   - Orphan scan (decisions folder requires an explicit route, not a prose mention)
   - Dead-link scan
   - Naming convention scan
   - CLAUDE.md size check
   - Individual doc size check
   - Sensitive files section check
   - Writing rules section check
3. At workspace root: check for monolithic `Security/configs.json`, propose splitting
4. At any router level: scan sibling projects for duplicate rules, propose lifting
5. For each issue, prompt user (or auto-fix if non-destructive)
6. Each fix is its own atomic commit
7. Report brain health score

### `ProjectSync`

**Inputs from user:** Conflict resolutions only (when the CLI reports contradictions).

**Steps:**
1. Verify `CLAUDE.md` has the `<!-- project-brain: managed -->` marker.
2. Generate a session id (`YYYY-MM-DD-HHMM-<rand>`).
3. Call `brain sync plan --session-id <id> --json`. The CLI returns one of four modes:
   - `empty` — nothing staged; extract insights, stage, and merge.
   - `quick` — only this session is staged; safe to merge in one shot.
   - `merge_first` — other sessions have staged items; stage this session's insights but do not merge. Surface the other sessions to the user.
   - `resolve_conflicts` — contradictions detected; present them, get user decisions, then continue to merge.
4. Apply the extraction rubric (`extraction-rubric.md`) to the conversation. Classify each keeper as `rule` / `fact` / `decision` / `correction`.
5. Write a pending file when mode is `merge_first` (or as an intermediate step in the other modes). Verify via `brain pending list` that every item parses with empty `issues`.
6. For modes that merge: group by target, dedup, resolve paraphrase/semantic conflicts with the user, apply via Edit tool, update `CLAUDE.md` routing, commit each target atomically.
7. Delete merged pending files. Run `brain audit` and report the health delta.

### Mode decision in one line

> If any conflicts → stop and ask. Else if other sessions staged → stage only, do not merge. Else merge everything, including this session's new items.

The CLI enforces this deterministically — the slash command does not recount pending files.

## Session-start behavior

When any new chat starts in a folder containing a project-brain managed CLAUDE.md (detected by the `<!-- project-brain: managed -->` marker):

1. Read CLAUDE.md.
2. Validate routing entries point to existing files.
3. Read `docs/.pending/` to count pending updates.
4. Output one line: `Brain loaded: X docs, Y pending. Ready.`
5. If `Y > 0`, prompt: `N pending updates from previous sessions. Run /ProjectSync? (y/n)`

This is implemented inside each command file's preamble, so any command run in a managed project triggers the check. The optional `SessionStart` hook in `references/hooks.md` also runs `brain audit` to surface drift and orphans immediately.

## Hook integration

Two optional hooks make the skill feel ambient without surrendering safety:

- **SessionStart** — auto-run `brain audit` + `brain drift`.
- **Stop** — prompt (not auto-run) `/ProjectSync` when brain docs were touched this turn.

See `references/hooks.md` for install snippets.
