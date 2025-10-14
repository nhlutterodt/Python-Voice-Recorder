
from cloud.google_uploader import GoogleDriveUploader
from cloud.metadata_schema import build_upload_metadata


class DummyRequest:
    def __init__(self, body):
        self._body = body
        self.total_size = None

    def next_chunk(self):
        # emulate immediate completion
        return (None, {"id": "fake-id", "name": self._body.get("name"), "size": 123, "createdTime": "now"})


class FakeMedia:
    def __init__(self, path, mimetype=None, resumable=False):
        self.size = 123


class FakeFiles:
    def __init__(self):
        self.last_body = None

    def create(self, body=None, media_body=None, fields=None):
        # record the body passed
        self.last_body = body
        return DummyRequest(body)


class FakeService:
    def __init__(self):
        self._files = FakeFiles()

    def files(self):
        return self._files


class FakeManager:
    def __init__(self):
        self._service = FakeService()

    def _get_service(self):
        return self._service

    def _ensure_recordings_folder(self):
        return "fld-1"

    def _import_http(self):
        # return (MediaFileUpload, MediaIoBaseDownload)-like tuple; we only need the first
        return (FakeMedia, None)


def test_google_uploader_passes_metadata(tmp_path):
    # create a small temp file
    p = tmp_path / "r.wav"
    p.write_bytes(b"RIFF....WAVE")

    mgr = FakeManager()
    uploader = GoogleDriveUploader(mgr)

    # call upload and capture the body used by the fake service
    # stub compute_content_sha256 so the uploader includes it
    import cloud.dedupe as dedupe
    from unittest.mock import patch

    with patch.object(dedupe, 'compute_content_sha256', return_value='deadbeef'):
        res = uploader.upload(str(p), title="T", description="D", tags=["x"], progress_callback=None, cancel_event=None, force=True)

    # verify result
    assert res["file_id"] == "fake-id"

    # ensure the fake service has recorded the body matching build_upload_metadata
    expected = build_upload_metadata(str(p), title="T", description="D", tags=["x"], content_sha256=None, folder_id="fld-1")

    # Compare appProperties keys present in expected
    recorded = mgr._service._files.last_body
    assert recorded is not None
    assert recorded.get("name") == expected.get("name")
    assert recorded.get("parents") == expected.get("parents")
    assert recorded.get("appProperties") is not None
    for k in expected.get("appProperties", {}):
        assert k in recorded.get("appProperties")
    # Verify content_sha256 was included by the uploader under appProperties
    assert recorded.get("appProperties").get('content_sha256') == 'deadbeef'
