"""State-aware planner and preflight for the unified /ProjectSync command.

`sync_plan` classifies the pending state into one of four modes
(empty | quick | merge_first | resolve_conflicts). `preflight` composes
that with `git.inspect` and a fresh session id into one JSON-serialisable
payload — the single source of truth `/ProjectSync` checks before writing
anything.

Everything here is side-effect-free: the CLI just reports. The slash
command does the actual writes.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .git import GitState, inspect
from .pending import Conflict, _find_pending_dir, detect_conflicts, list_pending
from .session import new_session_id

# Days after which a pending file counts as "stale" for sync-plan reporting.
# Matches the default --days for `brain pending archive`.
STALE_DAYS_DEFAULT = 14


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
    stale_pending_count: int = 0  # pending files older than STALE_DAYS_DEFAULT
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _count_stale(root: Path, days: int) -> int:
    """Same-pass stale count. Walks the pending dir once; no extra glob."""
    from .project import detect
    project = detect(root)
    if project is None:
        return 0
    pending_dir = _find_pending_dir(project.root)
    if pending_dir is None or not pending_dir.is_dir():
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    return sum(
        1 for f in pending_dir.glob("*.md")
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff
    )


def sync_plan(root: Path, session_id: str = "") -> SyncPlan | None:
    items = list_pending(root)
    if items is None:
        return None

    conflicts = detect_conflicts(items)
    bad = [it.id for it in items if it.issues]

    # Empty session_id means the caller didn't claim a session. Common when
    # a human runs `brain sync plan --inspect`. Treat all items uniformly.
    if session_id:
        this_session = [it for it in items if it.session_id == session_id]
        other_sessions_items = [it for it in items if it.session_id != session_id]
    else:
        this_session = []
        other_sessions_items = list(items)
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
        stale_pending_count=_count_stale(root, days=STALE_DAYS_DEFAULT),
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

    # With no session_id, every item is "other". If they all share one
    # session_id, nothing else is in the way — treat as `quick`.
    if not session_id and len(other_session_ids) == 1:
        plan.mode = "quick"
        plan.reason = (
            f"All {len(items)} pending item(s) belong to a single session "
            f"({other_session_ids[0]}). Safe to merge directly."
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


@dataclass
class Preflight:
    ok: bool                   # True when /ProjectSync is safe to proceed
    session_id: str
    git: GitState
    plan: SyncPlan | None
    blockers: list[dict] = field(default_factory=list)
    dry_run: bool = False      # echoed so the slash command can check on re-read

    def to_dict(self) -> dict:
        return asdict(self)


def _blocker(code: str, message: str, remedy: str) -> dict:
    """Structured blocker: a machine code, a human explanation, and a fix hint."""
    return {"code": code, "message": message, "remedy": remedy}


def preflight(
    root: Path,
    include_wip: bool = False,
    dry_run: bool = False,
) -> Preflight | None:
    """One-stop safety check for `/ProjectSync`.

    Mints a session id, inspects git, runs `sync_plan`, and aggregates
    everything into one payload. When `ok` is False, `blockers` lists
    structured reasons (code + message + remedy) so the slash command
    can surface each with the remediation the user should actually run.

    `include_wip=True` downgrades BOTH dirty working tree AND untracked
    files from blockers to warnings — for users who intentionally have
    un-synced work. In-progress git operations (merge/rebase/cherry-pick/
    bisect) remain blockers regardless, because those are broken states
    that would corrupt the commit history if Sync writes on top.

    `dry_run=True` is echoed in the result so the slash command can
    detect dry-run mode from any preflight JSON it re-reads mid-run.
    """
    sid = new_session_id()
    git = inspect(root)
    sp = sync_plan(root, session_id=sid)
    if sp is None:
        return None

    blockers: list[dict] = []
    if git.initialised:
        if git.operation_in_progress:
            blockers.append(_blocker(
                code="git_operation_in_progress",
                message=f"git {git.operation_in_progress} in progress.",
                remedy=(
                    f"Finish or abort the {git.operation_in_progress} "
                    f"(`git {git.operation_in_progress} --abort` or complete it), "
                    "then re-run /ProjectSync."
                ),
            ))
        if git.untracked_paths and not include_wip:
            blockers.append(_blocker(
                code="untracked_files",
                message=f"{len(git.untracked_paths)} untracked file(s) could be overwritten.",
                remedy=(
                    "`git add <paths>` + commit, add them to `.gitignore`, "
                    "or re-run with `--include-wip` to keep them."
                ),
            ))
        if git.dirty_paths and not include_wip:
            blockers.append(_blocker(
                code="dirty_working_tree",
                message=f"{len(git.dirty_paths)} file(s) with uncommitted changes.",
                remedy=(
                    "`git stash` or commit unrelated changes, "
                    "or re-run with `--include-wip` to keep them."
                ),
            ))

    return Preflight(
        ok=not blockers,
        session_id=sid,
        git=git,
        plan=sp,
        blockers=blockers,
        dry_run=dry_run,
    )


def render_preflight_human(pf: Preflight) -> str:
    lines = [
        f"Session id:      {pf.session_id}",
        f"Safe to proceed: {'YES' if pf.ok else 'NO'}",
        f"Dry run:         {pf.dry_run}",
        "",
        "Git:",
        f"  initialised: {pf.git.initialised}",
    ]
    if pf.git.initialised:
        state = pf.git.branch or "(unnamed)"
        if pf.git.unborn:
            state += " (unborn)"
        elif pf.git.detached:
            state = "(detached HEAD)"
        lines.append(f"  branch:      {state}")
        lines.append(f"  clean:       {pf.git.clean}")
    if pf.git.operation_in_progress:
        lines.append(f"  IN PROGRESS: {pf.git.operation_in_progress}")
    if pf.git.dirty_paths:
        lines.append(f"  dirty ({len(pf.git.dirty_paths)}):")
        for p in pf.git.dirty_paths[:10]:
            lines.append(f"    - {p}")
        if len(pf.git.dirty_paths) > 10:
            lines.append(f"    ... and {len(pf.git.dirty_paths)-10} more")
    if pf.git.untracked_paths:
        lines.append(f"  untracked ({len(pf.git.untracked_paths)}):")
        for p in pf.git.untracked_paths[:10]:
            lines.append(f"    - {p}")
        if len(pf.git.untracked_paths) > 10:
            lines.append(f"    ... and {len(pf.git.untracked_paths)-10} more")
    if pf.blockers:
        lines.append("")
        lines.append("Blockers:")
        for b in pf.blockers:
            lines.append(f"  ! [{b['code']}] {b['message']}")
            lines.append(f"    remedy: {b['remedy']}")
    lines.append("")
    lines.append("Plan:")
    if pf.plan is not None:
        lines.append(render_human(pf.plan))
    return "\n".join(lines)


def render_preflight_json(pf: Preflight) -> str:
    return json.dumps(pf.to_dict(), indent=2)


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
    if p.stale_pending_count:
        lines.append(
            f"Stale pending files (>{STALE_DAYS_DEFAULT}d): {p.stale_pending_count} — "
            f"consider `brain pending archive --days {STALE_DAYS_DEFAULT}`"
        )
    if p.reason:
        lines.append("")
        lines.append(p.reason)
    return "\n".join(lines)


def render_json(p: SyncPlan) -> str:
    return json.dumps(p.to_dict(), indent=2)
