import tempfile
from sqlalchemy import create_engine, inspect


def test_dev_create_all_registers_models(tmp_path):
    # Use a temporary sqlite DB file
    db_file = tmp_path / "test_app.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")

    # Import models (this should register them on Base)
    import voice_recorder.models.recording  # noqa: F401
    from voice_recorder.models import database as mdb

    # Create tables on the temp engine
    mdb.Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "recordings" in tables
