---
name: project-brain
description: >
  Set up and maintain a living "brain" for any project. Scaffolds folder
  structure, manages credentials in workspace-root Security/, and evolves
  documentation across sessions without bloating context. Use this skill
  whenever the user invokes any of these commands or asks about project
  documentation setup: ProjectNewSetup, ProjectSetupFix, ProjectSave,
  ProjectMerge, ProjectUpdate. Also trigger when the user asks to "set up
  a project", "create project structure", "audit project docs", "save
  project insights", "merge pending updates", or mentions setting up
  CLAUDE.md routing for a new or existing project.
---

# Project Brain

A living documentation system for any project. Provides 5 commands that scaffold, audit, and evolve project docs while keeping CLAUDE.md small and discoverable.

## When to invoke this skill

Activate whenever the user runs one of these slash commands or mentions project documentation setup:

| Command | Purpose |
|---|---|
| `ProjectNewSetup` | Scaffold a brand new project from nothing |
| `ProjectSetupFix` | Audit and polish an existing project's structure |
| `ProjectSave` | Mid-session checkpoint of insights to `.pending/` |
| `ProjectMerge` | Sweep `.pending/` into real docs |
| `ProjectUpdate` | Solo-chat shortcut: save + merge in one shot |

The actual command logic lives in `~/.claude/commands/<CommandName>.md` files. This skill provides shared references and templates that the commands use.

## How the brain works

Each project has three physically separated layers sharing one brain:

| Layer | Purpose | Folder | Deployed |
|---|---|---|---|
| Brain | Context, rules, decisions | `CLAUDE.md` + `docs/` | Never |
| Project | The deliverable | `project/` + `assets/` | Yes |
| Tools | Dev tools, tests, scripts | `tools/` | Never |

The brain auto-routes via `CLAUDE.md` (hard cap 200 lines). New docs get auto-wired into `CLAUDE.md` as routing entries, so every chat starts with a complete map of where knowledge lives.

## Key references

When executing any command, load these references as needed:

- **CLI tooling:** `cli/README.md` — the deterministic `brain` CLI (audit, etc.). Prefer calling the CLI over manually counting files.
- **Extraction rules:** `references/extraction-rubric.md` — what gets saved vs ignored during ProjectSave
- **Quality enforcement:** `references/quality-rules.md` — naming, size caps, ADR format, orphan detection
- **Command details:** `references/commands-overview.md` — full behavior matrix for all 5 commands
- **Hook setup:** `references/hooks.md` — SessionEnd hook config for auto-save

## Calling the CLI

Audits and merges are deterministic Python tools, not prose instructions. From any command:

```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" <subcommand> "<path>" --json
```

Available subcommands:
- `audit` — health score and finding lists
- `drift` — docs whose described code has changed
- `decisions list` / `decisions search <q>` — ADR ledger
- `query <text>` — retrieve only the brain sections relevant to a topic

## Retrieval-first behavior

When you need to answer a question about this project:

1. **First**, run `brain query "<topic>"` instead of reading whole docs. Pull only the returned sections into context.
2. Read full docs only when the user asks for an overview or when a query result references a section you need more of.
3. Before suggesting a significant change, run `brain decisions search "<topic>"` so you don't re-litigate a settled decision.

This keeps context small, conversation fast, and answers grounded in the exact passage that supports them.

## Templates

Located in `templates/`:

- `CLAUDE-MD-TEMPLATE.md` — full project CLAUDE.md skeleton
- `CLAUDE-MD-ROUTER-TEMPLATE.md` — router-level CLAUDE.md (just routes to sub-projects)
- `ADR-TEMPLATE.md` — architecture decision record
- `PENDING-FILE-TEMPLATE.yaml` — living-docs staging file
- `SECURITY-CONFIG-TEMPLATE.json` — per-project credentials skeleton
- `GITIGNORE-TEMPLATE` — workspace-root gitignore patterns
- `project-types/*.md` — project-type-specific extras (website, saas, ecommerce, client-work, tool)

## Core principles

1. **Zero headache** — never make the user read change logs
2. **Context efficiency** — `CLAUDE.md` stays small, sub-docs hold details
3. **Fractal** — same pattern at workspace root, branches, and leaf projects
4. **Multi-chat safe** — `.pending/` staging prevents conflicts between parallel sessions
5. **Self-growing** — new files auto-wire into `CLAUDE.md` routing
6. **Credential hygiene** — all secrets in workspace-root `Security/`, never scattered
