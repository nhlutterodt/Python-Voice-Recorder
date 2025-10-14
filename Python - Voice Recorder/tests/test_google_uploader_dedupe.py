from unittest.mock import Mock

import pytest

from cloud.drive_manager import GoogleDriveManager


class FakeAuth:
    def is_authenticated(self):
        return True
    def get_credentials(self):
        # Return a simple sentinel object; tests that call _get_service
        # will not actually use these credentials because we monkeypatch
        # network interactions, but providing this method avoids AttributeError.
        return Mock()


def test_get_uploader_upload_returns_existing_on_duplicate(monkeypatch, tmp_path):
    # create temp file
    p = tmp_path / "s.wav"
    p.write_bytes(b"RIFF....WAVE")

    # stub compute_content_sha256
    import cloud.dedupe as dedupe
    monkeypatch.setattr(dedupe, 'compute_content_sha256', lambda _p: 'deadbeef')

    # fake manager that has get_uploader semantics via get_uploader()
    mgr = GoogleDriveManager(FakeAuth())

    def fake_find_duplicate(self, ch: str):
        assert ch == 'deadbeef'
        return {'id': 'dup-xyz', 'name': 'exist.wav'}

    monkeypatch.setattr(GoogleDriveManager, 'find_duplicate_by_content_sha256', fake_find_duplicate)

    uploader = mgr.get_uploader()
    # The adapter now raises DuplicateFoundError for duplicates so callers
    # can prompt the user. Ensure the exception is raised when not forcing.
    from cloud.exceptions import DuplicateFoundError

    with pytest.raises(DuplicateFoundError) as exc:
        uploader.upload(str(p))

    assert getattr(exc.value, 'file_id', None) in (None, 'dup-xyz')
