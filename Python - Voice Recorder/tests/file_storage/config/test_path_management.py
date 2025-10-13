"""
Tests for Path Management Module (Phase 2)
Test the enhanced path management functionality added in Phase 2
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from voice_recorder.services.file_storage.config.path_management import (
    StoragePathType,
    StoragePathConfig,
    StoragePathManager,
    PathValidator,
    PathPermissions,
)
from voice_recorder.services.file_storage.exceptions import StorageConfigValidationError


class TestStoragePathType:
    """Test StoragePathType enum functionality"""
    
    def test_enum_values(self):
        """Test that all expected enum values exist"""
        expected_types = ["raw", "edited", "temp", "backup"]
        actual_types = StoragePathType.get_all_types()
        assert actual_types == expected_types
    
    def test_from_string_valid(self):
        """Test creating enum from valid string values"""
        for type_str in ["raw", "edited", "temp", "backup"]:
            path_type = StoragePathType.from_string(type_str)
            assert path_type.value == type_str
    
    def test_from_string_case_insensitive(self):
        """Test that from_string is case insensitive"""
        path_type = StoragePathType.from_string("RAW")
        assert path_type == StoragePathType.RAW
        
        path_type = StoragePathType.from_string("Edited")
        assert path_type == StoragePathType.EDITED
    
    def test_from_string_invalid(self):
        """Test that invalid strings raise ValueError"""
        with pytest.raises(ValueError, match="Invalid storage path type"):
            StoragePathType.from_string("invalid_type")


class TestPathPermissions:
    """Test PathPermissions dataclass functionality"""
    
    def test_full_access_permissions(self):
        """Test permissions with full access"""
        permissions = PathPermissions(
            readable=True, writable=True, executable=True,
            owner_readable=True, owner_writable=True, owner_executable=True
        )
        assert permissions.is_fully_accessible()
        
        summary = permissions.get_summary()
        assert summary['access'] == 'full'
        assert summary['readable']
        assert summary['writable']
    
    def test_limited_access_permissions(self):
        """Test permissions with limited access"""
        permissions = PathPermissions(
            readable=True, writable=False, executable=False,
            owner_readable=True, owner_writable=False, owner_executable=False
        )
        assert not permissions.is_fully_accessible()
        
        summary = permissions.get_summary()
        assert summary['access'] == 'limited'
        assert summary['readable']
        assert not summary['writable']


class TestStoragePathConfig:
    """Test StoragePathConfig dataclass functionality"""
    
    def test_valid_config_creation(self):
        """Test creating valid configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoragePathConfig(
                base_path=Path(temp_dir),
                raw_subdir="raw_files",
                edited_subdir="edited_files",
                temp_subdir="temp_files",
                backup_subdir="backup_files"
            )
            assert config.base_path == Path(temp_dir)
            assert config.raw_subdir == "raw_files"
            assert config.enable_backup_path
    
    def test_config_validation_empty_subdir(self):
        """Test that empty subdirectory names are rejected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(StorageConfigValidationError, match="must be a non-empty string"):
                StoragePathConfig(
                    base_path=Path(temp_dir),
                    raw_subdir=""
                )
    
    def test_config_validation_path_separators(self):
        """Test that subdirectory names with path separators are rejected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(StorageConfigValidationError, match="cannot contain path separators"):
                StoragePathConfig(
                    base_path=Path(temp_dir),
                    raw_subdir="raw/invalid"
                )
    
    def test_get_path_for_type(self):
        """Test getting paths for different storage types"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoragePathConfig(base_path=Path(temp_dir))
            
            raw_path = config.get_path_for_type(StoragePathType.RAW)
            assert raw_path == Path(temp_dir) / "raw"
            
            edited_path = config.get_path_for_type("edited")
            assert edited_path == Path(temp_dir) / "edited"
    
    def test_get_path_for_disabled_backup(self):
        """Test getting backup path when backup is disabled"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoragePathConfig(
                base_path=Path(temp_dir),
                enable_backup_path=False
            )
            
            with pytest.raises(ValueError, match="Backup path is disabled"):
                config.get_path_for_type(StoragePathType.BACKUP)
    
    def test_get_all_paths(self):
        """Test getting all configured paths"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoragePathConfig(base_path=Path(temp_dir))
            
            all_paths = config.get_all_paths()
            assert 'raw' in all_paths
            assert 'edited' in all_paths
            assert 'temp' in all_paths
            assert 'backup' in all_paths
            
            assert all_paths['raw'] == Path(temp_dir) / "raw"
    
    def test_merge_with_custom(self):
        """Test merging configuration with custom overrides"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoragePathConfig(base_path=Path(temp_dir))
            
            custom_config = {
                'raw_subdir': 'custom_raw',
                'enable_backup_path': False
            }
            
            merged = config.merge_with_custom(custom_config)
            assert merged.raw_subdir == 'custom_raw'
            assert not merged.enable_backup_path
            assert merged.base_path == config.base_path  # Should remain unchanged
    
    def test_merge_with_invalid_keys(self):
        """Test that invalid custom config keys are rejected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoragePathConfig(base_path=Path(temp_dir))
            
            custom_config = {'invalid_key': 'value'}
            
            with pytest.raises(StorageConfigValidationError, match="Invalid configuration keys"):
                config.merge_with_custom(custom_config)


class TestPathValidator:
    """Test PathValidator static methods"""
    
    def test_validate_path_exists_existing(self):
        """Test validating an existing path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            exists, message = PathValidator.validate_path_exists(path)
            assert exists
            assert "Path exists" in message
    
    def test_validate_path_exists_nonexistent(self):
        """Test validating a non-existent path"""
        path = Path("/nonexistent/path/that/should/not/exist")
        exists, message = PathValidator.validate_path_exists(path)
        assert not exists
        assert "Path does not exist" in message
    
    def test_validate_path_permissions_existing_directory(self):
        """Test validating permissions on an existing directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            valid, permissions, message = PathValidator.validate_path_permissions(path)
            
            assert valid
            assert permissions is not None
            assert isinstance(permissions, PathPermissions)
            assert "access" in message.lower()
    
    def test_validate_path_permissions_nonexistent(self):
        """Test validating permissions on non-existent path"""
        path = Path("/nonexistent/path")
        valid, permissions, message = PathValidator.validate_path_permissions(path)
        
        assert not valid
        assert permissions is None
        assert "does not exist" in message
    
    def test_validate_directory_creation_new(self):
        """Test creating a new directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"
            success, message = PathValidator.validate_directory_creation(new_dir)
            
            assert success
            assert new_dir.exists()
            assert "successfully" in message.lower()
    
    def test_validate_directory_creation_existing(self):
        """Test validation on existing directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            success, message = PathValidator.validate_directory_creation(path)
            
            assert success
            assert "already exists" in message
    
    def test_validate_cross_platform_path_valid(self):
        """Test cross-platform validation on valid path"""
        path = Path("valid/path/structure")
        valid, message = PathValidator.validate_cross_platform_path(path)
        assert valid
        assert "compatible" in message.lower()
    
    @patch('platform.system', return_value='Windows')
    def test_validate_cross_platform_path_windows_invalid_chars(self, _mock_system):
        """Test cross-platform validation with Windows invalid characters"""
        path = Path("invalid<path>with:bad|chars")
        valid, message = PathValidator.validate_cross_platform_path(path)
        assert not valid
        assert "invalid Windows character" in message
    
    @patch('platform.system', return_value='Windows')
    def test_validate_cross_platform_path_windows_reserved_names(self, _mock_system):
        """Test cross-platform validation with Windows reserved names"""
        path = Path("some/CON/path")
        valid, message = PathValidator.validate_cross_platform_path(path)
        assert not valid
        assert "reserved name" in message


class TestStoragePathManager:
    """Test StoragePathManager functionality"""
    
    def setUp_path_manager(self, temp_dir):
        """Helper to create a path manager for testing"""
        config = StoragePathConfig(base_path=Path(temp_dir))
        return StoragePathManager(config)
    
    def test_path_manager_creation(self):
        """Test creating a path manager"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.setUp_path_manager(temp_dir)
            assert manager.config.base_path == Path(temp_dir)
    
    def test_get_path_for_type(self):
        """Test getting path for storage type"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.setUp_path_manager(temp_dir)
            
            raw_path = manager.get_path_for_type(StoragePathType.RAW)
            assert raw_path == Path(temp_dir) / "raw"
            
            edited_path = manager.get_path_for_type("edited")
            assert edited_path == Path(temp_dir) / "edited"
    
    def test_get_all_paths(self):
        """Test getting all paths"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.setUp_path_manager(temp_dir)
            
            all_paths = manager.get_all_paths()
            assert len(all_paths) == 4  # raw, edited, temp, backup
            assert all(isinstance(path, Path) for path in all_paths.values())
    
    def test_get_supported_path_types(self):
        """Test getting supported path types"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.setUp_path_manager(temp_dir)
            
            types = manager.get_supported_path_types()
            assert types == ["raw", "edited", "temp", "backup"]
    
    def test_ensure_directories_success(self):
        """Test ensuring directories are created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.setUp_path_manager(temp_dir)
            
            result = manager.ensure_directories()
            assert result['success']
            assert len(result['created_directories']) > 0 or len(result['existing_directories']) > 0
            
            # Verify directories actually exist
            for path_type, path in manager.get_all_paths().items():
                assert path.exists(), f"Directory {path_type} was not created"
    
    def test_validate_path_configuration(self):
        """Test comprehensive path configuration validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.setUp_path_manager(temp_dir)
            
            # Create directories first
            manager.ensure_directories()
            
            validation_result = manager.validate_path_configuration()
            assert validation_result['paths_checked'] > 0
            assert validation_result['paths_valid'] >= 0
            assert 'details' in validation_result
    
    def test_get_path_information(self):
        """Test getting comprehensive path information"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self.setUp_path_manager(temp_dir)
            
            info = manager.get_path_information()
            assert 'configuration' in info
            assert 'paths' in info
            assert 'supported_types' in info
            assert 'platform' in info
            
            assert info['configuration']['base_path'] == str(temp_dir)
    
    def test_create_default(self):
        """Test creating default path manager"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = StoragePathManager.create_default(temp_dir)
            assert manager.config.base_path == Path(temp_dir)
            assert manager.config.enable_backup_path
    
    def test_create_from_environment_config(self):
        """Test creating path manager from environment config"""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_config = {
                'enable_backup': False,
                'min_disk_space_mb': 100
            }
            
            manager = StoragePathManager.create_from_environment_config(temp_dir, env_config)
            assert manager.config.base_path == Path(temp_dir)
            assert not manager.config.enable_backup_path


class TestPathManagementIntegration:
    """Integration tests for path management functionality"""
    
    def test_full_path_workflow(self):
        """Test complete path management workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create path manager
            config = StoragePathConfig(
                base_path=Path(temp_dir),
                raw_subdir="recordings",
                edited_subdir="processed",
                temp_subdir="temporary"
            )
            manager = StoragePathManager(config)
            
            # Ensure directories
            result = manager.ensure_directories()
            assert result['success']
            
            # Validate configuration
            validation = manager.validate_path_configuration()
            assert validation['paths_checked'] > 0
            
            # Get path information
            info = manager.get_path_information()
            assert len(info['paths']) > 0
            
            # Test individual path access
            raw_path = manager.get_path_for_type('raw')
            assert raw_path.exists()
            assert raw_path.name == "recordings"
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery in path operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoragePathConfig(base_path=Path(temp_dir))
            manager = StoragePathManager(config)
            
            # Test invalid path type
            with pytest.raises(StorageConfigValidationError):
                manager.get_path_for_type("invalid_type")
            
            # Test that valid operations still work after error
            raw_path = manager.get_path_for_type('raw')
            assert isinstance(raw_path, Path)
    
    def test_custom_configuration_override(self):
        """Test custom configuration with path management"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_config = StoragePathConfig(base_path=Path(temp_dir))
            
            custom_overrides = {
                'raw_subdir': 'audio_raw',
                'edited_subdir': 'audio_edited',
                'backup_subdir': 'audio_backup'
            }
            
            custom_config = base_config.merge_with_custom(custom_overrides)
            manager = StoragePathManager(custom_config)
            
            # Verify custom subdirectories are used
            raw_path = manager.get_path_for_type('raw')
            assert raw_path.name == 'audio_raw'
            
            edited_path = manager.get_path_for_type('edited')
            assert edited_path.name == 'audio_edited'
