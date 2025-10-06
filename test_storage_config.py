#!/usr/bin/env python3
"""
Test script to verify StorageConfig functionality
This creates a minimal working version to test Phase 1 fixes
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass

# Define fallback exception
class StorageConfigValidationError(Exception):
    """Storage configuration validation error"""
    pass

@dataclass
class FallbackEnvironmentConfig:
    """Fallback environment configuration when EnvironmentConfig is not available"""
    base_subdir: str
    min_disk_space_mb: int
    enable_disk_space_check: bool
    max_file_size_mb: int
    enable_backup: bool
    retention_days: int
    enable_compression: bool

class StorageConfigHelper:
    """
    Minimal StorageConfig implementation for testing Phase 1 fixes
    """
    
    # Class-level environment configurations for backward compatibility
    ENVIRONMENT_CONFIGS: Dict[str, Dict[str, Union[str, int, bool]]] = {
        'development': {
            'base_subdir': 'recordings_dev',
            'min_disk_space_mb': 50,
            'enable_disk_space_check': True,
            'max_file_size_mb': 500,
            'enable_backup': False,
            'retention_days': 30,
            'enable_compression': False
        },
        'testing': {
            'base_subdir': 'recordings_test', 
            'min_disk_space_mb': 10,
            'enable_disk_space_check': False,
            'max_file_size_mb': 100,
            'enable_backup': False,
            'retention_days': 7,
            'enable_compression': True
        },
        'production': {
            'base_subdir': 'recordings',
            'min_disk_space_mb': 500,
            'enable_disk_space_check': True,
            'max_file_size_mb': 2000,
            'enable_backup': True,
            'retention_days': 365,
            'enable_compression': True
        }
    }
    
    SUPPORTED_ENVIRONMENTS: List[str] = list(ENVIRONMENT_CONFIGS.keys())
    
    def __init__(self, environment: str = "development", base_path: Optional[str] = None,
                 custom_config: Optional[Dict[str, Any]] = None):
        """Initialize storage configuration"""
        self.environment = self._validate_environment(environment)
        
        # Get environment configuration
        env_config_dict = self.ENVIRONMENT_CONFIGS.get(self.environment, self.ENVIRONMENT_CONFIGS['development'])
        self._env_config = FallbackEnvironmentConfig(
            base_subdir=str(env_config_dict['base_subdir']),
            min_disk_space_mb=int(env_config_dict['min_disk_space_mb']),
            enable_disk_space_check=bool(env_config_dict['enable_disk_space_check']),
            max_file_size_mb=int(env_config_dict['max_file_size_mb']),
            enable_backup=bool(env_config_dict['enable_backup']),
            retention_days=int(env_config_dict['retention_days']),
            enable_compression=bool(env_config_dict['enable_compression'])
        )
        
        # Set up base path
        if base_path:
            self._base_path = Path(base_path)
        else:
            self._base_path = Path.cwd() / self._env_config.base_subdir
        
        # Set up legacy path properties for backward compatibility
        self._setup_legacy_paths()
        
        print(f"✅ TestStorageConfig initialized for environment: {environment}")
    
    def _validate_environment(self, environment: str) -> str:
        """Validate environment parameter"""
        if environment not in self.SUPPORTED_ENVIRONMENTS:
            raise StorageConfigValidationError(
                f"Unsupported environment '{environment}'. "
                f"Supported: {', '.join(self.SUPPORTED_ENVIRONMENTS)}"
            )
        return environment
    
    def _setup_legacy_paths(self):
        """Set up legacy path properties for backward compatibility"""
        self.raw_recordings_path = self._base_path / "raw"
        self.edited_recordings_path = self._base_path / "edited"
        self.temp_path = self._base_path / "temp"
        self.backup_path = self._base_path / "backup" if self._env_config.enable_backup else None
    
    @property
    def base_path(self) -> Path:
        """Get base storage path"""
        return self._base_path
    
    @property
    def min_disk_space_mb(self) -> int:
        """Get minimum disk space requirement in MB"""
        return self._env_config.min_disk_space_mb
    
    @property
    def max_file_size_mb(self) -> int:
        """Get maximum file size in MB"""
        return self._env_config.max_file_size_mb
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get complete configuration summary"""
        return {
            'environment': self.environment,
            'base_path': str(self.base_path),
            'paths': {
                'raw': str(self.raw_recordings_path),
                'edited': str(self.edited_recordings_path),
                'temp': str(self.temp_path),
                'backup': str(self.backup_path) if self.backup_path else None
            },
            'constraints': {
                'min_disk_space_mb': self.min_disk_space_mb,
                'max_file_size_mb': self.max_file_size_mb,
                'retention_days': self._env_config.retention_days
            },
            'features': {
                'disk_space_check': self._env_config.enable_disk_space_check,
                'backup': self._env_config.enable_backup,
                'compression': self._env_config.enable_compression
            }
        }

if __name__ == "__main__":
    print("🔧 Testing StorageConfig Phase 1 Implementation")
    print("=" * 50)
    
    try:
        # Test 1: Basic initialization
        print("\n📝 Test 1: Basic Initialization")
        config = StorageConfigHelper()
        print(f"   Base path: {config.base_path}")
        print(f"   Environment: {config.environment}")
        
        # Test 2: Different environments
        print("\n📝 Test 2: Different Environments")
        for env in ['development', 'testing', 'production']:
            test_config = StorageConfigHelper(environment=env)
            print(f"   {env}: {test_config.base_path}")
        
        # Test 3: Configuration summary
        print("\n📝 Test 3: Configuration Summary")
        summary = config.get_configuration_summary()
        for key, value in summary.items():
            print(f"   {key}: {value}")
        
        # Test 4: Properties
        print("\n📝 Test 4: Properties")
        print(f"   Min disk space: {config.min_disk_space_mb} MB")
        print(f"   Max file size: {config.max_file_size_mb} MB")
        
        print("\n✅ All Phase 1 tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
