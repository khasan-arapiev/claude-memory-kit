"""Git inspection for `/ProjectSync` preflight.

Separated from sync.py so the subprocess dance doesn't crowd the planning
logic. Pure read: never modifies the repo. Every git call is timeout-
bounded and swallows subprocess errors (treated as "no git").
"""
from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class GitState:
    initialised: bool
    clean: bool
    operation_in_progress: str | None   # "merge" | "rebase" | "cherry-pick" | "bisect" | None
    branch: str | None                   # symbolic branch name or None when detached/unborn
    detached: bool = False               # True when HEAD is checked-out to a commit, not a branch
    unborn: bool = False                 # True when repo has zero commits
    dirty_paths: list[str] = field(default_factory=list)
    untracked_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _run(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", *args], cwd=str(cwd),
            capture_output=True, text=True, timeout=10,
        )
        return p.returncode, p.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def inspect(root: Path) -> GitState:
    """Inspect git state at `root` without modifying anything.

    Detects: repo presence, dirty working tree, untracked files,
    in-progress operations (merge/rebase/cherry-pick/bisect), current
    branch, detached HEAD, unborn branch (fresh repo with no commits).
    """
    code, _ = _run(["rev-parse", "--git-dir"], root)
    if code != 0:
        return GitState(initialised=False, clean=True, operation_in_progress=None, branch=None)

    # Branch: use --symbolic-full-name so we can distinguish detached (HEAD)
    # from "on branch HEAD" (technically legal but bizarre). For an unborn
    # branch (fresh repo, no commits), --symbolic-full-name HEAD returns
    # "HEAD" with exit 0, and `symbolic-ref -q HEAD` returns the branch ref.
    branch: str | None = None
    detached = False
    unborn = False
    code_sym, sym_out = _run(["symbolic-ref", "-q", "HEAD"], root)
    if code_sym == 0 and sym_out.strip().startswith("refs/heads/"):
        ref = sym_out.strip()
        branch = ref[len("refs/heads/"):]
        # Unborn branch: symbolic-ref reports the branch, but HEAD has no commit yet.
        code_has, _ = _run(["rev-parse", "--verify", "HEAD"], root)
        if code_has != 0:
            unborn = True
    else:
        # Detached HEAD: symbolic-ref failed; HEAD points directly at a commit.
        detached = True

    # Working tree status
    _, porcelain = _run(["status", "--porcelain"], root)
    dirty: list[str] = []
    untracked: list[str] = []
    for line in porcelain.splitlines():
        if not line:
            continue
        flag = line[:2]
        path = line[3:].strip()
        if flag == "??":
            untracked.append(path)
        else:
            dirty.append(path)

    # In-progress operations
    _, gitdir_out = _run(["rev-parse", "--git-dir"], root)
    gitdir = Path(gitdir_out.strip()) if gitdir_out.strip() else None
    if gitdir and not gitdir.is_absolute():
        gitdir = (root / gitdir).resolve()
    op = None
    if gitdir:
        if (gitdir / "MERGE_HEAD").exists():
            op = "merge"
        elif (gitdir / "rebase-merge").exists() or (gitdir / "rebase-apply").exists():
            op = "rebase"
        elif (gitdir / "CHERRY_PICK_HEAD").exists():
            op = "cherry-pick"
        elif (gitdir / "BISECT_LOG").exists():
            op = "bisect"

    clean = not dirty and not untracked and op is None
    return GitState(
        initialised=True,
        clean=clean,
        operation_in_progress=op,
        branch=branch,
        detached=detached,
        unborn=unborn,
        dirty_paths=dirty,
        untracked_paths=untracked,
    )
