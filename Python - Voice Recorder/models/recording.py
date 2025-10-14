# models/recording.py
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.sql import func
import sys

# Resolve the application's canonical Base instance. Prefer the legacy
# import name 'models.database' because many tests import the 'models'
# package directly; importing it first prevents the same file from being
# loaded under two different module names. If legacy is not present,
# fall back to the canonical package import.
_base = None
if 'models.database' in sys.modules:
    _base = sys.modules['models.database']
elif 'voice_recorder.models.database' in sys.modules:
    _base = sys.modules['voice_recorder.models.database']

if _base is None:
    try:
        # Use canonical import path
        import voice_recorder.models.database as _mdb  # type: ignore
        _base = _mdb
    except Exception:
        # Fallback for environments where voice_recorder package is not set up
        try:
            from voice_recorder.models.database import Base as _dummy_base  # type: ignore
            # If we could import the canonical Base directly, get the module
            import voice_recorder.models.database as _mdb  # type: ignore
            _base = _mdb
        except Exception:
            # This should not happen in properly configured environment
            raise ImportError("Could not import voice_recorder.models.database")

if _base is not None and hasattr(_base, 'Base'):
    Base = _base.Base
else:
    # Should not happen, but raise a clear error if Base cannot be found
    raise ImportError("Could not locate Base in models.database or voice_recorder.models.database")


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    # original filename provided by user
    filename = Column(String, nullable=False)
    # stored internal filename (UUID) to avoid collisions
    stored_filename = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=True)

    # core audio metadata
    duration = Column(Float, nullable=False, default=0.0)  # Duration in seconds
    filesize_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String, nullable=True)

    # sync and provenance
    checksum = Column(String, nullable=True)  # sha256
    status = Column(String, default="active")  # active, archived, deleted
    sync_status = Column(String, default="unsynced")  # unsynced, syncing, synced, failed
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    # timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


# Trace mapping registration at import time to help debug duplicate Table definitions
try:
    print(f"[IMPORT TRACE] models.recording imported. Base.metadata id={id(Base.metadata)}; tables_before={list(Base.metadata.tables.keys())}")
except Exception:
    pass

# Ensure module is available under both module names to avoid re-importing
try:
    import sys as _sys
    _self = _sys.modules.get(__name__)
    if _self is not None:
        # Map legacy and canonical module names to the same module object
        _sys.modules.setdefault('models.recording', _self)
        _sys.modules.setdefault('voice_recorder.models.recording', _self)
        try:
            print(f"[IMPORT TRACE] models.recording aliases: models.recording -> {id(_sys.modules.get('models.recording'))}; voice_recorder.models.recording -> {id(_sys.modules.get('voice_recorder.models.recording'))}")
        except Exception:
            pass
except Exception:
    pass
