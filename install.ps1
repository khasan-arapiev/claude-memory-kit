# Claude Memory Kit installer for Windows (PowerShell 5.1+).
#
# Run from a local checkout:
#   .\install.ps1
#
# Or one-shot (once the repo is public):
#   irm https://raw.githubusercontent.com/khasan-arapiev/claude-memory-kit/main/install.ps1 | iex
#
# Idempotent: safe to re-run to upgrade.

$ErrorActionPreference = "Stop"

$ClaudeHome  = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $env:USERPROFILE ".claude" }
$SkillDir    = Join-Path $ClaudeHome "skills\claude-memory-kit"
$CommandsDir = Join-Path $ClaudeHome "commands"

# Resolve source dir
if ($PSCommandPath) {
  $SourceDir = Split-Path -Parent $PSCommandPath
} else {
  # iex-piped: clone to temp
  $SourceDir = Join-Path ([System.IO.Path]::GetTempPath()) "claude-memory-kit"
  Write-Host "==> Fetching claude-memory-kit..."
  if (Test-Path $SourceDir) { Remove-Item -Recurse -Force $SourceDir }
  git clone --depth=1 https://github.com/khasan-arapiev/claude-memory-kit.git $SourceDir
}

function Write-Bold($msg)   { Write-Host $msg -ForegroundColor White -BackgroundColor DarkGray }
function Write-Ok($msg)     { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg)   { Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg)    { Write-Host $msg -ForegroundColor Red }

Write-Bold "Claude Memory Kit installer"
Write-Host ""

# 1. Python check
$Py = $null
foreach ($cmd in @("python", "python3", "py")) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { $Py = $cmd; break }
}
if (-not $Py) {
  Write-Err "Python 3.10+ is required but not found."
  Write-Host "  Install from: https://www.python.org/downloads/"
  exit 1
}
$PyVersion = & $Py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$PyOk      = & $Py -c "import sys; print(sys.version_info >= (3, 10))"
if ($PyOk -ne "True") {
  Write-Err "Python 3.10+ required (found $PyVersion)."
  exit 1
}
Write-Ok "OK Python $PyVersion found ($Py)"

# 2. Copy skill
New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
Write-Host "==> Installing skill to $SkillDir"
# Wipe + copy (simple, idempotent)
Get-ChildItem -Path $SkillDir -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Copy-Item -Path "$SourceDir\*" -Destination $SkillDir -Recurse -Force `
  -Exclude @(".git", "install.sh", "install.ps1")
# Robustly remove unwanted top-level items if Copy-Item -Exclude missed them
foreach ($x in @(".git", "install.sh", "install.ps1")) {
  $p = Join-Path $SkillDir $x
  if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}
Write-Ok "OK Skill installed"

# 3. Copy commands
New-Item -ItemType Directory -Force -Path $CommandsDir | Out-Null
Write-Host "==> Installing slash commands to $CommandsDir"
$cmdFiles = Get-ChildItem -Path "$SourceDir\commands\Project*.md"
foreach ($f in $cmdFiles) {
  Copy-Item -Path $f.FullName -Destination $CommandsDir -Force
}
Write-Ok "OK Commands installed: $($cmdFiles.Count) file(s)"

# 4. Self-test
Write-Host "==> Running CLI self-test"
$cliRunner = Join-Path $SkillDir "cli\run.py"
try {
  $version = & $Py $cliRunner --version 2>&1
  Write-Ok "OK CLI works: $version"
} catch {
  Write-Warn "CLI self-test failed. Slash commands will fall back to manual logic."
}

# 5. Test suite (optional, only when run from local checkout)
$testsDir = Join-Path $SourceDir "tests"
if ((Test-Path $testsDir) -and ($env:SKIP_TESTS -ne "1")) {
  Write-Host "==> Running test suite"
  Push-Location $SourceDir
  try {
    & $Py -m unittest discover tests 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Write-Ok "OK All tests passing"
    } else {
      Write-Warn "Some tests failed (run 'python -m unittest discover tests -v' for details)"
    }
  } finally { Pop-Location }
}

Write-Host ""
Write-Bold "Install complete."
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Claude Code (so it picks up the new skill + commands)"
Write-Host "  2. cd into any project folder"
Write-Host "  3. Type:  /ProjectNewSetup    (new project)"
Write-Host "         or /ProjectSetupFix    (audit existing)"
Write-Host ""
Write-Host "Optional: enable auto-save on session end. See:"
Write-Host "  $SkillDir\references\hooks.md"
