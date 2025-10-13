"""Storage Configuration Module

Environment-specific storage configuration management.
"""

try:
    # Prefer canonical package imports so the same module object is used
    from voice_recorder.services.file_storage.config.storage_config import StorageConfig
except Exception:
    StorageConfig = None

try:
    from voice_recorder.services.file_storage.config.environment import Environment, EnvironmentConfig, EnvironmentManager
except Exception:
    Environment = None
    EnvironmentConfig = None
    EnvironmentManager = None

try:
    from voice_recorder.services.file_storage.config.path_management import (
        StoragePathType,
        StoragePathConfig,
        StoragePathManager,
        PathValidator,
        PathPermissions,
    )
except Exception:
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
