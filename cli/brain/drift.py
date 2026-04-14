"""`brain drift` - detect docs that describe code which has since changed.

Docs can opt into drift tracking with frontmatter:

    ---
    describes:
      - project/pages/checkout.html
      - project/assets/js/checkout.js
    last-synced: 2026-04-14
    ---

Drift rule: a described file was modified more recently than the doc's
`last-synced` date (or, if absent, the doc's own mtime). When drift is
detected, the doc is likely stale and should be reviewed.

Keeps the brain honest: no more docs rotting quietly while code evolves.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

from .frontmatter import parse_file
from .project import Project, detect, iter_doc_files


@dataclass
class DriftItem:
    doc: str
    described_file: str
    doc_synced: str         # ISO date or "(mtime)"
    file_modified: str      # ISO date
    days_behind: int


@dataclass
class DriftReport:
    project_path: str
    tracked_docs: int       # docs with `describes` frontmatter
    drift: list[DriftItem] = field(default_factory=list)
    missing_files: list[DriftItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def drift(root: Path) -> DriftReport | None:
    project = detect(root)
    if project is None:
        return None

    report = DriftReport(project_path=str(project.root), tracked_docs=0)

    for doc in iter_doc_files(project):
        fm = parse_file(doc)
        described = fm.list_of("describes")
        if not described:
            continue
        report.tracked_docs += 1

        synced = _sync_date(fm.get("last-synced"), doc)
        synced_label = (
            fm.get("last-synced").isoformat()
            if isinstance(fm.get("last-synced"), date)
            else "(mtime)"
        )

        for rel in described:
            target = (project.root / rel).resolve()
            if not target.exists():
                report.missing_files.append(
                    DriftItem(
                        doc=str(doc.relative_to(project.root).as_posix()),
                        described_file=rel,
                        doc_synced=synced_label,
                        file_modified="(missing)",
                        days_behind=-1,
                    )
                )
                continue

            file_mod = datetime.fromtimestamp(target.stat().st_mtime).date()
            if file_mod > synced:
                report.drift.append(
                    DriftItem(
                        doc=str(doc.relative_to(project.root).as_posix()),
                        described_file=rel,
                        doc_synced=synced_label,
                        file_modified=file_mod.isoformat(),
                        days_behind=(file_mod - synced).days,
                    )
                )

    return report


def _sync_date(last_synced, doc: Path) -> date:
    if isinstance(last_synced, date):
        return last_synced
    # Fallback: doc's own mtime
    return datetime.fromtimestamp(doc.stat().st_mtime).date()


def render_human(r: DriftReport) -> str:
    lines = [
        f"Project:       {r.project_path}",
        f"Tracked docs:  {r.tracked_docs} (docs with `describes:` frontmatter)",
        "",
    ]
    if not r.tracked_docs:
        lines.append("No docs declare `describes:` yet. Add frontmatter to start drift tracking.")
        lines.append("See cli/README.md § Frontmatter spec.")
        return "\n".join(lines)

    if not r.drift and not r.missing_files:
        lines.append("All tracked docs are in sync with their described files.")
        return "\n".join(lines)

    if r.drift:
        lines.append(f"Drift ({len(r.drift)}):")
        for d in r.drift:
            lines.append(
                f"  - {d.doc}"
                f"\n      describes: {d.described_file}"
                f"\n      doc synced: {d.doc_synced}, file modified: {d.file_modified} "
                f"({d.days_behind} days behind)"
            )
    if r.missing_files:
        lines.append("")
        lines.append(f"Missing described files ({len(r.missing_files)}):")
        for d in r.missing_files:
            lines.append(f"  - {d.doc} references missing {d.described_file}")
    return "\n".join(lines)


def render_json(r: DriftReport) -> str:
    return json.dumps(r.to_dict(), indent=2, default=str)
