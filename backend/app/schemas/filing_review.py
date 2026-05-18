from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ReviewedFieldInput(BaseModel):
    field_key: str
    field_label: str
    system_value: str | None = None
    reviewed_value: str | None = None
    confidence: float | None = None
    action_taken: str = "accepted"
    evidence_text: str | None = None
    source_type: str | None = None


class CreateReviewSessionRequest(BaseModel):
    extraction_job_id: int | None = None
    reviewed_by: str | None = None
    status: str = "draft"
    submit_ready: bool = False
    notes: str | None = None
    fields: list[ReviewedFieldInput] = Field(default_factory=list)


class ReviewSessionSummary(BaseModel):
    reviewed_session_id: int
    document_id: int
    extraction_job_id: int | None = None
    reviewed_by: str | None = None
    status: str
    submit_ready: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ReviewedFieldResponse(BaseModel):
    field_key: str
    field_label: str
    system_value: str | None = None
    reviewed_value: str | None = None
    confidence: float | None = None
    action_taken: str
    evidence_text: str | None = None
    source_type: str | None = None


class ReviewSessionResponse(BaseModel):
    session: ReviewSessionSummary
    fields: list[ReviewedFieldResponse]
