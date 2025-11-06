"""
Lazy import helpers for Google Cloud APIs

Centralized module for lazy-loading Google API libraries to support optional
cloud integration. Allows importing this module and the cloud package without
requiring Google API libraries to be installed.

This follows the pattern established in drive_manager.py and enables graceful
degradation when optional dependencies are unavailable.
"""

import importlib.util
import logging
from typing import Any, Tuple

logger = logging.getLogger(__name__)

# Module-level constant for error message (used in multiple places)
_GOOGLE_API_ERROR_MSG = (
    "Google API client libraries not available. "
    "Install with: pip install google-api-python-client"
)


def _has_module(module_name: str) -> bool:
    """
    Check if a module is available without importing it.
    
    Args:
        module_name: Fully-qualified module name (e.g., 'googleapiclient.discovery')
    
    Returns:
        True if the module is available, False otherwise
    """
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def has_google_apis_available() -> bool:
    """
    Check if all required Google API libraries are available.
    
    Verifies the presence of:
    - googleapiclient.discovery (for service building)
    - googleapiclient.http (for file uploads/downloads)
    - googleapiclient.errors (for error handling)
    
    Returns:
        True if all required libraries are available, False otherwise
    
    Example:
        >>> if has_google_apis_available():
        ...     from cloud import GoogleDriveManager
        ... else:
        ...     print("Google APIs not available")
    """
    required = [
        "googleapiclient.discovery",
        "googleapiclient.http",
        "googleapiclient.errors",
    ]
    return all(_has_module(module) for module in required)


def import_build() -> Any:
    """
    Lazy import and return the Drive API service builder.
    
    This is deferred until actually needed to allow the module to be imported
    even if Google API libraries are missing.
    
    Returns:
        The googleapiclient.discovery.build function
    
    Raises:
        ImportError: If googleapiclient.discovery is not available
    
    Example:
        >>> build = import_build()
        >>> service = build('drive', 'v3', credentials=credentials)
    """
    if not _has_module("googleapiclient.discovery"):
        raise ImportError(_GOOGLE_API_ERROR_MSG)
    
    try:
        from googleapiclient.discovery import build  # type: ignore
        return build  # type: ignore
    except ImportError as e:
        logger.error("Failed to import googleapiclient.discovery: %s", e)
        raise ImportError(_GOOGLE_API_ERROR_MSG) from e


def import_http() -> Tuple[Any, Any]:
    """
    Lazy import and return Google Drive HTTP utilities.
    
    Returns both MediaFileUpload (for file uploads) and MediaIoBaseDownload
    (for file downloads) in a tuple.
    
    Returns:
        Tuple of (MediaFileUpload, MediaIoBaseDownload) classes
    
    Raises:
        ImportError: If googleapiclient.http is not available
    
    Example:
        >>> MediaFileUpload, MediaIoBaseDownload = import_http()
        >>> media = MediaFileUpload(file_path, mimetype='audio/wav', resumable=True)
    """
    try:
        from googleapiclient.http import (  # type: ignore
            MediaFileUpload,
            MediaIoBaseDownload,
        )
        return MediaFileUpload, MediaIoBaseDownload  # type: ignore
    except ImportError as e:
        logger.error("Failed to import googleapiclient.http: %s", e)
        raise ImportError(_GOOGLE_API_ERROR_MSG) from e


def import_errors() -> Any:
    """
    Lazy import and return Google API error classes.
    
    Used for catching and handling Google Drive API errors (e.g., HttpError,
    ResumableUploadError).
    
    Returns:
        The googleapiclient.errors module
    
    Raises:
        ImportError: If googleapiclient.errors is not available
    
    Example:
        >>> errors = import_errors()
        >>> try:
        ...     response = service.files().get(...).execute()
        ... except errors.HttpError as e:
        ...     print(f"API error: {e}")
    """
    try:
        from googleapiclient import errors  # type: ignore
        return errors  # type: ignore
    except ImportError as e:
        logger.error("Failed to import googleapiclient.errors: %s", e)
        raise ImportError(_GOOGLE_API_ERROR_MSG) from e
