from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LocalTestDocumentPage(Base):
    __tablename__ = "local_test_document_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("local_test_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_words_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_lines_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_regions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_avg_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    text_length: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("LocalTestDocument", back_populates="pages")
