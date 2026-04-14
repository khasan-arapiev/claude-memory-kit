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
stays with Claude inside the /ProjectMerge slash command.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .project import detect


VALID_TYPES = {"rule", "fact", "decision", "correction"}
VALID_CONFIDENCE = {"high", "medium", "low"}

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


def detect_conflicts(items: list[PendingItem]) -> list[Conflict]:
    """Flag groups of pending items that likely conflict with each other.

    v1 rule: 2+ `decision` items targeting the same file with non-identical
    bodies. Decisions are explicit choices, so two of them at the same target
    are almost certainly contradictions Claude needs to resolve before merging.

    Identical-body duplicates are skipped (those are dedup work, not conflicts).
    Other types (rule, fact, correction) can stack at the same target without
    necessarily conflicting, so they're not flagged here.
    """
    conflicts: list[Conflict] = []
    by_key: dict[tuple[str, str], list[PendingItem]] = defaultdict(list)
    for item in items:
        if not item.target or item.issues:
            continue
        by_key[(item.target, item.type)].append(item)

    for (target, type_), group in by_key.items():
        if len(group) < 2 or type_ != "decision":
            continue
        unique_bodies = {it.content.strip() for it in group}
        if len(unique_bodies) < 2:
            continue  # all identical = dedup case, not a conflict
        conflicts.append(
            Conflict(
                target=target,
                type=type_,
                item_ids=[it.id for it in group],
                reason=f"{len(group)} decision items target the same file with different content",
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
    text = path.read_text(encoding="utf-8", errors="replace")
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
    items array. /ProjectMerge consumes both keys.
    """
    return json.dumps(
        {
            "items": [it.to_dict() for it in items],
            "conflicts": [c.to_dict() for c in (conflicts or [])],
        },
        indent=2,
    )
