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

from .exceptions import NotAuthenticatedError, APILibrariesMissingError

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
                         description: Optional[str] = None, tags: Optional[List[str]] = None) -> Optional[str]:
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
            
            # Create metadata
            class FileCreateMetadata(TypedDict, total=False):
                name: str
                parents: List[str]
                description: str
                properties: Dict[str, str]

            metadata: FileCreateMetadata = {
                'name': file_title,
                'parents': [folder_id],
                'description': description or f"Audio recording uploaded from Voice Recorder Pro on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            # Add properties for searchability
            properties: Dict[str, str] = {
                'source': 'Voice Recorder Pro',
                'upload_date': datetime.now().isoformat(),
                'file_size': str(file_size)
            }
            
            if tags:
                properties['tags'] = ','.join(tags)
            
            metadata['properties'] = properties
            
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
        except Exception as e:
            logging.error("Upload failed: %s", e)
            # Preserve previous behaviour of returning None for failures
            return None
    
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
    
    # Initialize managers
    auth_manager = GoogleAuthManager()
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
