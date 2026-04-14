# Commands Overview

Five slash commands implement the project-brain system. Each lives in `~/.claude/commands/` as its own `.md` file.

## Quick reference

| Command | When to use | Writes where | Multi-chat safe |
|---|---|---|---|
| `ProjectNewSetup` | Brand new project from nothing | Creates whole project skeleton | N/A |
| `ProjectSetupFix` | Audit existing project structure | Fixes existing files in place | N/A |
| `ProjectSave` | Mid-session checkpoint of insights | `docs/.pending/` | Yes |
| `ProjectMerge` | Sweep pending into real docs | `docs/` (real files) | Yes |
| `ProjectUpdate` | Solo-chat shortcut | `docs/` (real files, skips pending) | No |

## Detailed behavior

### `ProjectNewSetup`

**Inputs from user:**
- Router level or project level?
- (If project) Project type: website, saas, ecommerce, client-work, tool, other
- Project name and slug
- One-paragraph description

**Steps:**
1. Walk up directory tree to find workspace root (folder containing `Security/`)
2. Create folder structure (`docs/`, `project/`, `assets/`, `tools/`, plus type-specific extras)
3. Create `CLAUDE.md` from template, populated with all known fields
4. Create `Security/<project-slug>.json` from template (empty values)
5. If workspace root has no `.gitignore`, add it from `GITIGNORE-TEMPLATE`
6. Inherit writing rules from parent `CLAUDE.md` if present
7. Commit scaffold as one atomic git commit

### `ProjectSetupFix`

**Inputs from user:** None (auto-detects level)

**Steps:**
1. Detect level: scan for `docs/` and `project/` (project level) or only sub-folders with CLAUDE.md (router level)
2. Run all quality checks from `quality-rules.md`:
   - Orphan scan
   - Dead-link scan
   - Naming convention scan
   - CLAUDE.md size check
   - Individual doc size check
   - Sensitive files section check
   - Writing rules section check
3. At workspace root: check for monolithic `Security/configs.json`, propose splitting
4. At any router level: scan sibling projects for duplicate rules, propose lifting
5. For each issue, prompt user (or auto-fix if non-destructive)
6. Each fix is its own atomic commit
7. Report brain health score

### `ProjectSave`

**Inputs from user:** None (or invoked automatically by SessionEnd hook)

**Steps:**
1. Scan conversation since last save (or whole session if no prior save)
2. Apply extraction rubric (`extraction-rubric.md`) to identify high-signal items
3. Skip items already in existing docs (read CLAUDE.md routing, spot-check target docs)
4. Generate session id: `<YYYY-MM-DD-HHMM>-<random-4-chars>`
5. Write `docs/.pending/<session-id>.md` using PENDING-FILE-TEMPLATE.yaml format
6. Commit the pending file silently
7. Output: nothing (or one-line summary if invoked manually)

### `ProjectMerge`

**Inputs from user:** Conflict resolutions only (when contradictions detected)

**Steps:**
1. List all files in `docs/.pending/`
2. Parse each YAML file
3. Group items across files
4. Deduplicate: merge identical items, prefer high confidence
5. Detect contradictions: same target + opposing content
6. For contradictions, prompt user with both versions and ask which wins
7. For each unique item, decide target doc:
   - Read CLAUDE.md routing to find existing doc
   - If exists, append to appropriate section
   - If not, invoke self-growing schema (create new doc + add route)
8. Make all edits as atomic commits (one commit per doc updated)
9. Delete merged pending files
10. Output: `Merged X items into Y docs. Z conflicts resolved. N new files created.`

### `ProjectUpdate`

**Inputs from user:** None

**Steps:** Run `ProjectSave` logic in-memory (do not write pending), then immediately run `ProjectMerge` logic on the in-memory items.

This is a shortcut for solo-chat workflows where multi-chat coordination is not needed.

## Session-start behavior

When any new chat starts in a folder containing a project-brain managed CLAUDE.md (detected by the `<!-- project-brain: managed -->` marker):

1. Read CLAUDE.md
2. Validate routing entries point to existing files
3. Read `docs/.pending/` to count pending updates
4. Output one line: `Brain loaded: X docs, Y pending. Ready.`
5. If `Y > 0`, prompt: `N pending updates from previous sessions. Merge now? (y/n)`

This is implemented inside each command file's preamble, so any command run in a managed project triggers the check.

## Hook integration

The `SessionEnd` hook in `~/.claude/settings.json` runs `ProjectSave` automatically when a session closes. See `references/hooks.md` for setup.
