"""`brain decisions` - index and search the project decision ledger.

ADRs (Architecture Decision Records) live under `docs/decisions/` with
`YYYY-MM-DD-TITLE.md` naming. They use frontmatter for machine-readable
fields and prose for the human-readable rationale.

This module gives Claude (and humans) a fast, deterministic way to ask
"have we already decided X?" without re-reading every ADR.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from .frontmatter import parse_file
from .project import detect


# ADR id is the filename stem: 2026-04-14-LIVING-DOCS-MODEL
ADR_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")
TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
LEGACY_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*(\w+)", re.IGNORECASE)


@dataclass
class Decision:
    id: str                          # filename stem
    path: str                        # relative to project root
    date: str                        # ISO date
    title: str
    status: str                      # active | superseded | deprecated | proposed
    topics: list[str] = field(default_factory=list)
    supersedes: str | None = None
    superseded_by: str | None = None  # populated post-scan
    body_excerpt: str = ""           # first ~200 chars of body for previews
    warnings: list[str] = field(default_factory=list)  # frontmatter enum issues

    def to_dict(self) -> dict:
        return asdict(self)


def list_decisions(root: Path) -> list[Decision] | None:
    """Return all ADRs in the project, sorted newest first."""
    project = detect(root)
    if project is None:
        return None

    decisions_dir = project.root / "docs" / "decisions"
    if not decisions_dir.is_dir():
        return []

    decisions: list[Decision] = []
    by_id: dict[str, Decision] = {}

    for path in sorted(decisions_dir.glob("*.md"), reverse=True):
        d = _parse_adr(path, project.root)
        if d is None:
            continue
        decisions.append(d)
        by_id[d.id] = d

    # Wire up superseded_by back-references
    for d in decisions:
        if d.supersedes and d.supersedes in by_id:
            by_id[d.supersedes].superseded_by = d.id
            if by_id[d.supersedes].status == "active":
                by_id[d.supersedes].status = "superseded"

    return decisions


def search_decisions(root: Path, query: str) -> list[Decision] | None:
    """Search ADRs by title, topic, or body content (case-insensitive substring)."""
    all_dec = list_decisions(root)
    if all_dec is None:
        return None
    q = query.lower().strip()
    if not q:
        return all_dec

    matches: list[Decision] = []
    for d in all_dec:
        haystack = " ".join([
            d.title.lower(),
            " ".join(t.lower() for t in d.topics),
            d.body_excerpt.lower(),
        ])
        if q in haystack:
            matches.append(d)
    return matches


def _parse_adr(path: Path, project_root: Path) -> Decision | None:
    m = ADR_FILENAME_RE.match(path.name)
    if not m:
        return None
    iso_date = m.group(1)
    slug = m.group(2)

    fm = parse_file(path)

    # Title: first H1 in body, fallback to slug
    title_match = TITLE_RE.search(fm.body)
    title = title_match.group(1).strip() if title_match else slug.replace("-", " ").title()

    # Status: frontmatter first, fall back to legacy "**Status:**" line
    status = fm.get("status") or _legacy_status(fm.body) or "active"
    if isinstance(status, str):
        status = status.lower()

    topics = fm.list_of("topics")
    supersedes = fm.get("supersedes")
    if isinstance(supersedes, str) and supersedes.strip() == "":
        supersedes = None

    excerpt = _excerpt(fm.body)

    return Decision(
        id=path.stem,
        path=str(path.relative_to(project_root).as_posix()),
        date=iso_date,
        title=title,
        status=status,
        topics=topics,
        supersedes=supersedes,
        body_excerpt=excerpt,
        warnings=fm.validate(),
    )


_STATUS_ALIASES = {
    "accepted": "active",
    "approved": "active",
}


def _legacy_status(body: str) -> str | None:
    m = LEGACY_STATUS_RE.search(body)
    if not m:
        return None
    raw = m.group(1).lower()
    return _STATUS_ALIASES.get(raw, raw)


def _excerpt(body: str, n: int = 200) -> str:
    # Strip H1 and frontmatter remnants, take first non-empty paragraph
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("**Date:**"):
            continue
        lines.append(s)
        if sum(len(x) for x in lines) > n:
            break
    text = " ".join(lines)
    return text[:n] + ("…" if len(text) > n else "")


def render_list_human(decisions: list[Decision], header: str = "Decisions") -> str:
    if not decisions:
        return f"{header}: none found."
    lines = [f"{header} ({len(decisions)}):", ""]
    for d in decisions:
        marker = {
            "active": "[A]",
            "superseded": "[S]",
            "deprecated": "[D]",
            "proposed": "[P]",
        }.get(d.status, "[?]")
        topics = f"  topics: {', '.join(d.topics)}" if d.topics else ""
        chain = ""
        if d.supersedes:
            chain += f"  supersedes: {d.supersedes}"
        if d.superseded_by:
            chain += f"  superseded_by: {d.superseded_by}"
        lines.append(f"{marker} {d.date}  {d.title}")
        lines.append(f"    {d.path}")
        if topics or chain:
            lines.append(f"   {topics}{chain}")
        if d.body_excerpt:
            lines.append(f"    « {d.body_excerpt}")
        lines.append("")
    lines.append("Legend: [A]ctive  [S]uperseded  [D]eprecated  [P]roposed")
    return "\n".join(lines)


def render_json(decisions: list[Decision]) -> str:
    return json.dumps([d.to_dict() for d in decisions], indent=2)
