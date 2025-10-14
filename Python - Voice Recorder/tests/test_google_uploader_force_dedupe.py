from unittest.mock import Mock

import pytest
from cloud.exceptions import DuplicateFoundError


def make_fake_manager():
    m = Mock()
    # Provide minimal behaviours used by the adapter's create_request path
    m._get_service = Mock()
    m._ensure_recordings_folder = Mock(return_value="folder123")
    return m


@pytest.mark.integration
def test_upload_raises_on_duplicate_when_not_forced(monkeypatch):
    """When a duplicate is found and force=False, the uploader should raise DuplicateFoundError
    and must not call the chunked upload helper."""
    fake_manager = make_fake_manager()

    # Ensure hashing returns a value so the duplicate lookup runs
    monkeypatch.setattr("cloud.dedupe.compute_content_sha256", lambda p: "deadbeef")

    # Simulate that the manager finds a duplicate
    fake_manager.find_duplicate_by_content_sha256 = Mock(
        return_value={"id": "file123", "name": "existing.wav"}
    )

    # Patch the chunked upload helper so we can assert it wasn't called
    mock_chunked = Mock()
    monkeypatch.setattr(
        "cloud.google_uploader.chunked_upload_with_progress", mock_chunked
    )

    from cloud.google_uploader import GoogleDriveUploader

    uploader = GoogleDriveUploader(fake_manager)

    with pytest.raises(DuplicateFoundError):
        uploader.upload("recordings/raw/test.wav", force=False)

    mock_chunked.assert_not_called()


@pytest.mark.integration
def test_upload_proceeds_when_forced(monkeypatch):
    """When force=True the uploader should bypass the duplicate and call the upload helper."""
    fake_manager = make_fake_manager()

    # Hash present
    monkeypatch.setattr("cloud.dedupe.compute_content_sha256", lambda p: "deadbeef")

    # Manager still reports a duplicate, but caller forces upload
    fake_manager.find_duplicate_by_content_sha256 = Mock(
        return_value={"id": "file123", "name": "existing.wav"}
    )

    # Stub the chunked upload helper to return a Drive-like response dict
    def fake_chunked(create_request, progress_callback=None, cancel_check=None):
        # Ensure create_request can be invoked without raising (it will call into our fake manager)
        # We don't need to use the returned request for this stubbed path.
        try:
            _ = create_request()
        except Exception:
            # If create_request fails for unexpected reasons, surface it to the test
            raise
        return {
            "id": "uploaded-file-789",
            "name": "uploaded.wav",
            "size": "12345",
            "createdTime": "now",
        }

    monkeypatch.setattr(
        "cloud.google_uploader.chunked_upload_with_progress", fake_chunked
    )

    # Provide a fake media class via the manager import helper to keep create_request happy
    class FakeMedia:
        def __init__(self, path, mimetype=None, resumable=False):
            self.size = 12345

    fake_manager._import_http = Mock(return_value=(FakeMedia, None))

    from cloud.google_uploader import GoogleDriveUploader

    uploader = GoogleDriveUploader(fake_manager)

    result = uploader.upload("recordings/raw/test.wav", force=True)

    assert result["file_id"] == "uploaded-file-789"
    assert result["name"] == "uploaded.wav"
