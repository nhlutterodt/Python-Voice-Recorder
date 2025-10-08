import threading
import pytest

from cloud.upload_utils import chunked_upload_with_progress


class FakeStatus:
    def __init__(self, progress_values):
        self._vals = progress_values
        self._i = 0

    def progress(self):
        v = self._vals[self._i]
        self._i = min(self._i + 1, len(self._vals) - 1)
        return v


class FakeRequest:
    def __init__(self, chunks):
        # chunks is list of (status_obj or None, response or None)
        self._chunks = chunks
        self._i = 0

    def next_chunk(self):
        if self._i >= len(self._chunks):
            return (None, {'id': 'fileid'})
        val = self._chunks[self._i]
        self._i += 1
        return val


def test_chunked_upload_success_reports_progress():
    calls = []

    def progress_cb(uploaded, total):
        calls.append((uploaded, total))

    status = FakeStatus([0.1, 0.5, 1.0])
    req = FakeRequest([(status, None), (status, None), (status, {'id': 'ok'})])

    def create_req():
        return req

    resp = chunked_upload_with_progress(create_req, progress_callback=progress_cb, max_retries=1)
    assert resp == {'id': 'ok'}
    assert len(calls) >= 1


def test_chunked_upload_cancel_raises():
    cancel = threading.Event()

    def progress_cb(uploaded, total):
        pass

    status = FakeStatus([0.1])
    req = FakeRequest([(status, None)])

    def create_req():
        return req

    def cancel_check():
        return cancel.is_set()

    # schedule cancel after a short time
    cancel.set()

    with pytest.raises(RuntimeError):
        chunked_upload_with_progress(create_req, progress_callback=progress_cb, cancel_check=cancel_check, max_retries=1)


def test_chunked_upload_retries_on_exception(monkeypatch):
    calls = {'attempts': 0}

    def create_req():
        calls['attempts'] += 1

        class BadReq:
            def next_chunk(self):
                raise IOError("network")

        return BadReq()

    with pytest.raises(IOError):
        chunked_upload_with_progress(create_req, max_retries=2, retry_backoff=0)
    assert calls['attempts'] >= 2
