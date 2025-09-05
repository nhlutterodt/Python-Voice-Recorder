from typing import Optional
from sqlalchemy.orm import Session
from models.recording import Recording


class RecordingRepository:
    """Repository encapsulating DB operations for Recording model."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, recording: Recording) -> Recording:
        self.session.add(recording)
        self.session.flush()
        return recording

    def get(self, recording_id: int) -> Optional[Recording]:
        return self.session.query(Recording).filter(Recording.id == recording_id).one_or_none()

    def list(self, limit: int = 100, offset: int = 0):
        return self.session.query(Recording).order_by(Recording.created_at.desc()).offset(offset).limit(limit).all()

    def delete(self, recording: Recording, soft: bool = True) -> bool:
        if soft:
            recording.status = "deleted"
            self.session.add(recording)
        else:
            self.session.delete(recording)
        return True
