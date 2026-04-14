"""`brain query` - retrieve the most relevant brain sections for a query.

Splits every brain doc (CLAUDE.md + everything under docs/) into sections at
H2/H3 boundaries, builds a TF-IDF index, and returns the top N matching
sections for a query string.

Why this matters: instead of Claude reading every doc into context just in
case, it asks "where's the FTP password info?" and gets back the 200-token
chunk that actually answers the question. Context cost drops 5-10x.

Stdlib only. No embeddings, no external dependencies. Good enough for any
brain under ~500 sections; if you outgrow it, swap in a real vector store.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .project import detect, iter_doc_files


# Common English stopwords - keep the list tiny to avoid filtering useful terms.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "i", "if", "in", "into", "is",
    "it", "its", "of", "on", "or", "she", "so", "such", "that", "the",
    "their", "then", "there", "they", "this", "to", "was", "we", "were",
    "what", "when", "where", "which", "who", "why", "will", "with", "you",
    "your",
}

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
# Chunk on H2/H3 boundaries; H1 is usually the doc title and we want it as
# context for the first chunk, not its own heading.
CHUNK_HEADING_LEVEL = 2


@dataclass
class Chunk:
    doc_path: str          # relative to project root
    heading: str           # "Writing Rules" - empty string if pre-first-heading
    heading_level: int     # 0 for pre-heading content, else 2/3
    line_start: int        # 1-based line in source file
    body: str              # full section text including heading line


@dataclass
class QueryHit:
    score: float
    doc_path: str
    heading: str
    line_start: int
    snippet: str
    body: str

    def to_dict(self) -> dict:
        return asdict(self)


def query(root: Path, q: str, top_n: int = 3) -> list[QueryHit] | None:
    project = detect(root)
    if project is None:
        return None

    chunks: list[Chunk] = []
    # Index CLAUDE.md too - it has routing and high-signal facts
    chunks.extend(_chunk_doc(project.claude_md, project.root))
    for doc in iter_doc_files(project):
        chunks.extend(_chunk_doc(doc, project.root))

    if not chunks:
        return []

    return _score_chunks(chunks, q, top_n)


def _chunk_doc(path: Path, project_root: Path) -> list[Chunk]:
    """Split a doc into chunks at H2 boundaries (H3 nested inside count too)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = str(path.relative_to(project_root).as_posix())

    # Strip frontmatter so it doesn't pollute search
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5:]

    lines = text.splitlines()
    # Find all chunk-starting heading lines (level == CHUNK_HEADING_LEVEL)
    starts: list[tuple[int, int, str]] = []  # (line_index, level, heading_text)
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == CHUNK_HEADING_LEVEL:
            starts.append((i, len(m.group(1)), m.group(2).strip()))

    if not starts:
        # Whole doc is one chunk (no H2 to split on)
        body = "\n".join(lines).strip()
        if body:
            return [Chunk(doc_path=rel, heading="", heading_level=0, line_start=1, body=body)]
        return []

    chunks: list[Chunk] = []
    # Pre-heading content (intro, frontmatter remnants, H1)
    if starts[0][0] > 0:
        body = "\n".join(lines[: starts[0][0]]).strip()
        if body:
            chunks.append(Chunk(doc_path=rel, heading="", heading_level=0, line_start=1, body=body))

    for idx, (line_i, level, heading) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        body = "\n".join(lines[line_i:end]).strip()
        if body:
            chunks.append(
                Chunk(
                    doc_path=rel,
                    heading=heading,
                    heading_level=level,
                    line_start=line_i + 1,
                    body=body,
                )
            )
    return chunks


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS and len(t) > 1]


def _score_chunks(chunks: list[Chunk], q: str, top_n: int) -> list[QueryHit]:
    """Rank chunks by TF-IDF against query terms; boost heading matches."""
    query_terms = _tokenize(q)
    if not query_terms:
        return []

    chunk_tokens = [_tokenize(c.body) for c in chunks]
    n_chunks = len(chunks)

    # Document frequency for query terms only (cheap)
    df = Counter()
    for tokens in chunk_tokens:
        unique = set(tokens)
        for term in query_terms:
            if term in unique:
                df[term] += 1

    # IDF with smoothing
    idf = {
        t: math.log((n_chunks + 1) / (df[t] + 1)) + 1.0
        for t in query_terms
    }

    hits: list[QueryHit] = []
    for chunk, tokens in zip(chunks, chunk_tokens):
        if not tokens:
            continue
        tf = Counter(tokens)
        total = len(tokens)
        score = 0.0
        for term in query_terms:
            if term in tf:
                score += (tf[term] / total) * idf[term]
        if score == 0:
            continue
        # Heading boost: 2x if any query term appears in the heading
        heading_lower = chunk.heading.lower()
        if any(term in heading_lower for term in query_terms):
            score *= 2.0
        hits.append(
            QueryHit(
                score=round(score, 4),
                doc_path=chunk.doc_path,
                heading=chunk.heading,
                line_start=chunk.line_start,
                snippet=_make_snippet(chunk.body, query_terms),
                body=chunk.body,
            )
        )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_n]


def _make_snippet(body: str, query_terms: list[str], max_len: int = 240) -> str:
    """Return ~max_len chars centered on the first query-term match."""
    body_compact = re.sub(r"\s+", " ", body).strip()
    if not query_terms:
        return body_compact[:max_len]
    lower = body_compact.lower()
    best_idx = -1
    for term in query_terms:
        idx = lower.find(term)
        if idx != -1 and (best_idx == -1 or idx < best_idx):
            best_idx = idx
    if best_idx == -1:
        return body_compact[:max_len]
    start = max(0, best_idx - max_len // 3)
    end = min(len(body_compact), start + max_len)
    snippet = body_compact[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(body_compact):
        snippet = snippet + "…"
    return snippet


def render_human(hits: list[QueryHit], q: str) -> str:
    if not hits:
        return f'No matches for "{q}".'
    lines = [f'Top {len(hits)} matches for "{q}":', ""]
    for i, h in enumerate(hits, 1):
        loc = f"{h.doc_path}:{h.line_start}"
        head = f"§ {h.heading}" if h.heading else "(intro)"
        lines.append(f"{i}. [{h.score}]  {loc}  {head}")
        lines.append(f"   {h.snippet}")
        lines.append("")
    return "\n".join(lines)


def render_json(hits: list[QueryHit]) -> str:
    return json.dumps([h.to_dict() for h in hits], indent=2)
