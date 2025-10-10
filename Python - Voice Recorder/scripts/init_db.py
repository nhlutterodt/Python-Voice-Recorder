"""Initialize the application's database (idempotent).

Run this from the project root (Python - Voice Recorder) using the project's venv:

    & "venv\Scripts\python.exe" scripts\init_db.py

This script will:
- Ensure the sqlite db directory exists (mirrors behavior in models/database)
- Call Base.metadata.create_all(bind=engine) to create any missing tables
- Exit with 0 on success and non-zero on error
"""
from pathlib import Path
import logging

# Prefer canonical package imports so running scripts vs package doesn't
# create duplicate module instances. The repo's test/dev setup adds the
# project root (or src) to PYTHONPATH when needed; avoid manipulating
# sys.path here to keep the script deterministic and simple.
from voice_recorder.models import database as app_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("init_db")


def main() -> int:
    try:
        logger.info("Using database URL: %s", getattr(app_db, "DATABASE_URL", "<unknown>"))
        logger.info("Creating database tables (if missing)")
        app_db.Base.metadata.create_all(bind=app_db.engine)
        logger.info("Database initialization complete")
        return 0
    except Exception as e:
        logger.exception("Failed to initialize database: %s", e)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
