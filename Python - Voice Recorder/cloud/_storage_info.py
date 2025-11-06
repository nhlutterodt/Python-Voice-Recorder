"""
Storage Information Management for Google Drive

Handles storage quota and statistics retrieval.
Extracted from GoogleDriveManager to enable component-based testing and reuse.
"""

import logging
from typing import Any, Callable, Dict, Optional, Protocol

from .exceptions import NotAuthenticatedError, APILibrariesMissingError
from .storage_ops import format_file_size

logger = logging.getLogger(__name__)


class StorageInfo(Protocol):
    """Abstract protocol for storage information operations."""

    def get_storage_quota(self) -> Optional[Dict[str, Any]]:
        """Get storage quota information."""
        ...

    def get_storage_summary(self) -> Optional[Dict[str, str]]:
        """Get formatted storage summary."""
        ...


class GoogleStorageInfo:
    """Google Drive implementation of storage information management."""

    def __init__(self, auth_manager: Any, service_provider: Any = None):
        """
        Initialize storage info manager.

        Args:
            auth_manager: Google authentication manager
            service_provider: Optional Drive service provider (for testing)
        """
        self.auth_manager = auth_manager
        self.service_provider = service_provider
        self.service: Optional[Any] = None

    def _get_service(self) -> Any:
        """Get or create Google Drive service."""
        if self.service_provider:
            return self.service_provider

        if not self.auth_manager.is_authenticated():
            raise NotAuthenticatedError("Not authenticated. Please sign in first.")

        from ._lazy import has_google_apis_available

        if not has_google_apis_available():
            raise APILibrariesMissingError("Google API libraries not available.")

        if not self.service:
            try:
                # Import the build function (may raise ImportError if Google APIs missing)
                from ._lazy import import_build

                credentials = self.auth_manager.get_credentials()
                build: Callable[..., Any] = import_build()
                
                # Try with cache_discovery parameter (newer API versions)
                try:
                    self.service = build(
                        "drive", "v3", credentials=credentials, cache_discovery=False
                    )
                except TypeError:
                    # Fallback for older API versions that don't support cache_discovery
                    self.service = build("drive", "v3", credentials=credentials)
                    
            except (ImportError, APILibrariesMissingError) as e:
                logger.error("Failed to initialize Drive service - missing libraries: %s", e)
                raise
            except NotAuthenticatedError as e:
                logger.error("Failed to initialize Drive service - not authenticated: %s", e)
                raise
            except Exception as e:
                logger.error("Unexpected error initializing Drive service: %s", e)
                raise

        return self.service

    def get_storage_quota(self) -> Optional[Dict[str, Any]]:
        """
        Get storage quota information from Google Drive.

        Returns:
            Dict with 'usedBytes' and 'storageQuota' (limit in bytes), or None on error
        """
        try:
            service = self._get_service()

            about = service.about().get(fields="storageQuota").execute()
            storage_quota: Dict[str, Any] = about.get("storageQuota", {})

            used_bytes = int(storage_quota.get("usedBytes", 0))
            limit_bytes = int(storage_quota.get("limit", 0))

            return {
                "usedBytes": used_bytes,
                "limit": limit_bytes,
                "usedPercent": (used_bytes / limit_bytes * 100) if limit_bytes > 0 else 0,
            }

        except (NotAuthenticatedError, APILibrariesMissingError) as e:
            logger.error("Storage quota error: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to get storage quota: %s", e)
            return None

    def get_storage_summary(self) -> Optional[Dict[str, str]]:
        """
        Get formatted storage summary for display.

        Returns:
            Dict with formatted strings ('used', 'limit', 'percent'), or None on error
        """
        try:
            quota = self.get_storage_quota()
            if not quota:
                return None

            used_bytes = quota["usedBytes"]
            limit_bytes = quota["limit"]
            used_percent = quota["usedPercent"]

            return {
                "used": format_file_size(used_bytes),
                "limit": format_file_size(limit_bytes),
                "percent": f"{used_percent:.1f}%",
                "available": format_file_size(limit_bytes - used_bytes),
            }

        except Exception as e:
            logger.error("Failed to get storage summary: %s", e)
            return None
