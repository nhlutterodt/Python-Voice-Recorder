#!/usr/bin/env python3
"""Smoke test: record a short clip and verify DB metadata row."""
import time
from pathlib import Path
import sys
from pathlib import Path as _Path

"""Smoke test script for recording path.

This script prefers canonical package imports from `voice_recorder.*` so it
behaves the same whether the project is installed or run from the repository.
The development/test environment should set PYTHONPATH to include the repo
root (or the app folder and src) so `voice_recorder` resolves via the
package shim.
"""
# Heavy application imports (models, services, recorder) are imported inside
# main() to avoid import-time side-effects (SQLAlchemy table metadata creation)
AudioRecorderManager = None
SessionLocal = None
Recording = None
RecordingService = None
import wave
# _dbmod is imported lazily inside main() where needed to avoid creating
# SQLAlchemy metadata at module import time (which can cause duplicate
# Table definitions during migration/import checks).
_dbmod = None
import sqlite3


def main():
    print("Starting smoke test: short recording (3s)")

    # Import application modules here to avoid SQLAlchemy metadata being
    # created at module import time which can trigger "Table already defined"
    # errors when the same model module is loaded twice under different
    # import paths during migration checks.
    global AudioRecorderManager, SessionLocal, Recording, RecordingService
    from voice_recorder.audio_recorder import AudioRecorderManager as _ARM
    from voice_recorder.models.database import SessionLocal as _SessionLocal
    from voice_recorder.models.recording import Recording as _Recording
    from voice_recorder.services.recording_service import RecordingService as _RecordingService
    AudioRecorderManager = _ARM
    SessionLocal = _SessionLocal
    Recording = _Recording
    RecordingService = _RecordingService

    # Ensure recordings dir exists
    raw_dir = Path("recordings/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    mgr = AudioRecorderManager()

    filename = "smoke_test.wav"
    started = mgr.start_recording(filename=filename, sample_rate=44100)
    if not started:
        print("❌ Failed to start recording")
        return 2

    print("🔴 Recording for 3 seconds...")
    time.sleep(3)

    mgr.stop_recording()
    print("Stopped recording; waiting for finalizer...")
    time.sleep(2)

    # Check for file on disk
    files = list(raw_dir.glob("*smoke_test*.wav"))
    if not files:
        print("❌ No recording file found in recordings/raw/")
        return 3

    out_file = files[-1]
    print(f"✅ Recording file saved: {out_file} ({out_file.stat().st_size} bytes)")

    # Check DB for metadata row
    # Try to persist metadata using the RecordingService (preferred)
    try:
        # Use the application's db_context to ensure the same DB file/engine is targeted
        from voice_recorder.models.database import db_context as app_db_context
        svc = RecordingService(db_ctx=app_db_context)
        rec = svc.create_from_file(str(out_file))
        print("✅ DB metadata row created via RecordingService:", getattr(rec, 'id', None))
        # Debug DB path
        try:
            # Import the database module lazily for debugging so the module's
            # SQLAlchemy metadata is not created at import time for this script.
            from voice_recorder.models import database as _dbmod_local
            print("DEBUG: DATABASE_URL=", _dbmod_local.DATABASE_URL)
            if _dbmod_local.DATABASE_URL.startswith('sqlite:///'):
                db_path = _dbmod_local.DATABASE_URL.replace('sqlite:///', '')
                print("DEBUG: DB file exists:", sqlite3.os.path.exists(db_path))
                try:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute("SELECT count(*) FROM recordings")
                    print("DEBUG: recordings count (direct SQL):", cur.fetchone())
                    conn.close()
                except Exception as e:
                    print("DEBUG: direct SQL query failed:", e)
        except Exception:
            pass
    except Exception as e:
        print("⚠️ RecordingService failed to persist metadata:", e)
        print("➡️ Falling back to direct DB insert")
        # Fallback: compute duration and insert directly
        try:
            with wave.open(str(out_file), 'rb') as wf:
                duration = wf.getnframes() / wf.getframerate()
        except Exception:
            duration = 0.0

        session = SessionLocal()
        try:
            recording = Recording(
                filename=filename,
                stored_filename=out_file.name,
                duration=duration,
                status='active'
            )
            session.add(recording)
            session.commit()
            print("✅ DB metadata row inserted via fallback, id=", getattr(recording, 'id', None))
        except Exception as e2:
            print("❌ Fallback DB insert failed:", e2)
            return 5
        finally:
            session.close()

    # Final verification
    session = SessionLocal()
    try:
        rec = session.query(Recording).filter_by(filename=filename).order_by(Recording.id.desc()).first()
        if not rec:
            print("❌ No DB metadata row found after attempts")
            return 6

        print("✅ DB metadata row found:")
        print({
            "id": rec.id,
            "filename": rec.filename,
            "stored_filename": getattr(rec, 'stored_filename', None),
            "duration": getattr(rec, 'duration', None),
            "filesize_bytes": getattr(rec, 'filesize_bytes', None),
            "created_at": getattr(rec, 'created_at', None),
        })
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
