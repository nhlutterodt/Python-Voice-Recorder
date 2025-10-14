Alembic migrations

This folder contains Alembic scaffolding and an initial migration that creates the `recordings` table.

Quick usage (from project root `Python - Voice Recorder`):

PowerShell:

    & ".\venv\Scripts\python.exe" -m alembic upgrade head

If `alembic` is not installed in the venv, install it with:

    & ".\venv\Scripts\python.exe" -m pip install alembic

Notes:
- The `alembic/env.py` adds the project's `src` to `sys.path` so the `models` package can be imported.
- The provided migration `alembic/versions/0001_create_recordings_table.py` is a minimal initial migration. For future changes, use:

    & ".\venv\Scripts\python.exe" -m alembic revision --autogenerate -m "describe change"
    & ".\venv\Scripts\python.exe" -m alembic upgrade head

If you prefer not to run migrations, the app still has `scripts/init_db.py` which calls `Base.metadata.create_all` for dev convenience.
