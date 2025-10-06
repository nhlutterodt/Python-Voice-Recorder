# Voice Recorder Pro - AI Coding Agent Instructions

## Project Overview
Voice Recorder Pro is a professional desktop audio recording application built with Python and PySide6. It features real-time audio capture, waveform editing, cloud integration with Google Drive, and SQLAlchemy-based recording management. The app follows an offline-first architecture with optional cloud sync.

## Key Architecture Patterns

### Project Structure & Entry Points
- **Main Entry**: `src/enhanced_main.py` - Application bootstrap with PySide6 setup
- **Core UI**: `src/enhanced_editor.py` - Main window containing recording/editing interface  
- **Working Directory**: Always `Python - Voice Recorder/` (note the space in directory name)
- **Dependencies**: Core deps in `requirements.txt`, dev tools in `requirements_dev.txt`, cloud features in `requirements_cloud.txt`

### Configuration Management
The app uses environment-driven configuration via `src/config_manager.py`:
- Loads `.env` files from project root if present
- All settings have sensible defaults and can be overridden via environment variables
- Key configs: `DATABASE_URL`, `RECORDINGS_RAW_PATH`, `LOG_LEVEL`, `CLOUD_FEATURES_ENABLED`
- Google OAuth credentials loaded from `config/client_secrets.json` OR environment variables

### Database & Models
- **Pattern**: SQLAlchemy with Alembic migrations in `alembic/` directory
- **Session Management**: Use `core/database_context.py` for robust session handling with retry logic
- **Models**: Located in `models/` - main model is `Recording` with sync status tracking
- **Database Location**: `db/app.db` by default (configurable via `DATABASE_URL`)

### Cloud Integration Pattern
Cloud features use graceful degradation:
```python
# Pattern for optional cloud imports
_cloud_available = False
```markdown
# AI coding agent guide — Voice Recorder Pro (concise)

This file contains the essential, actionable facts an AI agent needs to be immediately productive.

- Main entry: `src/enhanced_main.py` (GUI bootstrap).
- Working directory: run from the repository subfolder named exactly `Python - Voice Recorder` (the space is important).
- PYTHONPATH: many failures come from import paths — set `PYTHONPATH=.` or run the repo's launcher which handles it.

Key files and folders to inspect for behavior and patterns:
- `src/enhanced_editor.py`, `src/audio_recorder.py`, `src/audio_processing.py`, `src/waveform_viewer.py` (UI, recording, processing, viz)
- `core/` (logging, database context, health checks) and `models/` (SQLAlchemy models)
- `cloud/` (auth_manager.py, drive_manager.py, feature_gate.py) — cloud features are optional and guarded by availability checks
- `alembic/` (migrations), `db/` (default sqlite `app.db`), `recordings/` (raw/edited storage)
- `scripts/` and `Launch_VoiceRecorderPro.*` (local setup and packaging helpers)

Launch & debug (PowerShell): prefer the provided launcher; if running manually use the venv Python and set PYTHONPATH:
```powershell
Set-Location "<repo-root>\Python - Voice Recorder"
$env:PYTHONPATH = "."
"<repo-root>\venv\Scripts\python.exe" src\enhanced_main.py
```
Or simply: `.\Launch_VoiceRecorderPro.ps1 -Dev` (recommended).

Project-specific conventions / gotchas:
- Always use `pathlib.Path` for paths; DB and recordings are resolved relative to project root.
- Cloud modules may not be importable in minimal dev environments — check `_cloud_available`/FeatureGate before calling cloud APIs.
- Long-running work (audio processing, sync) uses Qt threads/QThread patterns (see `audio_processing.py`) — prefer signal/slot testing patterns.
- Database sessions use `core/database_context.py` which includes retry/health logic; prefer that over ad-hoc session management.

Testing & CI:
- Tests live under `tests/` (pytest). Use `pytest` from the venv. GUI tests should set `QT_QPA_PLATFORM=offscreen`.
- Setup helper: `Python - Voice Recorder\scripts\setup_local_env.ps1` (creates venv, installs deps, initializes directories and DB).
- CI workflow: `.github/workflows/ci-cd.yml` — mirrors local build/test steps and PyInstaller packaging.

When modifying code, check these example files to match project patterns: `src/config_manager.py` (env-driven config), `core/logging_config.py` (structured logging), and `cloud/feature_gate.py` (conditional features).

If anything here is unclear or you need more detail (launch examples, test fixtures, or common failing import traces), ask and I will expand specific sections or merge additional content.
```