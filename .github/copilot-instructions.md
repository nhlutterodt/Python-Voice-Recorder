# Voice Recorder Pro - AI Coding Agent Instructions

**Last updated:** October 20, 2025  
**Version:** v2.0.0-beta

This file captures essential knowledge for AI agents working on Voice Recorder Pro—a professional PySide6 audio recording app with cloud integration.

## Executive Summary

- **Working Directory**: Always run from `Python - Voice Recorder/` (note: space in folder name)
- **Entry Point**: `src/entrypoint.py` via `python -m src.entrypoint` OR use `Launch_VoiceRecorderPro.ps1 -Dev`
- **PYTHONPATH**: Critical—set `PYTHONPATH=.` when running manually from the project folder
- **Architecture**: Offline-first desktop app (PySide6) + optional async Google Drive sync via job queue + SQLite database

---

## Architecture: The Big Picture

### Three-Layer Model

1. **UI Layer** (`src/enhanced_editor.py`, `src/enhanced_main.py`)
   - PySide6 main window with recording/editing tabs
   - Delegates audio I/O to `audio_recorder.py` (via QThread for non-blocking)
   - Cloud UI (`cloud/cloud_ui.py`) conditionally shown if Google credentials available

2. **Core Services** (`core/`, `src/config_manager.py`)
   - **Config Manager**: Env-driven settings (`.env` file + `os.environ` fallback)
   - **Database Context**: Robust SQLAlchemy session management with retry logic + disk-space checks
   - **Logging**: Structured logging via `core/logging_config.py` with PII filtering
   - **Telemetry**: Optional metrics collection (`core/telemetry_config.py`)

3. **Cloud Layer** (`cloud/`) — **Gracefully Degraded if Unavailable**
   - `feature_gate.py`: User tier enforcement (FREE/PREMIUM/PRO)
   - `drive_manager.py`: Google Drive sync orchestrator
   - `job_queue_sql.py`: Async job queue (DB-backed, runs via supervisor in entrypoint)
   - `auth_manager.py`: OAuth token refresh with keyring storage
   - **Key insight**: All cloud calls are guarded by `_cloud_available` flag or `FeatureGate` checks

### Data Flow: Recording → Storage → Cloud

```
User hits "Record" → audio_recorder.py captures frames (QThread) 
  → audio_processing.py encodes to WAV/MP3
  → Recording model saved to SQLite (`models/recording.py`)
  → Job enqueued to cloud/job_queue_sql.py
  → Background job_worker (started in entrypoint) uploads via drive_manager
```

---

## Critical Developer Workflows

### 1. **Launch & Debug**

**Recommended (PowerShell)**:
```powershell
cd "Python - Voice Recorder"
.\Launch_VoiceRecorderPro.ps1 -Dev
```

**Manual Launch**:
```powershell
Set-Location "Python - Voice Recorder"
$env:PYTHONPATH = "."
.\venv\Scripts\python.exe -m src.entrypoint
```

**GUI Tests (Headless)**:
```powershell
$env:QT_QPA_PLATFORM = "offscreen"
pytest tests/ -m "not integration"
```

### 2. **Database & Configuration**

**Setup local environment** (one-time):
```powershell
powershell -ExecutionPolicy Bypass -File ".\Python - Voice Recorder\scripts\setup_local_env.ps1"
```
→ Creates venv, installs deps, initializes `db/app.db`, creates directories

**Override config via environment**:
```powershell
$env:DATABASE_URL = "sqlite:///C:/mydb.db"
$env:LOG_LEVEL = "DEBUG"
$env:RECORDINGS_RAW_PATH = "C:/recordings/raw"
```

**Inspect database**:
```powershell
cd "Python - Voice Recorder"
$env:PYTHONPATH = "."
python -c "from models.recording import Recording; from core.database_context import DatabaseContextManager; # inspect"
```

### 3. **Testing & CI**

**Run unit tests locally**:
```powershell
cd "Python - Voice Recorder"
python -m pytest -m "not integration" --tb=short
```

**Mark your tests** (`tests/conftest.py`):
```python
@pytest.mark.integration  # Skipped in CI
@pytest.mark.slow
@pytest.mark.gui
def test_my_feature():
    pass
```

**CI mirrors local flow** (`.github/workflows/ci.yml`):
- Lints: ruff, black, isort, mypy
- Tests: pytest (unit only, integration marked but skipped)
- Security: pip-audit
- Runs on Python 3.12, ubuntu-latest + windows-latest

---

## Project-Specific Patterns & Conventions

### 1. **Cloud Features Are Optional**

Cloud modules may not be installed in minimal environments. Always check availability:

```python
# At module top-level (e.g., src/enhanced_editor.py):
_cloud_available = False
try:
    from cloud.drive_manager import DriveManager
    from cloud.cloud_ui import CloudUI
    _cloud_available = True
except ImportError as e:
    logger.info(f"Cloud features unavailable: {e}")

# In methods:
if _cloud_available and self.cloud_ui:
    self.cloud_ui.sync_recording(...)
```

**Alternative pattern** (preferred for new code):
```python
from cloud.feature_gate import FeatureGate

if self.feature_gate.is_feature_enabled("cloud_upload"):
    # Proceed
```

### 2. **Configuration & Environment**

**Pattern** (`src/config_manager.py`):
```python
class ConfigManager:
    def __init__(self, project_root=None):
        self.load_environment()  # Reads .env
        self.app_config = self._load_app_config()  # Dataclass with defaults
```

**For database URL specifically**:
- Relative paths are resolved against project root: `DATABASE_URL=sqlite:///db/app.db`
- Absolute paths work: `DATABASE_URL=sqlite:////tmp/test.db`
- Parent directories auto-created

### 3. **Database Sessions: Never Ad-Hoc**

**Always use** `core/database_context.py`:

```python
from core.database_context import DatabaseContextManager

db_ctx = DatabaseContextManager(session_factory)
with db_ctx.get_session() as session:
    recording = session.query(Recording).filter_by(id=1).first()
    # Built-in retry logic, connection pooling, disk-space checks
```

**Why**: Handles retries, circuit-breaker, disk space checks, graceful error boundaries

### 4. **Long-Running Work: Use Qt Threads**

**Pattern** (`src/audio_processing.py`, `src/audio_recorder.py`):
```python
from PySide6.QtCore import QThread, pyqtSignal

class AudioWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def run(self):
        try:
            # Long work here (never on main thread!)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

# Usage:
worker = AudioWorker()
worker.finished.connect(self.on_recording_done)
worker.start()
```

**Tests**: Mock signals or use fixtures that provide test double QThread

### 5. **Paths: Always Use `pathlib.Path`**

```python
from pathlib import Path

# ✅ Good
db_path = Path.cwd() / "db" / "app.db"
config_file = Path(__file__).parent / "config" / "settings.json"

# ❌ Avoid
db_path = "db/app.db"
```

**Why**: Cross-platform, relative paths resolve correctly, `.parent` / `.mkdir()` are ergonomic

### 6. **Logging: Structured & PII-Filtered**

**Pattern** (`core/logging_config.py`):
```python
from core.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Recording started", extra={"recording_id": "xyz"})  # Structured
# PII filter automatically scrubs emails, tokens, etc.
```

---

## Optional Dashboard System

The dashboard is a **config-driven, opt-in monitoring interface** (disabled by default). It provides operational visibility via JSON-configured widgets.

### Enablement & Security

**Enable dashboards** (`.env` or environment):
```powershell
$env:DASHBOARD_ENABLED = "true"
$env:DASHBOARD_PORT = "8080"
$env:DASHBOARD_ALLOW_REMOTE = "false"  # Only allow localhost by default
```

**Access control** (`core/dashboard/access_control.py`):
- Dashboard binds to `localhost:8080` by default (no remote access unless explicitly enabled)
- All requests are logged via structured logging with PII filtering
- Export formats: Text (terminal), JSON (API), Markdown (docs)

### Configuration

Dashboards are defined in JSON files under `config/dashboards/`:

```json
{
  "title": "System Overview",
  "description": "Real-time metrics and health checks",
  "widgets": [
    {
      "widget_type": "metric",
      "metric_name": "recording.count",
      "label": "Total Recordings"
    },
    {
      "widget_type": "chart",
      "metric_name": "cpu.usage",
      "label": "CPU Usage (24h)",
      "chart_type": "sparkline",
      "window_hours": 24
    }
  ]
}
```

### Programmatic Usage

```python
from core.dashboard import Dashboard

# Load and render dashboard
dashboard = Dashboard.from_config("overview")

# Render to various formats
print(dashboard.render_text())                # Terminal output
json_data = dashboard.render_json()           # JSON API response
markdown_text = dashboard.render_markdown()   # Markdown for docs
```

**Key files**: `core/dashboard/dashboard.py` (engine), `core/dashboard/widgets.py` (widget types), `core/dashboard/renderers.py` (output formats)

---

## Audio Device Initialization & Selection

Sounddevice initialization is **deferred until recording starts** to avoid blocking UI startup if audio hardware unavailable.

### Device Discovery

**Automatic device selection**:
```python
from src.audio_recorder import AudioRecorderThread
import sounddevice as sd

# Query available devices (safe, non-blocking)
devices = sd.query_devices()
default_input = sd.default.device[0]  # (input_device_idx, output_device_idx)

# Initialize recorder with device index or name
recorder = AudioRecorderThread(
    output_path="recording.wav",
    device=0  # Use first device, or device name string
)
```

### Device Manager Pattern

**Utility wrapper** (`voice_recorder/utilities/device_management.py`):
```python
from voice_recorder.utilities import AudioDeviceManager

manager = AudioDeviceManager()
available_devices = manager.list_available_devices()  # Returns list of (index, name)
manager.validate_device(device_id=0)                  # Returns bool

# Select device for recording
recorder.device = manager.get_recommended_device() or sd.default.device[0]
```

### Error Handling

**If audio device unavailable**:
1. UI checks `sounddevice.query_devices()` at startup
2. Shows warning if no input device detected
3. Recording button disabled until valid device available
4. No fallback to dummy device (explicit error better than silent failure)

**In tests**: Use `QT_QPA_PLATFORM=offscreen` + mock sounddevice:
```python
@pytest.fixture
def mock_audio_device(monkeypatch):
    def fake_query_devices():
        return [
            {'name': 'Test Device', 'max_input_channels': 2, 'default_samplerate': 44100}
        ]
    monkeypatch.setattr('sounddevice.query_devices', fake_query_devices)
```

---

## Adding New Google API Scopes

Google OAuth scopes control what permissions the app requests from users. Adding new scopes requires changes in multiple places.

### Current Scopes

Located in `cloud/auth_manager.py`:
```python
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",      # Upload/download files (not all files, only app-created)
    "https://www.googleapis.com/auth/userinfo.profile",  # Read user profile
    "https://www.googleapis.com/auth/userinfo.email",    # Read user email
    "openid",                                             # OpenID Connect
]
```

### Step-by-Step: Add a New Scope

**1. Update `GoogleAuthManager.SCOPES`** (`cloud/auth_manager.py`, line ~173):
```python
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.photos.readonly",  # NEW: Read user photos
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]
```

**2. Clear old credentials** (users must re-authenticate):
```powershell
Remove-Item -Path "Python - Voice Recorder\cloud\credentials\token.json" -Force
```

**3. Test locally**:
```powershell
cd "Python - Voice Recorder"
$env:PYTHONPATH = "."
.\venv\Scripts\python.exe -m src.entrypoint
# Login flow will prompt for new scope
```

**4. Verify scope in token**:
```python
# After authentication
from cloud.auth_manager import GoogleAuthManager
auth = GoogleAuthManager()
if auth.is_authenticated():
    token_info = auth.get_token_info()
    scopes = token_info.get("scopes", [])
    print(f"Granted scopes: {scopes}")
```

**5. Add integration test** (`tests/test_oauth_setup.py`):
```python
@pytest.mark.integration
def test_new_scope_granted(tmp_path):
    # Test that new scope is actually granted in token
    from cloud.auth_manager import GoogleAuthManager
    auth = GoogleAuthManager(app_dir=tmp_path)
    # (Mock or use test credentials)
    assert "drive.photos.readonly" in auth.get_granted_scopes()
```

**Reference**: [Google OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes) for complete list of available scopes.

---

## Telemetry & Metrics Baseline System

The app includes an **opt-in telemetry system** with privacy-first design: all data is aggregated, local, and never auto-enabled.

### Architecture

**Three-layer system**:
1. **Metrics Aggregation** (`core/metrics_aggregator.py`): Collects raw metrics (latency, error rates, resource usage)
2. **Baseline Calculation** (`core/metrics_baseline.py`): Computes rolling baselines and detects deviations
3. **Telemetry Config** (`core/telemetry_config.py`): Optional Sentry integration for error reporting

### Baseline System (Privacy-First Anomaly Detection)

**How it works**:
```python
from core.metrics_baseline import get_baseline_manager, BaselineConfig, AlertSeverity

manager = get_baseline_manager()

# Calculate baseline for a metric over last 24 hours
baseline = manager.calculate_baseline(
    metric_name="recording.duration_seconds",
    window_hours=24,
    config=BaselineConfig(
        threshold_multiplier=3.0,        # Alert if value > median + (3 × MAD)
        min_data_points=30,              # Require 30 samples
        alert_on_increase=True,
        alert_on_decrease=False
    )
)

# Check current value against baseline
current_value = 125.5
alert = manager.check_deviation(
    metric_name="recording.duration_seconds",
    current_value=current_value
)

if alert:
    print(f"Alert ({alert.severity}): {alert.message}")
    # Output: Alert (WARNING): Duration 125.5s > threshold 110.2s (median 85.0 + 3*MAD 8.4)
```

**Statistics computed**:
- **Median**: Robust central tendency (resistant to outliers)
- **MAD** (Median Absolute Deviation): Robust spread measure
- **Percentiles**: P50 (median), P95, P99
- **Mean & StdDev**: For reference (less robust, included for compatibility)

**Alert levels**:
- `INFO`: Minor deviation (1.5-2.0× MAD) → Log only
- `WARNING`: Moderate deviation (2.0-3.0× MAD) → Investigate
- `CRITICAL`: Severe deviation (>3.0× MAD) → Immediate action

### Enabling Telemetry (Optional Sentry)

**Environment variables**:
```powershell
$env:TELEMETRY_ENABLED = "true"
$env:SENTRY_DSN = "https://key@sentry.io/project"  # If using Sentry
$env:ENVIRONMENT = "production"  # or "development", "staging"
```

**Usage**:
```python
from core.telemetry_config import TelemetryConfig

config = TelemetryConfig(
    dsn="https://key@sentry.io/project",
    environment="production",
    release="2.0.0-beta",
    enabled=True
)
config.initialize()  # Initializes Sentry SDK

# Errors are now auto-captured by Sentry (PII-filtered by core/pii_filter.py)
try:
    risky_operation()
except Exception:
    pass  # Automatically reported to Sentry
```

**Privacy Controls**:
- All events filtered via `core/pii_filter.py` (removes emails, tokens, file paths)
- Aggregated baseline data stored **locally only** (never uploaded)
- Telemetry disabled by default (requires explicit opt-in)
- User can disable at any time via `.env` or UI settings

**Key files**:
- `core/telemetry_config.py`: Sentry SDK setup + environment detection
- `core/metrics_aggregator.py`: Time-series metric collection + storage
- `core/metrics_baseline.py`: Baseline calculation + deviation detection
- `core/pii_filter.py`: Automatic redaction of sensitive data

---

## Key Files: Examples of Project Patterns

| File | Purpose | Pattern Exemplified |
|------|---------|---------------------|
| `src/config_manager.py` | Env-driven config, secrets | Dataclass + environment loading |
| `core/database_context.py` | Robust session mgmt | Context managers + retry logic + circuit-breaker |
| `core/logging_config.py` | Structured logging | PII filtering, correlation IDs |
| `cloud/feature_gate.py` | Feature access control | User tier enforcement (FREE/PREMIUM/PRO) |
| `cloud/drive_manager.py` | Google Drive orchestrator | Async job delegation |
| `models/recording.py` | Core SQLAlchemy model | Sync status tracking, export helpers |
| `src/audio_recorder.py` | Audio capture + device mgmt | QThread + signal/slot + device discovery |
| `core/dashboard/dashboard.py` | Config-driven dashboards | JSON config → widget composition → render |
| `tests/conftest.py` | Test fixtures | Minimal imports, tmp_db_context, tmp_sqlite_engine |

---

## Database Migrations with Alembic

Schema changes use **Alembic** (SQLAlchemy migration tool). Migrations live in `alembic/versions/`.

### Initial Setup (One-Time)

Alembic already initialized; first migration creates `recordings` table. To verify:
```powershell
cd "Python - Voice Recorder"
$env:PYTHONPATH = "."
.\venv\Scripts\python.exe -m alembic upgrade head
```

### Workflow: Create New Schema Change

**1. Modify the Recording model** (`models/recording.py`):
```python
class Recording(Base):
    __tablename__ = "recordings"
    # ... existing fields ...
    new_field = Column(String, nullable=True)  # NEW
```

**2. Auto-generate migration**:
```powershell
cd "Python - Voice Recorder"
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "add new_field to recordings"
```
→ Creates `alembic/versions/XXXXX_add_new_field_to_recordings.py`

**3. Review and apply**:
```powershell
# Review the migration file first
cat alembic/versions/XXXXX_add_new_field_to_recordings.py

# Apply migration
.\venv\Scripts\python.exe -m alembic upgrade head
```

**4. Test the migration**:
```powershell
# Run tests to ensure migration doesn't break existing code
python -m pytest tests/ -m "not integration" -k migration
```

### Key Points

- **`alembic/env.py`**: Adds `src/` to `sys.path` so `models` package is importable
- **Downgrade**: Undo with `alembic downgrade -1` (goes to previous version)
- **Current revision**: Check with `alembic current`
- **All revisions**: List with `alembic history`
- **Testing**: App auto-applies migrations on startup via `core/database_context.py`

---

## Recording Service & Data Model

The **Recording model** is the core domain entity. It's created via **RecordingService** and lives in the database.

### Recording Model Fields (`models/recording.py`)

```python
class Recording(Base):
    __tablename__ = "recordings"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)           # User-provided name
    stored_filename = Column(String, nullable=False)    # UUID (no collisions)
    title = Column(String, nullable=True)               # User-editable title
    
    # Metadata
    duration = Column(Float, default=0.0)               # Seconds
    filesize_bytes = Column(BigInteger, nullable=True)  # Bytes on disk
    mime_type = Column(String, nullable=True)           # e.g., "audio/wav"
    
    # Sync & Integrity
    checksum = Column(String, nullable=True)            # SHA-256 hex
    status = Column(String, default="active")           # active / archived / deleted
    sync_status = Column(String, default="unsynced")    # unsynced / syncing / synced / failed
    last_synced_at = Column(DateTime, nullable=True)    # Last cloud sync time
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    modified_at = Column(DateTime, onupdate=func.now())
```

### Recording Service Pattern (`services/recording_service.py`)

**Create recording from audio file**:
```python
from services.recording_service import RecordingService

service = RecordingService()  # Uses default DB context + recordings/raw dir
recording = service.create_from_file(
    src_path="/tmp/audio.wav",
    title="My Meeting"
)
# Returns: Recording(id=1, filename="audio.wav", stored_filename="uuid-xxx", ...)
```

**Key behaviors**:
- Stores file internally with UUID name (prevents collisions)
- Computes SHA-256 checksum for integrity
- Detects MIME type from file extension
- Persists metadata to SQLite
- **Does NOT upload to cloud** (that's job queue's responsibility)

**Dependency injection** (for testing):
```python
from services.recording_service import RecordingService
from pathlib import Path

# Use custom DB context and recordings directory
service = RecordingService(
    db_ctx=test_db_context,
    recordings_dir=Path("/tmp/test_recordings")
)
recording = service.create_from_file(...)
```

### Sync Status Lifecycle

```
"unsynced" → "syncing" → "synced"  (success)
"unsynced" → "syncing" → "failed"  (error, can retry)
```

- Job queue sets `sync_status="syncing"` before upload
- On success: `sync_status="synced"`, `last_synced_at=now()`
- On failure: `sync_status="failed"`, `last_error=error_msg` (stored in job queue)

---

## Job Queue System (Async Upload Processing)

The **job queue** is a **SQLite-backed, durable queue** for background uploads. It decouples recording → sync from UI responsiveness.

### Architecture

```
RecordingService.create_from_file()
  ↓
Recording saved to SQLite (status=active, sync_status=unsynced)
  ↓
Job enqueued to job_queue_sql.py (pending)
  ↓
Background job_worker polls → picks up job
  ↓
drive_manager.upload() → File uploaded to Google Drive
  ↓
Job marked "succeeded", Recording.sync_status="synced"
```

### Job Queue Schema (`cloud/job_queue_sql.py`)

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,              -- UUID for idempotency
    file_path TEXT NOT NULL,          -- Local file to upload
    title TEXT,                       -- Display name
    status TEXT,                      -- pending / processing / succeeded / failed / cancelled
    attempts INT,                     -- How many times attempted
    max_attempts INT,                 -- Give up after this many
    created_iso TEXT,                 -- When job created
    last_error TEXT,                  -- Last error message
    drive_file_id TEXT,               -- Google Drive file ID after upload
    cancel_requested INT              -- 1 = cancel, 0 = proceed
)
```

### Usage Pattern

**1. Enqueue a job** (after recording created):
```python
from cloud.job_queue_sql import add_job

job_id = add_job(
    db_path="db/app.db",
    file_path="recordings/raw/recording_uuid.wav",
    title="My Recording",
    max_attempts=3
)
```

**2. Start background worker** (done in `src/entrypoint.py`):
```python
from cloud.job_queue_sql import run_worker

# This runs in background thread
run_worker(drive_manager, db_path="db/app.db")
```

**3. Worker polls and processes**:
- Picks up "pending" jobs
- Sets status → "processing"
- Calls `drive_manager.upload()`
- On success: status → "succeeded", captures `drive_file_id`
- On failure: status → "failed", increments `attempts`, retries up to `max_attempts`

### Error Handling & Resilience

**Retry strategy**:
- Failed jobs auto-retry up to `max_attempts` times
- Exponential backoff (configurable)
- If all retries exhausted: job marked "failed" permanently

**Idempotency**:
- Jobs keyed by UUID (stable across retries)
- If upload succeeds but acknowledgment lost, retry is idempotent (Google Drive dedupes)

**Cancellation**:
```python
from cloud.job_queue_sql import cancel_job

cancel_job(db_path="db/app.db", job_id="xyz")
```

---

## Error Boundaries & Graceful Degradation

The app uses **error boundaries** to prevent cascading failures. `core/error_boundaries.py` provides context managers for fault isolation.

### Error Boundary Pattern

```python
from core.error_boundaries import error_boundary, ErrorBoundary

@error_boundary(
    on_error=ErrorBoundary.LOG_AND_CONTINUE,
    error_context="cloud_sync"
)
def sync_recording():
    # Long operation that might fail
    drive_manager.upload(recording)
    # If error: logged, UI continues, app doesn't crash
```

**Behaviors**:
- `LOG_AND_CONTINUE`: Log error, return None, proceed
- `LOG_AND_RAISE`: Log error, re-raise (call stack stops)
- `SILENT_CONTINUE`: No log, proceed (use sparingly)
- `SILENT_RAISE`: Silent failure, re-raise

### Fallback Patterns

**Cloud features unavailable** (`cloud/cloud_fallback.py`):
```python
if _cloud_available:
    self.cloud_ui = CloudUI(...)
else:
    # Show fallback widget with actionable buttons
    self.fallback_widget = CloudFallbackWidget()
```

`CloudFallbackWidget` displays:
- Friendly message explaining unavailability
- Buttons: "Retry Init", "Open requirements_cloud.txt", "Open client_secrets.json"
- Users can fix issues without app restart

**Audio device unavailable**:
```python
devices = sounddevice.query_devices()
if not devices or len(devices) == 0:
    self.record_btn.setEnabled(False)
    self.statusBar().showMessage("⚠️ No audio device detected")
```

### Database Connection Failure

**Handled by** `core/database_context.py`:
```python
with db_context.get_session() as session:
    # Automatic retry logic (3 attempts with backoff)
    # Checks disk space (100+ MB required)
    # Circuit-breaker if repeated failures
    recording = session.query(Recording).first()
```

---

## Build System (PyInstaller)

Executable packaging uses **PyInstaller** to bundle Python + dependencies into standalone `.exe`.

### Build Command

```powershell
cd "Python - Voice Recorder"
python scripts/build_voice_recorder_pro.py
```

### What It Does

1. **Checks dependencies**: Verifies all required packages installed
2. **Runs PyInstaller**: Bundles Python + app into `dist/VoiceRecorderPro.exe`
3. **Compresses** (optional): Uses UPX if available (reduces size ~40%)
4. **Creates installer** (optional): Windows MSI or NSIS installer

### Build Artifacts

```
dist/
  VoiceRecorderPro.exe          # Standalone executable (~50-100MB)
  VoiceRecorderPro.zip          # Portable package (if built)
build/
  VoiceRecorderPro/             # Intermediate build files
```

### Running the Executable

```powershell
# Direct execution
.\dist\VoiceRecorderPro.exe

# No installation needed
# Data stored in AppData/Local/Voice Recorder Pro/ (Windows)
```

### Build Configuration

**Key PyInstaller settings** (`scripts/build_voice_recorder_pro.py`):
- Hidden imports: `cloud.*`, `services.*`, `repositories.*` (dynamically loaded)
- Excluded: `tests/`, `.git/`, venv (reduces size)
- One-file mode: Faster startup vs. one-dir
- Console hidden: GUI-only app on Windows

### Conditional Features in Build

**Cloud features**:
- If `requirements_cloud.txt` missing: Build succeeds, cloud disabled
- If cloud deps present: Bundled into executable

**Audio codecs** (pydub):
- If ffmpeg available: MP3/OGG transcoding enabled
- If missing: WAV only

### CI Build Workflow

`.github/workflows/build.yml` automatically:
1. Sets up Python
2. Installs dependencies
3. Runs build script
4. Uploads artifact to GitHub releases
5. Creates release notes

**To release manually**:
```powershell
python scripts/build_voice_recorder_pro.py
# Upload dist/VoiceRecorderPro.exe to GitHub releases
```

---

## Legacy Import Detection (CI Pattern)

The codebase migrated from `models.*` → `voice_recorder.models.*` imports. **CI enforces the new pattern** via `tools/check_imports.py`.

### What It Checks

**Forbidden** (legacy):
```python
from models import Recording
from models.recording import Recording
import models.something
```

**Required** (canonical):
```python
from voice_recorder.models import Recording
from voice_recorder.models.recording import Recording
import voice_recorder.models.something
```

### Rationale

- **Ambiguous names**: `models` appears in multiple places (venv, site-packages)
- **Module identity**: Legacy imports load same module twice with different names (breaks SQLAlchemy)
- **Canonical namespace**: `voice_recorder.*` prevents collisions

### Running the Check

```powershell
python tools/check_imports.py "Python - Voice Recorder"
```

Output shows violations:
```
Python - Voice Recorder/tests/test_old.py:5:   from models import Recording  ❌
```

### CI Integration

```yaml
- name: Check for legacy imports
  run: python tools/check_imports.py "Python - Voice Recorder"
  # Exits with code 1 if violations found → CI fails
```

**To fix violations**: Replace all `from models` with `from voice_recorder.models`

---

## Common Failure Modes & Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: voice_recorder` | PYTHONPATH not set or running from wrong dir | `Set-Item env:PYTHONPATH "."; cd Python-Voice-Recorder` |
| Cloud UI doesn't appear | Cloud deps not installed or ImportError silenced | Install `requirements_cloud.txt`; check `_cloud_available` flag |
| Database locked / Operational errors | Concurrent access or missing disk space | Check `core/database_context.py` retry config; verify 100+ MB free |
| Qt platform plugin not found | Headless environment | Set `QT_QPA_PLATFORM=offscreen` for tests |
| Audio device not detected | sounddevice not initialized | Ensure portaudio dev libs installed; test with `sounddevice.query_devices()` |
| Import cycle: `enhanced_editor` → `cloud` → `enhanced_editor` | Circular dependency | Use `_cloud_available` guard + lazy import in conditional blocks |

---

## Integration Points & External Dependencies

- **Google APIs**: OAuth token refresh via `cloud/auth_manager.py` + keyring storage (no hardcoded secrets)
- **sounddevice**: Professional audio I/O; queries available devices at startup
- **pydub + ffmpeg**: Audio encoding/decoding (MP3, OGG); may not be available on minimal installs
- **SQLAlchemy + Alembic**: Database schema migrations in `alembic/` (run on first launch via `core/database_context.py`)
- **pytest + pytest-cov**: Unit tests marked `@pytest.mark.unit`, `@pytest.mark.integration`, etc.

---

## Before You Ask for Help

✓ Check these files first:
- **Import errors?** → `tests/conftest.py` (sys.path setup) + `src/config_manager.py` (env loading)
- **Database issue?** → `core/database_context.py` (session + retry logic)
- **Cloud feature?** → `cloud/feature_gate.py` + `_cloud_available` guard
- **Qt/threading?** → `src/audio_recorder.py` (example of QThread usage)
- **Configuration?** → `.env.template` + `src/config_manager.py`

✓ For reproducible bug reports:
- PYTHONPATH, Python version, OS (Windows/Linux/macOS)
- Full error traceback
- Whether issue is in headless environment (set `QT_QPA_PLATFORM`)
- Cloud features enabled or disabled
```