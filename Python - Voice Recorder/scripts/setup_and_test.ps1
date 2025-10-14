<#
.\scripts\setup_and_test.ps1 - lightweight helper to create venv, install dev deps, and run tests.

Usage examples (PowerShell):
  .\scripts\setup_and_test.ps1 -Action setup        # create venv and install dev deps
  .\scripts\setup_and_test.ps1 -Action install-dev  # install dev deps into existing venv
  .\scripts\setup_and_test.ps1 -Action unit         # run unit tests
  .\scripts\setup_and_test.ps1 -Action import       # run import/smoke tests
  .\scripts\setup_and_test.ps1 -Action test         # run full pytest suite
#>

param(
    [string]$Action = 'help'
)

Set-StrictMode -Version Latest

function Write-Info($msg) { Write-Host $msg -ForegroundColor Cyan }
function Write-ErrorAndExit($msg, $code = 1) { Write-Host $msg -ForegroundColor Red; exit $code }

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Resolve-Path "$scriptDir\.." | Select-Object -ExpandProperty Path

# venv location preference: parent repository folder's venv (one level up)
$venvPath = Join-Path $projectDir "..\venv"
$venvPath = Resolve-Path -Path $venvPath -ErrorAction SilentlyContinue | ForEach-Object { $_.Path };
if (-not $venvPath) {
    # fallback: use a venv inside the project folder
    $venvPath = Join-Path $projectDir "venv"
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$requirementsFile = Join-Path $projectDir "requirements_dev.txt"

function Ensure-Venv {
    if (-not (Test-Path $venvPython)) {
        Write-Info "Creating virtual environment at: $venvPath"
        try {
            & python -m venv "$venvPath"
        } catch {
            Write-ErrorAndExit "Failed to create venv: $_"
        }
    } else {
        Write-Info "Using existing venv: $venvPath"
    }
}

function Install-Dev {
    if (-not (Test-Path $requirementsFile)) {
        Write-ErrorAndExit "requirements_dev.txt not found at $requirementsFile"
    }
    Ensure-Venv
    Write-Info "Upgrading pip and installing dev dependencies..."
    & $venvPython -m pip install --upgrade pip setuptools wheel
    $rc = & $venvPython -m pip install -r "$requirementsFile"
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorAndExit "pip install failed with exit code $LASTEXITCODE" $LASTEXITCODE
    }
}

function Run-Pytest([string]$args) {
    Ensure-Venv
    $cmd = "$venvPython -m pytest $args"
    Write-Info "Running: $cmd"
    & $venvPython -m pytest $args
    return $LASTEXITCODE
}

switch ($Action.ToLower()) {
    'help' {
        Write-Host "Usage: `n  .\scripts\setup_and_test.ps1 -Action setup|install-dev|unit|import|test|full" -ForegroundColor Green
        exit 0
    }
    'setup' {
        Ensure-Venv
        Install-Dev
        exit 0
    }
    'install-dev' {
        Install-Dev
        exit 0
    }
    'unit' {
        $rc = Run-Pytest "-q -m unit"
        exit $rc
    }
    'import' {
        $rc = Run-Pytest "-q -k import"
        exit $rc
    }
    'test' { # full suite
        $rc = Run-Pytest "-q"
        exit $rc
    }
    'full' {
        $rc = Run-Pytest "-q"
        exit $rc
    }
    default {
        Write-ErrorAndExit "Unknown action: $Action`nRun with -Action help for usage."
    }
}
