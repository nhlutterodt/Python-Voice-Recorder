import os
from pathlib import Path

import pytest

from cloud.drive_manager import GoogleDriveManager


class FakeAuth:
    def is_authenticated(self):
        return True


def test_upload_recording_returns_existing_file_id_on_duplicate(monkeypatch, tmp_path):
    # Create a small temp file so os.path.exists checks pass
    p = tmp_path / "sample.wav"
    p.write_bytes(b"RIFF....WAVE")

    # Force compute_content_sha256 to a known value (so upload_recording will use it)
    import cloud.dedupe as dedupe

    monkeypatch.setattr(dedupe, "compute_content_sha256", lambda _p: "deadbeef")

    # Monkeypatch find_duplicate_by_content_sha256 on GoogleDriveManager to avoid any network/auth
    def fake_find_duplicate(self, content_sha256: str):
        assert content_sha256 == "deadbeef"
        return {"id": "dup-123", "name": "existing.wav"}

    monkeypatch.setattr(GoogleDriveManager, "find_duplicate_by_content_sha256", fake_find_duplicate)

    mgr = GoogleDriveManager(FakeAuth())

    res = mgr.upload_recording(str(p), title=None, description=None, tags=None)

    # upload_recording should return the existing file id when a duplicate is found
    assert res == "dup-123"
