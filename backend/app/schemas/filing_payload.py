from __future__ import annotations

from pydantic import BaseModel, Field


class FilingPayloadField(BaseModel):
    key: str
    value: str | bool | None = None
    normalized_value: str | bool | None = None
    source: str | None = None
    confidence: float | None = None


class FilingFormPayload(BaseModel):
    case_type: str | None = None
    list_type: str | None = None
    with_application: bool = False

    petitioner_name: str | None = None
    petitioner_party_type: str | None = None
    hide_party_petitioner: bool = False
    differently_abled_petitioner: bool = False

    respondent_name: str | None = None
    respondent_party_type: str | None = None
    hide_party_respondent: bool = False
    differently_abled_respondent: bool = False

    advocates: list[dict] = Field(default_factory=list)


class FilingPayloadValidationIssue(BaseModel):
    field_key: str
    message: str
    severity: str = "error"


class FilingPayloadResponse(BaseModel):
    document_id: int
    extraction_job_id: int | None = None
    reviewed_session_id: int | None = None
    payload: FilingFormPayload
    issues: list[FilingPayloadValidationIssue] = Field(default_factory=list)
    ready_for_submit: bool = False
