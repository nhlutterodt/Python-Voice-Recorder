import pytest

from cloud.upload_utils import _discover_total_bytes, _normalize_progress, _check_and_handle_cancel, _handle_progress


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


def test_check_and_handle_cancel_raises_when_set():
    def cancel_true():
        return True

    with pytest.raises(RuntimeError):
        _check_and_handle_cancel(cancel_true)


def test_handle_progress_calls_callback_and_ignores_exceptions():
    calls = []

    class S:
        def __init__(self):
            self.uploaded = 3

    def cb(u, t):
        calls.append((u, t))

    _handle_progress(S(), None, cb)
    assert calls == [(3, None)]

    # exception in callback should be swallowed
    def bad_cb(u, t):
        raise ValueError("boom")

    # should not raise
    _handle_progress(S(), None, bad_cb)
