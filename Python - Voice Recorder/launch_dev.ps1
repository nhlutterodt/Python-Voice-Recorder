# Voice Recorder Pro - Quick Development Launcher
# This script reliably launches the application from source code

Write-Host "🎤 Voice Recorder Pro - Development Mode" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Gray

# Get current script directory (project root)
$projectRoot = $PSScriptRoot
$venvPath = Join-Path $projectRoot "..\venv\Scripts\python.exe"

Write-Host "📂 Project Root: $projectRoot" -ForegroundColor Cyan
Write-Host "🐍 Python Path: $venvPath" -ForegroundColor Cyan

# Validate environment
if (-not (Test-Path $venvPath)) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "💡 Run setup first: .\scripts\setup_local_env.ps1" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Environment validated" -ForegroundColor Green
Write-Host "🚀 Launching application..." -ForegroundColor Yellow
Write-Host ""

# Ensure PYTHONPATH points to the project root so package-style imports work
try {
    # Make sure the working directory is the project root and PYTHONPATH points to the project root
    Set-Location -Path $projectRoot
    $env:PYTHONPATH = $projectRoot

    Write-Host "Using PYTHONPATH=$env:PYTHONPATH" -ForegroundColor Cyan
    # Invoke the venv Python executable as a module so relative imports inside src/ work
    & "$venvPath" -m src.entrypoint
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Host "❌ Application exited with code $exitCode" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit $exitCode
    }
} catch {
    Write-Host "❌ Launch failed: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}