import sys
from pathlib import Path


# Ensure the project package folder (the 'Python - Voice Recorder' folder) is on sys.path
# so tests that import top-level modules like `services.*` can resolve them during collection.
tests_dir = Path(__file__).resolve().parent
project_root = tests_dir.parent
if str(project_root) not in sys.path:
    # Prepend project root (contains top-level packages like `services`) so tests import
    # the in-repo modules rather than installed packages.
    sys.path.insert(0, str(project_root))
"""Minimal fixtures for tests.

This intentionally minimal file avoids heavy runtime imports to permit
static analysis and linters to run across the test suite.
"""

from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from voice_recorder.models import database as app_db_mod


@pytest.fixture()
def tmp_sqlite_engine(tmp_path: Path):
    db_file = tmp_path / "test_app.db"
    url = f"sqlite:///{db_file.as_posix()}"
    eng = create_engine(url, future=True)
    yield eng
    try:
        eng.dispose()
    except Exception:
        pass


@pytest.fixture()
def tmp_db_context(tmp_sqlite_engine) -> Generator[object, None, None]:
    session_factory = sessionmaker(bind=tmp_sqlite_engine, autoflush=False)
    # Instantiate DatabaseContextManager lazily to avoid heavy imports at module import time.
    from voice_recorder.core.database_context import DatabaseContextManager

    db_ctx = DatabaseContextManager(session_factory)
    try:
        app_db_mod.Base.metadata.create_all(bind=tmp_sqlite_engine)
    except Exception:
        pass
    yield db_ctx
    try:
        app_db_mod.Base.metadata.drop_all(bind=tmp_sqlite_engine)
    except Exception:
        pass
