# Quality Rules

All commands enforce these rules. `ProjectSetupFix` audits against them and fixes violations.

## File naming

**Rule:** All doc files in `docs/` use `SCREAMING-KEBAB-CASE.md`.

- Correct: `DATABASE-SCHEMA.md`, `SEO-STRATEGY.md`, `CLIENT-ONBOARDING-FLOW.md`
- Wrong: `database-schema.md`, `DatabaseSchema.md`, `database_schema.md`

When creating any new doc file, enforce this naming. When auditing, rename violations and update CLAUDE.md routes accordingly.

## CLAUDE.md size budget

**Rule:** `CLAUDE.md` hard cap is **3000 tokens** (≈200 lines of dense prose).

- **Warning threshold:** 2250 tokens (suggest action on next sync)
- **Hard cap:** 3000 tokens (must lift sections out before commit)

The audit measures tokens, not lines, so layout-heavy markdown (tables, code blocks) isn't penalised for being formatted. Token estimation is `chars / 4` — no external tokenizer required. See `cli/brain/audit.py:CLAUDE_MD_TOKEN_CAP` for the source of truth.

When `CLAUDE.md` approaches or exceeds the cap:
1. Identify the largest section that is purely informational (not routing)
2. Propose lifting it to a dedicated doc file in the appropriate `docs/<category>/` folder
3. Replace the section in `CLAUDE.md` with a single routing line pointing to the new file

## Doc size budget

**Rule:** Individual doc files in `docs/` should not exceed **7500 tokens** (≈500 lines of dense prose).

When a doc crosses 7500 tokens:
1. Identify natural section boundaries
2. Propose splitting into 2 or more focused files
3. Update CLAUDE.md routing to point to all new files
4. Add a redirect note in the original file location (or move original to `docs/archive/`)

## Writing rules inheritance

**Rule:** Sub-projects inherit writing rules from the parent CLAUDE.md.

When scaffolding a new project inside a workspace that already has a CLAUDE.md:
1. Walk up to the nearest parent CLAUDE.md
2. Extract its "Writing Rules" section verbatim
3. Insert into the new project's CLAUDE.md under "Writing Rules"

## ADR format

**Rule:** Every file in `docs/decisions/` follows the ADR template.

Required sections:
- Title (H1)
- Date
- Status (Proposed | Accepted | Superseded | Deprecated)
- Context
- Decision
- Consequences (with Enables / Prevents / Trade-offs)
- Alternatives considered

Filename format: `YYYY-MM-DD-DECISION-TITLE.md`

## Orphan and dead-link detection

**Rule:** Every doc in `docs/` must be discoverable from `CLAUDE.md`. Every route in `CLAUDE.md` must point to a real file.

Audit logic for `ProjectSetupFix`:

1. **Orphan scan:**
   - List all `*.md` files under `docs/` (excluding `.pending/` and `archive/`)
   - For each, check if it appears in `CLAUDE.md` as a routing target
   - Files not referenced are orphans

2. **Dead-link scan:**
   - Parse all routing entries in `CLAUDE.md`
   - For each target path, check if the file exists
   - Missing targets are dead links

3. **Cross-reference scan:**
   - Parse all `[text](path)` and `path` mentions inside doc files
   - Verify each target exists

**Fix actions:**
- Orphans: prompt user to either (a) add a routing line for the orphan or (b) move it to `archive/`
- Dead links: prompt user to either (a) update the route to a valid target or (b) remove the route
- Cross-reference issues: same as dead links

## Sensitive files section

**Rule:** Every project-level CLAUDE.md must contain a "Sensitive Files" section pointing to its `Security/` config.

If absent, `ProjectSetupFix` adds it from the template.

## Brain health score

Calculated by `ProjectSetupFix`. Each metric scored 0 or weight (no partial credit unless noted).

| Metric | Weight | Pass condition |
|---|---|---|
| Orphan-free | 25% | Zero orphaned docs in `docs/` |
| Route integrity | 25% | Zero broken routes in CLAUDE.md |
| CLAUDE.md size | 15% | Under 3000 tokens (partial: 100% under 2250, 50% between 2250-3000, 0% over) |
| Doc size compliance | 15% | All docs under 7500 tokens (partial: -5% per doc over) |
| Naming convention | 10% | All `docs/*.md` files match SCREAMING-KEBAB-CASE |
| Writing rules present | 5% | "Writing Rules" section exists in CLAUDE.md |
| Sensitive files section | 5% | Section exists in CLAUDE.md |

Report format: `Brain health: X%. <one-line summary of findings>`

## Cross-project rule lifting

When `ProjectSetupFix` runs at a router level:

1. List all sibling sub-projects with claude-memory-kit markers
2. For each, extract any "Writing Rules" or recurring rules from their docs
3. Find rules that appear verbatim or near-verbatim in 2+ projects
4. Propose promoting them to the parent router's CLAUDE.md
5. On approval, add to parent and remove from children

## Self-growing schema

When a `ProjectSync` finds an item that does not fit any existing doc:

1. Determine the appropriate `docs/<category>/` folder based on item type:
   - `rule` → `docs/strategy/` or `docs/workflows/` (depending on rule scope)
   - `fact` → `docs/reference/` or `docs/context/`
   - `decision` → `docs/decisions/` (always, as ADR)
   - `correction` → wherever the original incorrect doc lives
2. Generate a filename in `SCREAMING-KEBAB-CASE.md` based on the item content
3. Create the file with appropriate template (ADR template for decisions, plain for others)
4. Edit `CLAUDE.md` to add a new routing entry under the correct "Working on..." section
5. Both the new file and the CLAUDE.md update are part of one atomic git commit
