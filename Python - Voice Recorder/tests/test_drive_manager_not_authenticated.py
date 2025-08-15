import os
import tempfile
import logging
import pytest
from typing import Any


def test_drive_manager_not_authenticated(monkeypatch: Any, caplog: Any):
    import cloud.drive_manager as dm

    # Stub auth that reports not authenticated
    class StubAuth:
        def is_authenticated(self) -> bool:
            return False

        def get_credentials(self):  # should never be called
            raise AssertionError("get_credentials should not be called when not authenticated")

    mgr = dm.GoogleDriveManager(StubAuth())

    # _get_service should raise a clear auth error first
    with pytest.raises(RuntimeError, match="Not authenticated. Please sign in first."):
        mgr._get_service()  # type: ignore[attr-defined]

    # Higher-level helpers should return safe defaults when not authenticated
    caplog.set_level(logging.ERROR)
    assert mgr.list_recordings() == []
    assert mgr.get_storage_info() == {}
    assert mgr.download_recording("id", os.path.join(os.getcwd(), "out.dat")) is False
    assert mgr.delete_recording("id") is False

    # upload_recording should return None; ensure file exists to pass existence check
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        assert mgr.upload_recording(path) is None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    # Verify error logs
    messages = [rec.message for rec in caplog.records]
    assert any("Error listing recordings" in m for m in messages)
    assert any("Error getting storage info" in m for m in messages)
    assert any("Download failed" in m for m in messages)
    assert any("Delete failed" in m for m in messages)
    assert any("Upload failed" in m for m in messages)
