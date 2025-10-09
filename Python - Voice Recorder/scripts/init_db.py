"""One-off helper to create missing DB tables for local development.

This script imports the project's SQLAlchemy Base and engine and runs
Base.metadata.create_all(bind=engine). It's intended for developer use
and mirrors what test fixtures do.
"""
from pathlib import Path
import sys

# Ensure project root is on sys.path when run from scripts/
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from models import database as app_db


def main() -> int:
    print(f"Using database URL: {app_db.DATABASE_URL}")
    try:
        print("Creating missing tables (if any)...")
        app_db.Base.metadata.create_all(bind=app_db.engine)
        print("Tables created/verified successfully.")
        return 0
    except Exception as e:
        print("Failed to create tables:", e)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
"""Initialize the application's database (idempotent).

Run this from the project root (Python - Voice Recorder) using the project's venv:

    & "venv\Scripts\python.exe" scripts\init_db.py

This script will:
- Ensure the sqlite db directory exists (mirrors behavior in models/database)
- Call Base.metadata.create_all(bind=engine) to create any missing tables
- Exit with 0 on success and non-zero on error
"""
from pathlib import Path
import sys
import logging

# Ensure project src path is importable when run from repo root
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from models.database import engine, Base

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("init_db")


def main():
    try:
        logger.info("Creating database tables (if missing)")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialization complete")
        return 0
    except Exception as e:
        logger.exception("Failed to initialize database: %s", e)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
