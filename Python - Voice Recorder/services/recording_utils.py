"""Utilities for recording-related helpers.

Small helpers that are lightweight and safe to import from CLI/tests.
"""
import hashlib
import uuid
from typing import Optional


def compute_sha256_for_bytes(data: bytes) -> str:
    """Compute SHA256 hex digest for given bytes."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def human_readable_size(num_bytes: Optional[int]) -> Optional[str]:
    """Return a human friendly size string like '1.2 MB'."""
    if num_bytes is None:
        return None
    try:
        num = float(num_bytes)
    except Exception:
        return None
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(num)} {unit}"
            return f"{num:.2f} {unit}"
        num /= 1024.0


def make_stored_filename(original_filename: Optional[str] = None) -> str:
    """Create a unique stored filename (UUID + optional extension).

    Keeps original extension when possible.
    """
    uid = uuid.uuid4().hex
    if original_filename:
        # try to preserve extension
        parts = original_filename.rsplit('.', 1)
        if len(parts) == 2 and parts[1]:
            return f"{uid}.{parts[1]}"
    return uid
