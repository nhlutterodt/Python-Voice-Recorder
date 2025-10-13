from __future__ import annotations

from typing import Optional, Callable, TypedDict, Any
import threading
import logging

from voice_recorder.cloud.uploader import Uploader, UploadProgress, UploadResult
from voice_recorder.cloud.upload_utils import chunked_upload_with_progress, TransientUploadError
from voice_recorder.cloud.exceptions import NotAuthenticatedError, APILibrariesMissingError, UploadError, DuplicateFoundError

logger = logging.getLogger(__name__)


class GoogleDriveUploader(Uploader):
    """Adapter that exposes a high-level Uploader interface while delegating
    actual Drive interactions to the existing GoogleDriveManager.
    """

    def __init__(self, drive_manager: Any, chunk_size: Optional[int] = None):
        self.drive_manager = drive_manager
        self.chunk_size = chunk_size

    def upload(self,
               file_path: str,
               *,
               title: Optional[str] = None,
               description: Optional[str] = None,
               tags: Optional[list[str]] = None,
               progress_callback: Optional[Callable[[UploadProgress], None]] = None,
               cancel_event: Optional[threading.Event] = None,
               force: bool = False) -> UploadResult:
        # New callers can pass `force=True` to bypass server-side duplicate
        # detection if they intentionally want to upload again. The manager
    # `find_duplicate_by_content_sha256` helper may raise DuplicateFoundError
        # which we propagate unless force is True.
        # Keep behaviour: raise typed exceptions used across the cloud package
        try:
            # Dedupe pre-check: compute content hash locally and ask manager
            # to locate an existing file. If found, raise DuplicateFoundError
            # (unless caller explicitly forces upload). Any auth/library errors
            # should surface from the manager's helpers.
            try:
                from voice_recorder.cloud.dedupe import compute_content_sha256
                ch = compute_content_sha256(file_path)
                if ch:
                    finder = getattr(self.drive_manager, 'find_duplicate_by_content_sha256', None)
                    if callable(finder):
                        existing = finder(ch)
                        if existing:
                            # If caller requested a forced upload, continue.
                            if force:
                                logger.info('Force upload requested; bypassing duplicate check for file %s', file_path)
                            else:
                                # Propagate a typed DuplicateFoundError so the UI can
                                # prompt the user to reuse or force-upload as desired.
                                raise DuplicateFoundError(file_id=existing.get('id'), name=existing.get('name'))
            except DuplicateFoundError:
                # Don't swallow DuplicateFoundError; let outer handler re-raise
                raise
            except Exception:
                # If hashing or lookup fails, continue to upload normally
                pass

            def create_request():
                # GoogleDriveManager currently creates a MediaFileUpload and
                # uses service.files().create(...). We reuse that logic by
                # invoking a small wrapper on the manager that returns a request
                # with .next_chunk() semantics.
                service = self.drive_manager._get_service()
                folder_id = self.drive_manager._ensure_recordings_folder()

                from voice_recorder.cloud.metadata_schema import build_upload_metadata

                metadata = build_upload_metadata(
                    file_path,
                    title=title or file_path.split('/')[-1],
                    description=description or '',
                    tags=tags,
                    content_sha256=ch,
                    folder_id=folder_id,
                )

                # Prefer a manager-provided _import_http if present, else import
                # the module-level helper from drive_manager.
                try:
                    get_http = getattr(self.drive_manager, '_import_http', None)
                    if callable(get_http):
                        media_cls = get_http()[0]
                    else:
                        from voice_recorder.cloud.drive_manager import _import_http as _module_import_http
                        media_cls = _module_import_http()[0]
                    # Respect configured chunk_size for MediaFileUpload if provided
                    chunksize = getattr(self, 'chunk_size', None)
                    if chunksize:
                        media = media_cls(file_path, mimetype=None, resumable=True, chunksize=chunksize)
                    else:
                        media = media_cls(file_path, mimetype=None, resumable=True)
                except Exception:
                    # Let underlying errors surface (auth/missing libs) so callers
                    # receive typed exceptions from _get_service/_import_http.
                    raise

                request = service.files().create(body=metadata, media_body=media, fields='id, name, size, createdTime')

                # Attach total_size if available on media
                try:
                    # MediaFileUpload exposes size and the request can be annotated for progress helpers
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

            # If the manager's pre-check raised DuplicateFoundError (when called
            # earlier) we expect callers to have handled it; however, some
            # managers might perform an inline pre-check on create_request.
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
        except DuplicateFoundError:
            # Let callers handle duplicates (UI may prompt to reuse existing file)
            raise
        except TransientUploadError as e:
            raise UploadError('Transient upload failure') from e
        except Exception as e:
            logger.exception('Upload failed')
            raise UploadError('Upload failed') from e
