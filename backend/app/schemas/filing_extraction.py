from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


FieldStatus = Literal["confirmed", "suggested", "missing", "rejected"]
JobStatus = Literal["queued", "running", "completed", "needs_review", "failed"]


class FieldEvidence(BaseModel):
    source_type: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    chunk_id: str | None = None
    text: str | None = None
    validation_notes: str | None = None


class FieldCandidate(BaseModel):
    value: str
    normalized_value: str | None = None
    confidence: float = 0.0
    status: FieldStatus = "suggested"
    evidence: FieldEvidence | None = None


class FieldResult(BaseModel):
    field_key: str
    field_label: str
    status: FieldStatus
    value: str | None = None
    normalized_value: str | None = None
    confidence: float = 0.0
    evidence: FieldEvidence | None = None
    suggestions: list[FieldCandidate] = Field(default_factory=list)


class AdvocateRowResult(BaseModel):
    row_index: int
    status: FieldStatus = "missing"
    confidence: float = 0.0
    adv_code: str | None = None
    enrol_no: str | None = None
    enrol_year: str | None = None
    name: str | None = None
    mobile: str | None = None
    remark: str | None = None
    evidence: list[FieldEvidence] = Field(default_factory=list)
    suggestions: dict[str, list[FieldCandidate]] = Field(default_factory=dict)


class PartyMoreDetailsResult(BaseModel):
    status: FieldStatus = "missing"
    confidence: float = 0.0
    address: str | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None
    mobile: str | None = None
    email: str | None = None
    evidence: list[FieldEvidence] = Field(default_factory=list)
    suggestions: dict[str, list[FieldCandidate]] = Field(default_factory=dict)


class FilingGroupedResult(BaseModel):
    core_fields: dict[str, FieldResult] = Field(default_factory=dict)
    petitioner_fields: dict[str, FieldResult] = Field(default_factory=dict)
    respondent_fields: dict[str, FieldResult] = Field(default_factory=dict)
    checkbox_fields: dict[str, FieldResult] = Field(default_factory=dict)
    advocate_rows: list[AdvocateRowResult] = Field(default_factory=list)
    petitioner_more_details: PartyMoreDetailsResult | None = None
    respondent_more_details: PartyMoreDetailsResult | None = None


class ExtractionRunRequest(BaseModel):
    triggered_by: str | None = None
    run_async: bool = True
    force_recompute: bool = False
    form_type: str = "filing_registration"


class ExtractionFeedbackItem(BaseModel):
    field_key: str
    system_value: str | None = None
    user_value: str
    correction_type: str = "edited"
    corrected_by: str | None = None


class ExtractionFeedbackRequest(BaseModel):
    items: list[ExtractionFeedbackItem]


class ExtractionJobSummary(BaseModel):
    extraction_job_id: int
    document_id: int
    form_type: str
    status: JobStatus
    extractor_version: str
    overall_confidence: float | None = None
    needs_review: bool = False
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ExtractionResponse(BaseModel):
    job: ExtractionJobSummary
    fields: list[FieldResult]
    grouped: FilingGroupedResult | None = None
    confirmed_count: int = 0
    suggested_count: int = 0
    missing_count: int = 0
    review_flags: list[str] = Field(default_factory=list)
