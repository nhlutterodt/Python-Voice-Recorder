"""
Typed exceptions for cloud integration

This module defines a small hierarchy of exceptions used by the
cloud package so callers (especially UI code) can react to
specific error conditions instead of catching generic RuntimeError.
"""

from __future__ import annotations

class CloudError(Exception):
    """Base class for cloud-related exceptions"""
    pass


class NotAuthenticatedError(CloudError):
    """Raised when an operation requires authentication but no valid credentials are present."""
    pass


class APILibrariesMissingError(CloudError):
    """Raised when required third-party Google API libraries are not available."""
    pass


class FeatureNotAllowedError(CloudError):
    """Raised when a user attempts to use a feature their tier doesn't allow."""
    pass


class UploadError(CloudError):
    """Generic upload error; used when an upload fails for reasons other than auth or missing libs."""
    pass
