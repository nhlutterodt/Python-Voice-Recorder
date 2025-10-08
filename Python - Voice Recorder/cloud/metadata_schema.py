from __future__ import annotations

from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import os

# Canonical appProperties keys
KEY_SOURCE = "source"
KEY_UPLOAD_DATE = "upload_date"
KEY_FILE_SIZE = "file_size"
KEY_TAGS = "tags"
KEY_CONTENT_SHA256 = "content_sha256"


def build_upload_metadata(
    file_path: str,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    content_sha256: Optional[str] = None,
    folder_id: Optional[str] = None,
    extra_properties: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build a Drive file metadata dict with canonical appProperties.

    Returns a mapping suitable for Drive `files().create(body=...)`.
    """
    file_name = Path(file_path).name
    file_size = None
    try:
        file_size = os.path.getsize(file_path)
    except Exception:
        file_size = None

    metadata: Dict[str, Any] = {
        "name": title or file_name,
    }

    if folder_id:
        metadata["parents"] = [folder_id]

    metadata["description"] = description or f"Audio recording uploaded from Voice Recorder Pro on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    props: Dict[str, str] = {
        KEY_SOURCE: "Voice Recorder Pro",
        KEY_UPLOAD_DATE: datetime.now().isoformat(),
    }

    if file_size is not None:
        props[KEY_FILE_SIZE] = str(file_size)

    if tags:
        props[KEY_TAGS] = ",".join(tags)

    if content_sha256:
        props[KEY_CONTENT_SHA256] = content_sha256

    if extra_properties:
        # extra_properties override defaults
        for k, v in extra_properties.items():
            props[k] = v

    # Use Drive's `appProperties` which are private to the app and intended
    # for application-specific metadata. This keeps user-visible metadata
    # cleaner while allowing the app to query and manage files by these keys.
    metadata["appProperties"] = props

    return metadata
