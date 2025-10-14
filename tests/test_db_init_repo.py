import os
import sqlite3
import sys
from pathlib import Path
import pytest


@pytest.mark.integration
def test_init_db_creates_tables(tmp_path, monkeypatch):
    # Create a temp sqlite db path
    db_file = tmp_path / "test_app.db"
    db_url = f"sqlite:///{db_file}"

    # Ensure environment variable is set so the project's models.database uses it
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Run the init_db script in-process to avoid subprocess path issues on
    # Windows. Adjust sys.path to include project src and root so imports
    # within the script resolve to the same interpreter environment.
    import runpy

    # Determine the repository root relative to this test file so the test
    # works regardless of the pytest current working directory.
    project_root = str(Path(__file__).resolve().parents[1])
    src_path = os.path.join(project_root, "Python - Voice Recorder", "src")

    # Insert src and project root into sys.path for imports
    sys.path.insert(0, src_path)
    sys.path.insert(0, project_root)

    script = os.path.join(project_root, "Python - Voice Recorder", "scripts", "init_db.py")
    assert os.path.exists(script), f"init_db script missing: {script}"

    # Execute the script as __main__ (it calls main internally). The
    # script calls SystemExit(main()), so catch SystemExit and assert
    # the returned exit code is zero.
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as se:
        assert se.code == 0, f"init_db exited with non-zero code: {se.code}"

    # Verify tables exist in the sqlite file
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()

    # Expect at least these tables to exist
    expected = {"recordings", "jobs", "alembic_version"}
    assert expected.intersection(tables), f"Expected tables missing; found: {tables}"
