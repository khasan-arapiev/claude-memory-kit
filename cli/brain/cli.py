"""Command-line entrypoint: `brain <command> [args]`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .audit import audit, render_human, render_json
from .drift import drift, render_human as drift_human, render_json as drift_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brain",
        description="Project Brain CLI - deterministic tooling for project-brain projects.",
    )
    parser.add_argument("--version", action="version", version=f"brain {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    audit_p = sub.add_parser("audit", help="Audit a project-brain folder and report health.")
    audit_p.add_argument("path", nargs="?", default=".", help="Project root (default: current directory)")
    audit_p.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    drift_p = sub.add_parser(
        "drift",
        help="Detect docs whose described code files have changed since last sync.",
    )
    drift_p.add_argument("path", nargs="?", default=".", help="Project root (default: current directory)")
    drift_p.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    args = parser.parse_args(argv)

    if args.command == "audit":
        return _cmd_audit(Path(args.path), json_output=args.json)
    if args.command == "drift":
        return _cmd_drift(Path(args.path), json_output=args.json)

    return 2  # unreachable


def _cmd_audit(path: Path, json_output: bool) -> int:
    report = audit(path)
    if report is None:
        msg = f"No CLAUDE.md found at {path.resolve()}. Run /ProjectNewSetup first."
        if json_output:
            print('{"error": "no_claude_md", "path": "%s"}' % path.resolve())
        else:
            print(msg, file=sys.stderr)
        return 1

    print(render_json(report) if json_output else render_human(report))
    # Exit 0 for healthy brains, 1 if any findings, for CI usage
    has_findings = any([
        report.orphans, report.dead_links, report.naming_violations,
        report.oversize_docs, report.missing_sections, report.missing_files,
    ])
    return 1 if has_findings else 0


def _cmd_drift(path: Path, json_output: bool) -> int:
    report = drift(path)
    if report is None:
        msg = f"No CLAUDE.md found at {path.resolve()}. Run /ProjectNewSetup first."
        if json_output:
            print('{"error": "no_claude_md", "path": "%s"}' % path.resolve())
        else:
            print(msg, file=sys.stderr)
        return 2

    print(drift_json(report) if json_output else drift_human(report))
    return 1 if (report.drift or report.missing_files) else 0
