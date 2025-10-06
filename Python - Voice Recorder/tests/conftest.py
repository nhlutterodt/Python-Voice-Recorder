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
