"""
Folder Management for Google Drive

Handles folder operations including creation, listing, and hierarchy management.
Extracted from GoogleDriveManager to enable component-based testing and reuse.

This module provides the FolderManager protocol and GoogleFolderManager implementation
for managing folders in Google Drive with proper error handling and pagination support.
"""

import logging
from typing import Any, Dict, List, Optional, Protocol

from ._query_builder import QueryBuilder
from .storage_ops import create_folder_metadata, paginate_results

logger = logging.getLogger(__name__)


class FolderManager(Protocol):
    """
    Abstract protocol for folder management operations.
    
    Defines the interface that any folder manager (Google Drive, OneDrive, etc.)
    must implement to be usable by other cloud storage components.
    """

    def list_folders(
        self, parent_id: Optional[str] = None, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List folders under the given parent.
        
        Args:
            parent_id: Parent folder ID (None = root)
            page_size: Results per page (1-1000, default 100)
        
        Returns:
            List of dicts with 'id' and 'name' keys
        
        Example:
            >>> folders = manager.list_folders()
            >>> for folder in folders:
            ...     print(f"{folder['name']} ({folder['id']})")
        """
        ...

    def create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a new folder.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID (None = root)
            description: Optional folder description
        
        Returns:
            Created folder ID, or None on failure
        
        Example:
            >>> folder_id = manager.create_folder("My Recordings")
            >>> print(f"Created folder {folder_id}")
        """
        ...

    def ensure_recordings_folder(self) -> str:
        """
        Ensure the recordings folder exists, creating if necessary.
        
        Returns:
            Recordings folder ID
        
        Raises:
            Exception: If folder cannot be created or retrieved
        
        Example:
            >>> folder_id = manager.ensure_recordings_folder()
            >>> print(f"Using folder {folder_id}")
        """
        ...

    def set_recordings_folder(self, folder_id: str) -> None:
        """
        Override the recordings folder ID.
        
        Args:
            folder_id: Folder ID to use for recordings
        
        Example:
            >>> manager.set_recordings_folder("abc123")
        """
        ...


class GoogleFolderManager:
    """
    Google Drive implementation of folder management.
    
    Manages folder operations in Google Drive including creation, listing,
    and ensuring the recordings folder exists with proper metadata.
    
    Attributes:
        RECORDINGS_FOLDER: Default name for recordings folder
        auth_manager: Authentication manager for Drive access
        service: Google Drive API service (lazy-loaded)
        recordings_folder_id: Cached recordings folder ID
    """

    RECORDINGS_FOLDER = "Voice Recorder Pro"

    def __init__(self, auth_manager: Any, service_provider: Any = None):
        """
        Initialize folder manager.
        
        Args:
            auth_manager: Google authentication manager
            service_provider: Optional Drive service provider (for testing)
        
        Example:
            >>> from cloud.auth_manager import GoogleAuthManager
            >>> auth = GoogleAuthManager()
            >>> folders = GoogleFolderManager(auth)
        """
        self.auth_manager = auth_manager
        self.service_provider = service_provider
        self.service: Optional[Any] = None
        self.recordings_folder_id: Optional[str] = None

    def _get_service(self) -> Any:
        """
        Get or create Google Drive service.
        
        Returns:
            Google Drive API service
        
        Raises:
            NotAuthenticatedError: If not authenticated
            APILibrariesMissingError: If Google libraries unavailable
        """
        if self.service_provider:
            return self.service_provider

        if not self.auth_manager.is_authenticated():
            from .exceptions import NotAuthenticatedError

            raise NotAuthenticatedError("Not authenticated. Please sign in first.")

        from ._lazy import has_google_apis_available
        from .exceptions import APILibrariesMissingError

        if not has_google_apis_available():
            raise APILibrariesMissingError("Google API libraries not available.")

        if not self.service:
            from ._lazy import _import_build

            credentials = self.auth_manager.get_credentials()
            build = _import_build()
            try:
                self.service = build(
                    "drive", "v3", credentials=credentials, cache_discovery=False
                )
            except TypeError:
                # Older googleapiclient versions don't accept cache_discovery
                self.service = build("drive", "v3", credentials=credentials)

        return self.service

    def list_folders(
        self, parent_id: Optional[str] = None, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List folders under the given parent.
        
        Args:
            parent_id: Parent folder ID (None = root)
            page_size: Results per page (1-1000, default 100)
        
        Returns:
            List of dicts with 'id' and 'name' keys
        
        Example:
            >>> folders = manager.list_folders()
            >>> root_folders = manager.list_folders()
            >>> subfolder = manager.list_folders("abc123")
        """
        try:
            service = self._get_service()

            # Build query using QueryBuilder
            query_builder = QueryBuilder().is_folder().not_trashed()
            if parent_id:
                query_builder.in_folder(parent_id)
            else:
                query_builder.at_root()

            query = query_builder.build()
            
            results = paginate_results(
                service,
                query,
                fields="files(id, name)",
                page_size=page_size,
            )

            return results

        except Exception as e:
            logger.error("Error listing folders: %s", e)
            return []

    def create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a new folder.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID (None = root)
            description: Optional folder description
        
        Returns:
            Created folder ID, or None on failure
        
        Example:
            >>> folder_id = manager.create_folder("New Folder")
            >>> sub_id = manager.create_folder("Subfolder", parent_id=folder_id)
        """
        try:
            service = self._get_service()
            metadata = create_folder_metadata(name, parent_id, description)

            folder = service.files().create(body=metadata, fields="id").execute()
            folder_id = folder.get("id")

            logger.info("Created folder '%s' with ID %s", name, folder_id)
            return folder_id

        except Exception as e:
            logger.error("Failed to create folder '%s': %s", name, e)
            return None

    def ensure_recordings_folder(self) -> str:
        """
        Ensure the recordings folder exists, creating if necessary.
        
        Returns:
            Recordings folder ID
        
        Raises:
            Exception: If folder cannot be created or retrieved
        
        Example:
            >>> folder_id = manager.ensure_recordings_folder()
            >>> print(f"Using folder {folder_id}")
        """
        if self.recordings_folder_id:
            return str(self.recordings_folder_id)

        try:
            service = self._get_service()

            # Search for existing recordings folder
            query = (
                QueryBuilder()
                .name_equals(self.RECORDINGS_FOLDER)
                .is_folder()
                .not_trashed()
                .build()
            )

            results = service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get("files", [])

            if folders:
                # Folder exists
                self.recordings_folder_id = folders[0]["id"]
                logger.info(
                    "Found existing recordings folder: %s", self.RECORDINGS_FOLDER
                )
            else:
                # Create new folder
                folder_id = self.create_folder(
                    self.RECORDINGS_FOLDER,
                    description="Audio recordings from Voice Recorder Pro",
                )
                if folder_id:
                    self.recordings_folder_id = folder_id
                    logger.info(
                        "Created new recordings folder: %s", self.RECORDINGS_FOLDER
                    )
                else:
                    raise Exception("Failed to create recordings folder")

            return str(self.recordings_folder_id)

        except Exception as e:
            logger.error("Error managing recordings folder: %s", e)
            raise

    def set_recordings_folder(self, folder_id: str) -> None:
        """
        Override the recordings folder ID.
        
        Args:
            folder_id: Folder ID to use for recordings
        
        Example:
            >>> manager.set_recordings_folder("abc123")
        """
        self.recordings_folder_id = str(folder_id)
        logger.info("Set recordings folder to %s", folder_id)
