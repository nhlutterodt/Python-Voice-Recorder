Initialize DB helper

Usage:

From the repository root (`Python - Voice Recorder`), run with the project's virtualenv:

PowerShell (recommended):

    & "venv\Scripts\python.exe" scripts\init_db.py

What it does:
- Ensures SQLite DB tables are present by calling SQLAlchemy `Base.metadata.create_all(bind=engine)`
- Is idempotent and safe to run multiple times

Notes & next steps:
- For production or structured schema evolution, use Alembic migrations instead of `create_all`.
- To add Alembic, run `alembic init alembic` and configure `alembic.ini` to reference `models.database.engine` and the `models` package.
- This helper intentionally keeps initialization simple for local/dev environments and CI.
