import unittest.mock as mock
from voice_recorder.services.file_storage.config import constraints


def test_normalize_with_mb_keys():
    si = {'free_mb': 1000, 'used_mb': 200, 'total_mb': 1200}
    norm = constraints._normalize_storage_info(si)
    assert norm['free_mb'] == 1000.0
    assert norm['used_mb'] == 200.0
    assert norm['total_mb'] == 1200.0


def test_normalize_with_bytes_keys():
    si = {'free_bytes': 1024 * 1024 * 50, 'used_bytes': 1024 * 1024 * 10, 'total_bytes': 1024 * 1024 * 60}
    norm = constraints._normalize_storage_info(si)
    assert abs(norm['free_mb'] - 50.0) < 1e-6
    assert abs(norm['used_mb'] - 10.0) < 1e-6
    assert abs(norm['total_mb'] - 60.0) < 1e-6


class ObjLike:
    def __init__(self, free_mb=None, used_mb=None, total_mb=None, free_bytes=None):
        self.free_mb = free_mb
        self.used_mb = used_mb
        self.total_mb = total_mb
        self.free_bytes = free_bytes


def test_normalize_with_object_attrs():
    o = ObjLike(free_mb=25, used_mb=5, total_mb=30)
    norm = constraints._normalize_storage_info(o)
    assert norm['free_mb'] == 25.0
    assert norm['used_mb'] == 5.0
    assert norm['total_mb'] == 30.0


def test_normalize_with_object_bytes_attr():
    o = ObjLike(free_bytes=1024 * 1024 * 7)
    norm = constraints._normalize_storage_info(o)
    assert abs(norm['free_mb'] - 7.0) < 1e-6


def test_is_valid_storage_info_rejects_magicmock():
    m = mock.MagicMock()
    # No numeric attributes set
    assert constraints._is_valid_storage_info(m) is False


def test_normalize_magicmock_returns_zeros():
    m = mock.MagicMock()
    norm = constraints._normalize_storage_info(m)
    assert norm == {'free_mb': 0.0, 'used_mb': 0.0, 'total_mb': 0.0}
