from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    # Only import for type checkers; at runtime we import the model lazily
    from models.recording import Recording  # type: ignore


class RecordingRepository:
    """Repository encapsulating DB operations for Recording model."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, recording: "Recording") -> "Recording":
        self.session.add(recording)
        self.session.flush()
        return recording

    def get(self, recording_id: int) -> Optional["Recording"]:
        from models.recording import Recording as _Recording

        return (
            self.session.query(_Recording)
            .filter(_Recording.id == recording_id)
            .one_or_none()
        )

    def list(self, limit: int = 100, offset: int = 0):
        from models.recording import Recording as _Recording

        return (
            self.session.query(_Recording)
            .order_by(_Recording.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def delete(self, recording: "Recording", soft: bool = True) -> bool:
        if soft:
            recording.status = "deleted"
            self.session.add(recording)
        else:
            self.session.delete(recording)
        return True
