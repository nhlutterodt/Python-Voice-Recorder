@echo off
title Voice Recorder Pro v2.0.0-beta
echo.
echo Starting Voice Recorder Pro v2.0.0-beta...
echo Build Date: 2025-08-15
echo.

cd /d "%~dp0"
if exist "dist\VoiceRecorderPro_v2.0.0-beta\VoiceRecorderPro.exe" (
    echo Loading application...
    start "" "dist\VoiceRecorderPro_v2.0.0-beta\VoiceRecorderPro.exe"
    echo Application started successfully!
) else (
    echo ERROR: Application not found!
    echo Expected: dist\VoiceRecorderPro_v2.0.0-beta\VoiceRecorderPro.exe
    echo.
    echo Please ensure the application was built correctly.
    pause
)
