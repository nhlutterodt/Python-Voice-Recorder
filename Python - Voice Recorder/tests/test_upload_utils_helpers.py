from cloud import upload_utils


class DummyStatus:
    def __init__(self, uploaded=None, total_size=None, progress_vals=None):
        self.uploaded = uploaded
        self.total_size = total_size
        self._p = progress_vals or []
        self._i = 0

    def progress(self):
        v = self._p[self._i]
        self._i = min(self._i + 1, len(self._p) - 1)
        return v


class DummyReq:
    def __init__(self, total_size=None):
        self.total_size = total_size


def test_discover_total_bytes_from_status():
    status = DummyStatus(total_size=12345)
    req = DummyReq(total_size=999)
    assert upload_utils._discover_total_bytes(status, req) == 12345


def test_discover_total_bytes_from_req():
    status = None
    req = DummyReq(total_size=999)
    assert upload_utils._discover_total_bytes(status, req) == 999


def test_discover_total_bytes_none_on_missing():
    status = DummyStatus()
    req = DummyReq()
    assert upload_utils._discover_total_bytes(status, req) is None


def test_normalize_progress_prefers_progress_method():
    status = DummyStatus(progress_vals=[0.5])
    assert upload_utils._normalize_progress(status, total_bytes=200) == 100


def test_normalize_progress_falls_back_to_uploaded():
    status = DummyStatus(uploaded=77)
    assert upload_utils._normalize_progress(status, total_bytes=None) == 77


def test_single_request_upload_reports_progress_and_returns():
    calls = []

    class Req:
        def __init__(self):
            self._i = 0
            self.total_size = 200

        def next_chunk(self):
            if self._i == 0:
                self._i += 1
                return (DummyStatus(progress_vals=[0.25]), None)
            return (None, {"id": "ok"})

    def progress_cb(u, t):
        calls.append((u, t))

    resp = upload_utils._single_request_upload(Req(), progress_callback=progress_cb)
    assert resp == {"id": "ok"}
    assert calls and calls[0][0] == 50
