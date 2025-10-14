"""
Services Package
Enhanced services for Voice Recorder Pro backend integration
"""

# Conditional imports to avoid circular dependencies during development
try:
    from .file_storage import (
        EnhancedFileStorageService,
        StorageConfig,
        FileMetadataCalculator,
        StorageValidationError
    )
except ImportError:
    # If imports fail, define None placeholders
    EnhancedFileStorageService = None
    StorageConfig = None
    FileMetadataCalculator = None
    StorageValidationError = None

__all__ = [
    'EnhancedFileStorageService',
    'StorageConfig', 
    'FileMetadataCalculator',
    'StorageValidationError'
]
