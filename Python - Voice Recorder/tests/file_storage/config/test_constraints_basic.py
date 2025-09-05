"""
Basic tests for Storage Constraints Module - Phase 3
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.file_storage.config.constraints import (
    ConstraintConfig,
    StorageConstraints,
    ConstraintValidator,
    create_constraints_from_environment
)
from services.file_storage.config.environment import EnvironmentConfig
from services.file_storage.exceptions import StorageConfigValidationError


def test_constraint_config_creation():
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
    print("✅ ConstraintConfig creation test passed")


def test_storage_constraints_initialization():
    """Test StorageConstraints initialization"""
    config = ConstraintConfig(
        min_disk_space_mb=100,
        max_file_size_mb=1000,
        enable_disk_space_check=True,
        retention_days=30
    )
    constraints = StorageConstraints(config)
    
    assert constraints.config == config
    assert constraints.config.min_disk_space_mb == 100
    assert constraints.config.max_file_size_mb == 1000
    print("✅ StorageConstraints initialization test passed")


def test_file_constraints_validation():
    """Test file constraint validation with real file"""
    config = ConstraintConfig(
        min_disk_space_mb=100,
        max_file_size_mb=1000,
        enable_disk_space_check=True,
        retention_days=30
    )
    constraints = StorageConstraints(config)
    
    # Test with a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b'0' * (1024 * 1024))  # 1MB file
        temp_file.flush()
        temp_file.close()
        
        try:
            result = constraints.validate_file_constraints(temp_file.name)
            
            assert result['valid'] is True
            assert abs(result['file_size_mb'] - 1.0) < 0.1  # Close to 1MB
            assert len(result['constraints_checked']) > 0
            assert result['applied_constraints']['max_file_size_mb'] == 1000
            
        finally:
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass

    print("✅ File constraints validation test passed")


def test_nonexistent_file_validation():
    """Test file constraint validation with nonexistent file"""
    config = ConstraintConfig(
        min_disk_space_mb=100,
        max_file_size_mb=1000,
        enable_disk_space_check=True,
        retention_days=30
    )
    constraints = StorageConstraints(config)
    
    result = constraints.validate_file_constraints('/nonexistent/file.txt')
    
    assert result['valid'] is False
    assert result['errors']
    assert 'File does not exist' in result['errors'][0]
    print("✅ Nonexistent file validation test passed")


def test_disk_space_validation():
    """Test disk space validation"""
    config = ConstraintConfig(
        min_disk_space_mb=100,
        max_file_size_mb=1000,
        enable_disk_space_check=True,
        retention_days=30
    )
    constraints = StorageConstraints(config)
    
    # Test with a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b'0' * (1024 * 1024))  # 1MB file
        temp_file.flush()
        temp_file.close()
        
        try:
            result = constraints.validate_disk_space_for_file(temp_file.name, Path('.'))
            
            # Should pass since we have plenty of disk space
            assert result['valid'] is True
            assert result['available_space_mb'] > 0
            assert result['required_space_mb'] > 0
            
        finally:
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass

    print("✅ Disk space validation test passed")


def test_disabled_disk_space_check():
    """Test disk space validation when disabled"""
    config = ConstraintConfig(
        min_disk_space_mb=100,
        max_file_size_mb=1000,
        enable_disk_space_check=False,
        retention_days=30
    )
    constraints = StorageConstraints(config)
    
    result = constraints.validate_disk_space_for_file('/some/file.txt', Path('.'))
    
    assert result['valid'] is True
    assert 'message' in result
    print("✅ Disabled disk space check test passed")


def test_constraint_validator():
    """Test ConstraintValidator initialization"""
    config = ConstraintConfig(
        min_disk_space_mb=100,
        max_file_size_mb=1000,
        enable_disk_space_check=True,
        retention_days=30
    )
    constraints = StorageConstraints(config)
    validator = ConstraintValidator(constraints)
    
    assert validator.constraints.config == config
    print("✅ ConstraintValidator test passed")


@patch('services.file_storage.config.environment.EnvironmentManager')
def test_create_constraints_from_environment(mock_env_manager_class):
    """Test creating constraints from environment manager"""
    # Mock environment manager
    mock_env_manager = MagicMock()
    mock_env_config = EnvironmentConfig(
        base_subdir='test',
        min_disk_space_mb=250,
        max_file_size_mb=1500,
        enable_disk_space_check=True,
        enable_backup=False,
        enable_compression=False,
        retention_days=45
    )
    mock_env_manager.get_config.return_value = mock_env_config
    mock_env_manager_class.return_value = mock_env_manager
    
    constraints = create_constraints_from_environment('testing')
    
    assert constraints.config.min_disk_space_mb == 250
    assert constraints.config.max_file_size_mb == 1500
    assert constraints.config.enable_disk_space_check is True
    assert constraints.config.retention_days == 45
    print("✅ Create constraints from environment test passed")


if __name__ == '__main__':
    """Run basic tests"""
    try:
        test_constraint_config_creation()
        test_storage_constraints_initialization()
        test_file_constraints_validation()
        test_nonexistent_file_validation()
        test_disk_space_validation()
        test_disabled_disk_space_check()
        test_constraint_validator()
        test_create_constraints_from_environment()
        print("\n🎉 All basic constraints tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
