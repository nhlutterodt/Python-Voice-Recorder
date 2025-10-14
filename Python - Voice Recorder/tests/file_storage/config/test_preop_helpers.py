from pathlib import Path

from services.file_storage.config.constraints import (
    ConstraintConfig,
    ConstraintValidator,
    StorageConstraints,
)


def test_validate_before_operation_sufficient_capacity(monkeypatch, tmp_path):
    # Create constraints with small min_disk to make easiest pass
    cfg = ConstraintConfig(
        min_disk_space_mb=10,
        max_file_size_mb=1000,
        enable_disk_space_check=True,
        retention_days=30,
    )
    sc = StorageConstraints(cfg)
    cv = ConstraintValidator(sc)

    # Patch _evaluate_capacity_for_operation to simulate plenty of space
    def fake_evaluator(constraints, base_path, estimated_size_mb):
        return True, [], [], [], {"valid": True, "capacity_info": {"free_mb": 1000.0}}

    monkeypatch.setattr(
        "services.file_storage.config.constraints._evaluate_capacity_for_operation",
        fake_evaluator,
    )

    res = cv.validate_before_operation(estimated_size_mb=10, base_path=Path(tmp_path))
    assert res["valid"] is True
    assert "disk_space_validation" in res


def test_validate_before_operation_insufficient_capacity(monkeypatch, tmp_path):
    cfg = ConstraintConfig(
        min_disk_space_mb=50,
        max_file_size_mb=1000,
        enable_disk_space_check=True,
        retention_days=30,
    )
    sc = StorageConstraints(cfg)
    cv = ConstraintValidator(sc)

    def fake_evaluator(constraints, base_path, estimated_size_mb):
        # simulate insufficient free space
        return (
            False,
            ["Not enough space"],
            ["low"],
            ["cleanup"],
            {
                "valid": False,
                "capacity_info": {"free_mb": 10.0},
                "errors": ["insufficient"],
            },
        )

    monkeypatch.setattr(
        "services.file_storage.config.constraints._evaluate_capacity_for_operation",
        fake_evaluator,
    )

    res = cv.validate_before_operation(estimated_size_mb=20, base_path=Path(tmp_path))
    assert res["valid"] is False
    assert "Not enough space" in res["errors"]
