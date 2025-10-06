"""
Tests for Storage Constraints Module - Phase 3 (Fixed)
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from services.file_storage.config.constraints import (
    ConstraintConfig,
    StorageConstraints,
    ConstraintValidator,
    create_constraints_from_environment
)
from services.file_storage.config.environment import EnvironmentConfig


class TestConstraintConfig:
    """Test ConstraintConfig dataclass"""
    
    def test_valid_constraint_config(self):
        """Test creating valid constraint configuration"""
        config = ConstraintConfig(
            min_disk_space_mb=50,
            max_file_size_mb=500,
            enable_disk_space_check=True,
            retention_days=30
        )
        
        assert config.min_disk_space_mb == 50
        assert config.max_file_size_mb == 500
        assert config.enable_disk_space_check is True
        assert config.retention_days == 30
    
    def test_invalid_min_disk_space(self):
        """Test constraint config with invalid min disk space"""
        with pytest.raises(ValueError, match="min_disk_space_mb must be positive"):
            ConstraintConfig(
                min_disk_space_mb=0,
                max_file_size_mb=500,
                enable_disk_space_check=True,
                retention_days=30
            )
    
    def test_invalid_max_file_size(self):
        """Test constraint config with invalid max file size"""
        with pytest.raises(ValueError, match="max_file_size_mb must be positive"):
            ConstraintConfig(
                min_disk_space_mb=50,
                max_file_size_mb=0,
                enable_disk_space_check=True,
                retention_days=30
            )


class TestStorageConstraints:
    """Test StorageConstraints class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.config = ConstraintConfig(
            min_disk_space_mb=100,
            max_file_size_mb=1000,
            enable_disk_space_check=True,
            retention_days=30
        )
        self.constraints = StorageConstraints(self.config)
    
    def test_initialization(self):
        """Test StorageConstraints initialization"""
        assert self.constraints.config == self.config
        assert self.constraints.config.min_disk_space_mb == 100
        assert self.constraints.config.max_file_size_mb == 1000
    
    def test_from_environment_config(self):
        """Test creating constraints from environment config"""
        env_config = EnvironmentConfig(
            min_disk_space_mb=200,
            max_file_size_mb=2000,
            enable_disk_space_check=False,
            retention_days=60
        )
        
        constraints = StorageConstraints.from_environment_config(env_config)
        assert constraints.config.min_disk_space_mb == 200
        assert constraints.config.max_file_size_mb == 2000
        assert constraints.config.enable_disk_space_check is False
        assert constraints.config.retention_days == 60
    
    def test_validate_constraints_configuration_valid(self):
        """Test constraint configuration validation with valid values"""
        result = self.constraints.validate_constraints_configuration()
        
        assert result['valid'] is True
        assert result['warnings'] == []
        assert result['constraints']['min_disk_space_mb'] == 100
        assert result['constraints']['max_file_size_mb'] == 1000
    
    def test_validate_file_constraints_nonexistent_file(self):
        """Test file constraint validation with nonexistent file"""
        result = self.constraints.validate_file_constraints('/nonexistent/file.txt')
        
        assert result['valid'] is False
        assert result['errors']
        assert 'file_existence' in result['constraints_checked']
    
    def test_validate_file_constraints_valid_file(self):
        """Test file constraint validation with valid file"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Write 1MB of data
            temp_file.write(b'0' * (1024 * 1024))
            temp_file.flush()
            temp_file.close()  # Close the file before testing

            try:
                result = self.constraints.validate_file_constraints(temp_file.name)

                assert result['valid'] is True
                assert result['file_size_mb'] == 1.0
                assert 'file_size' in result['constraints_checked']
                assert result['applied_constraints']['max_file_size_mb'] == 1000

            finally:
                # Clean up
                try:
                    os.unlink(temp_file.name)
                except (PermissionError, FileNotFoundError):
                    pass  # Ignore cleanup errors
    
    def test_validate_file_constraints_oversized_file(self):
        """Test file constraint validation with oversized file"""
        # Mock oversized file (2000MB - over 1000MB limit)
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=2000 * 1024 * 1024):
                result = self.constraints.validate_file_constraints('/mock/large_file.txt')
                
                assert result['valid'] is False
                assert result['errors']
                assert result['file_size_mb'] == 2000.0
                assert 'file_size' in result['constraints_checked']
    
    def test_validate_disk_space_disabled(self):
        """Test disk space validation when disabled"""
        config = ConstraintConfig(
            min_disk_space_mb=100,
            max_file_size_mb=1000,
            enable_disk_space_check=False,
            retention_days=30
        )
        constraints = StorageConstraints(config)
        
        result = constraints.validate_disk_space_for_file('/some/path', 50)
        
        assert result['valid'] is True
        assert result['skip_reason'] == 'disk_space_check_disabled'
    
    @patch('services.file_storage.config.storage_info.StorageInfoCollector')
    def test_validate_disk_space_for_file_sufficient_space(self, mock_collector_class):
        """Test disk space validation with sufficient space"""
        # Mock storage info collector
        mock_collector = MagicMock()
        mock_collector.get_disk_usage.return_value = {
            'free_bytes': 5000 * 1024 * 1024,  # 5000MB free
            'total_bytes': 10000 * 1024 * 1024,
            'used_bytes': 5000 * 1024 * 1024,
            'free_mb': 5000,
            'total_mb': 10000,
            'used_mb': 5000
        }
        mock_collector_class.return_value = mock_collector
        
        result = self.constraints.validate_disk_space_for_file('/test/path', 50)
        
        assert result['valid'] is True
        assert result['available_space_mb'] == 5000
        assert result['required_space_mb'] == 50
    
    @patch('services.file_storage.config.storage_info.StorageInfoCollector')
    def test_validate_disk_space_for_file_insufficient_space(self, mock_collector_class):
        """Test disk space validation with insufficient space"""
        # Mock storage info collector
        mock_collector = MagicMock()
        mock_collector.get_disk_usage.return_value = {
            'free_bytes': 30 * 1024 * 1024,  # Only 30MB free
            'total_bytes': 1000 * 1024 * 1024,
            'used_bytes': 970 * 1024 * 1024,
            'free_mb': 30,
            'total_mb': 1000,
            'used_mb': 970
        }
        mock_collector_class.return_value = mock_collector
        
        result = self.constraints.validate_disk_space_for_file('/test/path', 50)
        
        assert result['valid'] is False
        assert result['errors']
        assert result['available_space_mb'] == 30
        assert result['required_space_mb'] == 50


class TestConstraintValidator:
    """Test ConstraintValidator class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.config = ConstraintConfig(
            min_disk_space_mb=100,
            max_file_size_mb=1000,
            enable_disk_space_check=True,
            retention_days=30
        )
        self.validator = ConstraintValidator(self.config)
    
    @patch('services.file_storage.config.storage_info.StorageInfoCollector')
    def test_validate_before_operation_valid(self, mock_collector_class):
        """Test pre-operation validation with valid conditions"""
        # Mock storage info collector
        mock_collector = MagicMock()
        mock_collector.get_disk_usage.return_value = {
            'free_bytes': 5000 * 1024 * 1024,  # 5000MB free
            'total_bytes': 10000 * 1024 * 1024,
            'used_bytes': 5000 * 1024 * 1024,
            'free_mb': 5000,
            'total_mb': 10000,
            'used_mb': 5000
        }
        mock_collector_class.return_value = mock_collector
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'0' * (50 * 1024 * 1024))  # 50MB file
            temp_file.flush()
            temp_file.close()
            
            try:
                result = self.validator.validate_before_operation(
                    target_path='/test/target',
                    source_file_path=temp_file.name,
                    operation='copy'
                )
                
                assert result['valid'] is True
                assert result['operation'] == 'copy'
                assert 'source_file_validation' in result
                assert 'disk_space_validation' in result
                
            finally:
                try:
                    os.unlink(temp_file.name)
                except (PermissionError, FileNotFoundError):
                    pass


class TestCreateConstraintsFromEnvironment:
    """Test constraints creation from environment"""
    
    @patch('services.file_storage.config.environment.EnvironmentManager')
    def test_create_constraints_from_environment(self, mock_env_manager_class):
        """Test creating constraints from environment manager"""
        # Mock environment manager
        mock_env_manager = MagicMock()
        mock_env_manager.get_environment_config.return_value = EnvironmentConfig(
            min_disk_space_mb=250,
            max_file_size_mb=1500,
            enable_disk_space_check=True,
            retention_days=45
        )
        mock_env_manager_class.return_value = mock_env_manager
        
        constraints = create_constraints_from_environment()
        
        assert constraints.config.min_disk_space_mb == 250
        assert constraints.config.max_file_size_mb == 1500
        assert constraints.config.enable_disk_space_check is True
        assert constraints.config.retention_days == 45


class TestIntegrationConstraints:
    """Integration tests for constraint validation workflow"""
    
    @patch('services.file_storage.config.environment.EnvironmentManager')
    @patch('services.file_storage.config.storage_info.StorageInfoCollector')
    def test_full_constraint_workflow(self, mock_collector_class, mock_env_manager_class):
        """Test complete constraint validation workflow"""
        # Mock environment manager
        mock_env_manager = MagicMock()
        mock_env_manager.get_environment_config.return_value = EnvironmentConfig(
            min_disk_space_mb=100,
            max_file_size_mb=500,
            enable_disk_space_check=True,
            retention_days=30
        )
        mock_env_manager_class.return_value = mock_env_manager
        
        # Mock storage info collector
        mock_collector = MagicMock()
        mock_collector.get_disk_usage.return_value = {
            'free_bytes': 2000 * 1024 * 1024,  # 2000MB free
            'total_bytes': 5000 * 1024 * 1024,
            'used_bytes': 3000 * 1024 * 1024,
            'free_mb': 2000,
            'total_mb': 5000,
            'used_mb': 3000
        }
        mock_collector_class.return_value = mock_collector
        
        # Create constraints from environment
        constraints = create_constraints_from_environment()
        
        # Create validator
        validator = ConstraintValidator(constraints.config)
        
        # Test workflow with temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'0' * (10 * 1024 * 1024))  # 10MB file
            temp_file.flush()
            temp_file.close()
            
            try:
                # Validate file constraints
                file_result = constraints.validate_file_constraints(temp_file.name)
                assert file_result['valid'] is True
                
                # Validate before operation
                operation_result = validator.validate_before_operation(
                    target_path='/test/target',
                    source_file_path=temp_file.name,
                    operation='move'
                )
                assert operation_result['valid'] is True
                
            finally:
                try:
                    os.unlink(temp_file.name)
                except (PermissionError, FileNotFoundError):
                    pass
