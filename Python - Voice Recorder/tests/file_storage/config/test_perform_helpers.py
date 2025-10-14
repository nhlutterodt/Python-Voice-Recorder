from pathlib import Path

import services.file_storage.config.constraints as constraints_mod


def test_perform_source_file_validation_delegates(monkeypatch):
    # simulate internal _maybe_validate_source_file returning a dict
    fake = {"valid": True, "warnings": [], "errors": []}
    monkeypatch.setattr(
        constraints_mod, "_maybe_validate_source_file", lambda s, c: fake
    )

    out = constraints_mod._perform_source_file_validation("somefile", None)
    assert out is fake


def test_perform_capacity_preop_check_delegates(monkeypatch, tmp_path):
    fake_tuple = (
        True,
        [],
        [],
        [],
        {"valid": True, "capacity_info": {"free_mb": 500.0}},
    )
    monkeypatch.setattr(
        constraints_mod, "_evaluate_capacity_for_operation", lambda c, b, e: fake_tuple
    )

    out = constraints_mod._perform_capacity_preop_check(None, Path(tmp_path), 10.0)
    assert out == fake_tuple
