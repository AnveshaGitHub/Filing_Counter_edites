from __future__ import annotations

from pydantic import BaseModel, Field


class SubmissionValidationIssue(BaseModel):
    field_key: str
    message: str
    severity: str = "error"


class FilingSubmissionPayload(BaseModel):
    case_type: str | None = None
    list_type: str | None = None
    with_application: bool = False

    petitioner_party_type: str | None = None
    petitioner_name: str | None = None
    hide_party_petitioner: bool = False
    differently_abled_petitioner: bool = False

    respondent_party_type: str | None = None
    respondent_name: str | None = None
    hide_party_respondent: bool = False
    differently_abled_respondent: bool = False

    advocates: list[dict] = Field(default_factory=list)
    full_metadata: dict = Field(default_factory=dict)


class FilingSubmissionPreviewResponse(BaseModel):
    document_id: int
    extraction_job_id: int | None = None
    reviewed_session_id: int | None = None
    target_system: str = "phhc_filing"
    dry_run: bool = True
    ready_for_submit: bool = False
    payload: FilingSubmissionPayload
    validation_issues: list[SubmissionValidationIssue] = Field(default_factory=list)
    audit_meta: dict = Field(default_factory=dict)


class PrepareSubmissionRequest(BaseModel):
    dry_run: bool = True


class DryRunSubmissionResponse(BaseModel):
    document_id: int
    target_system: str
    dry_run: bool = True
    ready_for_submit: bool
    validation_issues: list[SubmissionValidationIssue] = Field(default_factory=list)
    automation_result: dict = Field(default_factory=dict)
