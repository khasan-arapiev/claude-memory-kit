"""Project detection and shared filesystem helpers.

A claude-memory-kit project has one of three layouts:
- project: contains CLAUDE.md + docs/ (and usually project/)
- router:  contains CLAUDE.md + sub-folders that are themselves projects, no local docs/
- flat:    contains CLAUDE.md + .md files at root, no docs/ folder (small projects)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


MANAGED_MARKER = "project-brain: managed"
# Marker must appear inside an HTML comment or YAML frontmatter to count as managed.
# This prevents prose mentions ("> the project-brain: managed marker") from being false-positives.
#
# NOTE: the string `project-brain: managed` is preserved forever as the
# backwards-compatible identifier. The product is called Claude Memory Kit
# (v0.3.1+) but every CLAUDE.md file — including ones out in the wild from
# the project-brain era — uses this marker to signal "this file is managed
# by the skill." Changing the marker string would break all existing installs.
MANAGED_MARKER_RE = re.compile(
    r"<!--[^>]*project-brain:\s*managed[^>]*-->|^---[\s\S]*?project-brain[\s\S]*?---",
    re.MULTILINE,
)
SCREAMING_KEBAB_RE = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")
# ADR format: YYYY-MM-DD-SCREAMING-KEBAB
ADR_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
# Filenames that are allowed to break SCREAMING-KEBAB-CASE (top-level convention files)
NAMING_EXEMPT = {"README.md", "CLAUDE.md", "CHANGELOG.md", "LICENSE.md"}


def is_valid_doc_name(path: Path) -> bool:
    """Check if a doc filename matches claude-memory-kit naming conventions.

    Accepts SCREAMING-KEBAB-CASE.md, or ADR format (YYYY-MM-DD-TITLE.md) inside a
    decisions/ folder.
    """
    if path.name in NAMING_EXEMPT:
        return True
    stem = path.stem
    if SCREAMING_KEBAB_RE.match(stem):
        return True
    if "decisions" in path.parts and ADR_NAME_RE.match(stem):
        return True
    return False


@dataclass
class Project:
    root: Path
    claude_md: Path
    layout: str  # "project" | "router" | "flat"
    docs_dir: Path | None
    brain_version: int | None
    claude_md_text: str
    sub_projects: list[Path] = field(default_factory=list)

    @property
    def has_marker(self) -> bool:
        return bool(MANAGED_MARKER_RE.search(self.claude_md_text))


def detect(root: Path) -> Project | None:
    """Inspect `root` and return a Project, or None if no CLAUDE.md found."""
    root = root.resolve()
    claude = root / "CLAUDE.md"
    if not claude.is_file():
        return None

    text = read_md(claude)
    docs = root / "docs"
    has_docs = docs.is_dir()

    # Find sub-projects: immediate child folders containing a CLAUDE.md
    sub_projects = []
    for child in root.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            if (child / "CLAUDE.md").is_file():
                sub_projects.append(child)

    if has_docs:
        layout = "project"
    elif sub_projects and not has_docs:
        layout = "router"
    else:
        layout = "flat"

    return Project(
        root=root,
        claude_md=claude,
        layout=layout,
        docs_dir=docs if has_docs else None,
        brain_version=parse_version(text),
        claude_md_text=text,
        sub_projects=sub_projects,
    )


def parse_version(text: str) -> int | None:
    """Parse brain version from CLAUDE.md.

    The marker string is always `project-brain:` — the original identifier,
    preserved across renames for backwards compatibility. See MANAGED_MARKER_RE.

    Supports:
      <!-- project-brain: managed -->            -> version 1 (implicit)
      <!-- project-brain: managed v2 -->         -> version 2
      YAML frontmatter  project-brain: {version:N} -> version N
    """
    m = re.search(r"project-brain:\s*managed(?:\s+v(\d+))?", text)
    if m:
        return int(m.group(1)) if m.group(1) else 1
    m = re.search(r"project-brain:[^\n]*version:\s*(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def iter_doc_files(project: Project) -> list[Path]:
    """Return all brain doc files depending on layout.

    For `project` layout: everything under docs/ (excluding .pending/ and archive/).
    For `flat` layout:    all .md at root except CLAUDE.md, README.md etc.
    For `router` layout:  no local docs (sub-projects audit themselves).
    """
    if project.layout == "project" and project.docs_dir:
        return sorted(
            p for p in project.docs_dir.rglob("*.md")
            if ".pending" not in p.parts and "archive" not in p.parts
        )
    if project.layout == "flat":
        return sorted(
            p for p in project.root.glob("*.md")
            if p.name not in NAMING_EXEMPT
        )
    return []


def read_md(path: Path) -> str:
    """Read a markdown file with UTF-8 tolerance and LF-normalised line endings.

    Single place for the encoding dance. Returns "" on `OSError` (permissions,
    missing file) rather than raising, so audits of large trees with a few
    unreadable files don't crash mid-scan. `ValueError` and other programmer
    errors are intentionally NOT caught — they should surface as tracebacks.

    `Path.read_text` already does universal-newline translation in text mode,
    but only when the host OS's native newline is `\\n`. A CRLF file read on
    a Windows host (or a lone-CR file anywhere) can leak `\\r` into the
    string and break regexes that pin on `\\n`. The explicit normalisation
    below handles those edge cases.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def estimate_tokens(text: str) -> int:
    """Rough token estimate: chars / 4 (close enough for budgeting).

    Real tokenizers like tiktoken would be more accurate but add a dependency.
    For brain-size budgeting this approximation is stable and good enough.
    """
    return max(1, len(text) // 4)
