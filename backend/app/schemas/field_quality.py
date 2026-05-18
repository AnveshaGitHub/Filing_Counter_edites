from __future__ import annotations

from pydantic import BaseModel


class FieldQualityResult(BaseModel):
    field_key: str
    original_value: str | None = None
    cleaned_value: str | None = None
    status: str
    reason: str | None = None
    confidence_penalty: float = 0.0
