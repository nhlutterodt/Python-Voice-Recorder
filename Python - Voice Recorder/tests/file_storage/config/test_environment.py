"""
Unit tests for Environment Configuration Module
Tests environment management functionality in isolation
"""

import pytest
from services.file_storage.config.environment import (
    Environment, 
    EnvironmentConfig, 
    EnvironmentManager
)
from services.file_storage.exceptions import StorageConfigValidationError


class TestEnvironment:
    """Test Environment enum functionality"""
    
    def test_environment_enum_values(self):
        """Test that all expected environments are defined"""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.PRODUCTION.value == "production"
    
    def test_get_all_values(self):
        """Test getting all environment values"""
        values = Environment.get_all_values()
        expected = ["development", "testing", "production"]
        assert values == expected
    
    def test_from_string_valid(self):
        """Test creating Environment from valid string"""
        env = Environment.from_string("development")
        assert env == Environment.DEVELOPMENT
        
        env = Environment.from_string("testing")
        assert env == Environment.TESTING
        
        env = Environment.from_string("production")
        assert env == Environment.PRODUCTION
    
    def test_from_string_invalid(self):
        """Test creating Environment from invalid string raises error"""
        with pytest.raises(StorageConfigValidationError) as exc_info:
            Environment.from_string("invalid_env")
        
        error_msg = str(exc_info.value)
        assert "Unsupported environment 'invalid_env'" in error_msg
        assert "development, testing, production" in error_msg


class TestEnvironmentConfig:
    """Test EnvironmentConfig dataclass functionality"""
    
    def test_valid_config_creation(self):
        """Test creating valid EnvironmentConfig"""
        config = EnvironmentConfig(
            base_subdir="test_recordings",
            min_disk_space_mb=100,
            enable_disk_space_check=True,
            max_file_size_mb=1000,
            enable_backup=True,
            enable_compression=False,
            retention_days=30
        )
        
        assert config.base_subdir == "test_recordings"
        assert config.min_disk_space_mb == 100
        assert config.enable_disk_space_check is True
        assert config.max_file_size_mb == 1000
        assert config.enable_backup is True
        assert config.enable_compression is False
        assert config.retention_days == 30
    
    def test_config_validation_negative_disk_space(self):
        """Test validation fails for negative disk space"""
        with pytest.raises(StorageConfigValidationError) as exc_info:
            EnvironmentConfig(
                base_subdir="test",
                min_disk_space_mb=-10,  # Invalid
                enable_disk_space_check=True,
                max_file_size_mb=1000,
                enable_backup=False,
                enable_compression=False,
                retention_days=30
            )
        
        assert "min_disk_space_mb must be positive" in str(exc_info.value)
    
    def test_config_validation_negative_file_size(self):
        """Test validation fails for negative file size"""
        with pytest.raises(StorageConfigValidationError) as exc_info:
            EnvironmentConfig(
                base_subdir="test",
                min_disk_space_mb=100,
                enable_disk_space_check=True,
                max_file_size_mb=-500,  # Invalid
                enable_backup=False,
                enable_compression=False,
                retention_days=30
            )
        
        assert "max_file_size_mb must be positive" in str(exc_info.value)
    
    def test_config_validation_negative_retention(self):
        """Test validation fails for negative retention days"""
        with pytest.raises(StorageConfigValidationError) as exc_info:
            EnvironmentConfig(
                base_subdir="test",
                min_disk_space_mb=100,
                enable_disk_space_check=True,
                max_file_size_mb=1000,
                enable_backup=False,
                enable_compression=False,
                retention_days=-7  # Invalid
            )
        
        assert "retention_days must be positive" in str(exc_info.value)
    
    def test_config_validation_empty_subdir(self):
        """Test validation fails for empty base_subdir"""
        with pytest.raises(StorageConfigValidationError) as exc_info:
            EnvironmentConfig(
                base_subdir="",  # Invalid
                min_disk_space_mb=100,
                enable_disk_space_check=True,
                max_file_size_mb=1000,
                enable_backup=False,
                enable_compression=False,
                retention_days=30
            )
        
        assert "base_subdir cannot be empty" in str(exc_info.value)
    
    def test_config_validation_multiple_errors(self):
        """Test validation reports multiple errors"""
        with pytest.raises(StorageConfigValidationError) as exc_info:
            EnvironmentConfig(
                base_subdir="",  # Invalid
                min_disk_space_mb=-10,  # Invalid
                enable_disk_space_check=True,
                max_file_size_mb=1000,
                enable_backup=False,
                enable_compression=False,
                retention_days=30
            )
        
        error_msg = str(exc_info.value)
        assert "min_disk_space_mb must be positive" in error_msg
        assert "base_subdir cannot be empty" in error_msg
    
    def test_merge_with_custom_valid(self):
        """Test merging with valid custom configuration"""
        base_config = EnvironmentConfig(
            base_subdir="test",
            min_disk_space_mb=100,
            enable_disk_space_check=True,
            max_file_size_mb=1000,
            enable_backup=False,
            enable_compression=False,
            retention_days=30
        )
        
        custom_config = {
            'min_disk_space_mb': 200,
            'enable_backup': True
        }
        
        merged_config = base_config.merge_with_custom(custom_config)
        
        # Check that custom values are applied
        assert merged_config.min_disk_space_mb == 200
        assert merged_config.enable_backup is True
        
        # Check that other values are preserved
        assert merged_config.base_subdir == "test"
        assert merged_config.max_file_size_mb == 1000
        assert merged_config.enable_compression is False
        assert merged_config.retention_days == 30
    
    def test_merge_with_custom_invalid_key(self):
        """Test merging with invalid custom key raises error"""
        base_config = EnvironmentConfig(
            base_subdir="test",
            min_disk_space_mb=100,
            enable_disk_space_check=True,
            max_file_size_mb=1000,
            enable_backup=False,
            enable_compression=False,
            retention_days=30
        )
        
        custom_config = {
            'invalid_key': 'invalid_value'
        }
        
        with pytest.raises(StorageConfigValidationError) as exc_info:
            base_config.merge_with_custom(custom_config)
        
        error_msg = str(exc_info.value)
        assert "Unknown configuration key: invalid_key" in error_msg
    
    def test_merge_with_custom_invalid_value(self):
        """Test merging with invalid custom value raises error"""
        base_config = EnvironmentConfig(
            base_subdir="test",
            min_disk_space_mb=100,
            enable_disk_space_check=True,
            max_file_size_mb=1000,
            enable_backup=False,
            enable_compression=False,
            retention_days=30
        )
        
        custom_config = {
            'min_disk_space_mb': -50  # Invalid value
        }
        
        with pytest.raises(StorageConfigValidationError):
            base_config.merge_with_custom(custom_config)
    
    def test_get_summary(self):
        """Test getting configuration summary"""
        config = EnvironmentConfig(
            base_subdir="test_recordings",
            min_disk_space_mb=100,
            enable_disk_space_check=True,
            max_file_size_mb=1000,
            enable_backup=True,
            enable_compression=False,
            retention_days=30
        )
        
        summary = config.get_summary()
        
        assert summary['storage']['base_subdir'] == "test_recordings"
        assert summary['storage']['min_disk_space_mb'] == 100
        assert summary['storage']['max_file_size_mb'] == 1000
        assert summary['storage']['enable_disk_space_check'] is True
        assert summary['features']['enable_backup'] is True
        assert summary['features']['enable_compression'] is False
        assert summary['policies']['retention_days'] == 30


class TestEnvironmentManager:
    """Test EnvironmentManager functionality"""
    
    def test_get_supported_environments(self):
        """Test getting supported environments"""
        environments = EnvironmentManager.get_supported_environments()
        expected = ["development", "testing", "production"]
        assert environments == expected
    
    def test_get_config_development(self):
        """Test getting development configuration"""
        config = EnvironmentManager.get_config("development")
        
        assert config.base_subdir == "recordings_dev"
        assert config.min_disk_space_mb == 50
        assert config.enable_disk_space_check is True
        assert config.max_file_size_mb == 500
        assert config.enable_backup is False
        assert config.retention_days == 30
        assert config.enable_compression is False
    
    def test_get_config_testing(self):
        """Test getting testing configuration"""
        config = EnvironmentManager.get_config("testing")
        
        assert config.base_subdir == "recordings_test"
        assert config.min_disk_space_mb == 10
        assert config.enable_disk_space_check is False  # Disabled for CI
        assert config.max_file_size_mb == 100
        assert config.enable_backup is False
        assert config.retention_days == 7
        assert config.enable_compression is True
    
    def test_get_config_production(self):
        """Test getting production configuration"""
        config = EnvironmentManager.get_config("production")
        
        assert config.base_subdir == "recordings"
        assert config.min_disk_space_mb == 500
        assert config.enable_disk_space_check is True
        assert config.max_file_size_mb == 2000
        assert config.enable_backup is True
        assert config.retention_days == 365
        assert config.enable_compression is True
    
    def test_get_config_invalid_environment(self):
        """Test getting config for invalid environment raises error"""
        with pytest.raises(StorageConfigValidationError) as exc_info:
            EnvironmentManager.get_config("invalid_env")
        
        assert "Unsupported environment 'invalid_env'" in str(exc_info.value)
    
    def test_get_config_with_custom_overrides(self):
        """Test getting config with custom overrides"""
        custom_config = {
            'min_disk_space_mb': 1000,
            'enable_backup': True
        }
        
        config = EnvironmentManager.get_config("development", custom_config)
        
        # Check custom overrides are applied
        assert config.min_disk_space_mb == 1000
        assert config.enable_backup is True
        
        # Check base values are preserved
        assert config.base_subdir == "recordings_dev"
        assert config.max_file_size_mb == 500
    
    def test_validate_environment_valid(self):
        """Test validating valid environments"""
        assert EnvironmentManager.validate_environment("development") == "development"
        assert EnvironmentManager.validate_environment("testing") == "testing"
        assert EnvironmentManager.validate_environment("production") == "production"
    
    def test_validate_environment_invalid(self):
        """Test validating invalid environment raises error"""
        with pytest.raises(StorageConfigValidationError):
            EnvironmentManager.validate_environment("invalid_env")
    
    def test_get_environment_summary(self):
        """Test getting environment summary"""
        summary = EnvironmentManager.get_environment_summary("development")
        
        assert summary['environment'] == "development"
        assert 'config' in summary
        assert summary['supported_environments'] == ["development", "testing", "production"]
        assert summary['is_production'] is False
        assert summary['backup_enabled'] is False
        assert summary['compression_enabled'] is False
    
    def test_get_environment_summary_production(self):
        """Test getting production environment summary"""
        summary = EnvironmentManager.get_environment_summary("production")
        
        assert summary['environment'] == "production"
        assert summary['is_production'] is True
        assert summary['backup_enabled'] is True
        assert summary['compression_enabled'] is True
    
    def test_compare_environments(self):
        """Test comparing different environments"""
        comparison = EnvironmentManager.compare_environments("development", "production")
        
        assert comparison['environments'] == ["development", "production"]
        assert 'differences' in comparison
        assert comparison['identical'] is False
        
        # Check some expected differences
        differences = comparison['differences']
        assert 'min_disk_space_mb' in differences
        assert differences['min_disk_space_mb']['development'] == 50
        assert differences['min_disk_space_mb']['production'] == 500
        
        assert 'enable_backup' in differences
        assert differences['enable_backup']['development'] is False
        assert differences['enable_backup']['production'] is True
    
    def test_compare_same_environment(self):
        """Test comparing same environment shows no differences"""
        comparison = EnvironmentManager.compare_environments("development", "development")
        
        assert comparison['environments'] == ["development", "development"]
        assert comparison['differences'] == {}
        assert comparison['identical'] is True
    
    def test_get_all_configurations(self):
        """Test getting all configurations"""
        all_configs = EnvironmentManager.get_all_configurations()
        
        assert len(all_configs) == 3
        assert "development" in all_configs
        assert "testing" in all_configs
        assert "production" in all_configs
        
        # Verify configurations are correct types
        for env_name, config in all_configs.items():
            assert isinstance(config, EnvironmentConfig)
            assert config.base_subdir  # Should have valid base_subdir


if __name__ == "__main__":
    pytest.main([__file__])
