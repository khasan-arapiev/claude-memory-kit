"""Pending-file lifecycle: move stale session files into `docs/.pending/archive/`.

Lives apart from `pending.py` (which owns parse + validate + render) because
archive is a filesystem verb, not parse logic. Collision-safe: if an archive
file with the same name already exists (abandoned sweep, duplicate session
id, manual mess), suffixes `.1`, `.2`, ... are appended until the target is
free. No data-loss on either Windows (where `Path.rename` raises) or POSIX
(where it silently overwrites).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from .pending import _find_pending_dir
from .project import detect


def _unique_target(target: Path) -> Path:
    """Return a path that does not yet exist by adding `.N` before `.md`.

    Examples:
      foo.md  (free)     -> foo.md
      foo.md  (taken)    -> foo.1.md
      foo.1.md (taken)   -> foo.2.md
    """
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    n = 1
    while True:
        candidate = parent / f"{stem}.{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def archive_old(root: Path, days: int = 14, dry_run: bool = False) -> dict:
    """Move pending files older than `days` into docs/.pending/archive/.

    Stale pending files block `/ProjectSync` forever in `merge_first` mode
    because they get counted as "other session" items. After a couple of
    weeks with no review they're almost always abandoned. This gives the
    user a safe way to sweep them aside without deleting anything.

    Returns: `{"scanned": int, "archived": int, "kept": int, "moved_paths": [str...]}`
    On a missing project: `{"error": "no_claude_md", ...}`.
    """
    project = detect(root)
    if project is None:
        return {"error": "no_claude_md", "scanned": 0, "archived": 0, "kept": 0, "moved_paths": []}

    pending_dir = _find_pending_dir(project.root)
    if pending_dir is None or not pending_dir.is_dir():
        return {"scanned": 0, "archived": 0, "kept": 0, "moved_paths": []}

    archive_dir = pending_dir / "archive"
    cutoff = datetime.now() - timedelta(days=days)
    scanned = archived = kept = 0
    moved: list[str] = []

    for file in sorted(pending_dir.glob("*.md")):
        scanned += 1
        mtime = datetime.fromtimestamp(file.stat().st_mtime)
        if mtime >= cutoff:
            kept += 1
            continue

        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
            target = _unique_target(archive_dir / file.name)
            file.rename(target)
        else:
            # In dry-run we still compute what the target *would* be so the
            # report is accurate. mkdir is skipped.
            target = _unique_target(archive_dir / file.name)

        archived += 1
        moved.append(str(target.relative_to(project.root).as_posix()))

    return {"scanned": scanned, "archived": archived, "kept": kept, "moved_paths": moved}


def stale_count(root: Path, days: int = 14) -> int:
    """How many pending files would be archived by `archive_old(days=days)`?

    Read-only helper used by `brain sync plan` to include a `stale_pending_count`
    field so slash commands can surface `brain pending archive` when merge_first
    keeps triggering.
    """
    project = detect(root)
    if project is None:
        return 0
    pending_dir = _find_pending_dir(project.root)
    if pending_dir is None or not pending_dir.is_dir():
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    count = 0
    for file in pending_dir.glob("*.md"):
        if datetime.fromtimestamp(file.stat().st_mtime) < cutoff:
            count += 1
    return count
