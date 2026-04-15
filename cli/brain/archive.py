"""Pending-file lifecycle: move stale session files into `docs/.pending/archive/`.

Lives apart from `pending.py` (which owns parse + validate + render) because
archive is a filesystem verb, not parse logic.

Atomic collision handling. `Path.rename` has a TOCTOU race (exists-then-
rename lets another process slip in between). Instead we use `os.link`
(hard-link) → `os.unlink`, retrying on `FileExistsError`. `os.link` is
atomic on POSIX and Windows (CreateHardLinkW), so the two-step is
race-free even with concurrent sweeps.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from .pending import _find_pending_dir
from .project import detect


def append_rejected(
    root: Path,
    session_id: str,
    type_: str,
    target: str,
    body: str,
    winner_id: str,
) -> dict:
    """Append a rejected conflict-loser to `docs/.pending/archive/rejected-<session>.md`.

    Called by `/ProjectSync` Step 7 BEFORE the session's pending file is
    deleted in Step 6.6 — guarantees the loser's full body survives even
    when the target is a rule or correction (neither of which has an
    "Alternatives considered" section to host the reject in-place).

    Returns `{"path": str, "bytes_written": int}` or an error dict.
    """
    project = detect(root)
    if project is None:
        return {"error": "no_claude_md"}
    if not session_id:
        return {"error": "missing_session_id"}

    archive_dir = project.root / "docs" / ".pending" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    rejected = archive_dir / f"rejected-{session_id}.md"
    header_needed = not rejected.exists()
    date = datetime.now().strftime("%Y-%m-%d")

    parts: list[str] = []
    if header_needed:
        parts.append(f"# Rejected during /ProjectSync {session_id}\n\n")
    parts.append(f"## {type_} targeting {target}\n\n")
    parts.append(body.rstrip() + "\n\n")
    parts.append(f"**Rejected in favour of:** {winner_id}\n")
    parts.append(f"**Date:** {date}\n\n")

    chunk = "".join(parts)
    with rejected.open("a", encoding="utf-8") as f:
        f.write(chunk)
    return {
        "path": str(rejected.relative_to(project.root).as_posix()),
        "bytes_written": len(chunk.encode("utf-8")),
    }


def _atomic_move_with_suffix(src: Path, target_dir: Path, name: str) -> Path:
    """Move `src` into `target_dir/name`, suffixing `.1`, `.2`, ... on collision.

    Race-safe: tries `os.link(src, candidate)` → `os.unlink(src)`. `os.link`
    fails atomically with `FileExistsError` if the target exists, so two
    concurrent callers can't clobber each other — the loser retries with
    the next suffix. Returns the final path.
    """
    base = Path(name).stem
    suffix = Path(name).suffix
    n = 0
    while True:
        candidate = target_dir / (name if n == 0 else f"{base}.{n}{suffix}")
        try:
            os.link(str(src), str(candidate))
        except FileExistsError:
            n += 1
            continue
        except OSError:
            # Fall back to rename — cross-filesystem or FS that disallows
            # hard links. Not race-safe, but nothing is in that case.
            candidate2 = target_dir / (name if n == 0 else f"{base}.{n}{suffix}")
            if candidate2.exists():
                n += 1
                continue
            os.rename(str(src), str(candidate2))
            return candidate2
        os.unlink(str(src))
        return candidate


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

    # Track which names we already "claimed" in this dry-run so two stale
    # files with the same basename don't both report the same suffix.
    claimed: set[str] = set()

    for file in sorted(pending_dir.glob("*.md")):
        scanned += 1
        mtime = datetime.fromtimestamp(file.stat().st_mtime)
        if mtime >= cutoff:
            kept += 1
            continue

        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
            final = _atomic_move_with_suffix(file, archive_dir, file.name)
        else:
            # Simulate the suffix bump without touching disk.
            base = file.stem
            suffix_ = file.suffix
            n = 0
            while True:
                name = file.name if n == 0 else f"{base}.{n}{suffix_}"
                path = archive_dir / name
                if not path.exists() and str(path) not in claimed:
                    final = path
                    claimed.add(str(path))
                    break
                n += 1

        archived += 1
        moved.append(str(final.relative_to(project.root).as_posix()))

    return {"scanned": scanned, "archived": archived, "kept": kept, "moved_paths": moved}
