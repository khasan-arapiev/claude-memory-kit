# Changelog

All notable changes to Project Brain. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
