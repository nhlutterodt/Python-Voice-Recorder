"""
Storage and File Operations Utilities

Provides reusable helper functions for Google Drive storage operations,
pagination, formatting, and metadata creation. Extracted to centralize
common patterns and reduce code duplication.

These utilities follow patterns from upload_utils.py and metadata_schema.py
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def paginate_results(
    service: Any,
    query: str,
    fields: str = "files(id, name)",
    page_size: int = 100,
    max_results: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch paginated results from Drive API with optional limit.
    
    Handles the pagination loop for Drive API list() requests, consolidating
    common pagination logic used throughout drive_manager.py
    
    Args:
        service: Google Drive API service instance (from _get_service())
        query: Drive API query string (build with QueryBuilder.build())
        fields: Fields to retrieve (default: basic file info)
        page_size: Results per page (max 1000, default 100)
        max_results: Maximum total results to return (None = unlimited)
    
    Returns:
        List of file/folder dicts with requested fields
    
    Example:
        >>> from cloud._query_builder import QueryBuilder
        >>> query = QueryBuilder().in_folder(folder_id).is_folder().not_trashed().build()
        >>> folders = paginate_results(service, query, max_results=50)
    """
    if page_size < 1 or page_size > 1000:
        logger.warning("Invalid page_size %d; using default 100", page_size)
        page_size = 100
    
    results: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    
    while True:
        try:
            response = (
                service.files()
                .list(
                    q=query,
                    fields=f"nextPageToken, {fields}",
                    pageToken=page_token,
                    pageSize=page_size,
                )
                .execute()
            )
            
            for item in response.get("files", []):
                results.append(item)
                
                # Check if we've hit the limit
                if max_results and len(results) >= max_results:
                    return results[:max_results]
            
            page_token = response.get("nextPageToken")
            if not page_token:
                break
                
        except Exception as e:
            logger.error("Error during pagination: %s", e)
            break
    
    return results


def format_file_size(size_bytes: Optional[int]) -> str:
    """
    Format bytes into human-readable file size.
    
    Converts byte counts to KB, MB, GB as appropriate.
    
    Args:
        size_bytes: Size in bytes (or None)
    
    Returns:
        Formatted size string (e.g., "1.5 MB")
    
    Example:
        >>> format_file_size(1536000)
        '1.5 MB'
        >>> format_file_size(None)
        'unknown'
    """
    if size_bytes is None:
        return "unknown"
    
    if size_bytes < 1024:
        return f"{size_bytes} B"
    
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.1f} KB"
    
    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.1f} MB"
    
    size_gb = size_mb / 1024
    return f"{size_gb:.1f} GB"


def create_folder_metadata(
    name: str,
    parent_id: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create Google Drive folder metadata dict.
    
    Builds the metadata structure needed for Drive API folder creation.
    Centralizes folder metadata creation to ensure consistency across the codebase.
    
    Args:
        name: Folder name
        parent_id: Parent folder ID (None = root)
        description: Optional folder description
    
    Returns:
        Metadata dict ready for service.files().create(body=...)
    
    Example:
        >>> metadata = create_folder_metadata("My Recordings", description="Voice recordings")
        >>> result = service.files().create(body=metadata, fields="id").execute()
        >>> folder_id = result.get("id")
    """
    metadata: Dict[str, Any] = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    
    if parent_id:
        metadata["parents"] = [parent_id]
    
    if description:
        metadata["description"] = description
    
    return metadata


def discover_total_bytes(
    request: Any,
) -> Optional[int]:
    """
    Discover total file size from upload request.
    
    Extracts the total file size from an upload request object
    before or during upload. Used for progress tracking.
    
    This follows the pattern from upload_utils.py
    
    Args:
        request: Google Drive API request object
    
    Returns:
        Total bytes to upload, or None if undeterminable
    
    Example:
        >>> media = MediaFileUpload(file_path, resumable=True)
        >>> request = service.files().create(body=metadata, media_body=media)
        >>> total = discover_total_bytes(request)
    """
    try:
        # Try to get media object - this can raise if side_effect set
        try:
            media = request.media_upload
        except Exception:
            return None
        
        if media is None:
            return None
        
        # Try size() method first
        try:
            if callable(getattr(media, "size", None)):
                size_val = media.size()
                if size_val is not None and isinstance(size_val, int):
                    return size_val
        except Exception:
            pass
        
        # Try size_string() method as fallback
        try:
            if callable(getattr(media, "size_string", None)):
                size_str = media.size_string()
                if size_str and size_str != "*" and isinstance(size_str, str):
                    return int(size_str)
        except (ValueError, TypeError):
            pass
        
        return None
    except Exception as e:
        logger.debug("Could not discover total bytes: %s", e)
        return None


def format_storage_info(
    used_bytes: Optional[int],
    limit_bytes: Optional[int],
) -> Dict[str, Any]:
    """
    Format storage quota information for display or logging.
    
    Converts raw storage quota values into human-readable format
    with calculated percentage.
    
    Args:
        used_bytes: Bytes used (or None if unavailable)
        limit_bytes: Storage limit in bytes (or None if unlimited)
    
    Returns:
        Dict with formatted display strings:
        - used: Human-readable used size (str)
        - limit: Human-readable limit (str)
        - percent: Percentage used (float | None)
    
    Example:
        >>> info = format_storage_info(5368709120, 107374182400)  # 5GB / 100GB
        >>> print(f"Using {info['used']} of {info['limit']} ({info['percent']:.1f}%)")
    """
    # Initialize result dict with proper types
    result: Dict[str, Any] = {
        "used": format_file_size(used_bytes),
        "limit": format_file_size(limit_bytes),
        "percent": None,  # type: ignore[typeddict-unknown-key]
    }
    
    # Calculate percentage if both values are available and limit is non-zero
    if used_bytes is not None and limit_bytes is not None and limit_bytes > 0:
        result["percent"] = (used_bytes / limit_bytes) * 100
    
    return result
