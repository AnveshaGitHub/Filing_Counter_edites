from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReviewedFilingField(Base):
    __tablename__ = "reviewed_filing_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    reviewed_session_id: Mapped[int] = mapped_column(
        ForeignKey("reviewed_filing_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    extraction_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("extraction_jobs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    field_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    field_label: Mapped[str] = mapped_column(String(255), nullable=False)

    system_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    action_taken: Mapped[str] = mapped_column(String(50), nullable=False, default="accepted")
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ReviewedFilingSession", back_populates="fields")
