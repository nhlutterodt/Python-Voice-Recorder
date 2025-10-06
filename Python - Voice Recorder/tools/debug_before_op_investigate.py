import tempfile, os
from unittest.mock import MagicMock
from pathlib import Path

from services.file_storage.config.constraints import ConstraintConfig, StorageConstraints, ConstraintValidator
from services.file_storage.config import storage_info as _si_mod

constraint_config = ConstraintConfig(min_disk_space_mb=100, max_file_size_mb=1000, enable_disk_space_check=True, retention_days=30)
constraints = StorageConstraints(constraint_config)
validator = ConstraintValidator(constraints)

# Mock storage info collector on storage_info module
mock_collector = MagicMock()
mock_collector.get_disk_usage.return_value = {
    'free_bytes': 5000 * 1024 * 1024,
    'total_bytes': 10000 * 1024 * 1024,
    'used_bytes': 5000 * 1024 * 1024,
    'free_mb': 5000,
    'total_mb': 10000,
    'used_mb': 5000
}
_si_mod.StorageInfoCollector = MagicMock(return_value=mock_collector)

with tempfile.NamedTemporaryFile(delete=False) as tf:
    tf.write(b'0' * (50 * 1024 * 1024))
    tf.flush()
    tf.close()
    tmp = tf.name

print('Temp file:', tmp)
res = validator.validate_before_operation(target_path='/test/target', source_file_path=tmp, operation='copy')
print('Result:', res)

# Also call capacity directly
cap = constraints.validate_storage_capacity(Path('/tmp'))
print('Capacity:', cap)

try:
    os.unlink(tmp)
except Exception:
    pass
