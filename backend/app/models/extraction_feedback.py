from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExtractionFeedback(Base):
    __tablename__ = "extraction_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    extraction_job_id: Mapped[int] = mapped_column(
        ForeignKey("extraction_jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    field_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    system_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_value: Mapped[str] = mapped_column(Text, nullable=False)
    correction_type: Mapped[str] = mapped_column(String(50), nullable=False, default="edited")
    corrected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("ExtractionJob", back_populates="feedback_items")
