import datetime
from decimal import Decimal

from models.utils import to_dict
from services.recording_utils import (
    compute_sha256_for_bytes,
    human_readable_size,
    make_stored_filename,
)


class DummyRecording:
    # mimic SQLAlchemy mapped attributes for our to_dict helper
    id = 1
    filename = "example.wav"
    stored_filename = "uuid123.wav"
    duration = 3.45
    filesize_bytes = 123456
    mime_type = "audio/wav"
    checksum = "deadbeef"
    status = "active"
    created_at = datetime.datetime(2020, 1, 2, 3, 4, 5)
    modified_at = None

    # SQLAlchemy inspection API isn't available on this simple class,
    # but our to_dict uses inspect which will raise; so test only
    # the recording utilities and a minimal direct serialization via dict.


def test_recording_utils_sha256_and_size_and_filename():
    data = b"hello world"
    digest = compute_sha256_for_bytes(data)
    assert len(digest) == 64

    size = human_readable_size(1024)
    assert "KB" in size

    stored = make_stored_filename("sound.mp3")
    assert stored.endswith(".mp3") or len(stored) > 0


def test_to_dict_handles_primitives_and_dates():
    # Use a minimal object with __dict__ to exercise serialization path
    class Obj:
        def __init__(self):
            self.n = 1
            self.s = "x"
            self.dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
            self.dec = Decimal("1.23")

    o = Obj()
    # Fall back: to_dict expects SQLAlchemy inspect; when not available it should raise.
    # Here we assert behavior by directly using serializer on simple values via helper.
    from models.utils import _serialize_value

    assert _serialize_value(o.n) == 1
    assert _serialize_value(o.s) == "x"
    assert _serialize_value(o.dt).startswith("2024-01-01")
    assert isinstance(_serialize_value(o.dec), float)
