# Voice Recorder Pro v2.0.0-beta PowerShell Launcher
# Build Date: 2025-09-04
# Updated: 2025-10-03 - Added development mode support

param(
    [switch]$Dev = $false,
    [switch]$Help = $false
)

if ($Help) {
    Write-Host ""
    Write-Host "Voice Recorder Pro Launcher" -ForegroundColor Green
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\Launch_VoiceRecorderPro.ps1          # Run built executable" -ForegroundColor White
    Write-Host "  .\Launch_VoiceRecorderPro.ps1 -Dev     # Run from source code" -ForegroundColor White
    Write-Host "  .\Launch_VoiceRecorderPro.ps1 -Help    # Show this help" -ForegroundColor White
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "🎤 Voice Recorder Pro v2.0.0-beta Launcher" -ForegroundColor Green
Write-Host "Build Date: 2025-09-04 | Updated: 2025-10-03" -ForegroundColor Gray
Write-Host ""

if ($Dev) {
    Write-Host "🔧 Starting in Development Mode..." -ForegroundColor Yellow
    
    # Get script directory (should be the project root)
    $projectRoot = $PSScriptRoot
    $venvPath = Join-Path $projectRoot "..\venv"
    $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    $mainScript = Join-Path $projectRoot "src\entrypoint.py"
    
    # Validate paths
    if (-not (Test-Path $venvPath)) {
        Write-Host "❌ ERROR: Virtual environment not found!" -ForegroundColor Red
        Write-Host "Expected: $venvPath" -ForegroundColor Yellow
        Write-Host "💡 Run setup script first: .\scripts\setup_local_env.ps1" -ForegroundColor Cyan
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    if (-not (Test-Path $pythonExe)) {
        Write-Host "❌ ERROR: Python executable not found in virtual environment!" -ForegroundColor Red
        Write-Host "Expected: $pythonExe" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    if (-not (Test-Path $mainScript)) {
        Write-Host "❌ ERROR: Main script not found!" -ForegroundColor Red
        Write-Host "Expected: $mainScript" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    Write-Host "✅ Virtual environment found: $venvPath" -ForegroundColor Green
    Write-Host "✅ Python executable found: $pythonExe" -ForegroundColor Green
    Write-Host "✅ Main script found: $mainScript" -ForegroundColor Green
    Write-Host ""
    
    # Use cmd to ensure proper working directory and environment handling
    Write-Host "🚀 Launching Voice Recorder Pro from source..." -ForegroundColor Yellow
    
        $cmd = "cd `"$projectRoot`" && set PYTHONPATH=. && `"$pythonExe`" -m src.entrypoint"
    
    try {
        cmd /c $cmd
        Write-Host "✅ Application launched successfully!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to launch application: $($_.Exception.Message)" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    
} else {
    Write-Host "📦 Starting Built Executable..." -ForegroundColor Yellow
    
    $exePath = Join-Path $PSScriptRoot "dist\VoiceRecorderPro_v2.0.0-beta\VoiceRecorderPro.exe"

    if (Test-Path $exePath) {
        Write-Host "✅ Executable found: $exePath" -ForegroundColor Green
        Write-Host "🚀 Loading application..." -ForegroundColor Yellow
        Start-Process $exePath
        Write-Host "✅ Application started successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ ERROR: Application executable not found!" -ForegroundColor Red
        Write-Host "Expected: $exePath" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "💡 Try development mode instead:" -ForegroundColor Cyan
        Write-Host "   .\Launch_VoiceRecorderPro.ps1 -Dev" -ForegroundColor White
        Write-Host ""
        Write-Host "💡 Or build the executable first:" -ForegroundColor Cyan
        Write-Host "   python scripts\build_voice_recorder_pro.py" -ForegroundColor White
        Read-Host "Press Enter to continue"
        exit 1
    }
}
