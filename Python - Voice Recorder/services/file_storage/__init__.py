"""
Enhanced File Storage Package
Modular file storage system with comprehensive metadata management and database integration
"""

# Import exceptions for backward compatibility
from voice_recorder.services.file_storage.exceptions import (
    StorageValidationError,
    FileMetadataError,
    DatabaseSessionError,
    FileConstraintError,
    StorageOperationError,
    StorageConfigValidationError
)

# Import metadata calculator
from voice_recorder.services.file_storage.metadata import FileMetadataCalculator

# Import storage configuration with error handling
try:
    from voice_recorder.services.file_storage.config import StorageConfig
except ImportError:
    StorageConfig = None

# Import core service (conditional import to avoid circular dependencies)
try:
    from voice_recorder.services.file_storage.core import EnhancedFileStorageService
except ImportError:
    # If core import fails, we'll handle it in Phase 6
    EnhancedFileStorageService = None

__all__ = [
    'StorageValidationError',
    'FileMetadataError', 
    'DatabaseSessionError',
    'FileConstraintError',
    'StorageOperationError',
    'StorageConfigValidationError',
    'FileMetadataCalculator',
    'StorageConfig',
    'EnhancedFileStorageService'
]
