from unittest.mock import Mock


from cloud.google_uploader import GoogleDriveUploader
from cloud.uploader import UploadProgress


class FakeReq:
    def __init__(self):
        self._i = 0

    def next_chunk(self):
        if self._i == 0:
            self._i += 1
            class S:
                def progress(self):
                    return 0.5
            return (S(), None)
        return (None, {'id': '123', 'name': 'a.wav', 'size': '1024', 'createdTime': 'now'})


class FakeService:
    def files(self):
        class C:
            def create(self, body, media_body, fields):
                return FakeReq()

        return C()


class FakeManager:
    def __init__(self):
        self._service = FakeService()

    def _get_service(self):
        return self._service

    def _ensure_recordings_folder(self):
        return 'folder'

    def _import_http(self):
        # Return a fake MediaFileUpload constructor and placeholder
        def fake_media(path, mimetype=None, resumable=False):
            m = Mock()
            m.size = 1024
            return m

        return (fake_media, None)


def test_google_uploader_happy_path_reports_progress_and_returns_result():
    mgr = FakeManager()
    uploader = GoogleDriveUploader(mgr)

    calls = []

    def progress_cb(progress: UploadProgress):
        calls.append(progress)

    res = uploader.upload('some/path.wav', progress_callback=progress_cb)
    assert res['file_id'] == '123'
    assert calls and calls[0]['percent'] == 50
