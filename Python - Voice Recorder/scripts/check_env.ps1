<#
check_env.ps1
Simple environment validator for this repo.

Checks:
- Are we running from the `Python - Voice Recorder` project directory?
- Is the repository venv present at `../venv/Scripts/python.exe`?
- Is `PYTHONPATH` set to include the project (recommended '.')?
- Can the venv Python import core runtime packages (PySide6, pydub, sounddevice, sqlalchemy)?

Usage:
  .\scripts\check_env.ps1

This script prints actionable hints to fix common launch issues (wrong working dir, missing venv,
missing PYTHONPATH). Designed for developers and CI pre-checks.
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir        # expected to be '...\Python - Voice Recorder'
$repoRoot = Split-Path -Parent $projectDir         # repository root (one level up)

Write-Host "Checking environment for Voice Recorder Pro"
Write-Host "Project directory: $projectDir"
Write-Host "Repository root:   $repoRoot"

$current = (Get-Location).Path

function Info($m) { Write-Host "[INFO]  $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "[WARN]  $m" -ForegroundColor Yellow }
function ErrorOut($m) { Write-Host "[ERROR] $m" -ForegroundColor Red }

# 1) working directory
if ($current -ieq $projectDir) {
    Info "Working directory is correct."
} else {
    Warn "Current directory ($current) is NOT the project directory."
    Write-Host "Recommended:"
    Write-Host "  Set-Location '$projectDir'`n"
}

# 2) venv python
$venvPython = Join-Path $repoRoot "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Info "Found venv python: $venvPython"
} else {
    Warn "Could not find venv python at: $venvPython"
    Write-Host "Fix: run the setup helper to create venv and install deps:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File \"$projectDir\scripts\setup_local_env.ps1\""
}

# 3) PYTHONPATH
$pyPath = $env:PYTHONPATH
if (-not [string]::IsNullOrEmpty($pyPath)) {
    if ($pyPath -match '^\.|;\.|\.|' -or $pyPath -match [regex]::Escape($projectDir)) {
        Info "PYTHONPATH looks okay (contains project or '.')."
    } else {
        Warn "PYTHONPATH is set but does not reference the project directory."
        Write-Host "If you run manually, set:"
        Write-Host "  PowerShell:  $env:PYTHONPATH = '.'"
        Write-Host "  cmd.exe:     set PYTHONPATH=."
    }
} else {
    Warn "PYTHONPATH is not set. The project expects PYTHONPATH='.' when launching manually."
    Write-Host "Recommended temporary set in PowerShell before running:"
    Write-Host "  $env:PYTHONPATH = '.'"
}

# 4) Quick import checks (only if venv python exists)
if (Test-Path $venvPython) {
    Info "Checking presence of core Python packages (PySide6, pydub, sounddevice, sqlalchemy) in the venv..."
    try {
    $pyCheck = & $venvPython -c "import importlib,sys; names=['PySide6','pydub','sounddevice','sqlalchemy']; missing=[n for n in names if importlib.util.find_spec(n) is None]; print(','.join(missing))" 2>&1
        if ($pyCheck -eq '') { Info "All core packages found." } else {
            $missing = $pyCheck.Trim()
            if ([string]::IsNullOrEmpty($missing)) { Info "All core packages found." } else {
                Warn "Missing packages in venv: $missing"
                Write-Host "Install missing packages in the venv:"
                Write-Host "  \"$venvPython\" -m pip install -r \"$projectDir\..\requirements.txt\""
                Write-Host "or install specific packages via pip."
            }
        }
    } catch {
        Warn "Failed to run python to check packages: $_"
    }
} else {
    Warn "Skipping package checks because venv python was not found."
}

Write-Host "`nSummary: follow the highlighted hints above. If you want, run the project's launcher which handles PYTHONPATH:"
Write-Host "  Set-Location '$projectDir' ; .\Launch_VoiceRecorderPro.ps1 -Dev"

if ((Test-Path $venvPython) -and ($current -ieq $projectDir)) { exit 0 } else { exit 2 }
