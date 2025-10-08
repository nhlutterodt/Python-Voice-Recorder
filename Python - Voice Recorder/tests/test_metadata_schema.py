import os
from pathlib import Path

import pytest

from cloud.metadata_schema import (
    build_upload_metadata,
    KEY_SOURCE,
    KEY_UPLOAD_DATE,
    KEY_FILE_SIZE,
    KEY_TAGS,
    KEY_CONTENT_SHA256,
)


def test_build_upload_metadata_happy_path(tmp_path):
    p = tmp_path / "recording.wav"
    p.write_bytes(b"RIFF....WAVE")

    md = build_upload_metadata(str(p), title="My Rec", description="desc", tags=["a", "b"], content_sha256="deadbeef", folder_id="fld-1")

    # top-level fields
    assert md["name"] == "My Rec"
    assert md["parents"] == ["fld-1"]
    assert "description" in md

    props = md.get("appProperties")
    assert props is not None
    assert props[KEY_SOURCE] == "Voice Recorder Pro"
    assert KEY_UPLOAD_DATE in props
    assert props[KEY_FILE_SIZE] == str(os.path.getsize(str(p)))
    assert props[KEY_TAGS] == "a,b"
    assert props[KEY_CONTENT_SHA256] == "deadbeef"


def test_build_upload_metadata_missing_file(tmp_path):
    # point to a non-existent file
    p = tmp_path / "missing.wav"

    md = build_upload_metadata(str(p), title=None, description=None, tags=None, content_sha256=None)

    assert md["name"] == Path(str(p)).name
    props = md.get("appProperties")
    assert props is not None
    # file size should be absent or not included
    assert KEY_FILE_SIZE not in props
