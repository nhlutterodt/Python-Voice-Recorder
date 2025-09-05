"""
Environment Configuration Management
Handles environment-specific settings and validation for storage configuration
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List

from ..exceptions import StorageConfigValidationError


class Environment(Enum):
    """Supported environment types with clear enumeration"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

    @classmethod
    def get_all_values(cls) -> List[str]:
        """Get all environment values as strings"""
        return [env.value for env in cls]

    @classmethod
    def from_string(cls, env_string: str) -> 'Environment':
        """Create Environment enum from string with validation"""
        try:
            return cls(env_string)
        except ValueError:
            supported = ', '.join(cls.get_all_values())
            raise StorageConfigValidationError(
                f"Unsupported environment '{env_string}'. Supported: {supported}"
            )


@dataclass(frozen=True)
class EnvironmentConfig:
    """
    Immutable environment-specific configuration
    
    This dataclass contains all environment-specific settings without any business logic.
    Making it frozen ensures configuration immutability and prevents accidental modifications.
    """
    # Storage path configuration
    base_subdir: str
    
    # Disk space constraints
    min_disk_space_mb: int
    enable_disk_space_check: bool
    
    # File size constraints
    max_file_size_mb: int
    
    # Feature flags
    enable_backup: bool
    enable_compression: bool
    
    # Data retention policy
    retention_days: int

    def __post_init__(self):
        """Validate configuration values after initialization"""
        validation_errors = []
        
        if self.min_disk_space_mb <= 0:
            validation_errors.append("min_disk_space_mb must be positive")
        
        if self.max_file_size_mb <= 0:
            validation_errors.append("max_file_size_mb must be positive")
        
        if self.retention_days <= 0:
            validation_errors.append("retention_days must be positive")
        
        if not self.base_subdir:
            validation_errors.append("base_subdir cannot be empty")
        
        if validation_errors:
            raise StorageConfigValidationError(
                f"Invalid environment configuration: {'; '.join(validation_errors)}"
            )

    def merge_with_custom(self, custom_config: Dict[str, Any]) -> 'EnvironmentConfig':
        """
        Create a new EnvironmentConfig with custom overrides
        
        Args:
            custom_config: Dictionary of custom configuration overrides
            
        Returns:
            New EnvironmentConfig instance with custom values applied
            
        Raises:
            StorageConfigValidationError: If custom config contains invalid values
        """
        # Start with current config values
        config_dict = {
            'base_subdir': self.base_subdir,
            'min_disk_space_mb': self.min_disk_space_mb,
            'enable_disk_space_check': self.enable_disk_space_check,
            'max_file_size_mb': self.max_file_size_mb,
            'enable_backup': self.enable_backup,
            'enable_compression': self.enable_compression,
            'retention_days': self.retention_days
        }
        
        # Apply custom overrides with validation
        for key, value in custom_config.items():
            if key not in config_dict:
                raise StorageConfigValidationError(
                    f"Unknown configuration key: {key}. "
                    f"Valid keys: {', '.join(config_dict.keys())}"
                )
            config_dict[key] = value
        
        # Create new instance (will trigger validation in __post_init__)
        return EnvironmentConfig(**config_dict)

    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging and logging"""
        return {
            'storage': {
                'base_subdir': self.base_subdir,
                'min_disk_space_mb': self.min_disk_space_mb,
                'max_file_size_mb': self.max_file_size_mb,
                'enable_disk_space_check': self.enable_disk_space_check
            },
            'features': {
                'enable_backup': self.enable_backup,
                'enable_compression': self.enable_compression
            },
            'policies': {
                'retention_days': self.retention_days
            }
        }


class EnvironmentManager:
    """
    Manages environment configuration selection and validation
    
    This class handles the business logic for environment management,
    including configuration loading, validation, and factory methods.
    """
    
    # Environment-specific configurations
    _ENVIRONMENT_CONFIGS = {
        Environment.DEVELOPMENT: EnvironmentConfig(
            base_subdir='recordings_dev',
            min_disk_space_mb=50,
            enable_disk_space_check=True,
            max_file_size_mb=500,
            enable_backup=False,
            retention_days=30,
            enable_compression=False
        ),
        Environment.TESTING: EnvironmentConfig(
            base_subdir='recordings_test',
            min_disk_space_mb=10,
            enable_disk_space_check=False,  # Disabled for CI/testing
            max_file_size_mb=100,
            enable_backup=False,
            retention_days=7,
            enable_compression=True
        ),
        Environment.PRODUCTION: EnvironmentConfig(
            base_subdir='recordings',
            min_disk_space_mb=500,
            enable_disk_space_check=True,
            max_file_size_mb=2000,
            enable_backup=True,
            retention_days=365,
            enable_compression=True
        )
    }

    @classmethod
    def get_supported_environments(cls) -> List[str]:
        """Get list of all supported environment names"""
        return Environment.get_all_values()

    @classmethod
    def get_config(cls, environment: str, custom_config: Optional[Dict[str, Any]] = None) -> EnvironmentConfig:
        """
        Get configuration for specified environment with optional custom overrides
        
        Args:
            environment: Environment name (development/testing/production)
            custom_config: Optional dictionary of custom configuration overrides
            
        Returns:
            EnvironmentConfig instance for the specified environment
            
        Raises:
            StorageConfigValidationError: If environment is invalid or custom config is invalid
        """
        # Validate and convert environment string to enum
        env_enum = Environment.from_string(environment)
        
        # Get base configuration for environment
        base_config = cls._ENVIRONMENT_CONFIGS[env_enum]
        
        # Apply custom overrides if provided
        if custom_config:
            return base_config.merge_with_custom(custom_config)
        
        return base_config

    @classmethod
    def validate_environment(cls, environment: str) -> str:
        """
        Validate environment string and return normalized value
        
        Args:
            environment: Environment string to validate
            
        Returns:
            Validated environment string
            
        Raises:
            StorageConfigValidationError: If environment is invalid
        """
        env_enum = Environment.from_string(environment)
        return env_enum.value

    @classmethod
    def get_environment_summary(cls, environment: str) -> Dict[str, Any]:
        """
        Get comprehensive summary for an environment
        
        Args:
            environment: Environment name to get summary for
            
        Returns:
            Dictionary containing environment summary information
        """
        env_config = cls.get_config(environment)
        return {
            'environment': environment,
            'config': env_config.get_summary(),
            'supported_environments': cls.get_supported_environments(),
            'is_production': environment == Environment.PRODUCTION.value,
            'backup_enabled': env_config.enable_backup,
            'compression_enabled': env_config.enable_compression
        }

    @classmethod
    def compare_environments(cls, env1: str, env2: str) -> Dict[str, Any]:
        """
        Compare configuration between two environments
        
        Args:
            env1: First environment to compare
            env2: Second environment to compare
            
        Returns:
            Dictionary showing differences between environments
        """
        config1 = cls.get_config(env1)
        config2 = cls.get_config(env2)
        
        differences = {}
        
        # Compare each configuration field
        for field in ['base_subdir', 'min_disk_space_mb', 'enable_disk_space_check',
                      'max_file_size_mb', 'enable_backup', 'enable_compression', 'retention_days']:
            value1 = getattr(config1, field)
            value2 = getattr(config2, field)
            
            if value1 != value2:
                differences[field] = {
                    env1: value1,
                    env2: value2
                }
        
        return {
            'environments': [env1, env2],
            'differences': differences,
            'identical': len(differences) == 0
        }

    @classmethod
    def get_all_configurations(cls) -> Dict[str, EnvironmentConfig]:
        """
        Get all environment configurations
        
        Returns:
            Dictionary mapping environment names to their configurations
        """
        return {
            env.value: config 
            for env, config in cls._ENVIRONMENT_CONFIGS.items()
        }
