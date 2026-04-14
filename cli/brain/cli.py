"""Command-line entrypoint: `brain <command> [args]`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows so non-ASCII chars (… « →) don't crash.
# reconfigure() is Python 3.7+; safe to skip if unavailable.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

from . import __version__
from .audit import audit, render_human, render_json
from .decisions import (
    list_decisions,
    render_json as decisions_json,
    render_list_human,
    search_decisions,
)
from .drift import drift, render_human as drift_human, render_json as drift_json
from .pending import (
    list_pending,
    render_human as pending_human,
    render_json as pending_json,
)
from .query import (
    query as run_query,
    render_human as query_human,
    render_json as query_json,
)


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

    dec_p = sub.add_parser("decisions", help="Index and search the project decision ledger (ADRs).")
    dec_sub = dec_p.add_subparsers(dest="dec_command", required=True)

    dec_list = dec_sub.add_parser("list", help="List all decisions, newest first.")
    dec_list.add_argument("path", nargs="?", default=".", help="Project root")
    dec_list.add_argument("--json", action="store_true")

    dec_search = dec_sub.add_parser("search", help="Find decisions by title, topic, or body.")
    dec_search.add_argument("query", help="Substring to match (case-insensitive).")
    dec_search.add_argument("path", nargs="?", default=".", help="Project root")
    dec_search.add_argument("--json", action="store_true")

    query_p = sub.add_parser(
        "query",
        help="Retrieve the most relevant brain sections for a query (TF-IDF over CLAUDE.md + docs/).",
    )
    query_p.add_argument("text", help="Query string. Quote multi-word queries.")
    query_p.add_argument("path", nargs="?", default=".", help="Project root")
    query_p.add_argument("--top", type=int, default=3, help="Number of results to return (default 3).")
    query_p.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    pending_p = sub.add_parser(
        "pending",
        help="Inspect items staged in docs/.pending/ (used by /ProjectMerge).",
    )
    pending_sub = pending_p.add_subparsers(dest="pending_command", required=True)
    pending_list = pending_sub.add_parser("list", help="List all pending items grouped by target.")
    pending_list.add_argument("path", nargs="?", default=".", help="Project root")
    pending_list.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "audit":
        return _cmd_audit(Path(args.path), json_output=args.json)
    if args.command == "drift":
        return _cmd_drift(Path(args.path), json_output=args.json)
    if args.command == "decisions":
        if args.dec_command == "list":
            return _cmd_decisions_list(Path(args.path), json_output=args.json)
        if args.dec_command == "search":
            return _cmd_decisions_search(Path(args.path), query=args.query, json_output=args.json)
    if args.command == "query":
        return _cmd_query(Path(args.path), text=args.text, top_n=args.top, json_output=args.json)
    if args.command == "pending":
        if args.pending_command == "list":
            return _cmd_pending_list(Path(args.path), json_output=args.json)

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


def _cmd_decisions_list(path: Path, json_output: bool) -> int:
    decisions = list_decisions(path)
    if decisions is None:
        _no_brain(path, json_output)
        return 2
    print(decisions_json(decisions) if json_output else render_list_human(decisions))
    return 0


def _cmd_decisions_search(path: Path, query: str, json_output: bool) -> int:
    decisions = search_decisions(path, query)
    if decisions is None:
        _no_brain(path, json_output)
        return 2
    header = f'Decisions matching "{query}"'
    print(decisions_json(decisions) if json_output else render_list_human(decisions, header))
    return 0 if decisions else 1


def _cmd_query(path: Path, text: str, top_n: int, json_output: bool) -> int:
    hits = run_query(path, text, top_n=top_n)
    if hits is None:
        _no_brain(path, json_output)
        return 2
    print(query_json(hits) if json_output else query_human(hits, text))
    return 0 if hits else 1


def _cmd_pending_list(path: Path, json_output: bool) -> int:
    items = list_pending(path)
    if items is None:
        _no_brain(path, json_output)
        return 2
    print(pending_json(items) if json_output else pending_human(items))
    return 0


def _no_brain(path: Path, json_output: bool) -> None:
    msg = f"No CLAUDE.md found at {path.resolve()}. Run /ProjectNewSetup first."
    if json_output:
        print('{"error": "no_claude_md", "path": "%s"}' % path.resolve())
    else:
        print(msg, file=sys.stderr)
