"""`brain sync plan` - deterministic state inspection for the unified /ProjectSync command.

The old model had three slash commands (Save / Merge / Update) and the user
had to pick the right one. This is the state half of the replacement: Claude
runs `brain sync plan --session-id <id>` and gets back a structured decision
about what should happen. The semantic half (extracting insights from the
conversation) still lives with Claude because the CLI can't read the chat.

Output modes:

- `empty`            No pending items anywhere. If the session has new
                     insights, stage them and merge. Otherwise nothing to do.
- `quick`            Only this session has pending items, zero conflicts.
                     Safe to merge in one shot (the old `ProjectUpdate` path).
- `merge_first`      Other sessions have pending items. Stage the current
                     session's items (if any) but don't merge — surface the
                     other sessions for the user to review.
- `resolve_conflicts` Pending items (from any session) have detected
                     conflicts. Merge must stop and ask the user.

Everything here is side-effect-free: the CLI just reports. The slash command
does the actual writes.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .pending import Conflict, PendingItem, detect_conflicts, list_pending


@dataclass
class SyncPlan:
    mode: str                   # empty | quick | merge_first | resolve_conflicts
    session_id: str             # echo of input for traceability
    pending_total: int
    pending_this_session: int
    pending_other_sessions: int
    other_session_ids: list[str] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)   # items with validation problems
    reason: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["conflicts"] = [c.to_dict() for c in self.conflicts]
        return d


def sync_plan(root: Path, session_id: str = "") -> SyncPlan | None:
    items = list_pending(root)
    if items is None:
        return None

    conflicts = detect_conflicts(items)
    bad = [it.id for it in items if it.issues]

    this_session = [it for it in items if session_id and it.session_id == session_id]
    other_sessions_items = [it for it in items if not session_id or it.session_id != session_id]
    other_session_ids = sorted({it.session_id for it in other_sessions_items})

    plan = SyncPlan(
        mode="empty",
        session_id=session_id,
        pending_total=len(items),
        pending_this_session=len(this_session),
        pending_other_sessions=len(other_sessions_items),
        other_session_ids=other_session_ids,
        conflicts=conflicts,
        issues=bad,
    )

    if conflicts:
        plan.mode = "resolve_conflicts"
        plan.reason = (
            f"{len(conflicts)} conflict(s) in pending. "
            "Resolve before merging so nothing gets overwritten."
        )
        return plan

    if not items:
        plan.mode = "empty"
        plan.reason = (
            "No pending items. Extract insights from the session; if any, "
            "stage and merge in one shot."
        )
        return plan

    if other_sessions_items:
        plan.mode = "merge_first"
        plan.reason = (
            f"{len(other_sessions_items)} item(s) from {len(other_session_ids)} "
            "other session(s) are staged. Stage this session's items if any, "
            "then surface the other sessions for the user to review before merge."
        )
        return plan

    plan.mode = "quick"
    plan.reason = (
        f"Only this session has staged items ({len(this_session)}), no conflicts. "
        "Safe to merge directly."
    )
    return plan


def render_human(p: SyncPlan) -> str:
    lines = [
        f"Mode:             {p.mode}",
        f"Session id:       {p.session_id or '(unspecified)'}",
        f"Pending total:    {p.pending_total}",
        f"  this session:   {p.pending_this_session}",
        f"  other sessions: {p.pending_other_sessions}",
    ]
    if p.other_session_ids:
        lines.append("Other session ids:")
        for sid in p.other_session_ids:
            lines.append(f"  - {sid}")
    if p.conflicts:
        lines.append(f"Conflicts: {len(p.conflicts)}")
        for c in p.conflicts:
            lines.append(f"  ! {c.target}  ({c.reason})")
    if p.issues:
        lines.append(f"Items with validation issues: {len(p.issues)}")
    if p.reason:
        lines.append("")
        lines.append(p.reason)
    return "\n".join(lines)


def render_json(p: SyncPlan) -> str:
    return json.dumps(p.to_dict(), indent=2)
