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
try:
    from cloud.auth_manager import GoogleAuthManager
    _cloud_available = True
except ImportError:
    # Define placeholders for type checking
    GoogleAuthManager = None
```
- Cloud modules: `cloud/auth_manager.py`, `cloud/drive_manager.py`, `cloud/feature_gate.py`
- Always check `_cloud_available` before using cloud features
- Use `FeatureGate` for conditional feature access

### Audio Processing Architecture
- **Recording**: `src/audio_recorder.py` - Uses sounddevice for real-time capture
- **Processing**: `src/audio_processing.py` - Asynchronous audio operations with pydub
- **Visualization**: `src/waveform_viewer.py` - matplotlib-based real-time waveform display
- **Storage**: Audio files stored in `recordings/raw/` with metadata in database

## Development Workflow

### Local Setup (Required)
```powershell
# Use the deterministic setup script
.\Python - Voice Recorder\scripts\setup_local_env.ps1
```

### Application Launch Methods
**🚀 Recommended - Quick Launch:**
```powershell
cd "Python - Voice Recorder"
.\Launch_VoiceRecorderPro.ps1 -Dev
```

**Alternative - Batch File:**
```batch
.\Launch_VoiceRecorderPro.bat -dev
```

**Manual Launch (for debugging):**
```powershell
cd "Python - Voice Recorder"
$env:PYTHONPATH = "."
& "..\venv\Scripts\python.exe" src\enhanced_main.py
```

**⚠️ Critical Launch Requirements:**
- Working directory MUST be `Python - Voice Recorder/`
- PYTHONPATH MUST be set to current directory (`.`)
- Use virtual environment Python from `../venv/Scripts/python.exe`

### Testing Strategy
- **Location**: `tests/` directory with pytest framework
- **Key Tests**: `test_critical_components.py`, `test_database_context.py`, `test_auth_manager.py`
- **Pattern**: Use `conftest.py` for shared fixtures, especially database setup
- **Headless Testing**: Set `QT_QPA_PLATFORM=offscreen` for GUI component tests

### Build Process
- **PyInstaller**: Build scripts in `scripts/build_exe.py` and `scripts/build_v2.py`
- **Artifacts**: Creates standalone executable in `dist/` directory
- **CI/CD**: `.github/workflows/ci-cd.yml` handles automated builds and releases

## Critical Developer Conventions

### Application Launch (CRITICAL - Updated Oct 2025)
**⚠️ The #1 issue: Complex launch requirements due to path/import issues**

**The Working Command (MEMORIZE THIS):**
```cmd
cd "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder" && set PYTHONPATH=. && "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\venv\Scripts\python.exe" src\enhanced_main.py
```

**Why other approaches fail:**
- PowerShell virtual env activation changes working directory unpredictably
- Relative imports break without proper PYTHONPATH 
- System Python lacks dependencies
- Import fixes required: `from waveform_viewer` NOT `from src.waveform_viewer`

**Reliable Launch Methods (order of preference):**
1. `.\Launch_VoiceRecorderPro.bat -dev` (handles everything automatically)
2. Direct cmd command above (for debugging)
3. PowerShell with execution policy bypass (advanced)

### Error Handling Pattern
Use structured logging with context:
```python
from core.logging_config import get_logger
logger = get_logger(__name__)

# Pattern for database operations
try:
    # operation
    logger.info("✅ Operation successful")
except SpecificError as e:
    logger.error(f"❌ Specific failure: {e}")
    # handle specifically
except Exception as e:
    logger.error(f"⚠️ Unexpected error: {e}")
    # general handling
```

### File Path Handling
- Always use `Path` objects from `pathlib` for cross-platform compatibility
- Audio files stored with UUID names in `recordings/raw/`, original filename in metadata
- Database paths resolved relative to project root automatically

### Async Operations Pattern
Long-running operations (audio processing, cloud sync) use QThread with progress dialogs:
```python
# See audio_processing.py for examples
class AudioLoaderThread(QThread):
    progress_updated = Signal(int)
    finished = Signal(object)
```

## Security & Credentials
- **Never commit**: `client_secrets.json`, `.env`, `token.json` files
- **CI Security**: Pipeline checks for leaked credentials automatically
- **OAuth Flow**: Google Drive uses localhost redirect with PKCE flow
- **Credential Storage**: Encrypted tokens stored in user's system credential store

## Integration Points
- **Google Drive API**: Upload/download recordings with retry logic and rate limiting
- **SQLAlchemy**: Database operations with connection pooling and health monitoring  
- **sounddevice**: Real-time audio I/O with callback-based recording
- **matplotlib**: Embedded waveform visualization with custom PySide6 integration

## Common Tasks

### Adding New Audio Features
1. Extend `audio_processing.py` with new operations
2. Add corresponding UI in `enhanced_editor.py`
3. Update database schema via Alembic if storing metadata
4. Add tests in `tests/test_audio_*.py`

### Database Schema Changes
1. Create migration: `alembic revision --autogenerate -m "description"`
2. Review generated migration in `alembic/versions/`
3. Test migration: `alembic upgrade head`
4. Update model classes in `models/`

### Adding Cloud Features  
1. Implement in appropriate `cloud/` module
2. Use `FeatureGate` for conditional access
3. Add graceful fallback for offline scenarios
4. Test with and without cloud credentials

Remember: This is a desktop app with complex audio/GUI requirements. Always test changes with actual audio hardware when modifying recording functionality.