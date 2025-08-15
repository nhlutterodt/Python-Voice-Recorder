# Voice Recorder Pro v2.0.0-beta PowerShell Launcher
# Build Date: 2025-08-15

Write-Host ""
Write-Host "Starting Voice Recorder Pro v2.0.0-beta..." -ForegroundColor Green
Write-Host "Build Date: 2025-08-15" -ForegroundColor Gray
Write-Host ""

$exePath = Join-Path $PSScriptRoot "dist\VoiceRecorderPro_v2.0.0-beta\VoiceRecorderPro.exe"

if (Test-Path $exePath) {
    Write-Host "Loading application..." -ForegroundColor Yellow
    Start-Process $exePath
    Write-Host "Application started successfully!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Application not found!" -ForegroundColor Red
    Write-Host "Expected: $exePath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please ensure the application was built correctly." -ForegroundColor Yellow
    Read-Host "Press Enter to continue"
}
