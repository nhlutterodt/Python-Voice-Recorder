from __future__ import annotations

from typing import Optional, Callable, TypedDict, Any
import threading
import logging

from .uploader import Uploader, UploadProgress, UploadResult
from .upload_utils import chunked_upload_with_progress, TransientUploadError
from .exceptions import NotAuthenticatedError, APILibrariesMissingError, UploadError

logger = logging.getLogger(__name__)


class GoogleDriveUploader(Uploader):
    """Adapter that exposes a high-level Uploader interface while delegating
    actual Drive interactions to the existing GoogleDriveManager.
    """

    def __init__(self, drive_manager: Any, chunk_size: int = 256 * 1024):
        self.drive_manager = drive_manager
        self.chunk_size = chunk_size

    def upload(self,
               file_path: str,
               *,
               title: Optional[str] = None,
               description: Optional[str] = None,
               tags: Optional[list[str]] = None,
               progress_callback: Optional[Callable[[UploadProgress], None]] = None,
               cancel_event: Optional[threading.Event] = None) -> UploadResult:
        # Keep behaviour: raise typed exceptions used across the cloud package
        try:
            # Validate the manager provides the internal helpers we rely on
            required = ('_get_service', '_ensure_recordings_folder', '_import_http')
            if not all(hasattr(self.drive_manager, name) for name in required):
                raise APILibrariesMissingError('Drive manager missing required methods for uploader')

            def create_request():
                # GoogleDriveManager currently creates a MediaFileUpload and
                # uses service.files().create(...). We reuse that logic by
                # invoking a small wrapper on the manager that returns a request
                # with .next_chunk() semantics.
                service = self.drive_manager._get_service()
                folder_id = self.drive_manager._ensure_recordings_folder()

                metadata = {
                    'name': title or file_path.split('/')[-1],
                    'parents': [folder_id],
                    'description': description or ''
                }

                media = self.drive_manager._import_http()[0](file_path, mimetype=None, resumable=True)

                request = service.files().create(body=metadata, media_body=media, fields='id, name, size, createdTime')

                # Attach total_size if available on media
                try:
                    request.total_size = int(getattr(media, 'size', 0) or 0) or None
                except Exception:
                    request.total_size = None

                return request

            def progress_wrapper(uploaded: int, total: Optional[int]):
                if progress_callback:
                    pct = None
                    if total:
                        try:
                            pct = int(uploaded * 100 / total)
                        except Exception:
                            pct = None
                    progress_callback({'uploaded_bytes': uploaded, 'total_bytes': total, 'percent': pct})

            def cancel_check():
                return cancel_event.is_set() if cancel_event is not None else False

            resp = chunked_upload_with_progress(create_request, progress_callback=progress_wrapper, cancel_check=cancel_check)

            # Map response to UploadResult
            result: UploadResult = {
                'file_id': resp.get('id'),
                'name': resp.get('name'),
                'size': int(resp.get('size', 0)),
                'created_time': resp.get('createdTime')
            }

            return result

        except NotAuthenticatedError:
            raise
        except APILibrariesMissingError:
            raise
        except TransientUploadError as e:
            raise UploadError('Transient upload failure') from e
        except Exception as e:
            logger.exception('Upload failed')
            raise UploadError('Upload failed') from e
