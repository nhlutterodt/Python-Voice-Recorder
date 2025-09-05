"""Storage Configuration Module

Environment-specific storage configuration management.
"""

# Temporarily comment out imports to fix circular dependency during Phase 1
try:
    from .storage_config import StorageConfig
except ImportError:
    StorageConfig = None

try:
    from .environment import Environment, EnvironmentConfig, EnvironmentManager
except ImportError:
    Environment = None
    EnvironmentConfig = None 
    EnvironmentManager = None

try:
    from .path_management import (
        StoragePathType, 
        StoragePathConfig, 
        StoragePathManager, 
        PathValidator, 
        PathPermissions
    )
except ImportError:
    StoragePathType = None
    StoragePathConfig = None
    StoragePathManager = None
    PathValidator = None
    PathPermissions = None

__all__ = [
    'StorageConfig',
    'Environment', 
    'EnvironmentConfig', 
    'EnvironmentManager',
    'StoragePathType',
    'StoragePathConfig', 
    'StoragePathManager', 
    'PathValidator', 
    'PathPermissions'
]
