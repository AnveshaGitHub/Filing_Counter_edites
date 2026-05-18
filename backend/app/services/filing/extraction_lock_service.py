from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.extraction_lock import ExtractionLock


class ExtractionLockService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def acquire_lock(
        self, document_id: int, locked_by: str | None, reason: str = "extraction"
    ) -> tuple[bool, str | None]:
        existing = (
            self.db.query(ExtractionLock)
            .filter(ExtractionLock.document_id == document_id)
            .first()
        )

        now = datetime.utcnow()

        if existing:
            if existing.expires_at > now:
                return False, f"document_locked_by:{existing.locked_by or 'unknown'}"
            self.db.delete(existing)
            self.db.commit()

        lock = ExtractionLock(
            document_id=document_id,
            locked_by=locked_by,
            lock_reason=reason,
            locked_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        self.db.add(lock)
        self.db.commit()
        return True, None

    def release_lock(self, document_id: int) -> None:
        existing = (
            self.db.query(ExtractionLock)
            .filter(ExtractionLock.document_id == document_id)
            .first()
        )
        if existing:
            self.db.delete(existing)
            self.db.commit()
