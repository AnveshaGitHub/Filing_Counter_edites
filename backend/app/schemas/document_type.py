from __future__ import annotations

from pydantic import BaseModel, Field


class PageSignal(BaseModel):
    page_no: int
    page_type: str
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class DocumentTypeDecision(BaseModel):
    document_type: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)
    priority_pages: list[int] = Field(default_factory=list)


class LowerCourtCandidate(BaseModel):
    field_key: str
    value: str
    confidence: float
    page_no: int | None = None
    evidence: str | None = None
    source: str = "lower_court_extractor"
