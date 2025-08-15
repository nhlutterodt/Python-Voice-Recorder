# models/recording.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from models.database import Base

class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=True)
    duration = Column(Float, nullable=False)  # Duration in seconds  # type: ignore
    status = Column(String, default="active")  # active, archived, deleted
    created_at = Column(DateTime(timezone=True), server_default=func.now())
