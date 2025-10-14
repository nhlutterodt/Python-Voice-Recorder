from __future__ import annotations

import threading
from typing import Callable, Optional, TypedDict


class UploadProgress(TypedDict):
    uploaded_bytes: int
    total_bytes: Optional[int]
    percent: Optional[int]


class UploadResult(TypedDict):
    file_id: str
    name: str
    size: int
    created_time: str


class Uploader:
    """Abstract uploader interface for cloud storage backends."""

    def upload(
        self,
        file_path: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        force: bool = False,
    ) -> UploadResult:
        raise NotImplementedError
