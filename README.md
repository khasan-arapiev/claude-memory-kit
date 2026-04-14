# Project Brain — A Living Documentation System for Claude Code

**Keep every Claude Code chat context-aware, without ever re-explaining your project.**

Project Brain is a Claude Code skill that turns any project folder into a self-maintaining knowledge base. It scaffolds your docs, keeps `CLAUDE.md` lean, auto-routes new information, and evolves across sessions so Claude always knows your project — without bloating context or losing decisions.

> Built for solo founders, agencies, and teams who want Claude Code to feel like a long-term collaborator, not a forgetful assistant.

**Status:** v0.1.0 MVP. Validated end-to-end against a real project. 48 tests passing. See [CHANGELOG.md](CHANGELOG.md) for what's shipped and [the bottom of this README](#status--known-limitations) for honest known limitations.

---

## Why Project Brain

Large projects die a slow death in `CLAUDE.md`. It balloons past 500 lines, every chat re-reads the same stale context, and new learnings get lost between sessions. Project Brain fixes this with one opinionated pattern:

- **`CLAUDE.md` is a router**, not a dumping ground. Hard cap: 200 lines.
- **Details live in `docs/`**, split by purpose and auto-linked from the router.
- **Insights save automatically** at session end into a `.pending/` staging area.
- **Merges are safe for parallel chats** — no overwrites, no conflicts.
- **Credentials stay in one place** — workspace-root `Security/`, never scattered.

The result: every new Claude chat starts with a complete, current picture of your project. Nothing is re-explained. Nothing is lost.

---

## The 5 Commands

| Command | What it does | When to use |
|---|---|---|
| `/ProjectNewSetup` | Scaffolds folder structure, `CLAUDE.md`, Security config from scratch | Starting a brand-new project |
| `/ProjectSetupFix` | Audits docs, fixes orphans, broken routes, oversize files, reports brain health score | Cleaning up or onboarding an existing project |
| `/ProjectSave` | Captures this chat's insights into `docs/.pending/` | Mid-session checkpoint |
| `/ProjectMerge` | Sweeps `.pending/` files into real docs, resolves conflicts, auto-wires routes | After saves pile up |
| `/ProjectUpdate` | Save + merge in one shot (solo chat shortcut) | When no parallel sessions are running |

---

## How it Works

```
your work → /ProjectSave → docs/.pending/ → /ProjectMerge → real docs → auto-wired in CLAUDE.md
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
- Copies the 5 slash commands to `~/.claude/commands/`
- Runs the test suite (44 tests, stdlib only)
- Prints next steps

Re-run any time to upgrade. The script is idempotent.

### Manual install (if you don't trust scripts)

Copy `.` to `~/.claude/skills/project-brain/` and `commands/Project*.md` to `~/.claude/commands/`. That's it.

### After install

1. Restart Claude Code (so it picks up the new skill + commands)
2. `cd` into any project folder
3. Type `/ProjectNewSetup` (for a new project) or `/ProjectSetupFix` (to audit an existing one)

### (Optional) Auto-save on session end

See `references/hooks.md` for a SessionEnd hook that runs `/ProjectSave` automatically.

---

## Folder Layout of this Repo

```
.
├── SKILL.md                      Skill entrypoint (Claude reads this)
├── commands/                     The 5 slash commands
│   ├── ProjectNewSetup.md
│   ├── ProjectSetupFix.md
│   ├── ProjectSave.md
│   ├── ProjectMerge.md
│   └── ProjectUpdate.md
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
```

**Users never call these directly.** Slash commands invoke the CLI under the hood — same as how Claude already calls Bash for git or file operations. The CLI is the engine; slash commands are the steering wheel.

**Test suite:** `python -m unittest discover tests -v` (44 tests, all stdlib).

See `cli/README.md` for the full CLI reference. Planned: `brain impact`, `brain init`.

---

## Core Principles

1. **Zero headache.** You never read change logs. The brain just stays current.
2. **Context efficiency.** `CLAUDE.md` stays under 200 lines. Details live in focused sub-docs.
3. **Fractal.** Same pattern works at workspace root, mid-level folders, and leaf projects.
4. **Multi-chat safe.** `.pending/` staging prevents conflicts between parallel Claude sessions.
5. **Self-growing.** New docs auto-wire into `CLAUDE.md` routing — no manual linking.
6. **Credential hygiene.** Secrets live in workspace-root `Security/<project>.json`. Never in `.env` files scattered across sub-folders.

---

## Quality Enforcement

`/ProjectSetupFix` scores your brain 0–100% across:

- Orphan docs (files not routed from `CLAUDE.md`)
- Dead links (routes pointing to missing files)
- `CLAUDE.md` size (cap 200 lines, warn at 150)
- Doc size (cap 500 lines per file)
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

**Honest status:** v0.1.0 MVP. Every command runs end-to-end on real projects. Foundation is real software (deterministic CLI, 48 tests, cross-platform installers) — not a clever prompt.

Validated by a full dogfood pass against a fresh SaaS project:
- 5 of 5 slash commands exercised
- 3 parallel subagent saves (no corruption)
- 2 contradicting subagent decisions (conflict caught and resolved)
- Drift detection on a real opt-in doc
- Final brain: 100% clean, 14 docs, 1 drift-tracked

**Known limitations** (none are blockers, all are roadmap):
- `brain query` uses TF-IDF, not semantic embeddings. Synonym mismatches happen ("Sentry" vs "error monitoring").
- `brain drift` is mtime-based, not diff-aware. Whitespace-only edits trigger false drift.
- Conflict detection covers `decision` items only; semantic conflicts in rules and facts still need Claude to read.
- SessionEnd auto-save hook is documented (see `references/hooks.md`) but not auto-installed.

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
