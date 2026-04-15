#!/usr/bin/env bash
# Claude Memory Kit installer for macOS and Linux.
#
# Run from a local checkout:
#   ./install.sh
#
# Or one-shot (once the repo is public):
#   curl -fsSL https://raw.githubusercontent.com/khasan-arapiev/claude-memory-kit/main/install.sh | bash
#
# Idempotent: safe to re-run to upgrade.

set -euo pipefail

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SKILL_DIR="$CLAUDE_HOME/skills/claude-memory-kit"
COMMANDS_DIR="$CLAUDE_HOME/commands"

# Resolve the directory this script lives in (works whether sourced, run, or piped via curl)
if [[ -t 0 ]] || [[ -n "${BASH_SOURCE[0]:-}" ]]; then
  SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
else
  # Curl-piped: clone to a temp dir
  SOURCE_DIR="$(mktemp -d)/claude-memory-kit"
  echo "==> Fetching claude-memory-kit..."
  git clone --depth=1 https://github.com/khasan-arapiev/claude-memory-kit.git "$SOURCE_DIR"
fi

bold()   { printf "\033[1m%s\033[0m\n" "$*"; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
red()    { printf "\033[31m%s\033[0m\n" "$*"; }

bold "Claude Memory Kit installer"
echo

# 1. Python check (must actually execute - skip Windows MS Store shortcut)
PY=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
      PY="$candidate"
      break
    fi
  fi
done
if [[ -z "$PY" ]]; then
  red "Python 3.10+ is required but not found (or only Windows MS Store stub is present)."
  echo "  macOS:  brew install python@3.12"
  echo "  Ubuntu: sudo apt install python3"
  echo "  Windows: install from https://www.python.org/downloads/"
  exit 1
fi
PY_VERSION="$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
green "✓ Python $PY_VERSION found at $(command -v "$PY")"

# 2. Copy skill
mkdir -p "$SKILL_DIR"
echo "==> Installing skill to $SKILL_DIR"
# rsync if available (preserves attrs, faster on re-install), else cp
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude='.git' --exclude='install.sh' --exclude='install.ps1' "$SOURCE_DIR/" "$SKILL_DIR/"
else
  rm -rf "$SKILL_DIR"
  mkdir -p "$SKILL_DIR"
  cp -R "$SOURCE_DIR"/. "$SKILL_DIR/"
  rm -rf "$SKILL_DIR/.git" "$SKILL_DIR/install.sh" "$SKILL_DIR/install.ps1" 2>/dev/null || true
fi
green "✓ Skill installed"

# 3. Copy commands
mkdir -p "$COMMANDS_DIR"
echo "==> Installing slash commands to $COMMANDS_DIR"
for f in "$SOURCE_DIR"/commands/Project*.md; do
  cp "$f" "$COMMANDS_DIR/"
done
green "✓ Commands installed: $(ls "$COMMANDS_DIR"/Project*.md | wc -l | tr -d ' ') file(s)"

# 4. Self-test
echo "==> Running CLI self-test"
if "$PY" "$SKILL_DIR/cli/run.py" --version >/dev/null 2>&1; then
  green "✓ CLI works: $($PY "$SKILL_DIR/cli/run.py" --version)"
else
  yellow "⚠ CLI self-test failed. Slash commands will fall back to manual logic."
fi

# 5. Run test suite (optional, only if invoked from local checkout)
if [[ -d "$SOURCE_DIR/tests" ]] && [[ "${SKIP_TESTS:-}" != "1" ]]; then
  echo "==> Running test suite"
  if (cd "$SOURCE_DIR" && "$PY" -m unittest discover tests >/dev/null 2>&1); then
    green "✓ All tests passing"
  else
    yellow "⚠ Some tests failed (run 'python -m unittest discover tests -v' for details)"
  fi
fi

echo
bold "Install complete."
echo
echo "Next steps:"
echo "  1. Restart Claude Code (so it picks up the new skill + commands)"
echo "  2. cd into any project folder"
echo "  3. Type:  /ProjectNewSetup    (new project)"
echo "         or /ProjectSetupFix    (audit existing)"
echo
echo "Optional: enable auto-save on session end. See:"
echo "  $SKILL_DIR/references/hooks.md"
