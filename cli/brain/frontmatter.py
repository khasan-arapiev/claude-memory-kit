"""Minimal YAML-ish frontmatter parser (stdlib only).

Supports the small subset we need for brain docs:

    ---
    describes:
      - path/to/file.js
      - path/to/other.html
    last-synced: 2026-04-14
    status: active
    ---

Returns a dict plus the remaining body. Intentionally conservative: only
bare strings, numbers, ISO dates, and simple lists-of-strings. Anything
weirder should not be in frontmatter anyway.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


ALLOWED_STATUS = {"active", "superseded", "deprecated", "proposed", "accepted", "approved"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


@dataclass
class Frontmatter:
    data: dict = field(default_factory=dict)
    body: str = ""

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def list_of(self, key: str) -> list[str]:
        v = self.data.get(key)
        if isinstance(v, list):
            return [str(x) for x in v]
        if isinstance(v, str):
            return [v]
        return []

    def validate(self) -> list[str]:
        """Return a list of human-readable warnings for unknown enum values.

        Only checks fields that project-brain actually understands. Unknown
        keys are allowed through (frontmatter is extensible), but typos in
        known enums would otherwise silently pass and break routing later.
        """
        warnings: list[str] = []
        status = self.data.get("status")
        if isinstance(status, str) and status.lower() not in ALLOWED_STATUS:
            warnings.append(
                f"unknown status '{status}' (valid: {sorted(ALLOWED_STATUS)})"
            )
        confidence = self.data.get("confidence")
        if isinstance(confidence, str) and confidence.lower() not in ALLOWED_CONFIDENCE:
            warnings.append(
                f"unknown confidence '{confidence}' (valid: {sorted(ALLOWED_CONFIDENCE)})"
            )
        return warnings


def parse(text: str) -> Frontmatter:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return Frontmatter(data={}, body=text)
    raw = m.group(1)
    body = text[m.end():]
    return Frontmatter(data=_parse_block(raw), body=body)


def parse_file(path: Path) -> Frontmatter:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return Frontmatter(data={}, body="")
    return parse(text)


def _parse_block(raw: str) -> dict:
    """Parse a simple key: value / list block. Indentation = 2 spaces for lists."""
    out: dict = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value == "":
            # Collect subsequent "- item" lines as a list
            items: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                stripped = nxt.lstrip()
                if stripped.startswith("- "):
                    items.append(stripped[2:].strip())
                    j += 1
                elif nxt.strip() == "":
                    j += 1
                else:
                    break
            if items:
                out[key] = items
                i = j
                continue
            out[key] = ""
            i += 1
            continue
        out[key] = _coerce(value)
        i += 1
    return out


def _coerce(value: str):
    # Strip wrapping quotes
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    # ISO date?
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # Int?
    if re.match(r"^-?\d+$", value):
        return int(value)
    # Bool
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    return value
