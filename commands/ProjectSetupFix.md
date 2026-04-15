---
description: Audit and polish an existing project's structure, fix orphans, broken routes, naming, sizes, and report brain health
---

You are running the `ProjectSetupFix` command from the `claude-memory-kit` skill.

## Your job

Audit the current directory's claude-memory-kit structure using the deterministic `brain audit` CLI, then fix detected issues interactively, and report the health score.

## Required references

Load these files from the claude-memory-kit skill as needed:
- `~/.claude/skills/claude-memory-kit/references/quality-rules.md` — rules and fix actions
- `~/.claude/skills/claude-memory-kit/templates/CLAUDE-MD-TEMPLATE.md` — section templates
- `~/.claude/skills/claude-memory-kit/templates/README-TEMPLATE.md` — used when README is missing

## Step 1 — Run the deterministic audit

Do NOT count files or score health manually. Call the CLI:

```bash
python -m brain audit "<project path>" --json
```

(The CLI lives at `~/.claude/skills/claude-memory-kit/cli/`. If your shell's `python` is not the one with the CLI module on PYTHONPATH, fall back to: `python "$HOME/.claude/skills/claude-memory-kit/cli/run.py" audit "<path>" --json`.)

The CLI returns JSON like:
```json
{
  "project_path": "...",
  "layout": "project|router|flat",
  "brain_version": 1,
  "has_marker": true,
  "orphans": [{"path": "...", "detail": "..."}],
  "dead_links": [...],
  "naming_violations": [...],
  "oversize_docs": [...],
  "missing_sections": ["Writing Rules", "Sensitive Files"],
  "missing_files": ["README.md"],
  "claude_md_tokens": 1886,
  "total_brain_tokens": 8784,
  "doc_count": 5,
  "score": 100,
  "summary": "clean"
}
```

Parse this JSON. Everything downstream works off these findings. If the CLI returns `{"error": "no_claude_md"}`, tell the user to run `/ProjectNewSetup` first and stop.

## Step 2 — Handle missing marker

If `has_marker` is false, ask the user: "This CLAUDE.md is not marked as claude-memory-kit managed. Should I treat it as managed and add the marker?" If yes, add `<!-- project-brain: managed v1 -->` near the top of CLAUDE.md.

## Step 3 — Fix issues interactively

For each finding in the JSON, take the matching action from this table:

| Finding | Auto-fix | Prompt user |
|---|---|---|
| `orphans[]` | No | "Add `<path>` to CLAUDE.md routing, or move it to `docs/archive/`?" |
| `dead_links[]` | No | "Route points to missing `<path>`. Update the route or remove it?" |
| `naming_violations[]` | No | "Rename `<old>` to `<NEW>` (SCREAMING-KEBAB-CASE)?" |
| `oversize_docs[]` | No | "`<path>` is over the token cap. Split into smaller files?" |
| `missing_sections: ["Writing Rules"]` | Yes | Auto-add empty "## Writing Rules" section from template |
| `missing_sections: ["Sensitive Files"]` | Yes | Auto-add "## Sensitive Files" section from template |
| `missing_files: ["README.md"]` | Yes | Auto-create from `README-TEMPLATE.md` (substitute `{{PROJECT_NAME}}` from CLAUDE.md top H1) |

Each fix is one atomic git commit with a clear message.

## Step 4 — Workspace-root extras

If this folder is the workspace root (contains `Security/`):

- If `Security/configs.json` exists (monolith), propose splitting into per-project `Security/<slug>.json` files. Back up original to `.bak`. Do not delete until user verifies.

## Step 5 — Router-level extras

If `layout == "router"` (folder has sub-projects, no local docs/):

- For each sub-project with a CLAUDE.md, run `brain audit` against it too.
- Compare their "Writing Rules" sections. If 2+ sub-projects share the same rule verbatim, propose lifting to the parent CLAUDE.md and removing from children.

## Step 6 — Re-audit and report

After fixes, call `brain audit` again. Report to the user:

```
Brain health: 94% (was 72%)

Fixed:
  - 2 orphans → added to routing
  - 1 naming violation → renamed
  - Missing README.md → created

Deferred:
  - 1 oversize doc (docs/strategy/PLAN.md, 9200 tokens) — user chose not to split

Suggested next steps:
  - /ProjectSync if there are pending updates
  - Consider splitting PLAN.md next session
```

## Error cases

- No CLAUDE.md: tell user to run `/ProjectNewSetup` first.
- CLAUDE.md without marker: ask confirmation before treating as managed.
- CLI unavailable (Python missing, module not installed): fall back to the manual scan logic in `references/quality-rules.md`, but warn the user their audit will be slower and less reliable.
