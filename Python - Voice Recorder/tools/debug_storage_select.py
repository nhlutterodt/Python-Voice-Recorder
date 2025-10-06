import sys
from pathlib import Path
# Ensure project root is on sys.path
proj_root = Path(__file__).resolve().parents[1]
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

from unittest.mock import MagicMock
from services.file_storage.config import constraints
from services.file_storage.config.environment import EnvironmentConfig

print('constraints module:', constraints)

cfg = constraints.ConstraintConfig(min_disk_space_mb=100, max_file_size_mb=1000, enable_disk_space_check=True, retention_days=30)
sc = constraints.StorageConstraints(cfg)

# Mock collector class that returns dict with both bytes and mb
mock_collector = MagicMock()
mock_collector.get_disk_usage.return_value = {
    'free_bytes': 5000 * 1024 * 1024,
    'total_bytes': 10000 * 1024 * 1024,
    'used_bytes': 5000 * 1024 * 1024,
    'free_mb': 5000,
    'total_mb': 10000,
    'used_mb': 5000
}

# Case A: patch constraints.StorageInfoCollector
print('\nCase A: patching constraints.StorageInfoCollector')
constraints.StorageInfoCollector = lambda base: mock_collector
resA = sc.validate_disk_space_for_file('/test/file', 50)
print('result A:', resA)

# Case B: patch storage_info.StorageInfoCollector
print('\nCase B: patching storage_info.StorageInfoCollector')
from services.file_storage.config import storage_info as _si
_si.StorageInfoCollector = lambda base: mock_collector
# remove constraints level to simulate tests that only patch storage_info
try:
    delattr(constraints, 'StorageInfoCollector')
except Exception:
    pass
resB = sc.validate_disk_space_for_file('/test/file', 50)
print('result B:', resB)

# Show normalization direct
print('\nDirect normalization check:')
print(constraints._normalize_storage_info(mock_collector.get_disk_usage()))
