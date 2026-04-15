# Changelog

All notable changes to Project Brain. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
