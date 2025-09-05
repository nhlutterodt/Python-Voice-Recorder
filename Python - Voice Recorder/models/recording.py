# models/recording.py
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.sql import func
from models.database import Base


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
