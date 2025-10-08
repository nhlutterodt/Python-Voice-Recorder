"""
Google Drive Manager for Voice Recorder Pro

Handles file uploads, downloads, and management of audio recordings
in the user's Google Drive with proper metadata and organization.
"""

import os
import mimetypes
import logging
import importlib.util
from pathlib import Path
from typing import Optional, List, Dict, Any, TypedDict
from datetime import datetime

from .exceptions import NotAuthenticatedError, APILibrariesMissingError, DuplicateFoundError

# Type checking imports removed - using lazy imports with helper functions instead

# Lazy-import helpers so importing this module doesn't fail when Google libs are missing
def _has_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


GOOGLE_APIS_AVAILABLE: bool = all(
    [
        _has_module("googleapiclient.discovery"),
        _has_module("googleapiclient.http"),
        _has_module("googleapiclient.errors"),
    ]
)

def _import_build() -> Any:
    from googleapiclient.discovery import build  # type: ignore

    return build  # type: ignore


def _import_http() -> tuple[Any, Any]:
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload  # type: ignore

    return MediaFileUpload, MediaIoBaseDownload



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
        self.service: Optional[Any] = None
        self.recordings_folder_id: Optional[str] = None
        
    def _get_service(self) -> Any:
        """Get or create Google Drive service"""
        if not self.auth_manager.is_authenticated():
            raise NotAuthenticatedError("Not authenticated. Please sign in first.")

        if not GOOGLE_APIS_AVAILABLE:
            raise APILibrariesMissingError("Google API libraries not available.")

        if not self.service:
            credentials = self.auth_manager.get_credentials()
            build = _import_build()
            self.service = build("drive", "v3", credentials=credentials)

        return self.service  # type: ignore[return-value]
    
    def _ensure_recordings_folder(self) -> str:
        """Ensure the recordings folder exists in Google Drive"""
        if self.recordings_folder_id:
            return str(self.recordings_folder_id)
            
        try:
            service = self._get_service()
            
            # Search for existing folder
            query = f"name='{self.RECORDINGS_FOLDER}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                # Folder exists
                self.recordings_folder_id = folders[0]['id']
                logging.info("Found existing folder: %s", self.RECORDINGS_FOLDER)
            else:
                # Create new folder
                folder_metadata = {
                    'name': self.RECORDINGS_FOLDER,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'description': 'Audio recordings from Voice Recorder Pro'
                }
                
                folder = service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                self.recordings_folder_id = folder.get('id')
                logging.info("Created new folder: %s", self.RECORDINGS_FOLDER)
            
            return str(self.recordings_folder_id)
            
        except Exception as e:
            logging.error("Error managing recordings folder: %s", e)
            raise
    
    def upload_recording(self, file_path: str, title: Optional[str] = None,
                         description: Optional[str] = None, tags: Optional[List[str]] = None,
                         force: bool = False) -> Optional[str]:
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
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            # Compute SHA-256 content hash early (content_sha256) and attempt a server-side lookup
            # before creating Drive service objects. If a duplicate is found
            # return the existing file id immediately so callers (including
            # legacy code) receive the id instead of creating a duplicate.
            ch = None
            try:
                from .dedupe import compute_content_sha256
                ch = compute_content_sha256(file_path)
            except Exception:
                ch = None

            if ch:
                try:
                    finder = getattr(self, 'find_duplicate_by_content_sha256', None)
                    if callable(finder):
                        existing = finder(ch)
                        if existing:
                            # If caller explicitly requested a forced upload, bypass dedupe
                            if force:
                                logging.info('Force upload requested; bypassing duplicate check for file %s', file_path)
                            else:
                                # Return the existing file id to avoid duplicating uploads
                                return existing.get('id')
                except Exception:
                    # If lookup fails, continue with the upload path below
                    logging.debug('Duplicate lookup failed; continuing with upload')

            service = self._get_service()
            folder_id = self._ensure_recordings_folder()
            
            # Prepare file metadata
            file_name = Path(file_path).name
            file_title = title or file_name
            
            # Get file size and MIME type
            file_size = os.path.getsize(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'audio/wav'  # Default for audio files
            
            # Build canonical metadata including appProperties using a shared helper
            from .metadata_schema import build_upload_metadata

            metadata = build_upload_metadata(
                file_path,
                title=file_title,
                description=description,
                tags=tags,
                content_sha256=ch,
                folder_id=folder_id,
            )
            
            # Prepare media upload
            media_file_upload, _ = _import_http()
            media = media_file_upload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )
            
            logging.info("Uploading: %s (%.1f MB)", file_title, file_size / 1024 / 1024)
            
            # Upload file
            request = service.files().create(
                body=metadata,
                media_body=media,
                fields='id, name, size, createdTime'
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logging.info("Upload progress: %d%%", progress)

            file_id = response.get('id')
            logging.info("Upload successful. File ID: %s", file_id)

            return file_id

        except (NotAuthenticatedError, APILibrariesMissingError) as e:
            # Preserve backward-compatible behaviour: higher-level callers
            # in the application expect upload_recording to return None on
            # failure rather than raise. Log the condition and return None.
            logging.error("Upload failed due to auth/library issue: %s", e)
            return None

    # Compatibility helper: return Optional[str] like the original API while
    # delegating to the new adapter-based implementation. This keeps older
    # callers working while new code should use `get_uploader()` and the
    # typed `Uploader` contract.
    def upload_recording_legacy(self, file_path: str, title: Optional[str] = None,
                                description: Optional[str] = None, tags: Optional[List[str]] = None,
                                force: bool = False) -> Optional[str]:
        try:
            # Lazy-import the adapter to avoid import-time cycles and keep
            # runtime behavior identical when cloud libs are missing.
            from .google_uploader import GoogleDriveUploader

            uploader = GoogleDriveUploader(self)
            # upload() returns a typed UploadResult or raises on error.
            try:
                result = uploader.upload(file_path, title=title, description=description, tags=tags, force=force)
                return result.get('file_id')
            except DuplicateFoundError as e:
                # Legacy behavior: log and return existing file id to keep callers
                logging.info('Duplicate found during legacy upload: %s', getattr(e, 'file_id', None))
                return getattr(e, 'file_id', None)
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
        try:
            service = self._get_service()
            folder_id = self._ensure_recordings_folder()
            
            # Query for audio files in recordings folder
            query = f"'{folder_id}' in parents and trashed=false"
            
            results = service.files().list(
                q=query,
                fields="files(id, name, size, createdTime, modifiedTime, description, properties)",
                orderBy="createdTime desc"
            ).execute()
            
            files = results.get('files', [])

            recordings: List[Dict[str, Any]] = []
            for file in files:
                recording: Dict[str, Any] = {
                    'id': file['id'],
                    'name': file['name'],
                    'size': int(file.get('size', 0)),
                    'created': file.get('createdTime'),
                    'modified': file.get('modifiedTime'),
                    'description': file.get('description', ''),
                    'properties': file.get('properties', {})
                }
                recordings.append(recording)
            
            logging.info("Found %d recordings in Google Drive", len(recordings))
            return recordings
            
        except Exception as e:
            logging.error("Error listing recordings: %s", e)
            return []

    def find_duplicate_by_content_sha256(self, content_sha256: str) -> Optional[Dict[str, Any]]:
        """Find a file in the recordings folder with a matching appProperties.content_sha256.

        Returns a dict with keys 'id' and 'name' or None if not found.
        This implementation lists files in the recordings folder and checks
        their `appProperties` client-side to avoid complex Drive query syntax.
        """
        try:
            service = self._get_service()
            folder_id = self._ensure_recordings_folder()

            # List files in folder (page through if necessary) and match by appProperties
            page_token = None
            while True:
                resp = service.files().list(q=f"'{folder_id}' in parents and trashed=false", fields='nextPageToken, files(id, name, appProperties)', pageToken=page_token, pageSize=100).execute()
                files = resp.get('files', [])
                for f in files:
                    props = f.get('appProperties') or {}
                    if props.get('content_sha256') == content_sha256:
                        return {'id': f.get('id'), 'name': f.get('name')}
                page_token = resp.get('nextPageToken')
                if not page_token:
                    break
        except Exception:
            logging.debug('Error during duplicate lookup', exc_info=True)
        return None
    
    def download_recording(self, file_id: str, download_path: str) -> bool:
        """
        Download a recording from Google Drive
        
        Args:
            file_id (str): Google Drive file ID
            download_path (str): Local path to save the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            service = self._get_service()
            
            # Get file metadata
            file_metadata = service.files().get(fileId=file_id).execute()
            file_name = file_metadata['name']
            
            logging.info("Downloading: %s", file_name)
            
            # Download file content
            request = service.files().get_media(fileId=file_id)
            
            # Ensure download directory exists
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            
            # Save file
            _, media_io_base_download = _import_http()
            with open(download_path, 'wb') as fh:
                downloader = media_io_base_download(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        logging.info("Download progress: %d%%", progress)
            
            logging.info("Download complete: %s", download_path)
            return True
            
        except Exception as e:
            logging.error("Download failed: %s", e)
            return False
    
    def delete_recording(self, file_id: str) -> bool:
        """
        Delete a recording from Google Drive
        
        Args:
            file_id (str): Google Drive file ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            service = self._get_service()
            
            # Get file name for confirmation
            file_metadata = service.files().get(fileId=file_id, fields='name').execute()
            file_name = file_metadata['name']
            
            # Delete file
            service.files().delete(fileId=file_id).execute()
            
            logging.info("Deleted recording: %s", file_name)
            return True
            
        except Exception as e:
            logging.error("Delete failed: %s", e)
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get Google Drive storage information
        
        Returns:
            Dict: Storage usage information
        """
        try:
            service = self._get_service()
            
            about = service.about().get(fields='storageQuota, user').execute()
            quota = about.get('storageQuota', {})
            user = about.get('user', {})
            
            total = int(quota.get('limit', 0))
            used = int(quota.get('usage', 0))

            storage_info: Dict[str, Any] = {
                'total_bytes': total,
                'used_bytes': used,
                'free_bytes': total - used if total > 0 else 0,
                'total_gb': round(total / (1024**3), 2) if total > 0 else 'Unlimited',
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round((total - used) / (1024**3), 2) if total > 0 else 'Unlimited',
                'user_email': user.get('emailAddress', 'Unknown')
            }
            
            return storage_info
            
        except Exception as e:
            logging.error("Error getting storage info: %s", e)
            return {}

# Example usage
if __name__ == "__main__":
    from cloud.auth_manager import GoogleAuthManager
    from config_manager import config_manager
    
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
            size_mb = recording['size'] / (1024 * 1024)
            print(f"  📄 {recording['name']} ({size_mb:.1f} MB)")
    
    # Get storage info
    storage = drive_manager.get_storage_info()
    if storage:
        print(f"\n💾 Storage: {storage['used_gb']} GB / {storage['total_gb']} GB used")
