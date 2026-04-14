# Tests

Stdlib `unittest` suite. **Zero dependencies** — `python -m unittest discover tests` is all you need.

## Run all tests

```bash
python -m unittest discover tests -v
```

## Layout

```
tests/
├── fixtures/                   Reproducible mini-projects used by tests
│   ├── clean/                  Scores 100, no findings
│   ├── broken/                 Orphans, dead links, naming, missing sections
│   ├── drifted/                One doc tracks code that's newer (drift expected)
│   └── decisions/              3 ADRs incl. supersede chain + legacy format
├── test_audit.py               Audit scoring + findings against clean & broken
├── test_drift.py               Drift detection against drifted fixture
├── test_decisions.py           ADR list/search/supersede-chain logic
└── test_frontmatter.py         Stdlib YAML-ish parser unit tests
```

## Adding a new fixture

1. Make a new folder under `tests/fixtures/<name>/`.
2. Put at minimum a `CLAUDE.md` in it (with the `<!-- project-brain: managed v1 -->` marker if testing managed projects).
3. Write a test in `tests/test_<feature>.py` that calls the CLI module against `FIXTURES / "<name>"` and asserts on the result.

Fixtures should be **as small as possible** — only the files needed to exercise the behavior under test.

## Why unittest, not pytest

Pytest is nicer, but unittest ships with Python. Zero install, zero `requirements.txt`, no excuse not to run the suite. Contributors who prefer pytest can still run `pytest tests/` — unittest tests are auto-discovered.
