# Project Brain — A Living Documentation System for Claude Code

**Keep every Claude Code chat context-aware, without ever re-explaining your project.**

Project Brain is a Claude Code skill that turns any project folder into a self-maintaining knowledge base. It scaffolds your docs, keeps `CLAUDE.md` lean, auto-routes new information, and evolves across sessions so Claude always knows your project — without bloating context or losing decisions.

> Built for solo founders, agencies, and teams who want Claude Code to feel like a long-term collaborator, not a forgetful assistant.

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

Requires [Claude Code](https://claude.com/claude-code).

### 1. Install the skill

Copy the skill into your Claude skills folder:

```bash
# macOS / Linux
cp -r . ~/.claude/skills/project-brain/

# Windows (Git Bash)
cp -r . "$USERPROFILE/.claude/skills/project-brain/"
```

### 2. Install the commands

Copy the 5 slash commands:

```bash
# macOS / Linux
cp commands/Project*.md ~/.claude/commands/

# Windows (Git Bash)
cp commands/Project*.md "$USERPROFILE/.claude/commands/"
```

### 3. Restart Claude Code

Commands and skills load at session start. Next chat: type `/ProjectNewSetup` inside any folder.

### 4. (Optional) Enable auto-save on session end

See `references/hooks.md` for a SessionEnd hook that runs `/ProjectSave` automatically when you close a chat.

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

## License

MIT (add LICENSE file before making public).

---

## Credits

Built by [Khasan Arapiev](https://github.com/khasan-arapiev) to keep [Zexora Media](https://zexoramedia.com) projects coherent across hundreds of Claude Code sessions.

Contributions and issues welcome.
