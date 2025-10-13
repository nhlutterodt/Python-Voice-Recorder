"""
Original Recording model for initial migration.
This represents the schema before the metadata additions.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from voice_recorder.models.database import Base


if 'recordings' not in getattr(Base, 'metadata').tables:
    class RecordingOriginal(Base):
        """Original Recording model for migration baseline"""
        __tablename__ = "recordings"

        id = Column(Integer, primary_key=True, index=True)
        filename = Column(String, unique=True, nullable=False)
        title = Column(String, nullable=True)
        duration = Column(Float, nullable=False)  # Duration in seconds
        status = Column(String, default="active")  # active, archived, deleted
        created_at = Column(DateTime(timezone=True), server_default=func.now())


try:
    print(f"[IMPORT TRACE] models.recording_original imported. Base.metadata id={id(Base.metadata)}; tables={list(Base.metadata.tables.keys())}")
except Exception:
    pass
