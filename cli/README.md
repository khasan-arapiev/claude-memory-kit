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

### `brain drift [path] [--json]`

Flags docs whose described code files have changed since the doc was last synced. Opt-in per doc via frontmatter.

**How a doc opts in:**

```markdown
---
describes:
  - project/pages/checkout.html
  - project/assets/js/checkout.js
last-synced: 2026-04-14
---

# Checkout Flow
...body...
```

**How drift is detected:**
- For each described file, compare its mtime to `last-synced` (or to the doc's own mtime if `last-synced` is absent).
- If the file is newer than the sync date, the doc is drifted.
- Missing described files are surfaced separately.

**Output (human):**
```
Project:       /path/to/project
Tracked docs:  3 (docs with `describes:` frontmatter)

Drift (1):
  - docs/CHECKOUT-FLOW.md
      describes: project/checkout.js
      doc synced: 2026-03-01, file modified: 2026-04-14 (44 days behind)
```

**Output (`--json`):**
```json
{
  "project_path": "...",
  "tracked_docs": 3,
  "drift": [{"doc": "...", "described_file": "...", "doc_synced": "...", "file_modified": "...", "days_behind": 44}],
  "missing_files": []
}
```

**Why this exists:** docs rot silently when the code they describe evolves. Drift detection makes rot visible, so Claude can auto-propose updates or a human can refresh the doc.

## Frontmatter spec

Brain docs support a small YAML-ish frontmatter block (parsed by a stdlib parser, no PyYAML dependency):

```markdown
---
describes:
  - relative/path/to/code.js
  - relative/path/to/other.html
last-synced: 2026-04-14
status: active             # or: superseded | deprecated
---
```

Supported keys:
- `describes` (list of strings) — code files this doc is about; drives drift detection
- `last-synced` (ISO date) — when this doc was last verified against the described code
- `status` (string) — active / superseded / deprecated (used by future decision-ledger features)

Paths in `describes:` are resolved relative to the project root.

### `brain decisions list [path] [--json]`
### `brain decisions search <query> [path] [--json]`

Index and search the project's decision ledger (ADRs in `docs/decisions/`).

**ADR format** (file `docs/decisions/2026-04-14-LIVING-DOCS-MODEL.md`):

```markdown
---
status: active                  # active | superseded | deprecated | proposed
topics:
  - documentation
  - ergonomics
supersedes: 2026-01-12-OLD-DECISION
---

# Living Docs Model

## Context
...

## Decision
...
```

**Supersede chains** are auto-tracked: if ADR B has `supersedes: A`, then A is auto-marked `superseded` and gains a `superseded_by` back-reference.

**Legacy ADRs** without frontmatter are still parsed: a `**Status:** Accepted` line is normalized to `status: active`.

**Output (human):**
```
Decisions (3):

[A] 2026-03-08  Switch to Tailwind
    docs/decisions/2026-03-08-SWITCH-TO-TAILWIND.md
   topics: frontend, css  supersedes: 2026-01-12-USE-BOOTSTRAP

[S] 2026-01-12  Use Bootstrap for UI
    docs/decisions/2026-01-12-USE-BOOTSTRAP.md
   topics: frontend, css  superseded_by: 2026-03-08-SWITCH-TO-TAILWIND

Legend: [A]ctive  [S]uperseded  [D]eprecated  [P]roposed
```

**Why this exists:** Claude can ask "have we already decided about X?" before suggesting an approach. No more re-litigating settled questions.

### `brain query <text> [path] [--top N] [--json]`

Retrieve the most relevant brain sections for a query. Splits every doc into chunks at H2/H3 headings, ranks chunks with TF-IDF (heading matches get a 2x boost), and returns the top N hits with snippets.

**Why this matters:** instead of Claude reading every doc into context "just in case," it asks a targeted question and pulls back only the relevant 200-token chunk. Context cost drops 5-10x on a real brain.

**Output (human):**
```
Top 3 matches for "FTP password":

1. [0.92]  docs/HOSTING.md:5  § FTP Access
   The FTP root is `public_html`. Use relative paths only.
   Credentials live in workspace-root `Security/project.json` under the `ftp` key…

2. [0.34]  CLAUDE.md:42  § Sensitive Files
   Do not read unless needed. These files contain credentials…
```

**Output (`--json`):**
```json
[
  {
    "score": 0.92,
    "doc_path": "docs/HOSTING.md",
    "heading": "FTP Access",
    "line_start": 5,
    "snippet": "The FTP root is `public_html`...",
    "body": "...full section text..."
  }
]
```

**How Claude should use this:** before reading any whole brain doc, run `brain query "<topic>"` and read only the returned sections. This is the difference between "Claude knows everything because it crammed the whole brain into its head" and "Claude finds what it needs in seconds."

### `brain pending list [path] [--json]`

List items staged in `docs/.pending/` for `/ProjectMerge` to apply. Each item declares a type, target doc, confidence, and body content.

**Pending file format** (plain markdown, not YAML):

```markdown
# Pending updates - 2026-04-14-1430-a3b9

## rule
**target:** docs/strategy/WRITING-RULES.md
**confidence:** high

Never use em dashes in copy.

## fact
**target:** docs/reference/EXTERNAL-SYSTEMS.md
**confidence:** high

Meta Pixel ID: 0000000000000000
```

Valid types: `rule`, `fact`, `decision`, `correction`. Valid confidence: `high`, `medium`, `low`.

**Output (JSON):** array of items with `id`, `session_id`, `type`, `target`, `confidence`, `content`, `source_file`, and `issues` (validation problems).

**Why this matters:** `/ProjectMerge` used to parse pending files in prose, which broke whenever the body had a colon or a quote. The CLI parses with a tiny stdlib regex and reports validation problems up front, so Claude can focus on the semantic merge work (dedup, conflicts, placement).

## Tests

```bash
python -m unittest discover tests -v
```

44 tests covering audit, drift, decisions, query (TF-IDF ranking + chunking), pending parsing, and frontmatter. Stdlib only. See `tests/README.md`.

## Roadmap

Planned subcommands (not yet built):
- `brain impact <file>` — dependency blast radius for a code file
- `brain init` — replace `/ProjectNewSetup` prose with deterministic CLI scaffold
