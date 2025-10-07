import os
import tempfile
import logging
import pytest
from typing import Any


def test_drive_manager_behaviour_when_google_apis_unavailable(monkeypatch: Any, caplog: Any):
    # Import module and force-disable Google APIs
    import cloud.drive_manager as dm
    monkeypatch.setattr(dm, "GOOGLE_APIS_AVAILABLE", False, raising=True)

    class StubAuth:
        def is_authenticated(self) -> bool:
            return True

        def get_credentials(self):
            return object()

    mgr = dm.GoogleDriveManager(StubAuth())

    # _get_service should raise a predictable error
    from cloud.exceptions import APILibrariesMissingError
    with pytest.raises(APILibrariesMissingError):
        mgr._get_service()  # type: ignore[attr-defined]  # accessing protected for test coverage

    # Methods should fail gracefully and return safe defaults
    caplog.set_level(logging.ERROR)
    # list_recordings -> []
    assert mgr.list_recordings() == []

    # get_storage_info -> {}
    assert mgr.get_storage_info() == {}

    # download/delete -> False
    assert mgr.download_recording("fake_id", os.path.join(os.getcwd(), "out.dat")) is False
    assert mgr.delete_recording("fake_id") is False

    # upload_recording -> None, use a real temp file so it passes the exists() check
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        assert mgr.upload_recording(path) is None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    # Verify expected error logs were emitted
    messages = [rec.message for rec in caplog.records]
    assert any("Error listing recordings" in m for m in messages)
    assert any("Error getting storage info" in m for m in messages)
    assert any("Download failed" in m for m in messages)
    assert any("Delete failed" in m for m in messages)
    assert any("Upload failed" in m for m in messages)
