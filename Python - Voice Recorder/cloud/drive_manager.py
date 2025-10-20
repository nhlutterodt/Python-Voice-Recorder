"""
Google Drive Manager for Voice Recorder Pro

Handles file uploads, downloads, and management of audio recordings
in the user's Google Drive with proper metadata and organization.
"""

import logging
from typing import Any, Dict, List, Optional

from .exceptions import DuplicateFoundError
from ._folder_manager import GoogleFolderManager
from ._file_manager import GoogleFileManager
from ._storage_info import GoogleStorageInfo

# Type checking imports removed - using lazy imports with helper functions instead


# Lazy-import helpers so importing this module doesn't fail when Google libs are missing
# Type checking imports removed - using component-based architecture instead


class GoogleDriveManager:
    """Manages Google Drive operations for audio recordings"""

    # Folder name in Google Drive for recordings
    RECORDINGS_FOLDER = "Voice Recorder Pro"

    def __init__(self, auth_manager: Any):
        """
        Initialize Google Drive manager

        Args:
            auth_manager: GoogleAuthManager instance
        """
        self.auth_manager = auth_manager
        self.recordings_folder_id: Optional[str] = None
        
        # Phase 3 components (lazily initialized)
        self._folder_manager: Optional[GoogleFolderManager] = None
        self._file_manager: Optional[GoogleFileManager] = None
        self._storage_info: Optional[GoogleStorageInfo] = None

    @property
    def folder_manager(self) -> GoogleFolderManager:
        """Get or create the FolderManager component."""
        if self._folder_manager is None:
            self._folder_manager = GoogleFolderManager(self.auth_manager)
        return self._folder_manager

    @property
    def file_manager(self) -> GoogleFileManager:
        """Get or create the FileManager component."""
        if self._file_manager is None:
            self._file_manager = GoogleFileManager(
                self.auth_manager, self.folder_manager
            )
        return self._file_manager

    @property
    def storage_info(self) -> GoogleStorageInfo:
        """Get or create the StorageInfo component."""
        if self._storage_info is None:
            self._storage_info = GoogleStorageInfo(self.auth_manager)
        return self._storage_info

    def _ensure_recordings_folder(self) -> str:
        """Ensure the recordings folder exists in Google Drive"""
        if self.recordings_folder_id:
            return str(self.recordings_folder_id)

        # Delegate to FolderManager
        self.recordings_folder_id = self.folder_manager.ensure_recordings_folder()
        return str(self.recordings_folder_id)

    def list_folders(
        self, parent_id: Optional[str] = None, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """List folders under the given parent (or top-level if None).

        Returns a list of dicts with keys 'id' and 'name'.
        """
        # Delegate to FolderManager
        return self.folder_manager.list_folders(parent_id, page_size)

    def create_folder(
        self, name: str, parent_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a folder with the given name under parent_id (or root) and return its id."""
        # Delegate to FolderManager
        return self.folder_manager.create_folder(name, parent_id)

    def set_recordings_folder(self, folder_id: str) -> None:
        """Set the manager's target recordings folder id."""
        self.recordings_folder_id = str(folder_id)
        # Sync with FolderManager
        self.folder_manager.set_recordings_folder(folder_id)

    def upload_recording(
        self,
        file_path: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        force: bool = False,
    ) -> Optional[str]:
        """
        Upload an audio recording to Google Drive

        Args:
            file_path (str): Path to the audio file
            title (str): Custom title for the recording
            description (str): Description of the recording
            tags (List[str]): Tags for categorization

        Returns:
            str: File ID if successful, None if failed
        """
        # Delegate to FileManager
        return self.file_manager.upload_file(
            file_path, title=title, description=description, tags=tags, force=force
        )

    # Compatibility helper: return Optional[str] like the original API while
    # delegating to the new adapter-based implementation. This keeps older
    # callers working while new code should use `get_uploader()` and the
    # typed `Uploader` contract.
    def upload_recording_legacy(
        self,
        file_path: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        force: bool = False,
    ) -> Optional[str]:
        try:
            # Lazy-import the adapter to avoid import-time cycles and keep
            # runtime behavior identical when cloud libs are missing.
            from .google_uploader import GoogleDriveUploader

            uploader = GoogleDriveUploader(self)
            # upload() returns a typed UploadResult or raises on error.
            try:
                result = uploader.upload(
                    file_path,
                    title=title,
                    description=description,
                    tags=tags,
                    force=force,
                )
                return result.get("file_id")
            except DuplicateFoundError as e:
                # Legacy behavior: log and return existing file id to keep callers
                logging.info(
                    "Duplicate found during legacy upload: %s",
                    getattr(e, "file_id", None),
                )
                return getattr(e, "file_id", None)
        except Exception as e:
            logging.error("Legacy upload failed: %s", e)
            return None

    def get_uploader(self):
        """Return a preconfigured GoogleDriveUploader for this manager.

        Use this in new code to access the typed uploader interface and
        improved error semantics. This is a convenience method and does
        a lazy import of the adapter.
        """
        from .google_uploader import GoogleDriveUploader

        return GoogleDriveUploader(self)

    def list_recordings(self) -> List[Dict[str, Any]]:
        """
        List all recordings in Google Drive

        Returns:
            List[Dict]: List of recording metadata
        """
        # Delegate to FileManager
        folder_id = self._ensure_recordings_folder()
        return self.file_manager.list_files(folder_id)

    def find_duplicate_by_content_sha256(
        self, content_sha256: str
    ) -> Optional[Dict[str, Any]]:
        """Find a file in the recordings folder with a matching appProperties.content_sha256.

        Returns a dict with keys 'id' and 'name' or None if not found.
        """
        # Delegate to FileManager
        return self.file_manager.find_duplicate_by_hash(content_sha256)

    def download_recording(self, file_id: str, download_path: str) -> bool:
        """
        Download a recording from Google Drive

        Args:
            file_id (str): Google Drive file ID
            download_path (str): Local path to save the file

        Returns:
            bool: True if successful, False otherwise
        """
        # Delegate to FileManager
        return self.file_manager.download_file(file_id, download_path)

    def delete_recording(self, file_id: str) -> bool:
        """
        Delete a recording from Google Drive

        Args:
            file_id (str): Google Drive file ID

        Returns:
            bool: True if successful, False otherwise
        """
        # Delegate to FileManager
        return self.file_manager.delete_file(file_id)

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get Google Drive storage information

        Returns:
            Dict: Storage usage information
        """
        # Delegate to StorageInfo component
        quota = self.storage_info.get_storage_quota()
        if not quota:
            return {}

        total = quota.get("limit", 0)
        used = quota.get("usedBytes", 0)

        storage_info: Dict[str, Any] = {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": total - used if total > 0 else 0,
            "total_gb": round(total / (1024**3), 2) if total > 0 else "Unlimited",
            "used_gb": round(used / (1024**3), 2),
            "free_gb": (
                round((total - used) / (1024**3), 2) if total > 0 else "Unlimited"
            ),
        }

        return storage_info

    def get_storage_quota(self) -> Optional[Dict[str, Any]]:
        """
        Get storage quota information.

        Returns:
            Dict: Quota with usedBytes, limit, usedPercent, or None on error
        """
        # Delegate to StorageInfo component
        return self.storage_info.get_storage_quota()

    def get_storage_summary(self) -> Optional[Dict[str, str]]:
        """
        Get formatted storage summary for display.

        Returns:
            Dict: Formatted strings ('used', 'limit', 'percent', 'available'), or None on error
        """
        # Delegate to StorageInfo component
        return self.storage_info.get_storage_summary()


# Example usage
if __name__ == "__main__":
    from voice_recorder.cloud.auth_manager import GoogleAuthManager
    from voice_recorder.config_manager import config_manager

    # Initialize managers
    auth_manager = GoogleAuthManager(use_keyring=config_manager.prefers_keyring())
    drive_manager = GoogleDriveManager(auth_manager)

    # Check authentication
    if not auth_manager.is_authenticated():
        print("🔐 Please authenticate first")
        if auth_manager.authenticate():
            print("✅ Authentication successful")
        else:
            print("❌ Authentication failed")
            exit(1)

    # List recordings
    recordings = drive_manager.list_recordings()
    if recordings:
        print("\n📁 Recordings in Google Drive:")
        for recording in recordings[:5]:  # Show first 5
            size_mb = recording["size"] / (1024 * 1024)
            print(f"  📄 {recording['name']} ({size_mb:.1f} MB)")

    # Get storage info
    storage = drive_manager.get_storage_info()
    if storage:
        print(f"\n💾 Storage: {storage['used_gb']} GB / {storage['total_gb']} GB used")
