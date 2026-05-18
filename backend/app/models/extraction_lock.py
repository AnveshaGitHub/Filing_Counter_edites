from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExtractionLock(Base):
    __tablename__ = "extraction_locks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        unique=True,
    )
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lock_reason: Mapped[str] = mapped_column(String(100), nullable=False, default="extraction")
    locked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.utcnow() + timedelta(minutes=15),
        nullable=False,
    )
