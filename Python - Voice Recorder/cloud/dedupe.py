"""Helpers for content hashing and deduplication of recordings.

This module provides a deterministic content-hash function so uploads
can be annotated with a hash and used to detect duplicates server-side
or during local pre-checks.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


def compute_content_sha256(file_path: str, chunk_size: int = 65536) -> Optional[str]:
    """Compute a SHA-256 content hash for the given file.

    Returns a hex string or None if the file can't be read.
    """
    try:
        h = hashlib.sha256()
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return None

        with p.open('rb') as fh:
            while True:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)

        return h.hexdigest()
    except Exception:
        return None
