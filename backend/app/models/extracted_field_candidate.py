from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExtractedFieldCandidate(Base):
    __tablename__ = "extracted_field_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    field_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, default=0.0)
    status: Mapped[str | None] = mapped_column(String(40), default="suggested")
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extractor: Mapped[str | None] = mapped_column(String(160), nullable=True)
    validation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
