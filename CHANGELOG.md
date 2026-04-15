# Changelog

All notable changes to Project Brain. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.3.0] — 2026-04-15

Third independent review cycle surfaced 16 items. All fixed. Theme: turning the remaining prose-only promises into CLI-enforced behaviour, plus the structural cleanup the prior cycles deferred.

### Added — CLI enforcement for the last prose promises

- **`brain pending reject`** — deterministic CLI helper that appends a rejected conflict-loser to `docs/.pending/archive/rejected-<session>.md`. `/ProjectSync` Step 7 now calls this instead of asking Claude to hand-write the file. Closes the "rejected-loser persistence is prose-only" gap from cycle 3.
- **`brain sync preflight --dry-run`** echoes `dry_run: true` in the output, so the slash command can detect dry-run mode on any re-read of the payload. Dry-run behaviour is now specified once up front in `ProjectSync.md` (Dry-run contract section) instead of scattered per-step caveats.
- **`--include-wip` now covers untracked files too** (not just dirty working tree). First-time runs in a repo with any new file no longer dead-end.
- **Structured blockers** — preflight returns `[{code, message, remedy}]` instead of plain strings. `/ProjectSync` prints the `remedy` to the user so they know exactly what to do.

### Added — git inspection improvements

- **Detached HEAD, unborn branch, and "branch named HEAD"** now reliably distinguishable via `symbolic-ref -q HEAD` (was indistinguishable under `rev-parse --abbrev-ref HEAD`). New fields: `git.detached: bool`, `git.unborn: bool`.
- `git.py` split out of `sync.py` — ~100 lines of subprocess logic lives on its own now.

### Added — race-safe archive

- `archive_old` uses `os.link` → `os.unlink` (atomic on POSIX + Windows) with `FileExistsError` retry instead of the old check-then-rename. Race between two concurrent sweeps is now safe: the loser just gets the next `.N` suffix.
- Dry-run collision reporting fixed: simulates the suffix bump so two stale files with identical basenames don't both report the same target.

### Added — Stop hook hardening

- Hook now only nudges when the session made commits that *actually touched `docs/` or `CLAUDE.md`*. Unrelated commits (feature work, typo fixes) no longer trigger the prompt — kills the "banner-blind" problem.
- Install path overridable via `BRAIN_SKILL_DIR` env var (was hardcoded to `~/.claude/skills/project-brain`).

### Added — tests

- 95 total (was 80). New coverage: `inspect_git` on detached HEAD / unborn branch / untracked files; `append_rejected` first call + subsequent appends + missing session-id; atomic archive collision preserves both payloads; preflight `dry_run` echo; `include_wip` covering untracked; `frontmatter.parse_file` on actual CRLF bytes (closes the "CRLF fix unverified" finding from cycle 3).
- New test files: `tests/test_git.py`, `tests/test_crlf.py`.

### Removed — back-compat shims

- `pending.archive_old` forwarder deleted. Import from `brain.archive` instead.
- `sync.new_session_id` re-export deleted. Import from `brain.session` instead.

Pre-release software, no external consumers — the shims were dead weight hiding the real imports.

### Changed — module layout

```
cli/brain/
  __init__.py, audit.py, cli.py, decisions.py, drift.py, frontmatter.py,
  project.py, query.py,
  # new in 0.3:
  archive.py    # lifecycle (archive_old, append_rejected)
  git.py        # subprocess wrapping (inspect, GitState)
  pending.py    # parse + conflicts + render
  session.py    # new_session_id only
  sync.py       # SyncPlan, sync_plan, Preflight, preflight, rendering
```

### Fixed — small polish

- `_cmd_sync_new_id` now `@_guard`-wrapped for consistency with every other handler.
- `sync_plan` no longer walks the pending dir twice (stale count now inline, single pass).
- `cli.py` `import json` moved to the top-of-module stdlib group.
- Dead `_read_claude_md` helper removed; `detect()` uses `read_md` directly.
- `SKILL.md:88` + `README.md:125` referenced the retired `PENDING-FILE-TEMPLATE.yaml`. Fixed.
- Redundant "asdict handles nesting" comments consolidated.

### Minor version bump

v0.3.0 instead of v0.2.3 because the back-compat-shim removal is technically a breaking change for anyone who imported from the old module paths (no external consumers exist, but the versioning should reflect reality).

## [0.2.2] — 2026-04-15

Second independent review cycle surfaced 14 more items. This patch ships all of them. Focus: moving enforcement out of prose and into the CLI, so the v0.2.1 safety claims actually hold.

### Added — `brain sync preflight`

One CLI call returns `session_id`, full git state (including untracked files and in-progress operations), the sync plan, and a pass/fail with blocker list. `/ProjectSync` Step 2 now calls this instead of reimplementing a partial git check in bash. Moves the safety policy out of the slash command and into Python.

- Detects merge / rebase / cherry-pick / bisect in progress (was missed in 0.2.1's `git diff --quiet`).
- Detects untracked files (was missed).
- Surfaces current branch.
- Optional `--include-wip` downgrades "dirty working tree" from blocker to warning for users with intentional WIP. Untracked files and in-progress ops remain blockers.

### Added — archive lifecycle

- **`brain sync plan` now includes `stale_pending_count`** so `/ProjectSync` can surface `brain pending archive --days 14` when the user hits `merge_first` because of old forgotten sessions (not their own).
- **Archive collision safety.** `archive_old` now appends `.1`, `.2`, ... suffixes when the archive file already exists. Previously raised `FileExistsError` on Windows and silently overwrote on POSIX.
- **Test fixture** covers the collision path.

### Added — `brain sync plan --inspect`

`--session-id` is now required for action-taking callers. `--inspect` exists for read-only human shell inspection (emits a session-agnostic snapshot). Prevents the "forgot to pass session_id → CLI recommends `quick` → wrong session's items get merged" failure mode.

### Added — non-ADR conflict persistence

Losing items in rule/correction conflicts used to be dropped entirely (ADR winners got an "Alternatives considered" home; non-ADR winners did not). `/ProjectSync` now appends full losing bodies to `docs/.pending/archive/rejected-${session_id}.md` before deleting the pending file, so rejected knowledge is recoverable.

### Fixed — CRLF was half-a-fix in 0.2.1

`frontmatter.parse_file` bypassed `read_md`, so the CRLF normalisation didn't actually reach decisions or drift. Both now route through `read_md`, and the redundant inner `_read_claude_md` was removed.

### Fixed — `--dry-run` was under-specified in 0.2.1

ProjectSync.md Step 6.1 said "Stage first (all modes)" without a dry-run escape. Every write step in the new Step 6 now has an explicit "skip under `--dry-run`" clause, plus a closing summary that reminds the user no files or commits were touched.

### Fixed — Stop hook cross-platform

The v0.2.1 one-liner (nested `python -c` inside bash inside JSON) broke on PowerShell. Stop hook now ships as a proper Python script at `hooks/stop-prompt.py` — same on every OS.

### Changed — module boundaries

- **`new_session_id` moved from `sync.py` to a new `session.py`** (it has nothing to do with planning). Re-exported from `sync` for back-compat.
- **`archive_old` moved from `pending.py` to a new `archive.py`** (filesystem lifecycle, not parse logic). Back-compat re-exported via `pending.archive_old`.
- **`_stage_pending` / `clone_clean` / `minimal_item`** extracted to `tests/_helpers.py`. Every test file now uses them instead of inlining setup.

### Fixed — consistency

- All CLI errors (human and `--json`) now emit to **stderr**. Stdout is reserved for pipeable payloads.
- `_cmd_pending_archive` and `_cmd_sync_new_id` use the top-level `json` import instead of local `import json as _json`.
- `read_md` narrowed to catch only `OSError` (was `OSError | ValueError`). Programmer errors now bubble up as tracebacks, matching the new `_guard` philosophy in 0.2.1.
- Unused `datetime` / `timedelta` imports removed.

### Added — tests

- 80 total (73 → 80). New coverage:
  - `preflight` returns a plan on clean fixtures.
  - `preflight` on missing project returns None.
  - `inspect_git` detects absence of git cleanly.
  - `sync plan` `--inspect` works; missing both `--session-id` and `--inspect` exits 2 via argparse.
  - `archive_old` collision uses `.N` suffix and preserves prior archive.
  - All test files share `tests/_helpers.py`.

## [0.2.1] — 2026-04-15

Triple independent code review found 20+ issues in v0.2.0. This patch ships all of them.

### Fixed — correctness

- **`detect_conflicts` hid real conflicts** when either side had a body issue (empty body, bad confidence). Now only excludes items whose *target* is unusable; body-issue items still participate in conflict detection so contradictions can't slip past validation noise.
- **`sync_plan` with empty `session_id` always returned `merge_first`** when any pending existed. Now: no session means "session-agnostic" — single-session pending → `quick`, multi-session → `merge_first`.
- **Single-brace placeholder typos** (`{date}` vs `{{date}}`) silently passed; now flagged as validation issues with a "did you mean…?" hint.
- **Audit decisions exemption was too wide** — any folder named `decisions/` anywhere under the project was exempted from orphan checks. Now scoped to top-level `docs/decisions/` only.
- **`read_md` CRLF handling** — Windows-authored docs read on Linux/macOS broke the frontmatter and chunk-split regexes. `read_md` now normalises `\r\n` → `\n` on read.
- **`__version__`** still said `0.1.0` (the bump in 0.2.0 was missed). `brain --version` now reports the real version.

### Fixed — safety

- **Git working-tree check in `/ProjectSync`.** The command now aborts (with a helpful message) if there are uncommitted changes, so brain commits stay atomic and don't pull in unrelated work.
- **Pending-file deletion scoped to current session.** The old spec told Claude to "delete pending files whose items have all been applied" — which could wipe another session's file mid-review. Now `/ProjectSync` only deletes `${session_id}.md`.
- **`empty`-mode lifecycle specified.** Every merge, even from an empty state, goes through a pending file first as the audit trail.
- **Non-ADR conflict resolution specified.** Losing items on ADR targets go into "Alternatives considered"; on rule/correction targets they are dropped and the rationale goes into the commit message.
- **`_guard` no longer catches `ValueError`.** Programmer errors now produce a traceback instead of a misleading "IO error" message.

### Added — CLI

- **`brain sync new-session-id`** — emit a fresh session id from stdlib Python. Replaces the old shell snippet that used `/dev/urandom`, `base64`, and `md5sum` (broken on macOS).
- **`brain pending archive --days N`** — move stale pending files older than `N` days into `docs/.pending/archive/`. Supports `--dry-run`. Fixes the case where forgotten pending files block every future `/ProjectSync` as `merge_first` forever.
- **`brain pending list` exit code** now non-zero when any item has validation issues (was zero if no conflicts — CI couldn't catch bad items).
- **`/ProjectSync --dry-run`** flag — preview every step without writing files or making commits.

### Added — docs

- **`templates/PENDING-FILE-TEMPLATE.yaml` → `.md`** — the template was renamed to match the actual markdown format. `extraction-rubric.md` reference updated accordingly.
- **Token-based caps replace line counts in user-facing docs.** README and `quality-rules.md` stated the 200-line / 500-line caps that v0.1.0 replaced with 3000 / 7500 tokens. Docs now match the code.
- **Stop hook redesigned.** The v0.2.0 hook checked `git diff --name-only HEAD` — always empty right after `/ProjectSync` committed, so the prompt never fired. New hook checks pending count + recent `sync:` commits. A simpler-but-noisier alternative is also documented.

### Added — tests

- 21 new tests (52 → 73 total):
  - Empty-session-id regression (both single and multi-session pending).
  - Placeholder validator (known, unknown double-brace, single-brace typo).
  - Conflict detection with body-issue sibling (regression).
  - `brain pending archive` (real move + dry-run).
  - `new_session_id` format and uniqueness.
  - CLI smoke tests covering all subcommands' exit codes.
  - `_guard` does not swallow `ValueError`.
  - Exact audit score on broken fixture (30/100), not just "under 50".

### Deferred (explicit)

- **Extract `render_human` / `render_json` into `render.py`.** Each module's renderer takes different args — a shared module would be ~200 lines of dispatch for zero behaviour change. Kept inline.
- **Split `pending.py` into parse + conflicts + archive.** Current file is 330 lines and cohesive enough. Splitting would add import churn without meaningful clarity.

## [0.2.0] — 2026-04-15

Unified workflow + safety hardening.

### Changed — one sync command replaces three

- `/ProjectSave`, `/ProjectMerge`, `/ProjectUpdate` removed. Replaced by `/ProjectSync`, which asks the CLI (`brain sync plan`) which of four modes applies — `empty`, `quick`, `merge_first`, `resolve_conflicts` — and acts accordingly. Users can no longer pick the wrong command.
- New CLI subcommand `brain sync plan --session-id <id>`: deterministic state inspection, returns JSON with pending counts, per-session breakdown, conflicts, and a recommended mode.

### Added — safety & validation

- Widened conflict detection in `brain pending list`: now flags `rule`, `decision`, and `correction` items at the same target with different bodies (was decisions-only). `fact` items still stack because they are usually additive.
- Pending items with unknown `{{placeholder}}` tokens in their `target:` field are now flagged as validation issues. Known placeholders: `{{date}}`, `{{project-slug}}`, `{{slug}}`.
- Frontmatter parser validates known enum fields (`status`, `confidence`). Typos surface as warnings instead of silently passing.
- IO-error guards on every CLI entry point (exit code `3` on unhandled `OSError` / `ValueError`). A locked or unreadable file no longer crashes a whole-project audit.
- Stricter orphan detection: the decisions folder must have an explicit route (e.g. `[Decisions](docs/decisions/)`, backticked path) — not a prose mention of the word "decisions".

### Added — efficiency

- Query chunks pre-compute tokens and whitespace-compacted bodies at chunk time. `brain query` no longer re-tokenizes the same chunk on every run and snippet building no longer collapses whitespace per call.
- Shared `read_md` helper replaces eight copies of the `encoding="utf-8", errors="replace"` boilerplate and handles IO errors centrally.

### Added — hooks

- `references/hooks.md` rewritten with two opt-in hook blocks: `SessionStart` (auto-run `brain audit` + `brain drift` in managed projects) and `Stop` (prompt `/ProjectSync` when brain docs were touched this turn).

### Added — tests

- 4 new tests for `brain sync plan` covering all four modes.
- Test fixtures for `.pending/` are now tracked in git (previously gitignored, which broke a fresh clone's test run).

### Fixed

- `.gitignore` previously excluded `tests/fixtures/**/.pending/` along with runtime `.pending/` dirs. Split the pattern so runtime is still ignored but fixtures ship with the repo.

## [0.1.0] — 2026-04-14 (MVP)

First public-ready release. Validated end-to-end against a real project (test2/Habitloop) with full create → save → merge → audit → query → drift → conflict resolution cycle.

### Added — slash commands (5)

- `/ProjectNewSetup` — scaffold a new project with full structure, type-aware stubs, and Security config
- `/ProjectSetupFix` — audit and fix orphans, dead links, naming, oversize files; reports brain health
- `/ProjectSave` — capture session insights into `docs/.pending/` (plain markdown, not YAML)
- `/ProjectMerge` — apply pending items to real docs, resolve conflicts, auto-grow new files
- `/ProjectUpdate` — solo-chat shortcut: save + merge in one step

### Added — deterministic CLI (`brain`)

- `brain audit` — token-aware health score with orphan / dead-link / naming / size checks
- `brain drift` — flag docs whose described code has changed since last sync (mtime-based)
- `brain decisions list` / `search` — index and search the project's ADR ledger with supersede chains
- `brain query` — TF-IDF retrieval over CLAUDE.md + docs/, with H2-section chunking and heading-match boost
- `brain pending list` — enumerate `docs/.pending/` items; emits both `items` and `conflicts` arrays
- Conflict detection (v1): flags 2+ `decision` items targeting the same file with different bodies

### Added — infrastructure

- Stdlib-only Python 3.10+ package (zero dependencies)
- 48 unit tests covering audit, drift, decisions, query ranking, pending parsing, conflict detection, frontmatter
- Test fixtures: `clean`, `broken`, `drifted`, `decisions`, `pending`, `searchable`
- Cross-platform installer (`install.sh` for macOS/Linux, `install.ps1` for Windows)
- Installer self-tests on install
- Token-aware size budgets (3000 / 7500 tokens) replace prior line-count caps
- ADR-format naming exemption (`YYYY-MM-DD-TITLE.md` under `decisions/`)
- ADR orphan exemption (decisions are indexed via `brain decisions`, not per-file CLAUDE.md routes)
- UTF-8 stdout on Windows (no more `cp1252` crashes on `…`)

### Added — content & docs

- Project-type templates: `WEBSITE`, `SAAS`, `ECOMMERCE`, `CLIENT-WORK`, `TOOL`
- `ADR-TEMPLATE.md` updated to use frontmatter (`status`, `topics`, `supersedes`)
- `README.md` with one-line install, command table, philosophy
- `cli/README.md` with full subcommand reference
- `tests/README.md` with run instructions and fixture conventions
- `LICENSE` (MIT)
- `CONTRIBUTING.md` with test + commit conventions
- This `CHANGELOG.md`

### Known limitations

- `brain query` uses TF-IDF, not semantic embeddings — vocabulary mismatches happen ("Sentry" vs "error monitoring")
- `brain drift` is mtime-based, not diff-aware — whitespace edits trigger false drift
- Conflict detection covers `decision` items only; semantic conflicts in rules/facts still need Claude
- SessionEnd auto-save hook is documented (`references/hooks.md`) but not auto-installed

### Roadmap (post-MVP)

- `brain impact <file>` — dependency blast radius via language-aware parsing
- `brain init` — replace `/ProjectNewSetup` prose with deterministic CLI scaffold
- Synonym table or pluggable embeddings for `brain query`
- Diff-aware drift detection
- One-command SessionEnd hook installer
