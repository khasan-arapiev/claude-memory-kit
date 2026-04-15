"""`brain pending list` - enumerate items staged in docs/.pending/.

Pending files are plain markdown (not YAML), one file per session, append-only.
Each item is an H2 declaring a type, followed by metadata fields and a body:

    # Pending updates - 2026-04-14-1430-a3b9

    ## rule
    **target:** docs/strategy/WRITING-RULES.md
    **confidence:** high

    Never use em dashes in copy.

    ## fact
    **target:** docs/reference/EXTERNAL-SYSTEMS.md
    **confidence:** high

    Meta Pixel ID: 0000000000000000

The CLI handles the deterministic parts (parse, list, validate). Semantic
work (which doc to put an item in, conflict resolution, dedup-by-meaning)
stays with Claude inside the /ProjectSync slash command.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .project import detect, read_md


# Back-compat re-export: `archive_old` moved to `brain.archive` in v0.2.2
# but consumers importing it from `brain.pending` still work.
def archive_old(*args, **kwargs):
    from .archive import archive_old as _impl
    return _impl(*args, **kwargs)


VALID_TYPES = {"rule", "fact", "decision", "correction"}
VALID_CONFIDENCE = {"high", "medium", "low"}
# Placeholders allowed inside `target:` fields. Expanded at merge time by the
# slash command. Any other {{...}} token is a typo or an unsupported template.
KNOWN_PLACEHOLDERS = {"{{date}}", "{{project-slug}}", "{{slug}}"}
PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")
# Single-brace tokens like `{date}` are almost always typos of `{{date}}`.
# Catch them separately so we can give a helpful error instead of writing
# a file literally named `{date}-X.md`.
SINGLE_BRACE_RE = re.compile(r"(?<!\{)\{(?!\{)([a-z][a-z0-9_-]*)\}(?!\})", re.IGNORECASE)

H2_RE = re.compile(r"^##\s+(\S+)\s*$", re.MULTILINE)
FIELD_RE = re.compile(r"^\*\*([a-z][a-z_-]*):\*\*[ \t]*([^\r\n]*?)[ \t]*$", re.MULTILINE)


@dataclass
class Conflict:
    target: str
    type: str
    item_ids: list[str]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PendingItem:
    id: str                  # session_id::index
    session_id: str          # filename stem
    type: str                # rule | fact | decision | correction
    target: str              # destination doc path (may contain {{date}} placeholder)
    confidence: str          # high | medium | low
    content: str             # body text
    source_file: str         # relative path to .pending/<file>.md
    issues: list[str] = field(default_factory=list)  # validation problems

    def to_dict(self) -> dict:
        return asdict(self)


_TARGET_ISSUE_MARKERS = ("missing **target:**", "unknown placeholder")


def _has_target_issue(item: PendingItem) -> bool:
    """True if any of `item.issues` is about the target itself.

    Body-only issues (empty body, bad type, invalid confidence) are not
    target issues — those items should still participate in conflict
    detection so contradictions don't slip past validation noise.
    """
    return any(any(m in i for m in _TARGET_ISSUE_MARKERS) for i in item.issues)


def detect_conflicts(items: list[PendingItem]) -> list[Conflict]:
    """Flag groups of pending items that likely conflict with each other.

    Rule: 2+ items of the same type targeting the same file with non-identical
    bodies. Decisions are the most obvious case (explicit choices), but the
    same shape of bug can hit `rule` items ("never use dashes" vs "always use
    dashes") and `correction` items (two corrections at the same spot).

    `fact` items are exempted: two facts at the same target are almost always
    stackable (list of IDs, list of env vars) rather than contradictory.

    Identical-body duplicates are skipped — those are dedup work, not conflicts.
    """
    conflicts: list[Conflict] = []
    by_key: dict[tuple[str, str], list[PendingItem]] = defaultdict(list)
    for item in items:
        # Only skip items whose *target* is unusable for conflict keying.
        # A body-issue item can still conflict with a valid sibling — the
        # user still needs to resolve "A says X, B says Y (and B is also
        # missing stuff)" before anything gets merged.
        if not item.target or _has_target_issue(item):
            continue
        by_key[(item.target, item.type)].append(item)

    for (target, type_), group in by_key.items():
        if len(group) < 2:
            continue
        if type_ == "fact":
            continue  # facts stack, they don't contradict
        unique_bodies = {it.content.strip() for it in group}
        if len(unique_bodies) < 2:
            continue  # all identical = dedup case, not a conflict
        conflicts.append(
            Conflict(
                target=target,
                type=type_,
                item_ids=[it.id for it in group],
                reason=f"{len(group)} {type_} items target the same file with different content",
            )
        )
    return conflicts


def list_pending(root: Path) -> list[PendingItem] | None:
    project = detect(root)
    if project is None:
        return None

    pending_dir = _find_pending_dir(project.root)
    if pending_dir is None or not pending_dir.is_dir():
        return []

    items: list[PendingItem] = []
    for file in sorted(pending_dir.glob("*.md")):
        items.extend(_parse_pending_file(file, project.root))
    return items


def _find_pending_dir(root: Path) -> Path | None:
    """Find docs/.pending under project root (or root/.pending for flat layouts)."""
    candidates = [root / "docs" / ".pending", root / ".pending"]
    for c in candidates:
        if c.is_dir():
            return c
    return None


def _parse_pending_file(path: Path, project_root: Path) -> list[PendingItem]:
    text = read_md(path)
    session_id = path.stem
    rel_source = str(path.relative_to(project_root).as_posix())

    # Find every H2 heading (each is a new item)
    headings = list(H2_RE.finditer(text))
    if not headings:
        return []

    items: list[PendingItem] = []
    for idx, h in enumerate(headings):
        type_token = h.group(1).strip().lower()
        start = h.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
        block = text[start:end]

        fields = {m.group(1).lower(): m.group(2).strip() for m in FIELD_RE.finditer(block)}

        # Body = whatever's after the last metadata line
        body_start = 0
        for m in FIELD_RE.finditer(block):
            body_start = max(body_start, m.end())
        body = block[body_start:].strip()

        target = fields.get("target", "")
        confidence = fields.get("confidence", "medium").lower()

        item = PendingItem(
            id=f"{session_id}::{idx}",
            session_id=session_id,
            type=type_token,
            target=target,
            confidence=confidence,
            content=body,
            source_file=rel_source,
        )
        # Validate
        if type_token not in VALID_TYPES:
            item.issues.append(f"unknown type '{type_token}' (valid: {sorted(VALID_TYPES)})")
        if not target:
            item.issues.append("missing **target:** field")
        if confidence not in VALID_CONFIDENCE:
            item.issues.append(f"invalid confidence '{confidence}' (valid: {sorted(VALID_CONFIDENCE)})")
        if not body:
            item.issues.append("empty body")
        # Flag unknown {{placeholder}} tokens in target paths so /ProjectSync
        # doesn't silently write a file literally named "{{date}}-X.md".
        for token in PLACEHOLDER_RE.findall(target):
            if token not in KNOWN_PLACEHOLDERS:
                item.issues.append(
                    f"unknown placeholder '{token}' in target "
                    f"(known: {sorted(KNOWN_PLACEHOLDERS)})"
                )
        # Single-brace typos ({date}, {slug}) — almost always meant double.
        for m in SINGLE_BRACE_RE.finditer(target):
            item.issues.append(
                f"single-brace token '{{{m.group(1)}}}' in target "
                f"(did you mean '{{{{{m.group(1)}}}}}'?)"
            )

        items.append(item)
    return items


def render_human(items: list[PendingItem], conflicts: list[Conflict] | None = None) -> str:
    if not items:
        return "No pending items."

    conflicts = conflicts or []

    by_target: dict[str, list[PendingItem]] = {}
    for it in items:
        by_target.setdefault(it.target or "(no target)", []).append(it)

    lines = [f"Pending items: {len(items)} across {len(by_target)} target(s).", ""]
    issue_count = sum(1 for it in items if it.issues)
    if issue_count:
        lines.append(f"WARNING: {issue_count} item(s) have validation issues.")
        lines.append("")
    if conflicts:
        lines.append(f"CONFLICTS DETECTED: {len(conflicts)}")
        for c in conflicts:
            lines.append(f"  ! {c.target}")
            lines.append(f"    {c.reason}")
            for iid in c.item_ids:
                lines.append(f"      - {iid}")
        lines.append("")

    for target, group in by_target.items():
        lines.append(f"-> {target}")
        for it in group:
            tag = f"[{it.type}/{it.confidence}]"
            preview = it.content.replace("\n", " ")[:120]
            lines.append(f"  {tag} {it.id}")
            lines.append(f"    {preview}")
            for issue in it.issues:
                lines.append(f"    ISSUE: {issue}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_json(items: list[PendingItem], conflicts: list[Conflict] | None = None) -> str:
    """Emit a JSON object with `items` and `conflicts` arrays.

    Note: this is a shape change from earlier versions which emitted a bare
    items array. /ProjectSync consumes both keys.
    """
    return json.dumps(
        {
            "items": [it.to_dict() for it in items],
            "conflicts": [c.to_dict() for c in (conflicts or [])],
        },
        indent=2,
    )
