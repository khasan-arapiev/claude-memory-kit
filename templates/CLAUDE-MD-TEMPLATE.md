# {{PROJECT_NAME}}

> {{PROJECT_TAGLINE}}
> Created: {{CREATION_DATE}}
> Type: {{PROJECT_TYPE}}

---

## What This Project Is

{{ONE_PARAGRAPH_DESCRIPTION}}

## Task Routing

Read the right files for the task. Do not read everything.

*Routing entries auto-populate below as docs are created. Each entry maps a task type to specific files.*

<!-- AUTO-GROWN ROUTES BELOW THIS LINE — managed by ProjectSync -->

---

## Writing Rules

{{INHERITED_WRITING_RULES_FROM_PARENT}}

---

## Key Facts

| Detail | Value |
|---|---|
| Project name | {{PROJECT_NAME}} |
| Type | {{PROJECT_TYPE}} |
| Created | {{CREATION_DATE}} |
| Status | Active |

---

## Credentials

All credentials for this project live in:
`{{WORKSPACE_ROOT}}/Security/{{PROJECT_SLUG}}.json`

Do not create any local `.env`, `credentials.json`, or `config.local.json` files in this project. If you need a credential that is not in the Security file, ask the user.

---

## Sensitive Files (Do Not Read Unless Needed)

- `{{WORKSPACE_ROOT}}/Security/{{PROJECT_SLUG}}.json` (project credentials)
- `{{WORKSPACE_ROOT}}/Security/workspace-config.json` (workspace credentials)
- Any `.env*` files in this project (should not exist, but check before reading)

---

## Claude Memory Kit Markers

<!-- These markers signal the claude-memory-kit skill that this file is managed -->
<!-- project-brain: managed -->
<!-- claude-memory-kit: version 1 -->
<!-- claude-memory-kit: type project -->
