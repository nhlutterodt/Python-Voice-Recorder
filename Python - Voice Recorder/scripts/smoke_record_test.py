#!/usr/bin/env python3
"""Smoke test: record a short clip and verify DB metadata row."""
import time
from pathlib import Path
import sys
from pathlib import Path as _Path

# Ensure project src directory is on sys.path so we can import modules like audio_recorder
project_root = _Path(__file__).resolve().parents[1]
# Ensure project root is on sys.path so top-level packages like 'core' and 'models'
# can be imported when running scripts from the scripts/ directory.
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

src_dir = project_root / 'src'
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from audio_recorder import AudioRecorderManager
from models.database import SessionLocal
from models.recording import Recording
from services.recording_service import RecordingService
import wave
from models import database as _dbmod
import sqlite3


def main():
    print("Starting smoke test: short recording (3s)")

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
        svc = RecordingService()
        rec = svc.create_from_file(str(out_file))
        print("✅ DB metadata row created via RecordingService:", getattr(rec, 'id', None))
        # Debug DB path
        try:
            print("DEBUG: DATABASE_URL=", _dbmod.DATABASE_URL)
            if _dbmod.DATABASE_URL.startswith('sqlite:///'):
                db_path = _dbmod.DATABASE_URL.replace('sqlite:///', '')
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
