# Voice Recorder Pro v2.0.0-beta

## Build Information
- **Version**: 2.0.0-beta
- **Build Date**: 2025-09-04
- **Python Version**: 3.12.10
- **Platform**: win32

## Features
- 🎤 Professional Audio Recording
- ✂️ Advanced Audio Editing
- ☁️ Cloud Storage Integration (Google Drive)
- 💾 SQLite Database Support
- 🎨 Enhanced User Interface
- 📊 Performance Monitoring

## Quick Start
1. Run `VoiceRecorderPro.exe` to start the application
2. Use the interface to record or load audio files
3. Edit audio with trim, volume, and effects
4. Save locally or upload to Google Drive
5. Access your recordings through the database

## Launch from source (developer-friendly)

Follow these precise steps when running from source (PowerShell examples). Incorrect working directory or PYTHONPATH is the most common cause of import failures.

1. Prepare your environment (one-time):

```powershell
# From repository root
powershell -ExecutionPolicy Bypass -File ".\Python - Voice Recorder\scripts\setup_local_env.ps1"
```

1. Recommended developer launch (uses the project's launcher which handles PYTHONPATH):

```powershell
Set-Location "<repo-root>\Python - Voice Recorder"
.\Launch_VoiceRecorderPro.ps1 -Dev
```

1. Manual launch (if you need to run the main script directly):

```powershell
Set-Location "<repo-root>\Python - Voice Recorder"
$env:PYTHONPATH = "."
"<repo-root>\venv\Scripts\python.exe" src\enhanced_main.py
```

- Notes and common gotchas:

- The folder name includes a space: `Python - Voice Recorder`. Always run from that directory when launching manually.
- If imports fail, confirm `PYTHONPATH` is set to `.` and you are using the venv Python from the repository root (`venv\Scripts\python.exe`).
- To run in cmd.exe, replace PowerShell variable syntax with `set PYTHONPATH=.` and run the venv python executable directly.

## System Requirements
- Windows 10/11 (64-bit)
- Microphone (for recording)
- Internet connection (for cloud features)

## Support
For issues or questions, check the documentation or contact support.

---
Built with ❤️ using Python and PyInstaller
