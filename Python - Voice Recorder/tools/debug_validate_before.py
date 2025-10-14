import tempfile
import os
from unittest.mock import MagicMock

from services.file_storage.config.constraints import ConstraintConfig, StorageConstraints, ConstraintValidator

# Setup constraints and validator
constraint_config = ConstraintConfig(min_disk_space_mb=100, max_file_size_mb=1000, enable_disk_space_check=True, retention_days=30)
constraints = StorageConstraints(constraint_config)
validator = ConstraintValidator(constraints)

# Mock storage info collector on storage_info module
from services.file_storage.config import storage_info as _si_mod
mock_collector = MagicMock()
mock_collector.get_disk_usage.return_value = {
    'free_bytes': 5000 * 1024 * 1024,
    'total_bytes': 10000 * 1024 * 1024,
    'used_bytes': 5000 * 1024 * 1024,
    'free_mb': 5000,
    'total_mb': 10000,
    'used_mb': 5000
}
# Patch the StorageInfoCollector symbol
_si_mod.StorageInfoCollector = MagicMock(return_value=mock_collector)

# create temp file
with tempfile.NamedTemporaryFile(delete=False) as temp_file:
    temp_file.write(b'0' * (50 * 1024 * 1024))
    temp_file.flush()
    temp_file.close()
    temp_name = temp_file.name

print('Temp file:', temp_name)

result = validator.validate_before_operation(target_path='/test/target', source_file_path=temp_name, operation='copy')
print('Validation result:', result)

try:
    os.unlink(temp_name)
except Exception:
    pass
