# Project Brain CLI

Deterministic tooling for the project-brain skill. Claude calls these tools instead of doing the counting in its head, which cuts token cost, removes variance, and gives you reproducible health scores.

**Zero dependencies.** Pure Python 3.10+ stdlib. Works on Windows, macOS, Linux.

## Commands

### `brain audit [path] [--json]`

Audits a project-brain folder. Returns human-readable output by default, JSON with `--json`.

**Checks:**
- Orphan docs (files in `docs/` not referenced from `CLAUDE.md`)
- Dead links (markdown links in `CLAUDE.md` that point to missing files)
- Naming violations (must be `SCREAMING-KEBAB-CASE.md`, or ADR format under `decisions/`)
- Token-aware size (CLAUDE.md cap 3000 tokens, doc cap 7500 tokens)
- Missing required sections ("Writing Rules", "Sensitive Files")
- Missing README.md

**Output (human):**
```
Project:        /path/to/project
Layout:         project
Brain version:  1
Managed marker: yes

Brain health:   94%  (1 orphan(s); 1 oversize doc(s))

CLAUDE.md:      1886 tokens (warn 2250, cap 3000)
Total brain:    8784 tokens across 5 doc(s)

Orphans:
  - docs/strategy/OLD-PLAN.md
```

**Output (`--json`):**
```json
{
  "project_path": "...",
  "layout": "project|router|flat",
  "brain_version": 1,
  "has_marker": true,
  "orphans": [{"kind": "orphan", "path": "...", "detail": "..."}],
  "dead_links": [],
  "naming_violations": [],
  "oversize_docs": [],
  "missing_sections": [],
  "missing_files": [],
  "claude_md_tokens": 1886,
  "total_brain_tokens": 8784,
  "doc_count": 5,
  "score": 94,
  "summary": "1 orphan(s); 1 oversize doc(s)"
}
```

**Exit codes:**
- `0` — clean (no findings)
- `1` — findings present (useful for CI)
- `2` — fatal error (no CLAUDE.md, bad args)

## How to call it

### From a Claude slash command
```bash
python "$HOME/.claude/skills/project-brain/cli/run.py" audit "<project path>" --json
```

### As a module (after install)
```bash
python -m brain audit <path> [--json]
```

### Direct
```bash
cd /path/to/project-brain-skill/cli
python run.py audit /path/to/your/project
```

## Token budgets

Unlike line-count rules, token budgets match what Claude actually pays to read:

| Budget | Limit | Reason |
|---|---|---|
| `CLAUDE.md` soft warn | 2250 tokens (~150 lines) | Nudge toward trimming |
| `CLAUDE.md` hard cap | 3000 tokens (~200 lines) | Forces section lifting |
| Individual doc cap | 7500 tokens (~500 lines) | Forces doc splitting |

Tokens are estimated at `len(text) / 4` (stable heuristic, no external dependency).

## Scoring weights

Total 100 points.

| Metric | Weight | Pass |
|---|---|---|
| No orphans | 25 | `len(orphans) == 0` |
| No dead links | 25 | `len(dead_links) == 0` |
| CLAUDE.md size | 15 | Full under warn, half under cap, 0 over cap |
| Doc size | 15 | Minus 5 per oversize doc, floor 0 |
| Naming | 10 | All doc names match convention |
| Writing Rules section | 5 | Present in CLAUDE.md |
| Sensitive Files section | 5 | Present in CLAUDE.md |

## Roadmap

Planned subcommands (not yet built):
- `brain query <text>` — retrieve brain sections matching a topic
- `brain impact <file>` — dependency blast radius for a code file
- `brain drift` — detect code/doc desync after edits
- `brain merge` — apply `.pending/` updates to real docs
- `brain decisions <topic>` — search the decision ledger
