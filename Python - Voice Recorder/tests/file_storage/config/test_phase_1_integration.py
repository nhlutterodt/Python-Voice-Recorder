"""
Integration test for Phase 1: Environment Configuration Module
Tests that the new environment module integrates properly with existing code
"""

import tempfile
from pathlib import Path

from services.file_storage.config.environment import EnvironmentManager, EnvironmentConfig
from services.file_storage.config import StorageConfig


class TestPhase1Integration:
    """Integration tests for Phase 1: Environment Configuration Module"""
    
    def test_environment_module_integration(self):
        """Test that environment module can be used independently"""
        # Test that environment manager works independently
        environments = EnvironmentManager.get_supported_environments()
        assert len(environments) == 3
        assert "development" in environments
        assert "testing" in environments
        assert "production" in environments
        
        # Test getting configurations for each environment
        for env in environments:
            config = EnvironmentManager.get_config(env)
            assert isinstance(config, EnvironmentConfig)
            assert config.base_subdir
            assert config.min_disk_space_mb > 0
            assert config.max_file_size_mb > 0
            assert config.retention_days > 0
        
        # Test custom configuration overrides
        custom_config = {
            'min_disk_space_mb': 1000,
            'enable_backup': True
        }
        
        dev_config = EnvironmentManager.get_config('development', custom_config)
        assert dev_config.min_disk_space_mb == 1000
        assert dev_config.enable_backup is True
        assert dev_config.base_subdir == "recordings_dev"  # Original value preserved
        
        # Test environment comparison
        comparison = EnvironmentManager.compare_environments('development', 'production')
        assert not comparison['identical']
        assert len(comparison['differences']) > 0
        
        # Test that existing StorageConfig still works (backward compatibility)
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = StorageConfig.from_environment('testing', base_path=temp_dir)
            assert storage_config.environment == 'testing'
            assert storage_config.base_path == Path(temp_dir)

    def test_environment_configuration_consistency(self):
        """Test that environment configurations are consistent and sensible"""
        # Get all configurations
        all_configs = EnvironmentManager.get_all_configurations()
        
        # Test that production has the highest constraints
        dev_config = all_configs['development']
        test_config = all_configs['testing'] 
        prod_config = all_configs['production']
        
        # Production should have highest disk space requirement
        assert prod_config.min_disk_space_mb > dev_config.min_disk_space_mb
        assert prod_config.min_disk_space_mb > test_config.min_disk_space_mb
        
        # Production should have highest file size limit
        assert prod_config.max_file_size_mb > dev_config.max_file_size_mb
        assert prod_config.max_file_size_mb > test_config.max_file_size_mb
        
        # Production should have longest retention
        assert prod_config.retention_days > dev_config.retention_days
        assert prod_config.retention_days > test_config.retention_days
        
        # Testing should have most relaxed constraints (for CI)
        assert test_config.min_disk_space_mb <= dev_config.min_disk_space_mb
        assert test_config.enable_disk_space_check is False  # Disabled for CI
        
        # Only production should have backup enabled by default
        assert prod_config.enable_backup is True
        assert dev_config.enable_backup is False
        assert test_config.enable_backup is False

    def test_environment_module_error_handling(self):
        """Test that environment module handles errors appropriately"""
        # Test invalid environment
        try:
            EnvironmentManager.get_config("invalid_environment")
            assert False, "Should have raised error for invalid environment"
        except Exception as e:
            assert "Unsupported environment" in str(e)
        
        # Test invalid custom configuration
        try:
            EnvironmentManager.get_config("development", {"invalid_key": "value"})
            assert False, "Should have raised error for invalid custom config"
        except Exception as e:
            assert "Unknown configuration key" in str(e)
        
        # Test invalid values in custom configuration
        try:
            EnvironmentManager.get_config("development", {"min_disk_space_mb": -100})
            assert False, "Should have raised error for negative disk space"
        except Exception as e:
            assert "min_disk_space_mb must be positive" in str(e)
