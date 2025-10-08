import os
import importlib
from types import SimpleNamespace

import pytest


@pytest.fixture(scope='session')
def qapp():
    """Provide a headless Qt QApplication for widget tests.

    Uses the offscreen platform so tests don't require a display.
    """
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def cloud_mocks(monkeypatch):
    """Provide dummy cloud classes and patch them into the enhanced_editor module.

    Returns a small dict with keys: 'ee' (the enhanced_editor module), 'DummyAuth',
    and 'DummyCloudUI' so tests can inspect last created instances.
    """
    ee = importlib.import_module('enhanced_editor')

    class DummyAuthManager:
        last_instance = None

        def __init__(self, use_keyring=True, *a, **kw):
            DummyAuthManager.last_instance = self
            self.use_keyring = use_keyring

    class DummyDriveManager:
        def __init__(self, auth):
            self.auth = auth

    class DummyFeatureGate:
        def __init__(self, auth):
            self.auth = auth

    # QWidget subclass for tab acceptance
    from PySide6.QtWidgets import QWidget

    class DummyCloudUI(QWidget):
        def __init__(self, auth, drive, feature_gate):
            super().__init__()
            self.auth = auth
            self.drive = drive
            self.feature_gate = feature_gate

    monkeypatch.setattr(ee, '_cloud_available', True)
    monkeypatch.setattr(ee, 'GoogleAuthManager', DummyAuthManager)
    monkeypatch.setattr(ee, 'GoogleDriveManager', DummyDriveManager)
    monkeypatch.setattr(ee, 'FeatureGate', DummyFeatureGate)
    monkeypatch.setattr(ee, 'CloudUI', DummyCloudUI)

    return {
        'ee': ee,
        'DummyAuth': DummyAuthManager,
        'DummyCloudUI': DummyCloudUI,
    }
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database_context import DatabaseContextManager, DBContextProtocol
from models import database as app_db_mod


@pytest.fixture()
def tmp_sqlite_engine(tmp_path: Path):
    """Create a temporary SQLite engine bound to a file in tmp_path."""
    db_file = tmp_path / "test_app.db"
    url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(url, future=True)
    yield engine
    try:
        engine.dispose()
    except Exception:
        pass


@pytest.fixture()
def tmp_db_context(tmp_sqlite_engine) -> Generator[DBContextProtocol, None, None]:
    """Return a DatabaseContextManager using a sessionmaker bound to the tmp engine."""
    session_factory = sessionmaker(bind=tmp_sqlite_engine, autoflush=False)
    db_ctx: DBContextProtocol = DatabaseContextManager(session_factory)
    # Ensure models are imported so metadata includes all tables
    # Importing models.recording registers the Recording model with Base
    try:
        __import__("models.recording")
    except Exception:
        # Best-effort import; tests will fail if models are broken
        pass
    # Create tables for the test engine
    try:
        app_db_mod.Base.metadata.create_all(bind=tmp_sqlite_engine)
    except Exception:
        pass

    yield db_ctx

    # Teardown: drop tables and dispose engine
    try:
        app_db_mod.Base.metadata.drop_all(bind=tmp_sqlite_engine)
    except Exception:
        pass
    try:
        tmp_sqlite_engine.dispose()
    except Exception:
        pass


@pytest.fixture()
def recordings_dir(tmp_path: Path) -> Path:
    d = tmp_path / "recordings"
    d.mkdir(parents=True, exist_ok=True)
    return d
import os
import sys
from pathlib import Path


# Ensure project src path is on sys.path for tests
ROOT = Path(__file__).resolve().parents[1]  # tests/.. -> project root (Python - Voice Recorder)
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
import shutil
import pytest
from pathlib import Path
from models.database import Base, engine

# Prevent pytest from trying to collect the standalone comprehensive auth test
# (it provides its own TestRunner and is meant to be executed directly).
collect_ignore = ["test_auth_manager_comprehensive.py"]


@pytest.fixture(scope="function")
def tmp_recordings_dir(tmp_path):
    d = tmp_path / "recordings" / "raw"
    d.mkdir(parents=True)
    orig = Path("recordings/raw")
    # move aside if exists
    moved = False
    if orig.exists():
        backup = tmp_path / "orig_recordings"
        shutil.move(str(orig), str(backup))
        moved = True
    # symlink not reliable on Windows; instead set env or monkeypatch RECORDINGS_DIR in service tests
    yield d
    # cleanup
    if orig.exists():
        shutil.rmtree(str(orig), ignore_errors=True)
    if moved:
        shutil.move(str(backup), str(orig))


@pytest.fixture(scope="function")
def temp_db_file(tmp_path):
    db_file = tmp_path / "test.db"
    # monkeypatch engine? For simplicity tests will rely on in-memory DB setup externally
    Base.metadata.create_all(bind=engine)
    yield db_file
    Base.metadata.drop_all(bind=engine)
