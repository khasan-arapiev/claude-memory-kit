# {{PROJECT_NAME}}

This project uses the **project-brain** system, a living documentation setup that keeps your project knowledge organized and up to date across every Claude chat.

## What it does

- Every new chat starts with a complete picture of the project, no re-explaining needed
- Facts, rules, and decisions you make get saved automatically at the end of each session
- Docs never bloat, `CLAUDE.md` stays small, details live in focused sub-files
- New knowledge auto-wires itself into the routing system so it's always discoverable

## The 5 commands

Type these as slash commands in Claude Code:

| Command | What it does | When to use |
|---|---|---|
| `/ProjectNewSetup` | Builds a new project structure from nothing | Starting a brand new project |
| `/ProjectSetupFix` | Audits the project, fixes orphans, broken routes, oversize files, reports brain health | Cleaning up or auditing |
| `/ProjectSave` | Captures insights from the current chat into `docs/.pending/` | Mid-session checkpoint |
| `/ProjectMerge` | Merges `.pending/` files into real docs, creates new files if needed | After saves pile up |
| `/ProjectUpdate` | Save plus merge in one step, skips the pending folder | Solo chat, no parallel sessions |

## How it fits together

```
Your work → ProjectSave (auto at session end) → .pending/ → ProjectMerge → real docs
```

Or the shortcut: run `/ProjectUpdate` to do both at once.

## Folder layout

- `CLAUDE.md` — the router. Tells Claude where to find each type of knowledge. Capped at 200 lines.
- `docs/` — context, rules, decisions, reference material. The brain. Never deployed.
- `project/` — the actual deliverable. What ships.
- `assets/` — raw and optimized assets.
- `tools/` — dev tools, tests, experiments. Not part of the deliverable.

## Credentials

All secrets live in workspace-root `Security/<project-slug>.json`. Never create local `.env` or `credentials.json` files inside the project.
