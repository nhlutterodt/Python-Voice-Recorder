import pytest

from cloud.google_uploader import GoogleDriveUploader
from cloud.exceptions import DuplicateFoundError


def test_google_uploader_raises_on_duplicate(monkeypatch):
    # Force compute_content_sha256 to return a deterministic value
    import cloud.dedupe as dedupe

    monkeypatch.setattr(dedupe, "compute_content_sha256", lambda p: "deadbeef")

    class FakeManager:
        def find_duplicate_by_content_sha256(self, ch: str):
            assert ch == "deadbeef"
            return {"id": "dup-123", "name": "existing.wav"}

    uploader = GoogleDriveUploader(FakeManager())

    with pytest.raises(DuplicateFoundError) as exc:
        uploader.upload("/some/path.wav")

    assert getattr(exc.value, "file_id") == "dup-123"
    assert getattr(exc.value, "name") == "existing.wav"
