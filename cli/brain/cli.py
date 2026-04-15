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
    archive_old,
    detect_conflicts,
    list_pending,
    render_human as pending_human,
    render_json as pending_json,
)
from .query import (
    query as run_query,
    render_human as query_human,
    render_json as query_json,
)
from .sync import (
    new_session_id,
    render_human as sync_human,
    render_json as sync_json,
    sync_plan,
)


def _guard(fn):
    """Wrap a CLI handler so IO errors become structured failures, not crashes.

    Lets huge-project audits survive a locked file or a stale symlink instead
    of aborting half-scanned. Returns exit code 3 on unhandled IO issues.

    Scope is intentionally narrow: only `OSError` (and its subclasses
    like `PermissionError`, `FileNotFoundError`). `ValueError` and friends
    are *programmer* errors — if one escapes a handler, we want the
    traceback, not a misleading "IO error" message.
    """
    def wrapped(*args, **kwargs) -> int:
        try:
            return fn(*args, **kwargs)
        except OSError as e:
            print(f"brain: IO error: {e}", file=sys.stderr)
            return 3
    wrapped.__name__ = fn.__name__
    return wrapped


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
        help="Inspect items staged in docs/.pending/ (used by /ProjectSync).",
    )
    pending_sub = pending_p.add_subparsers(dest="pending_command", required=True)
    pending_list = pending_sub.add_parser("list", help="List all pending items grouped by target.")
    pending_list.add_argument("path", nargs="?", default=".", help="Project root")
    pending_list.add_argument("--json", action="store_true")

    pending_archive = pending_sub.add_parser(
        "archive",
        help="Move stale pending files (older than --days) into docs/.pending/archive/.",
    )
    pending_archive.add_argument("path", nargs="?", default=".", help="Project root")
    pending_archive.add_argument(
        "--days", type=int, default=14,
        help="Archive files older than this many days (default 14).",
    )
    pending_archive.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be moved without touching the filesystem.",
    )
    pending_archive.add_argument("--json", action="store_true")

    sync_p = sub.add_parser(
        "sync",
        help="State-aware planner for /ProjectSync (decides stage vs merge vs quick).",
    )
    sync_sub = sync_p.add_subparsers(dest="sync_command", required=True)
    sync_plan_p = sync_sub.add_parser(
        "plan",
        help="Inspect docs/.pending/ and emit the recommended action for this session.",
    )
    sync_plan_p.add_argument("path", nargs="?", default=".", help="Project root")
    sync_plan_p.add_argument(
        "--session-id", default="",
        help="Current session id. When unset, mode is computed session-agnostic.",
    )
    sync_plan_p.add_argument("--json", action="store_true")

    sync_newid_p = sync_sub.add_parser(
        "new-session-id",
        help="Emit a fresh session id (stdlib-only — no shell dependencies).",
    )
    sync_newid_p.add_argument(
        "--json", action="store_true",
        help='Emit as JSON ({"session_id": "..."}) instead of bare string.',
    )

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
        if args.pending_command == "archive":
            return _cmd_pending_archive(
                Path(args.path),
                days=args.days,
                dry_run=args.dry_run,
                json_output=args.json,
            )
    if args.command == "sync":
        if args.sync_command == "plan":
            return _cmd_sync_plan(
                Path(args.path),
                session_id=args.session_id,
                json_output=args.json,
            )
        if args.sync_command == "new-session-id":
            return _cmd_sync_new_id(json_output=args.json)

    return 2  # unreachable


@_guard
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


@_guard
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


@_guard
def _cmd_decisions_list(path: Path, json_output: bool) -> int:
    decisions = list_decisions(path)
    if decisions is None:
        _no_brain(path, json_output)
        return 2
    print(decisions_json(decisions) if json_output else render_list_human(decisions))
    return 0


@_guard
def _cmd_decisions_search(path: Path, query: str, json_output: bool) -> int:
    decisions = search_decisions(path, query)
    if decisions is None:
        _no_brain(path, json_output)
        return 2
    header = f'Decisions matching "{query}"'
    print(decisions_json(decisions) if json_output else render_list_human(decisions, header))
    return 0 if decisions else 1


@_guard
def _cmd_query(path: Path, text: str, top_n: int, json_output: bool) -> int:
    hits = run_query(path, text, top_n=top_n)
    if hits is None:
        _no_brain(path, json_output)
        return 2
    print(query_json(hits) if json_output else query_human(hits, text))
    return 0 if hits else 1


@_guard
def _cmd_pending_list(path: Path, json_output: bool) -> int:
    items = list_pending(path)
    if items is None:
        _no_brain(path, json_output)
        return 2
    conflicts = detect_conflicts(items)
    if json_output:
        print(pending_json(items, conflicts))
    else:
        print(pending_human(items, conflicts))
    # Non-zero if attention is needed: conflicts OR validation issues. CI
    # scripts should see a red light when pending files have broken items
    # (bad type, missing target, unknown placeholder) — previously the
    # exit code was 0 and only the human output surfaced the issues.
    has_issues = any(it.issues for it in items)
    return 1 if (conflicts or has_issues) else 0


@_guard
def _cmd_pending_archive(path: Path, days: int, dry_run: bool, json_output: bool) -> int:
    result = archive_old(path, days=days, dry_run=dry_run)
    if "error" in result:
        _no_brain(path, json_output)
        return 2
    if json_output:
        import json as _json
        result["dry_run"] = dry_run
        result["days"] = days
        print(_json.dumps(result, indent=2))
    else:
        verb = "Would move" if dry_run else "Moved"
        print(f"Scanned: {result['scanned']} pending file(s)")
        print(f"{verb}: {result['archived']}  Kept: {result['kept']}  "
              f"(cutoff: {days} day(s))")
        for p in result["moved_paths"]:
            print(f"  -> {p}")
    return 0


def _cmd_sync_new_id(json_output: bool) -> int:
    sid = new_session_id()
    if json_output:
        import json as _json
        print(_json.dumps({"session_id": sid}))
    else:
        print(sid)
    return 0


@_guard
def _cmd_sync_plan(path: Path, session_id: str, json_output: bool) -> int:
    plan = sync_plan(path, session_id=session_id)
    if plan is None:
        _no_brain(path, json_output)
        return 2
    print(sync_json(plan) if json_output else sync_human(plan))
    # Non-zero when user attention is needed (conflicts or other sessions staged).
    return 1 if plan.mode in ("merge_first", "resolve_conflicts") else 0


def _no_brain(path: Path, json_output: bool) -> None:
    msg = f"No CLAUDE.md found at {path.resolve()}. Run /ProjectNewSetup first."
    if json_output:
        print('{"error": "no_claude_md", "path": "%s"}' % path.resolve())
    else:
        print(msg, file=sys.stderr)
