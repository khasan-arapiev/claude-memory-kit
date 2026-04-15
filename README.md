# Project Brain — A Living Documentation System for Claude Code

**Keep every Claude Code chat context-aware, without ever re-explaining your project.**

Project Brain is a Claude Code skill that turns any project folder into a self-maintaining knowledge base. It scaffolds your docs, keeps `CLAUDE.md` lean, auto-routes new information, and evolves across sessions so Claude always knows your project — without bloating context or losing decisions.

> Built for solo founders, agencies, and teams who want Claude Code to feel like a long-term collaborator, not a forgetful assistant.

**Status:** v0.2.2. Validated end-to-end against a real project. 80 tests passing. See [CHANGELOG.md](CHANGELOG.md) for what's shipped and [the bottom of this README](#status--known-limitations) for honest known limitations.

---

## Why Project Brain

Large projects die a slow death in `CLAUDE.md`. It balloons past 500 lines, every chat re-reads the same stale context, and new learnings get lost between sessions. Project Brain fixes this with one opinionated pattern:

- **`CLAUDE.md` is a router**, not a dumping ground. Hard cap: 3000 tokens (≈200 lines of dense prose).
- **Details live in `docs/`**, split by purpose and auto-linked from the router.
- **Insights save automatically** at session end into a `.pending/` staging area.
- **Merges are safe for parallel chats** — no overwrites, no conflicts.
- **Credentials stay in one place** — workspace-root `Security/`, never scattered.

The result: every new Claude chat starts with a complete, current picture of your project. Nothing is re-explained. Nothing is lost.

---

## The 3 Commands

| Command | What it does | When to use |
|---|---|---|
| `/ProjectNewSetup` | Scaffolds folder structure, `CLAUDE.md`, Security config from scratch | Starting a brand-new project |
| `/ProjectSetupFix` | Audits docs, fixes orphans, broken routes, oversize files, reports brain health score | Cleaning up or onboarding an existing project |
| `/ProjectSync` | Extracts session insights, stages them, merges when safe, surfaces conflicts when not | Any time — replaces the old Save / Merge / Update trio |

The unified `/ProjectSync` reads the current pending state from the CLI (`brain sync plan`) and picks the right action automatically: stage-only when other sessions have unmerged items, quick-merge when you're solo, stop-and-ask when items conflict. You can't pick the wrong command because there's only one.

---

## How it Works

```
your work → /ProjectSync → (stage if other sessions pending) → docs/.pending/
                        → (merge when safe)                  → real docs + auto-wired CLAUDE.md
```

Each project has three physically separated layers sharing one brain:

| Layer | Purpose | Folder | Deployed |
|---|---|---|---|
| **Brain** | Context, rules, decisions | `CLAUDE.md` + `docs/` | Never |
| **Project** | The actual deliverable | `project/` + `assets/` | Yes |
| **Tools** | Dev tools, tests, scripts | `tools/` | Never |

Small single-project folders can use a **flat layout** instead (just `.md` files at root). Both styles are supported — `/ProjectSetupFix` detects which you have.

---

## Installation

Requires [Claude Code](https://claude.com/claude-code) and Python 3.10+.

### One-line install

**macOS / Linux:**
```bash
git clone https://github.com/khasan-arapiev/project-brain.git
cd project-brain && ./install.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/khasan-arapiev/project-brain.git
cd project-brain; .\install.ps1
```

The installer:
- Verifies Python 3.10+
- Copies the skill to `~/.claude/skills/project-brain/`
- Copies the 3 slash commands to `~/.claude/commands/`
- Runs the test suite (80 tests, stdlib only)
- Prints next steps

Re-run any time to upgrade. The script is idempotent.

### Manual install (if you don't trust scripts)

Copy `.` to `~/.claude/skills/project-brain/` and `commands/Project*.md` to `~/.claude/commands/`. That's it.

### After install

1. Restart Claude Code (so it picks up the new skill + commands)
2. `cd` into any project folder
3. Type `/ProjectNewSetup` (for a new project) or `/ProjectSetupFix` (to audit an existing one)

### (Optional) Hooks

See `references/hooks.md` for two recommended hooks:
- **SessionStart** — auto-run `brain audit` + `brain drift` so you see project health the moment a session opens.
- **Stop** — if the session touched brain docs, prompt (not auto-run) `/ProjectSync`.

---

## Folder Layout of this Repo

```
.
├── SKILL.md                      Skill entrypoint (Claude reads this)
├── commands/                     The 3 slash commands
│   ├── ProjectNewSetup.md
│   ├── ProjectSetupFix.md
│   └── ProjectSync.md
├── cli/                          Deterministic tooling (Python 3.10+ stdlib)
│   ├── run.py                    Standalone runner: python run.py audit <path>
│   ├── brain/                    Package: brain.audit, brain.project, brain.cli
│   └── README.md                 CLI reference
├── references/                   Rules and behavior specs
│   ├── commands-overview.md
│   ├── extraction-rubric.md      What gets saved vs ignored
│   ├── quality-rules.md          Naming, size caps, health scoring
│   └── hooks.md                  Auto-save hook setup
└── templates/                    Skeletons used by commands
    ├── CLAUDE-MD-TEMPLATE.md
    ├── CLAUDE-MD-ROUTER-TEMPLATE.md
    ├── ADR-TEMPLATE.md
    ├── PENDING-FILE-TEMPLATE.yaml
    ├── SECURITY-CONFIG-TEMPLATE.json
    ├── README-TEMPLATE.md
    ├── GITIGNORE-TEMPLATE
    └── project-types/            Type-specific extras (saas, website, ecommerce, ...)
```

## Deterministic CLI

Slash commands used to count orphans and score health in prose, which costs tokens and produces variable results. They now call a zero-dependency Python CLI that emits JSON:

```bash
python cli/run.py audit              /path/to/project --json
python cli/run.py drift              /path/to/project --json
python cli/run.py decisions list     /path/to/project
python cli/run.py decisions search "css framework" /path/to/project
python cli/run.py query "FTP password" /path/to/project --top 3
python cli/run.py pending list       /path/to/project --json
python cli/run.py sync plan          /path/to/project --session-id <id> --json
```

**Users never call these directly.** Slash commands invoke the CLI under the hood — same as how Claude already calls Bash for git or file operations. The CLI is the engine; slash commands are the steering wheel.

**Test suite:** `python -m unittest discover tests -v` (80 tests, all stdlib).

See `cli/README.md` for the full CLI reference. Planned: `brain impact`, `brain init`.

---

## Core Principles

1. **Zero headache.** You never read change logs. The brain just stays current.
2. **Context efficiency.** `CLAUDE.md` stays under 3000 tokens (~200 lines of dense prose). Details live in focused sub-docs.
3. **Fractal.** Same pattern works at workspace root, mid-level folders, and leaf projects.
4. **Multi-chat safe.** `.pending/` staging prevents conflicts between parallel Claude sessions.
5. **Self-growing.** New docs auto-wire into `CLAUDE.md` routing — no manual linking.
6. **Credential hygiene.** Secrets live in workspace-root `Security/<project>.json`. Never in `.env` files scattered across sub-folders.

---

## Quality Enforcement

`/ProjectSetupFix` scores your brain 0–100% across:

- Orphan docs (files not routed from `CLAUDE.md`)
- Dead links (routes pointing to missing files)
- `CLAUDE.md` size (cap 3000 tokens, warn at 2250)
- Doc size (cap 7500 tokens per file, ~500 lines of dense prose)
- Naming convention (`SCREAMING-KEBAB-CASE.md`)
- Required sections (Writing Rules, Sensitive Files)
- Presence of README.md

See `references/quality-rules.md` for the full rubric.

---

## Use Cases

- **Agencies** managing many client projects from one workspace
- **Solo founders** juggling multiple businesses without losing context
- **Long-running codebases** where decisions and conventions get forgotten
- **Teams** who want Claude Code to stay coherent across contributors
- **Anyone** tired of re-pasting the same context into every Claude chat

---

## Status & known limitations

**Honest status:** v0.2.2. Every command runs end-to-end on real projects. Foundation is real software (deterministic CLI, 80 tests, cross-platform installers) — not a clever prompt.

**What's new in v0.2.2 (patch):**
- `brain sync preflight` — one CLI call returns session id, full git state (untracked files + in-progress merges/rebases detected), the sync plan, and a go/no-go with blocker list. `/ProjectSync` trusts it.
- Archive collisions fixed — `archive_old` suffixes `.N` instead of crashing on Windows or silently overwriting on POSIX.
- `brain sync plan` requires `--session-id` (action) or `--inspect` (read-only). Closes a "forgot the flag → merged wrong session" hole.
- Non-ADR conflict losers persisted to `docs/.pending/archive/rejected-*.md` (no more silently-lost rules).
- `--dry-run` specified step-by-step in `ProjectSync.md` (was under-specified in 0.2.1).
- Stop hook ships as `hooks/stop-prompt.py` — same script on Windows, macOS, Linux.
- `stale_pending_count` in sync-plan output so `/ProjectSync` auto-suggests archive when old sessions block merge_first.
- Module splits: `session.py`, `archive.py`, `tests/_helpers.py`. All CLI errors go to stderr consistently.
- 80 tests (was 73).

**What shipped in v0.2.1:**
- Git working-tree check before `/ProjectSync` (doc-only — replaced by preflight in 0.2.2).
- `brain sync new-session-id` replaced the broken-on-macOS shell snippet.
- `brain pending archive --days N` sweeps stale pending files into an archive folder.
- Conflict detection no longer hides conflicts involving body-issue items.
- Docs match code: token-based caps (3000 / 7500), not retired line counts (200 / 500).
- Single-brace placeholder typos (`{date}` vs `{{date}}`) caught with "did you mean".
- Plus: CRLF normalisation, tighter `_guard` scope, renamed pending template to `.md`, `__version__` unstuck.

**What shipped in v0.2.0:**
- `/ProjectSave`, `/ProjectMerge`, `/ProjectUpdate` collapsed into one state-aware `/ProjectSync`.
- Conflict detection widened to `rule` / `decision` / `correction` (not just decisions).
- Stricter orphan detection for decisions (requires an explicit route, not a prose mention).
- Unknown `{{placeholder}}` tokens in pending targets now surface as validation issues.
- Frontmatter validates known enum values (`status`, `confidence`).
- IO-error guards on every CLI command — a locked file no longer aborts a whole audit.
- Query pre-tokenizes chunks — faster on large brains.

**Known limitations** (none are blockers, all are roadmap):
- `brain query` uses TF-IDF, not semantic embeddings. Synonym mismatches happen ("Sentry" vs "error monitoring").
- `brain drift` is mtime-based, not diff-aware. Whitespace-only edits trigger false drift.
- `fact` items still stack at the same target without conflict detection (intentional — facts are usually additive).
- Hooks are documented (see `references/hooks.md`) but not auto-installed.

See [CHANGELOG.md](CHANGELOG.md) for the full roadmap.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). TL;DR: stdlib only, tests before features, deterministic CLI vs prose-driven slash commands is the dividing line.

---

## License

[MIT](LICENSE).

---

## Credits

Built by [Khasan Arapiev](https://github.com/khasan-arapiev) to keep [Zexora Media](https://zexoramedia.com) projects coherent across hundreds of Claude Code sessions.

Contributions and issues welcome.
