"""
Enhanced File Storage Exceptions
Custom exceptions for file storage operations with enhanced error handling
"""


class StorageValidationError(Exception):
    """Raised when storage validation fails"""
    pass


class FileMetadataError(Exception):
    """Raised when file metadata calculation fails"""
    pass


class DatabaseSessionError(Exception):
    """Raised when database session operations fail"""
    pass


class FileConstraintError(Exception):
    """Raised when file constraints are violated"""
    pass


class StorageOperationError(Exception):
    """Raised when storage operations fail"""
    pass


class StorageConfigValidationError(Exception):
    """Raised when storage configuration validation fails"""
    pass
