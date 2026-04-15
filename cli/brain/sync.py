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

from .archive import stale_count
from .pending import Conflict, detect_conflicts, list_pending
# Re-export for backward compatibility (tests/users that imported from .sync).
from .session import new_session_id  # noqa: F401

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
        # `asdict` already walks nested dataclasses, so conflicts serialise
        # themselves correctly without manual conversion.
        return asdict(self)


def sync_plan(root: Path, session_id: str = "") -> SyncPlan | None:
    items = list_pending(root)
    if items is None:
        return None

    conflicts = detect_conflicts(items)
    bad = [it.id for it in items if it.issues]

    # Empty session_id means the caller didn't claim a session. That's common
    # when a human runs `brain sync plan` directly to inspect state. In that
    # case "this session" is meaningless; treat all items uniformly and let
    # the mode fall out of the normal checks.
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
        stale_pending_count=stale_count(root, days=STALE_DAYS_DEFAULT),
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

    # With no session_id, every pending item is "other". Collapsing multiple
    # sessions into merge_first is right (the user needs to review). But if
    # every pending item shares one session_id, there is nothing to merge
    # against — treat as `quick` so a one-shot inspection is actionable.
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
class GitState:
    initialised: bool
    clean: bool
    operation_in_progress: str | None  # "merge" | "rebase" | "cherry-pick" | "bisect" | None
    branch: str | None
    dirty_paths: list[str] = field(default_factory=list)
    untracked_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_git(root: Path) -> GitState:
    """Inspect the git state at `root` without modifying anything.

    Checks: repo presence, uncommitted changes (staged + working tree),
    untracked files, in-progress operations (merge/rebase/cherry-pick/bisect),
    and current branch. `/ProjectSync` uses this via `brain sync preflight`
    so the safety check lives in Python, not in a bash snippet whose
    correctness depends on which shell Claude happens to run.
    """
    import subprocess

    def _run(args: list[str]) -> tuple[int, str]:
        try:
            p = subprocess.run(
                ["git", *args], cwd=str(root),
                capture_output=True, text=True, timeout=10,
            )
            return p.returncode, p.stdout
        except (OSError, subprocess.SubprocessError):
            return 1, ""

    code, _ = _run(["rev-parse", "--git-dir"])
    if code != 0:
        return GitState(initialised=False, clean=True, operation_in_progress=None, branch=None)

    # Current branch (detached HEAD → "HEAD")
    _, branch_out = _run(["rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_out.strip() or None

    # Working tree status
    _, porcelain = _run(["status", "--porcelain"])
    dirty: list[str] = []
    untracked: list[str] = []
    for line in porcelain.splitlines():
        if not line:
            continue
        code2 = line[:2]
        path = line[3:].strip()
        if code2 == "??":
            untracked.append(path)
        else:
            dirty.append(path)

    # In-progress ops
    _, gitdir_out = _run(["rev-parse", "--git-dir"])
    gitdir = Path(gitdir_out.strip()) if gitdir_out.strip() else None
    if gitdir and not gitdir.is_absolute():
        gitdir = (root / gitdir).resolve()
    op = None
    if gitdir:
        if (gitdir / "MERGE_HEAD").exists():
            op = "merge"
        elif (gitdir / "rebase-merge").exists() or (gitdir / "rebase-apply").exists():
            op = "rebase"
        elif (gitdir / "CHERRY_PICK_HEAD").exists():
            op = "cherry-pick"
        elif (gitdir / "BISECT_LOG").exists():
            op = "bisect"

    clean = not dirty and not untracked and op is None
    return GitState(
        initialised=True,
        clean=clean,
        operation_in_progress=op,
        branch=branch,
        dirty_paths=dirty,
        untracked_paths=untracked,
    )


@dataclass
class Preflight:
    ok: bool                   # True when /ProjectSync is safe to proceed
    session_id: str
    git: GitState
    plan: SyncPlan | None
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        # plan dataclass already nested; asdict handles it.
        return d


def preflight(root: Path, include_wip: bool = False) -> Preflight | None:
    """One-stop safety check for `/ProjectSync`.

    Mints a session id, inspects git, runs `sync_plan`, and aggregates
    everything into a single JSON-serialisable payload. Slash commands no
    longer need to run three separate CLI calls + a bash `git diff` that
    misses untracked files. When `ok` is False, `blockers` lists the
    reasons so the slash command can surface each one to the user.

    `include_wip=True` downgrades "dirty working tree" from blocker to
    warning — for users who intentionally have un-synced work they want
    to preserve across the run. Untracked files and in-progress git
    operations are still blockers regardless.
    """
    sid = new_session_id()
    git = inspect_git(root)
    sp = sync_plan(root, session_id=sid)
    if sp is None:
        return None

    blockers: list[str] = []
    if git.initialised:
        if git.operation_in_progress:
            blockers.append(
                f"git {git.operation_in_progress} in progress — finish or abort "
                "that operation before running /ProjectSync."
            )
        if git.untracked_paths:
            blockers.append(
                f"{len(git.untracked_paths)} untracked file(s) could be overwritten. "
                "Commit or gitignore them first, or re-run with --include-wip."
            )
        if git.dirty_paths and not include_wip:
            blockers.append(
                f"{len(git.dirty_paths)} file(s) with uncommitted changes. "
                "Commit/stash them, or re-run with --include-wip to keep them."
            )

    return Preflight(
        ok=not blockers,
        session_id=sid,
        git=git,
        plan=sp,
        blockers=blockers,
    )


def render_preflight_human(pf: Preflight) -> str:
    lines = [
        f"Session id:      {pf.session_id}",
        f"Safe to proceed: {'YES' if pf.ok else 'NO'}",
        "",
        "Git:",
        f"  initialised: {pf.git.initialised}",
        f"  branch:      {pf.git.branch or '(none)'}",
        f"  clean:       {pf.git.clean}",
    ]
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
            lines.append(f"  ! {b}")
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
