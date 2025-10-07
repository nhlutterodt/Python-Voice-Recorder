from services.recording_service import RecordingService
from models.database import engine, Base, db_context as app_db_context


def test_create_from_file(tmp_path):
    # ensure DB schema matches current models
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # create a small dummy wav file
    src = tmp_path / "sample.wav"
    src.write_bytes(b"RIFF....WAVEfmt ")

    # Inject the app's db_context so the service uses the same engine used by Base.create_all
    rs = RecordingService(db_ctx=app_db_context)
    rec = rs.create_from_file(str(src), title="Test Recording")

    assert rec.id is not None
    assert rec.filename == "sample.wav"
    assert hasattr(rec, "checksum")

    Base.metadata.drop_all(bind=engine)
