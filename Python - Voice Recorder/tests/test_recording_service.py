import tempfile
from pathlib import Path
from services.recording_service import RecordingService
from models.database import engine, Base


def test_create_from_file(tmp_path):
    # ensure DB schema matches current models
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # create a small dummy wav file
    src = tmp_path / "sample.wav"
    src.write_bytes(b"RIFF....WAVEfmt ")

    rs = RecordingService()
    rec = rs.create_from_file(str(src), title="Test Recording")

    assert rec.id is not None
    assert rec.filename == "sample.wav"
    assert hasattr(rec, "checksum")

    Base.metadata.drop_all(bind=engine)
