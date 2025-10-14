import pytest
from cloud.exceptions import DuplicateFoundError
from cloud.google_uploader import GoogleDriveUploader


def test_google_uploader_raises_on_duplicate(monkeypatch, tmp_path):
    # Force compute_content_sha256 to return a deterministic value
    from unittest.mock import Mock, patch

    # Patch the import path used by google_uploader
    with patch(
        "voice_recorder.cloud.dedupe.compute_content_sha256", return_value="deadbeef"
    ):

        class FakeManager:
            def find_duplicate_by_content_sha256(self, ch: str):
                assert ch == "deadbeef"
                return {"id": "dup-123", "name": "existing.wav"}

            def _get_service(self):
                # Return a mock service - won't be used since duplicate is found before upload
                return Mock()

        uploader = GoogleDriveUploader(FakeManager())

        # Create a temporary file so the path exists
        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"RIFF....WAVE")

        with pytest.raises(DuplicateFoundError) as exc:
            uploader.upload(str(test_file))

        assert getattr(exc.value, "file_id") == "dup-123"
        assert getattr(exc.value, "name") == "existing.wav"
