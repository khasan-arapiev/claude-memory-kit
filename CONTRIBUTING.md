# Contributing to Claude Memory Kit

Thanks for considering a contribution. The project is small and opinionated; the rules below keep it that way.

## Philosophy

- **Stdlib only.** Python 3.10+ stdlib. No `pip install` dependencies. Every contribution must keep this true.
- **Deterministic over clever.** If the CLI can compute the answer the same way every time, do it in the CLI. If it requires judgment, leave it to Claude (the slash command).
- **Tests before features.** Add a fixture and a test for any new check, parser, or scoring rule.
- **Token cost is a feature constraint.** Every prompt loaded by Claude costs tokens. Smaller is better.

## Setup

```bash
git clone https://github.com/khasan-arapiev/claude-memory-kit.git
cd claude-memory-kit
python -m unittest discover tests -v   # 48 tests, < 1 second
```

No virtualenv needed (no deps). If your platform's `python` is missing or is the Windows MS Store stub, install Python 3.10+ from python.org.

## Running the CLI locally

```bash
python cli/run.py audit /path/to/some/project
python cli/run.py query "FTP password" /path/to/some/project
```

## Adding a new check or feature

1. **Write the test first.** Add a fixture under `tests/fixtures/<name>/` that triggers the new behavior. Add a test under `tests/test_<feature>.py` that asserts on the result.
2. **Implement the smallest possible change.** Reuse `project.py`, `frontmatter.py`, and existing helpers wherever possible.
3. **Surface results in both human and JSON output.** Slash commands consume the JSON; humans read the human form.
4. **Document in `cli/README.md`.** One section per subcommand, including the "why this matters" sentence.
5. **Run the full suite.** Must pass `python -m unittest discover tests` before commit.

## Code style

- Type hints throughout (`from __future__ import annotations` at the top of each module so forward refs work on 3.10).
- Dataclasses for structured data; `to_dict()` method for JSON-serializable types.
- Module-level docstring on every file explains what it does and why.
- Comments only when the *why* is non-obvious. Don't narrate what the code already says.
- No emojis in output. Plain ASCII for portability across terminals.

## Commit messages

```
<short imperative summary, under 70 chars>

Optional longer body explaining the *why*. Wrap at 80 cols.
Reference test counts and fixtures touched.

Co-Authored-By: ... (if applicable)
```

Conventional commits prefixes (`feat:`, `fix:`, `chore:`, `docs:`) are encouraged but not enforced.

## Pull requests

- One conceptual change per PR.
- Include test counts (`48 -> 50 passing`).
- Include a screenshot or terminal log if changing user-visible output.
- Squash before merge unless commits tell a meaningful story.

## Reporting bugs

Open an issue with:
- Your OS + Python version
- The exact command you ran
- Expected vs actual output
- A minimal fixture that reproduces (a `tests/fixtures/<name>/` style folder is ideal)

## What this project is not

- It's not a vector database. Don't propose embeddings until we've outgrown TF-IDF.
- It's not a documentation site generator. Brain docs stay as plain markdown.
- It's not a replacement for git/GitHub. It complements them.
