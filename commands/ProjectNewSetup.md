---
description: Scaffold a new project with the project-brain folder structure, CLAUDE.md, and Security config
---

You are running the `ProjectNewSetup` command from the `project-brain` skill.

## Your job

Scaffold a brand new project with the full project-brain structure. The user has invoked this command in the current working directory or has specified a target directory.

## Required references

Load these files from the project-brain skill before proceeding:
- `~/.claude/skills/project-brain/SKILL.md`
- `~/.claude/skills/project-brain/references/quality-rules.md`
- `~/.claude/skills/project-brain/references/commands-overview.md`
- `~/.claude/skills/project-brain/templates/CLAUDE-MD-TEMPLATE.md`
- `~/.claude/skills/project-brain/templates/CLAUDE-MD-ROUTER-TEMPLATE.md`
- `~/.claude/skills/project-brain/templates/SECURITY-CONFIG-TEMPLATE.json`
- `~/.claude/skills/project-brain/templates/GITIGNORE-TEMPLATE`

## Steps

### 1. Confirm target directory

Ask the user (one question at a time):
- "Where should I scaffold the new project? (current directory `<cwd>`, or specify a path)"

### 2. Determine level

Ask: "Is this a **router level** (just routes to sub-projects) or a **project level** (full structure with docs, project, assets, tools)?"

### 3. (Project level only) Determine type

Ask: "What type of project? (website, saas, ecommerce, client-work, tool, other)"

If a type other than "other" is chosen, load the corresponding template from `~/.claude/skills/project-brain/templates/project-types/<TYPE>.md` for type-specific extras.

### 4. Gather metadata

Ask one at a time:
- "Project name? (e.g. 'Acme Studio')"
- "Project slug? (lowercase-kebab, e.g. 'acme-studio')"
- "One-sentence description?"

### 5. Find workspace root

Walk up the directory tree from the target directory looking for a folder containing `Security/`. If found, that is the workspace root. If not found, ask the user: "No workspace root with `Security/` found. Should I treat the target directory as the workspace root and create `Security/` here?"

### 6. Inherit writing rules

If a parent CLAUDE.md exists between the target and workspace root, read it and extract the "Writing Rules" section. This will be inserted into the new CLAUDE.md.

### 7. Create folder structure

For project level:
```bash
mkdir -p <target>/docs/{context,architecture,workflows,decisions,reference,archive,.pending}
mkdir -p <target>/project
mkdir -p <target>/assets/raw
mkdir -p <target>/tools/{playwright,scripts,experiments}
```

For router level: just `<target>/` with no subfolders.

If a project type was chosen, create the type-specific extra folder per the type template.

### 8. Create CLAUDE.md

Read the appropriate template (`CLAUDE-MD-TEMPLATE.md` for project, `CLAUDE-MD-ROUTER-TEMPLATE.md` for router). Replace all `{{PLACEHOLDERS}}` with gathered values:
- `{{PROJECT_NAME}}` → user-provided name
- `{{PROJECT_TAGLINE}}` → user-provided description
- `{{CREATION_DATE}}` → current date in ISO format
- `{{PROJECT_TYPE}}` → user-provided type
- `{{PROJECT_SLUG}}` → user-provided slug
- `{{ONE_PARAGRAPH_DESCRIPTION}}` → user-provided description
- `{{INHERITED_WRITING_RULES_FROM_PARENT}}` → parent rules or "(none defined yet)"
- `{{WORKSPACE_ROOT}}` → relative path from project to workspace root (use `.` if the project IS the workspace root)

Write to `<target>/CLAUDE.md`.

### 9. Create README.md for the user

Read `~/.claude/skills/project-brain/templates/README-TEMPLATE.md`. Replace:
- `{{PROJECT_NAME}}` → user-provided project name

Write the result to `<target>/README.md`.

This README explains the project-brain system, the 5 commands, and the folder layout in plain language so anyone opening the project (including the user) understands how it works.

### 10. Create Security config

Read `SECURITY-CONFIG-TEMPLATE.json`. Replace these three placeholders:
- `{{PROJECT_NAME}}` → user-provided project name
- `{{PROJECT_SLUG}}` → user-provided slug
- `{{CREATION_DATE}}` → today's date in ISO format

Write the result to `<workspace-root>/Security/<project-slug>.json`.

If `<workspace-root>/Security/` does not exist, create it.

### 11. Ensure workspace gitignore

If `<workspace-root>/.gitignore` does not exist, create it from `GITIGNORE-TEMPLATE`. If it exists, check that key patterns are present (`**/.env`, `!Security/`); if missing, append them.

### 12. Verify scaffold

Read back the created CLAUDE.md and verify all `{{PLACEHOLDERS}}` were replaced (no `{{...}}` remain).

```bash
grep -c "{{" "<target>/CLAUDE.md" || true
grep -c "{{" "<target>/README.md" || true
```
Expected: 0 for both

### 13. Commit

```bash
cd <workspace-root>
git add <relative-path-to-target>/CLAUDE.md
git add <relative-path-to-target>/README.md
git add Security/<project-slug>.json
git add .gitignore  # if changed
git -c user.name="<from-recent-commits>" -c user.email="<from-recent-commits>" commit -m "feat: scaffold <project-name> via ProjectNewSetup"
```

If git is not initialized in the workspace, skip the commit step and tell the user.

### 14. Report

Output a single concise summary:
```
Project scaffolded:
  Name: <project-name>
  Type: <type>
  Location: <target>
  Credentials: <workspace-root>/Security/<project-slug>.json
  Inherited rules: <yes/no>
Ready to use. Next: fill in docs/context/ files when you have time.
```

## Errors

- If the target directory already contains a `CLAUDE.md`, abort and tell the user to use `ProjectSetupFix` instead.
- If git author identity is not available from recent commits and no `git config user.name` is set, ask the user for their git identity before committing.
