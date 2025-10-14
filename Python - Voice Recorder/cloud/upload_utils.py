from __future__ import annotations

import logging
import random
import time
from typing import Callable, Optional, Protocol, Tuple, runtime_checkable

logger = logging.getLogger(__name__)


class TransientUploadError(Exception):
    """Raised when the upload fails repeatedly with transient errors."""


# Heuristics for transient error detection (no extra deps).
_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "temporar",  # catches 'temporary'
    "connection",
    "network",
    "too many requests",
    "429",
)


def _is_transient_error(exc: Exception) -> bool:
    """
    Conservative detection of transient network/API errors.
    Vendor-specific exceptions should still be caught by message/name checks.
    """
    name = type(exc).__name__.lower()
    msg = str(exc).lower()

    if any(m in msg for m in _TRANSIENT_MARKERS):
        return True

    # Common connection-ish signal in the class name (e.g., ConnectionError)
    if "connection" in name:
        return True

    # Rough 5xx check in message text
    if any(code in msg for code in ("500", "502", "503", "504")):
        return True

    return False


def _calc_backoff(base: float, attempt: int, *, max_backoff: float = 30.0) -> float:
    """
    Exponential backoff with jitter, capped.
    attempt: 1-based attempt counter.
    """
    exp = base * (2 ** (attempt - 1))
    jitter = random.uniform(0.0, min(exp, 1.0))
    return min(exp + jitter, max_backoff)


def _discover_total_bytes(
    status: Optional[_StatusLike], req: _RequestLike
) -> Optional[int]:
    """Try to discover the total upload size from status or request.

    Returns an int number of bytes or None if not discoverable.
    """
    try:
        maybe = getattr(status, "total_size", None) if status is not None else None
        if maybe is None:
            maybe = getattr(req, "total_size", None)
        return int(maybe) if maybe not in (None, 0) else None
    except Exception:
        return None


def _normalize_progress(status: _StatusLike, total_bytes: Optional[int]) -> int:
    """Return uploaded bytes as an int from a status-like object.

    Prefer a progress() method, falling back to status.uploaded attribute.
    """
    try:
        # Try calling progress() if available; allow it to raise/attribute error.
        p = status.progress()  # type: ignore[call-arg]
        if isinstance(p, float) and total_bytes is not None:
            return max(0, min(total_bytes, int(p * total_bytes)))
        return int(p)
    except Exception:
        # fall through to attribute fallback
        pass

    try:
        return int(getattr(status, "uploaded", 0) or 0)
    except Exception:
        return 0


def _single_request_upload(
    req: _RequestLike,
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> object:
    """Perform the inner loop for a single request instance.

    Returns the response object when upload completes. May raise exceptions
    raised by req.next_chunk() or RuntimeError on cancellation.
    """
    response: object | None = None
    total_bytes: Optional[int] = None

    while response is None:
        _check_and_handle_cancel(cancel_check)

        status, response = req.next_chunk()

        if total_bytes is None:
            total_bytes = _discover_total_bytes(status, req)

        if status and progress_callback:
            _handle_progress(status, total_bytes, progress_callback)

    return response


def _check_and_handle_cancel(cancel_check: Optional[Callable[[], bool]]):
    """Raise RuntimeError if cancel_check signals cancellation."""
    if cancel_check and cancel_check():
        logger.info("Upload cancelled by caller")
        raise RuntimeError("upload_cancelled")


def _handle_progress(
    status: _StatusLike,
    total_bytes: Optional[int],
    progress_callback: Callable[[int, Optional[int]], None],
):
    """Normalize status and call the progress callback, swallowing callback errors."""
    uploaded = _normalize_progress(status, total_bytes)
    try:
        progress_callback(uploaded, total_bytes)
    except Exception:
        logger.debug("Progress callback raised; ignoring.", exc_info=True)


@runtime_checkable
class _StatusLike(Protocol):
    # Optional attributes some SDKs expose
    total_size: int | None
    uploaded: int | None

    # Optional method
    def progress(self) -> float | int: ...


@runtime_checkable
class _RequestLike(Protocol):
    # Required by this helper
    def next_chunk(self) -> Tuple[Optional[_StatusLike], Optional[object]]: ...

    # Optional attribute some SDKs expose
    total_size: int | None


def chunked_upload_with_progress(
    create_request: Callable[[], _RequestLike],
    progress_callback: Optional[Callable[[int, Optional[int]], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    max_retries: int = 5,
    retry_backoff: float = 0.5,
) -> object:
    """
    Run a resumable, chunked upload using a request-like object.

    The object returned by `create_request()` must implement `.next_chunk()`
    and return `(status, response)` where `response` is `None` until complete.
    `status` may expose:
      - `progress()` -> fraction [0.0..1.0] or absolute bytes
      - `uploaded` (absolute bytes)
      - `total_size` (absolute bytes)
    The request may also expose `total_size`.

    Progress callback receives `(uploaded_bytes, total_bytes)` where `total_bytes`
    can be `None` if not discoverable.
    """
    attempt = 0

    while True:
        attempt += 1
        try:
            req = create_request()
            # Delegate the per-request loop to a helper for clarity.
            response = _single_request_upload(
                req, progress_callback=progress_callback, cancel_check=cancel_check
            )
            return response

        except KeyboardInterrupt:
            logger.info("Upload interrupted by user (KeyboardInterrupt).")
            raise

        except Exception as e:
            # Decide whether to retry this whole request
            if not _is_transient_error(e) or attempt > max_retries:
                logger.error("Upload failed (attempt=%d): %s", attempt, e)
                raise

            backoff = _calc_backoff(retry_backoff, attempt)
            logger.debug(
                "Transient upload error, retrying in %.2fs (attempt %d/%d): %s",
                backoff,
                attempt,
                max_retries,
                e,
            )
            time.sleep(backoff)
