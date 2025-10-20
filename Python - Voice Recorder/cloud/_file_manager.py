"""
File Management for Google Drive

Handles file operations including uploads, downloads, and searching.
Extracted from GoogleDriveManager to enable component-based testing and reuse.
"""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from ._query_builder import QueryBuilder
from .exceptions import DuplicateFoundError, NotAuthenticatedError, APILibrariesMissingError
from .metadata_schema import build_upload_metadata
from .storage_ops import paginate_results, discover_total_bytes

logger = logging.getLogger(__name__)


class FileManager(Protocol):
    """Abstract protocol for file management operations."""

    def upload_file(
        self,
        file_path: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        force: bool = False,
    ) -> Optional[str]:
        """Upload file to Drive. Returns file ID or None on failure."""
        ...

    def download_file(self, file_id: str, download_path: str) -> bool:
        """Download file from Drive. Returns True if successful."""
        ...

    def list_files(
        self, folder_id: str, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """List files in folder."""
        ...

    def find_duplicate_by_hash(
        self, content_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Find file by content hash."""
        ...

    def delete_file(self, file_id: str) -> bool:
        """Delete file from Drive."""
        ...


class GoogleFileManager:
    """Google Drive implementation of file management."""

    def __init__(self, auth_manager: Any, folder_manager: Any, service_provider: Any = None):
        """
        Initialize file manager.
        
        Args:
            auth_manager: Google authentication manager
            folder_manager: FolderManager instance for folder operations
            service_provider: Optional Drive service provider (for testing)
        """
        self.auth_manager = auth_manager
        self.folder_manager = folder_manager
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
            from ._lazy import _import_build

            credentials = self.auth_manager.get_credentials()
            build = _import_build()
            try:
                self.service = build(
                    "drive", "v3", credentials=credentials, cache_discovery=False
                )
            except TypeError:
                self.service = build("drive", "v3", credentials=credentials)

        return self.service

    def upload_file(
        self,
        file_path: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        force: bool = False,
    ) -> Optional[str]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Path to file
            title: Custom title
            description: File description
            tags: Tags for categorization
            force: Skip duplicate check
        
        Returns:
            File ID if successful, None if failed
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Check for duplicates
            content_hash = None
            try:
                from .dedupe import compute_content_sha256
                content_hash = compute_content_sha256(file_path)
            except Exception:
                pass

            if content_hash and not force:
                existing = self.find_duplicate_by_hash(content_hash)
                if existing:
                    logger.info("Duplicate found, returning existing file ID")
                    return existing.get("id")

            service = self._get_service()
            folder_id = self.folder_manager.ensure_recordings_folder()

            # Prepare metadata
            file_name = Path(file_path).name
            file_title = title or file_name
            file_size = os.path.getsize(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "audio/wav"

            metadata = build_upload_metadata(
                file_path,
                title=file_title,
                description=description,
                tags=tags,
                content_sha256=content_hash,
                folder_id=folder_id,
            )

            # Upload
            from ._lazy import _import_http
            media_file_upload, _ = _import_http()
            media = media_file_upload(file_path, mimetype=mime_type, resumable=True)

            logger.info("Uploading: %s (%.1f MB)", file_title, file_size / 1024 / 1024)

            request = service.files().create(
                body=metadata, media_body=media, fields="id, name, size, createdTime"
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info("Upload progress: %d%%", progress)

            file_id = response.get("id")
            logger.info("Upload successful. File ID: %s", file_id)
            return file_id

        except (NotAuthenticatedError, APILibrariesMissingError) as e:
            logger.error("Upload failed: %s", e)
            return None
        except Exception as e:
            logger.error("Upload error: %s", e)
            return None

    def download_file(self, file_id: str, download_path: str) -> bool:
        """
        Download file from Google Drive.
        
        Args:
            file_id: Drive file ID
            download_path: Local path to save
        
        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_service()
            from ._lazy import _import_http
            _, media_io_download = _import_http()

            request = service.files().get_media(fileId=file_id)
            media_download = media_io_download(request, chunksize=1024 * 256, resumable=True)

            with open(download_path, "wb") as f:
                while not media_download.complete():
                    status, chunk = media_download.next_chunk()
                    if chunk:
                        f.write(chunk)
                    if status:
                        logger.info("Download progress: %.1f%%", status.progress() * 100)

            logger.info("Download successful: %s", download_path)
            return True

        except Exception as e:
            logger.error("Download error: %s", e)
            return False

    def list_files(
        self, folder_id: str, page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List files in a folder.
        
        Args:
            folder_id: Folder ID
            page_size: Results per page
        
        Returns:
            List of file dicts
        """
        try:
            service = self._get_service()

            query = QueryBuilder().in_folder(folder_id).not_trashed().build()

            results = paginate_results(
                service,
                query,
                fields="files(id, name, size, createdTime, modifiedTime, description, appProperties)",
                page_size=page_size,
            )

            files: List[Dict[str, Any]] = []
            for file in results:
                files.append({
                    "id": file.get("id"),
                    "name": file.get("name"),
                    "size": int(file.get("size", 0)),
                    "created": file.get("createdTime"),
                    "modified": file.get("modifiedTime"),
                    "description": file.get("description", ""),
                    "properties": file.get("appProperties", {}),
                })

            logger.info("Found %d files in folder", len(files))
            return files

        except Exception as e:
            logger.error("Error listing files: %s", e)
            return []

    def find_duplicate_by_hash(
        self, content_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find file by content hash.
        
        Args:
            content_hash: SHA-256 content hash
        
        Returns:
            File dict with 'id' and 'name', or None
        """
        try:
            service = self._get_service()
            folder_id = self.folder_manager.ensure_recordings_folder()

            page_token = None
            while True:
                resp = (
                    service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed=false",
                        fields="nextPageToken, files(id, name, appProperties)",
                        pageToken=page_token,
                        pageSize=100,
                    )
                    .execute()
                )
                files = resp.get("files", [])
                for f in files:
                    props = f.get("appProperties") or {}
                    if props.get("content_sha256") == content_hash:
                        return {"id": f.get("id"), "name": f.get("name")}
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
        except Exception:
            logger.debug("Error during duplicate lookup", exc_info=True)
        return None

    def delete_file(self, file_id: str) -> bool:
        """
        Delete file from Google Drive.
        
        Args:
            file_id: Drive file ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_service()
            service.files().delete(fileId=file_id).execute()
            logger.info("Deleted file: %s", file_id)
            return True
        except Exception as e:
            logger.error("Error deleting file: %s", e)
            return False
