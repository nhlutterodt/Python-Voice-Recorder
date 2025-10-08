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


class DuplicateFoundError(CloudError):
    """Raised when a pre-upload dedupe check finds an existing file with the same content.

    Attributes:
        file_id: the Drive file id that was found
        name: the file name on Drive (if available)
    """
    def __init__(self, file_id: str | None = None, name: str | None = None, *args: object) -> None:
        super().__init__(*args)
        self.file_id = file_id
        self.name = name
