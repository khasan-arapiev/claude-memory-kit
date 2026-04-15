"""Shared fixtures/helpers for test modules. Kept inside tests/ so it ships
with the test suite but does not collide with the package namespace.

Usage from a test file:

    from tests._helpers import clone_clean, stage_pending

    with tempfile.TemporaryDirectory() as tmp:
        proj = clone_clean(Path(tmp))
        stage_pending(proj, "2026-04-15-0900-aaaa", body="...")
"""
from __future__ import annotations

import shutil
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FIXTURES = _REPO_ROOT / "tests" / "fixtures"


def clone_clean(tmp: Path) -> Path:
    """Copy the `clean` fixture into `tmp/proj/`. Returns the project path."""
    proj = tmp / "proj"
    shutil.copytree(_FIXTURES / "clean", proj)
    return proj


def stage_pending(proj: Path, session_id: str, body: str) -> Path:
    """Write `body` to `proj/docs/.pending/<session_id>.md`. Returns the path."""
    pending = proj / "docs" / ".pending"
    pending.mkdir(parents=True, exist_ok=True)
    file = pending / f"{session_id}.md"
    file.write_text(body, encoding="utf-8")
    return file


def minimal_item(
    type_: str = "rule",
    target: str = "docs/strategy/WRITING-RULES.md",
    body: str = "Short sentences only.",
    confidence: str = "high",
) -> str:
    """Build a one-item pending-file body for quick fixtures."""
    return (
        f"# Pending - stub\n\n"
        f"## {type_}\n"
        f"**target:** {target}\n"
        f"**confidence:** {confidence}\n\n"
        f"{body}\n"
    )
