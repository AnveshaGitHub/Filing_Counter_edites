from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    form_type: Mapped[str] = mapped_column(String(100), nullable=False, default="filing_registration")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    extractor_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v2_phase_2")
    triggered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    fields = relationship(
        "ExtractedField",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    feedback_items = relationship(
        "ExtractionFeedback",
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
