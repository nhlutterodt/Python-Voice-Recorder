from pathlib import Path

from services.file_storage.config.constraints import (
    StorageConstraints,
    ConstraintConfig,
    ConstraintValidator,
)


def test_resolve_operation_kwargs_with_legacy_keys(tmp_path):
    cfg = ConstraintConfig(min_disk_space_mb=10, max_file_size_mb=500, enable_disk_space_check=False, retention_days=30)
    sc = StorageConstraints(cfg)
    cv = ConstraintValidator(sc)

    # Pass legacy keys 'operation' and 'size_mb'
    res = cv.validate_before_operation(size_mb=12, base_path=Path(tmp_path), operation='copy')
    assert res['operation'] == 'copy'
    assert abs(res['estimated_size_mb'] - 12.0) < 0.001


def test_resolve_operation_kwargs_with_estimated_size_key(tmp_path):
    cfg = ConstraintConfig(min_disk_space_mb=10, max_file_size_mb=500, enable_disk_space_check=False, retention_days=30)
    sc = StorageConstraints(cfg)
    cv = ConstraintValidator(sc)

    res = cv.validate_before_operation(estimated_size_mb=None, size_mb='15', base_path=Path(tmp_path))
    assert abs(res['estimated_size_mb'] - 15.0) < 0.001
