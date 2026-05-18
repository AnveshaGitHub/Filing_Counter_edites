from __future__ import annotations

from pydantic import BaseModel, Field


class PageClassificationResult(BaseModel):
    page_no: int
    page_type: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)
    text_preview: str | None = None


class DocumentClassificationResult(BaseModel):
    document_id: int
    document_type: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)
    pages: list[PageClassificationResult] = Field(default_factory=list)
