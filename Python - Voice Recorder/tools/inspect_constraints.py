import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from services.file_storage.config.constraints import ConstraintConfig, StorageConstraints

# Setup
cfg = ConstraintConfig(min_disk_space_mb=100, max_file_size_mb=1000, enable_disk_space_check=True, retention_days=30)
constraints = StorageConstraints(cfg)

# Create a temp file
with tempfile.NamedTemporaryFile() as tf:
    base_path = Path(tf.name).parent
    print('temp file:', tf.name)

    # Create mock collector
    mock_collector = MagicMock()
    mock_collector.get_raw_storage_info.return_value = {'free_mb': 2000, 'used_mb': 1000, 'total_mb': 3000}

    # Patch the collector class on the constraints module
    import services.file_storage.config.constraints as constraints_mod
    class DummyCollector:
        def __init__(self, path):
            print('DummyCollector.__init__ path=', path)
        def get_raw_storage_info(self):
            print('DummyCollector.get_raw_storage_info called')
            return {'free_mb': 2000, 'used_mb': 1000, 'total_mb': 3000}

    # Monkeypatch the StorageInfoCollector symbol on the module to the mock class
    constraints_mod.StorageInfoCollector = lambda base: mock_collector

    # Call the function
    result = constraints.validate_disk_space_for_file(tf.name, base_path)
    print('result:', result)

    # Show module-level collector symbol
    print('module StorageInfoCollector is', constraints_mod.StorageInfoCollector)
