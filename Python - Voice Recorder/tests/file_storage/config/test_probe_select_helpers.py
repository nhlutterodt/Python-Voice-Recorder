import types
import unittest.mock as mock

from services.file_storage.config import constraints


def test_get_candidate_collectors_prefers_module_level_mock(monkeypatch):
    # Ensure that when the constraints module-level StorageInfoCollector is a Mock,
    # _get_candidate_collectors prefers it over the storage_info module symbol.
    fake_storage_info_mod = types.SimpleNamespace()

    class RealCollector:
        pass

    fake_storage_info_mod.StorageInfoCollector = RealCollector

    monkeypatch.setitem(
        constraints.__dict__,
        "StorageInfoCollector",
        mock.MagicMock(name="ModuleLevelMock"),
    )
    # Patch import inside function by inserting a module object into package
    monkeypatch.setitem(
        constraints.__package__ and __import__(constraints.__package__).__dict__,
        "storage_info",
        fake_storage_info_mod,
    )

    candidates = constraints._get_candidate_collectors()
    assert len(candidates) >= 1
    assert candidates[0] is constraints.StorageInfoCollector


def test_probe_candidate_collectors_returns_valid_candidates(tmp_path):
    # Fake collector exposing get_storage_info
    class FakeCollector:
        def __init__(self, base_path):
            self.base_path = base_path

        def get_storage_info(self):
            return {"free_mb": 2000, "used_mb": 1000, "total_mb": 3000}

    results = constraints._probe_candidate_collectors([FakeCollector], tmp_path)
    assert isinstance(results, list)
    assert results, "No candidate results returned"
    cls, candidate, method_name, method_obj = results[0]
    assert cls is FakeCollector
    assert isinstance(candidate, dict)
    assert method_name in (
        "get_raw_storage_info",
        "get_disk_usage",
        "get_storage_info",
        "__call__",
    )
    assert constraints._is_valid_storage_info(candidate)


def test_select_candidate_prefers_mock():
    # Build candidate_results where the second entry is backed by a Mock
    class FakeCollector:
        pass

    # Create a real method object (callable) for the first entry
    def real_method():
        return {"free_mb": 5}

    # Create a mock-backed entry
    mock_cls = mock.MagicMock(name="MockCollector")
    mock_method = mock.MagicMock(name="mock_method")
    mock_candidate = {"free_mb": 100}

    candidate_results = [
        (FakeCollector, {"free_mb": 5}, "get_storage_info", real_method),
        (mock_cls, mock_candidate, "get_storage_info", mock_method),
    ]

    chosen = constraints._select_candidate(candidate_results)
    assert chosen is not None
    chosen_cls, chosen_candidate, chosen_method = chosen
    # Should pick the mock-backed entry
    assert chosen_cls is mock_cls
    assert chosen_candidate == mock_candidate
    assert chosen_method == "get_storage_info"
