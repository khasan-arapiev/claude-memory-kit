---
description: Audit and polish an existing project's structure, fix orphans, broken routes, naming, sizes, and report brain health
---

You are running the `ProjectSetupFix` command from the `project-brain` skill.

## Your job

Audit the current directory's project-brain structure, fix all detected issues, and report a brain health score.

## Required references

Load these files from the project-brain skill:
- `~/.claude/skills/project-brain/references/quality-rules.md`
- `~/.claude/skills/project-brain/references/commands-overview.md`
- `~/.claude/skills/project-brain/templates/CLAUDE-MD-TEMPLATE.md`
- `~/.claude/skills/project-brain/templates/GITIGNORE-TEMPLATE`

## Steps

### 1. Detect project level

Scan the current directory:
- If contains `docs/` AND `project/` → project level
- If contains only sub-folders with CLAUDE.md and no `docs/` of its own → router level
- If contains nothing recognizable → tell user "no project-brain structure here, run `ProjectNewSetup` first"

### 2. Read CLAUDE.md and check markers

Verify the file has `<!-- project-brain: managed -->` marker. If absent, ask user: "This CLAUDE.md is not marked as project-brain managed. Should I treat it as managed and add the marker?"

### 3. Run all quality checks

Following `quality-rules.md` exactly:

#### 3a. Orphan scan
List every `*.md` file under `docs/` (excluding `.pending/` and `archive/`). For each, grep CLAUDE.md for the filename. Files not found are orphans. Record list.

```bash
find docs -name "*.md" -not -path "docs/.pending/*" -not -path "docs/archive/*" | while read f; do
  basename=$(basename "$f")
  grep -q "$basename" CLAUDE.md || echo "ORPHAN: $f"
done
```

#### 3b. Dead-link scan
Parse routing entries in CLAUDE.md (lines containing `docs/` followed by a `.md` filename). For each target, verify file exists.

```bash
grep -oE 'docs/[^[:space:])]+\.md' CLAUDE.md | while read target; do
  test -f "$target" || echo "DEAD: $target"
done
```

#### 3c. Naming convention scan
Find any `*.md` files in `docs/` that do not match SCREAMING-KEBAB-CASE pattern.

```bash
find docs -name "*.md" -not -path "docs/.pending/*" | while read f; do
  basename=$(basename "$f" .md)
  if ! [[ "$basename" =~ ^[A-Z0-9-]+$ ]]; then
    echo "NAMING: $f"
  fi
done
```

#### 3d. CLAUDE.md size check
```bash
lines=$(wc -l < CLAUDE.md)
if [ "$lines" -gt 200 ]; then
  echo "OVERSIZE: CLAUDE.md is $lines lines (cap 200)"
elif [ "$lines" -gt 150 ]; then
  echo "WARNING: CLAUDE.md is $lines lines (warning at 150)"
fi
```

#### 3e. Doc size check
```bash
find docs -name "*.md" | while read f; do
  lines=$(wc -l < "$f")
  if [ "$lines" -gt 500 ]; then
    echo "OVERSIZE: $f is $lines lines (cap 500)"
  fi
done
```

#### 3f. Sensitive files section check
```bash
grep -q "## Sensitive Files" CLAUDE.md || echo "MISSING: Sensitive Files section"
```

#### 3g. Writing rules section check
```bash
grep -q "## Writing Rules" CLAUDE.md || echo "MISSING: Writing Rules section"
```

#### 3h. README.md presence check
```bash
test -f README.md || echo "MISSING: README.md"
```

If missing, auto-create it from `~/.claude/skills/project-brain/templates/README-TEMPLATE.md`. Replace `{{PROJECT_NAME}}` with the project name extracted from CLAUDE.md's top H1 heading. This README explains the project-brain system to anyone (including the user) who opens the folder.

### 4. Workspace root extras

If this is the workspace root (contains `Security/`):

#### 4a. Check for monolithic Security/configs.json
```bash
if [ -f "Security/configs.json" ]; then
  echo "MONOLITH: Security/configs.json should be split per project"
fi
```

If found, propose splitting:
1. Read `Security/configs.json`
2. Identify which sub-project each credential block belongs to
3. Create per-project files: `Security/<project-slug>.json`
4. Move credentials from monolith to per-project files
5. Backup original to `Security/configs.json.bak`
6. Ask user to verify before deleting backup

### 5. Router-level extras

If this is a router level:

#### 5a. Cross-project rule lifting
For each sub-project containing a CLAUDE.md:
```bash
# Extract their Writing Rules sections
# Compare for duplicates
# If 2+ sub-projects have the same rule verbatim, propose lifting
```

Surface duplicates to user, ask "Lift to parent CLAUDE.md and remove from children? (y/n)".

### 6. Fix issues

For each issue found, take the appropriate action:

| Issue | Auto-fix | Prompt user |
|---|---|---|
| Orphan | No | "Add to routing or move to archive?" |
| Dead link | No | "Update target or remove route?" |
| Naming violation | No | "Rename `<old>` to `<NEW>`?" |
| CLAUDE.md oversize | No | "Lift `<section>` to its own file?" |
| Doc oversize | No | "Split `<file>` into N smaller files?" |
| Missing sensitive files section | Yes | (auto-add from template) |
| Missing writing rules section | Yes | (auto-add empty placeholder) |
| Missing README.md | Yes | (auto-create from `README-TEMPLATE.md`, substitute `{{PROJECT_NAME}}`) |
| Monolith Security file | No | "Split into per-project files?" |
| Duplicate rule across projects | No | "Lift to parent?" |

Each fix must be one atomic git commit with a clear message.

### 7. Calculate brain health score

Apply weights from `quality-rules.md`:

```
score = 0
if no orphans: score += 25
if no dead links: score += 25
if CLAUDE.md <= 150 lines: score += 15
elif CLAUDE.md <= 200 lines: score += 7.5
docs_oversize_count = (number of docs > 500 lines)
score += max(0, 15 - docs_oversize_count * 5)
if all docs match naming: score += 10
if writing rules section exists: score += 5
if sensitive files section exists: score += 5
```

### 8. Report

Output a single structured summary:

```
Brain health: 94%

Findings:
  Orphans: 2 fixed (added to routing)
  Broken routes: 0
  Naming violations: 1 fixed (renamed)
  CLAUDE.md size: 140/200 lines (healthy)
  Oversize docs: 1 (docs/strategy/PLAN.md at 540 lines, suggested split deferred)
  Sensitive files section: present
  Writing rules section: present

Suggested next steps:
  - Run /ProjectMerge to apply pending updates
  - Consider splitting docs/strategy/PLAN.md
```

## Errors

- If no CLAUDE.md exists: tell user to run `/ProjectNewSetup` first.
- If CLAUDE.md exists but has no project-brain marker: ask user to confirm before treating as managed.
