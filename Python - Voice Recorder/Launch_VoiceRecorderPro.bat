@echo off
title Voice Recorder Pro v2.0.0-beta
REM Updated: 2025-10-03 - Added development mode support

echo.
echo 🎤 Voice Recorder Pro v2.0.0-beta Launcher
echo ==========================================

REM Check for -dev parameter
if "%1"=="-dev" goto :dev_mode
if "%1"=="--dev" goto :dev_mode
if "%1"=="/dev" goto :dev_mode

:exe_mode
echo 📦 Starting Built Executable...
cd /d "%~dp0"
if exist "dist\VoiceRecorderPro_v2.0.0-beta\VoiceRecorderPro.exe" (
    echo ✅ Executable found
    echo 🚀 Loading application...
    start "" "dist\VoiceRecorderPro_v2.0.0-beta\VoiceRecorderPro.exe"
    echo ✅ Application started successfully!
    goto :end
) else (
    echo ❌ ERROR: Application executable not found!
    echo Expected: dist\VoiceRecorderPro_v2.0.0-beta\VoiceRecorderPro.exe
    echo.
    echo 💡 Try development mode instead:
    echo    %~nx0 -dev
    echo.
    echo 💡 Or build the executable first
    pause
    exit /b 1
)

:dev_mode
echo 🔧 Starting in Development Mode...

REM Set project paths
set "projectRoot=%~dp0"
set "venvPath=%projectRoot%..\venv\Scripts\python.exe"
set "mainScript=%projectRoot%src\entrypoint.py"

REM Validate paths
if not exist "%venvPath%" (
    echo ❌ ERROR: Virtual environment not found!
    echo Expected: %venvPath%
    echo 💡 Run setup script first: .\scripts\setup_local_env.ps1
    pause
    exit /b 1
)

if not exist "%mainScript%" (
    echo ❌ ERROR: Main script not found!
    echo Expected: %mainScript%
    pause
    exit /b 1
)

echo ✅ Virtual environment found
echo ✅ Main script found
echo 🚀 Launching Voice Recorder Pro from source...
echo.

REM Change to project directory and set PYTHONPATH
cd /d "%projectRoot%"
set PYTHONPATH=.
"%venvPath%" -m src.entrypoint

if errorlevel 1 (
    echo ❌ Application failed to start
    pause
    exit /b 1
)

:end
echo.
echo Launch script completed.
