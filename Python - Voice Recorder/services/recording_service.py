import shutil
import uuid
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional
import models.database as mdb
from models.database import db_context
from repositories.recording_repository import RecordingRepository
from models.recording import Recording
from datetime import datetime, timezone

from core.logging_config import get_logger
from core.database_context import DBContextProtocol

logger = get_logger(__name__)

RECORDINGS_DIR = Path("recordings/raw").resolve()
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class RecordingService:
    """Service to handle ingestion and metadata capture for recordings.

    Supports dependency injection for the database context and recordings
    directory to simplify testing. If not provided, falls back to the
    module-level defaults for backward compatibility.
    """

    def __init__(self, db_ctx: Optional[DBContextProtocol] = None, recordings_dir: Optional[Path] = None) -> None:
        # db_ctx is an instance exposing get_session(...) (DatabaseContextManager or test double)
        # Fall back to the module-level db_context imported from models.database
        self.db_context: DBContextProtocol = db_ctx or db_context

        # Allow overriding the recordings directory for tests
        if recordings_dir:
            self.recordings_dir = Path(recordings_dir).resolve()
            try:
                self.recordings_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                logger.exception("Failed to create recordings_dir: %s", self.recordings_dir)
        else:
            self.recordings_dir = RECORDINGS_DIR

    def _compute_checksum(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def create_from_file(self, src_path: str, title: Optional[str] = None) -> Recording:
        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        try:
            # determine mime and duration placeholder
            mime_type, _ = mimetypes.guess_type(str(src))
            mime_type = mime_type or "audio/wav"

            # copy into recordings dir with uuid filename
            stored_name = f"{uuid.uuid4().hex}{src.suffix}"
            dest = self.recordings_dir / stored_name
            shutil.copy2(src, dest)

            checksum = self._compute_checksum(dest)
            filesize = dest.stat().st_size
        except PermissionError as e:
            logger.error(f"Permission denied accessing file {src_path}: {e}")
            raise
        except OSError as e:
            logger.error(f"File system error processing {src_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing file {src_path}: {e}")
            raise

        # Debug: report which DATABASE_URL / engine we're targeting
        try:
            resolved = getattr(mdb, 'DATABASE_URL', None)
            logger.info("RecordingService resolved DATABASE_URL: %s", resolved)
            logger.debug("RecordingService resolved DATABASE_URL: %s", resolved)
        except Exception:
            logger.exception("Failed to read DATABASE_URL from models.database")

        # create DB row using context manager (use injected db_context)
        with self.db_context.get_session(autocommit=True) as session:
            try:
                bind = session.get_bind()
                # session.get_bind() may return Engine or Connection
                bind_url = getattr(bind, 'url', None) or str(bind)
                logger.info("RecordingService session bind: %s", bind_url)
                logger.debug("RecordingService session bind: %s", bind_url)
            except Exception:
                logger.exception("Failed to determine session bind/engine URL")

            repo = RecordingRepository(session)
            rec = Recording(
                filename=src.name,
                stored_filename=stored_name if hasattr(Recording, "stored_filename") else None,
                title=title,
                duration=0.0,
                status="active",
                created_at=datetime.now(timezone.utc),
            )
            # store extended fields if present on model
            if hasattr(rec, "stored_filename"):
                rec.stored_filename = stored_name
            if hasattr(rec, "filesize_bytes"):
                rec.filesize_bytes = filesize
            if hasattr(rec, "mime_type"):
                rec.mime_type = mime_type
            if hasattr(rec, "checksum"):
                rec.checksum = checksum

            repo.add(rec)
            try:
                # Ensure the new record is committed to the DB before returning.
                session.commit()
            except Exception:
                logger.exception("Commit failed in RecordingService")
                raise
            session.refresh(rec)
            logger.info("Created recording %s (checksum=%s)", rec.id, checksum)
            return rec
