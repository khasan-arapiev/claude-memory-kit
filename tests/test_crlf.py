"""Verify CRLF handling reaches every consumer of markdown reads."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from brain.frontmatter import parse_file  # noqa: E402
from brain.project import read_md  # noqa: E402


class TestCRLFHandling(unittest.TestCase):
    """Regression: `frontmatter.parse_file` bypassed `read_md` pre-0.2.2, so
    CRLF docs broke decisions + drift. 0.2.2 routed through `read_md`. This
    test feeds actual `\\r\\n` bytes to prove the fix holds."""

    def _write_bytes(self, path: Path, content: bytes) -> None:
        path.write_bytes(content)

    def test_read_md_normalises_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.md"
            self._write_bytes(p, b"line1\r\nline2\r\nline3\r\n")
            text = read_md(p)
            self.assertEqual(text, "line1\nline2\nline3\n")
            self.assertNotIn("\r", text)

    def test_read_md_normalises_lone_cr(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.md"
            self._write_bytes(p, b"old\rmac\rstyle\r")
            text = read_md(p)
            self.assertEqual(text, "old\nmac\nstyle\n")

    def test_parse_file_handles_crlf_frontmatter(self):
        """The real regression: CRLF frontmatter must parse correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "doc.md"
            self._write_bytes(
                p,
                b"---\r\n"
                b"status: active\r\n"
                b"topics:\r\n"
                b"  - alpha\r\n"
                b"  - beta\r\n"
                b"---\r\n"
                b"body line\r\n",
            )
            fm = parse_file(p)
            self.assertEqual(fm.get("status"), "active")
            self.assertEqual(fm.list_of("topics"), ["alpha", "beta"])
            self.assertIn("body line", fm.body)
            self.assertNotIn("\r", fm.body)


if __name__ == "__main__":
    unittest.main()
