"""`brain audit` - deterministic project-brain health check.

Emits structured findings and a 0-100 hygiene score. Designed to be called
from a slash command like /ProjectSetupFix, which reads the JSON and narrates
results to the user without doing its own counting.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .drift import drift as run_drift
from .project import (
    Project,
    detect,
    estimate_tokens,
    is_valid_doc_name,
    iter_doc_files,
    read_md,
)

# An explicit route to the decisions folder. Matches `[text](docs/decisions/...)`,
# `[text](decisions/...)`, or bare backticked paths like `` `docs/decisions/` ``.
# Substring presence of the word "decisions" is too loose (false positives in prose).
DECISIONS_ROUTE_RE = re.compile(
    r"(?:\]\([^)]*\bdecisions/?[^)]*\))|(?:`[^`]*\bdecisions/?[^`]*`)",
    re.IGNORECASE,
)

# Budgets (token-based, not line-based)
CLAUDE_MD_TOKEN_CAP = 3000        # ~200 lines dense prose
CLAUDE_MD_TOKEN_WARN = 2250       # ~150 lines
DOC_TOKEN_CAP = 7500              # ~500 lines

# Scoring weights (must sum to 100)
WEIGHTS = {
    "orphans": 25,
    "dead_links": 25,
    "claude_md_size": 15,
    "doc_size": 15,
    "naming": 10,
    "writing_rules": 5,
    "sensitive_files": 5,
}


@dataclass
class Finding:
    kind: str
    path: str
    detail: str = ""


@dataclass
class AuditReport:
    project_path: str
    layout: str
    brain_version: int | None
    has_marker: bool
    orphans: list[Finding] = field(default_factory=list)
    dead_links: list[Finding] = field(default_factory=list)
    naming_violations: list[Finding] = field(default_factory=list)
    oversize_docs: list[Finding] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    claude_md_tokens: int = 0
    total_brain_tokens: int = 0
    doc_count: int = 0
    drift_count: int = 0        # docs whose described code has changed since sync
    tracked_docs: int = 0       # docs that opted into drift tracking via frontmatter
    score: int = 0
    summary: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


def audit(root: Path) -> AuditReport | None:
    project = detect(root)
    if project is None:
        return None

    report = AuditReport(
        project_path=str(project.root),
        layout=project.layout,
        brain_version=project.brain_version,
        has_marker=project.has_marker,
    )
    report.claude_md_tokens = estimate_tokens(project.claude_md_text)

    docs = iter_doc_files(project)
    report.doc_count = len(docs)

    _scan_orphans(project, docs, report)
    _scan_dead_links(project, report)
    _scan_naming(docs, report)
    _scan_doc_sizes(docs, report)
    _scan_sections(project, report)
    _scan_required_files(project, report)

    report.total_brain_tokens = report.claude_md_tokens + sum(
        estimate_tokens(read_md(p)) for p in docs
    )

    drift_report = run_drift(project.root)
    if drift_report is not None:
        report.tracked_docs = drift_report.tracked_docs
        report.drift_count = len(drift_report.drift) + len(drift_report.missing_files)

    report.score = _score(report)
    report.summary = _summarize(report)
    return report


def _scan_orphans(project: Project, docs: list[Path], report: AuditReport) -> None:
    """Flag docs not referenced from CLAUDE.md.

    Files inside `decisions/` are exempt: ADRs are indexed by date/topic via
    `brain decisions`, not by per-file CLAUDE.md route. As long as CLAUDE.md
    routes the decisions folder itself (or mentions it anywhere), individual
    ADRs are considered discoverable.
    """
    text = project.claude_md_text
    # Require an explicit route to `decisions/`, not a prose mention of the word.
    decisions_routed = bool(DECISIONS_ROUTE_RE.search(text))
    for doc in docs:
        # Only exempt the canonical docs/decisions/ folder at project root,
        # not any nested folder happening to be named "decisions".
        rel_parts = doc.relative_to(project.root).parts
        is_top_level_adr = (
            len(rel_parts) >= 2
            and rel_parts[0] == "docs"
            and rel_parts[1] == "decisions"
        )
        if is_top_level_adr and decisions_routed:
            continue
        name = doc.name
        rel = doc.relative_to(project.root).as_posix()
        if name in text or rel in text:
            continue
        report.orphans.append(
            Finding(kind="orphan", path=rel, detail=f"{name} is not referenced in CLAUDE.md")
        )


def _scan_dead_links(project: Project, report: AuditReport) -> None:
    """Flag markdown links and backticked paths that point to missing .md files.

    Only explicit routes count: `[text](path.md)` and `` `path.md` `` forms.
    Bare filename mentions in prose are ignored (too noisy, they're not routes).
    """
    patterns = [
        re.compile(r"\]\(([^)]+\.md)(?:#[^)]*)?\)"),   # [text](path.md)
        re.compile(r"`([^`\s]+\.md)`"),                # `path.md`
    ]
    seen: set[str] = set()
    text = project.claude_md_text
    for pat in patterns:
        for m in pat.finditer(text):
            target = m.group(1).strip()
            if target in seen:
                continue
            # Skip external references: URLs, mailto, home-dir, absolute paths,
            # Windows drive letters, and parent-relative escapes (../../).
            if target.startswith((
                "http://", "https://", "mailto:",
                "~", "/", "\\",
                "../",
            )):
                continue
            if re.match(r"^[A-Za-z]:[\\/]", target):  # Windows drive (C:\, D:/)
                continue
            seen.add(target)
            # Resolve against project root, then docs/
            paths = [project.root / target, project.root / "docs" / target]
            if not any(p.is_file() for p in paths):
                report.dead_links.append(
                    Finding(
                        kind="dead_link",
                        path=target,
                        detail="referenced in CLAUDE.md but file not found",
                    )
                )


def _scan_naming(docs: list[Path], report: AuditReport) -> None:
    for doc in docs:
        if is_valid_doc_name(doc):
            continue
        report.naming_violations.append(
            Finding(
                kind="naming",
                path=str(doc),
                detail=f"{doc.name} is not SCREAMING-KEBAB-CASE (or ADR format under decisions/)",
            )
        )


def _scan_doc_sizes(docs: list[Path], report: AuditReport) -> None:
    for doc in docs:
        tokens = estimate_tokens(read_md(doc))
        if tokens > DOC_TOKEN_CAP:
            report.oversize_docs.append(
                Finding(
                    kind="oversize",
                    path=str(doc),
                    detail=f"{tokens} tokens exceeds cap {DOC_TOKEN_CAP}",
                )
            )


def _scan_sections(project: Project, report: AuditReport) -> None:
    """Tolerates numbered headings: `## 2. Writing Rules` counts the same."""
    text = project.claude_md_text
    if not re.search(r"^##\s+(?:\d+\.\s+)?Writing Rules\b", text, re.MULTILINE):
        report.missing_sections.append("Writing Rules")
    if not re.search(r"^##\s+(?:\d+\.\s+)?Sensitive Files\b", text, re.MULTILINE):
        report.missing_sections.append("Sensitive Files")


def _scan_required_files(project: Project, report: AuditReport) -> None:
    if not (project.root / "README.md").is_file():
        report.missing_files.append("README.md")


def _score(r: AuditReport) -> int:
    s = 0
    if not r.orphans:
        s += WEIGHTS["orphans"]
    if not r.dead_links:
        s += WEIGHTS["dead_links"]

    # CLAUDE.md size: full weight under warn threshold, half between warn and cap, zero over cap
    if r.claude_md_tokens <= CLAUDE_MD_TOKEN_WARN:
        s += WEIGHTS["claude_md_size"]
    elif r.claude_md_tokens <= CLAUDE_MD_TOKEN_CAP:
        s += WEIGHTS["claude_md_size"] // 2

    # Doc size: -5 per oversize doc, floor 0
    s += max(0, WEIGHTS["doc_size"] - 5 * len(r.oversize_docs))

    if not r.naming_violations:
        s += WEIGHTS["naming"]

    if "Writing Rules" not in r.missing_sections:
        s += WEIGHTS["writing_rules"]
    if "Sensitive Files" not in r.missing_sections:
        s += WEIGHTS["sensitive_files"]

    return min(100, s)


def _summarize(r: AuditReport) -> str:
    parts = []
    if r.orphans:
        parts.append(f"{len(r.orphans)} orphan(s)")
    if r.dead_links:
        parts.append(f"{len(r.dead_links)} dead link(s)")
    if r.naming_violations:
        parts.append(f"{len(r.naming_violations)} naming violation(s)")
    if r.oversize_docs:
        parts.append(f"{len(r.oversize_docs)} oversize doc(s)")
    if r.drift_count:
        parts.append(f"{r.drift_count} doc(s) drifted")
    if r.missing_sections:
        parts.append("missing: " + ", ".join(r.missing_sections))
    if r.missing_files:
        parts.append("missing file(s): " + ", ".join(r.missing_files))
    if not parts:
        return "clean"
    return "; ".join(parts)


def render_human(r: AuditReport) -> str:
    """Pretty-print an audit report for terminal output."""
    lines = [
        f"Project:        {r.project_path}",
        f"Layout:         {r.layout}",
        f"Brain version:  {r.brain_version if r.brain_version else '(unmarked)'}",
        f"Managed marker: {'yes' if r.has_marker else 'NO'}",
        "",
        f"Brain health:   {r.score}%  ({r.summary})",
        "",
        f"CLAUDE.md:      {r.claude_md_tokens} tokens "
        f"(warn {CLAUDE_MD_TOKEN_WARN}, cap {CLAUDE_MD_TOKEN_CAP})",
        f"Total brain:    {r.total_brain_tokens} tokens across {r.doc_count} doc(s)",
        f"Drift tracking: {r.tracked_docs} doc(s) tracked, {r.drift_count} drifted",
    ]
    if r.orphans:
        lines += ["", "Orphans:"] + [f"  - {f.path}" for f in r.orphans]
    if r.dead_links:
        lines += ["", "Dead links:"] + [f"  - {f.path}: {f.detail}" for f in r.dead_links]
    if r.naming_violations:
        lines += ["", "Naming violations:"] + [f"  - {f.path}" for f in r.naming_violations]
    if r.oversize_docs:
        lines += ["", "Oversize docs:"] + [f"  - {f.path}: {f.detail}" for f in r.oversize_docs]
    if r.missing_sections:
        lines += ["", "Missing sections:"] + [f"  - {s}" for s in r.missing_sections]
    if r.missing_files:
        lines += ["", "Missing files:"] + [f"  - {s}" for s in r.missing_files]
    return "\n".join(lines)


def render_json(r: AuditReport) -> str:
    return json.dumps(r.to_dict(), indent=2)
