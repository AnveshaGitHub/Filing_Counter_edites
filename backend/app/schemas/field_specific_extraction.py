from __future__ import annotations

from pydantic import BaseModel


class FieldSpecificCandidate(BaseModel):
    field_key: str
    value: str
    normalized_value: str | None = None
    confidence: float
    page_no: int | None = None
    page_type: str | None = None
    evidence: str | None = None
    extractor: str
    status: str = "suggested"
    validation_note: str | None = None
