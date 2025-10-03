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

# Use the exact command that worked in our testing
$launchCmd = "cd `"$projectRoot`" && set PYTHONPATH=. && `"$venvPath`" src\enhanced_main.py"

try {
    cmd /c $launchCmd
} catch {
    Write-Host "❌ Launch failed: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}