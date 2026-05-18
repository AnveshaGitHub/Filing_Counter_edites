from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.local_test_document_page import LocalTestDocumentPage
from app.schemas.filing_payload import FilingPayloadResponse
from app.schemas.filing_submission import (
    FilingSubmissionPayload,
    FilingSubmissionPreviewResponse,
    SubmissionValidationIssue,
)
from app.services.filing.document_type_router_service import DocumentTypeRouterService
from app.services.filing.field_quality_gate_service import FieldQualityGateService
from app.services.filing.final_submission_gate_service import FinalSubmissionGateService
from app.services.filing.filing_payload_builder_service import FilingPayloadBuilderService
from app.services.filing.page_priority_service import PageText
from app.services.filing.submission_validation_service import SubmissionValidationService
from app.services.filing.validation_issue_utils import dedupe_validation_issues


class SubmissionMappingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.payload_builder = FilingPayloadBuilderService(db)
        self.validator = SubmissionValidationService()
        self.final_gate = FinalSubmissionGateService()
        self.quality_gate = FieldQualityGateService()

    def _detect_document_type(self, document_id: int) -> str | None:
        rows = (
            self.db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .limit(40)
            .all()
        )
        pages = [
            PageText(
                page_no=row.page_no,
                text=row.ocr_text or "",
                page_type=getattr(row, "page_type", None) or getattr(row, "detected_page_type", None),
            )
            for row in rows
        ]
        if not pages:
            return None
        return DocumentTypeRouterService().decide(pages).document_type

    def build_submission_preview(self, document_id: int, dry_run: bool = True) -> FilingSubmissionPreviewResponse:
        payload_response: FilingPayloadResponse = self.payload_builder.get_filing_payload(document_id)

        submission_payload = FilingSubmissionPayload(
            case_type=payload_response.payload.case_type,
            list_type=payload_response.payload.list_type,
            with_application=payload_response.payload.with_application,
            petitioner_party_type=payload_response.payload.petitioner_party_type,
            petitioner_name=payload_response.payload.petitioner_name,
            hide_party_petitioner=payload_response.payload.hide_party_petitioner,
            differently_abled_petitioner=payload_response.payload.differently_abled_petitioner,
            respondent_party_type=payload_response.payload.respondent_party_type,
            respondent_name=payload_response.payload.respondent_name,
            hide_party_respondent=payload_response.payload.hide_party_respondent,
            differently_abled_respondent=payload_response.payload.differently_abled_respondent,
            advocates=payload_response.payload.advocates,
            full_metadata=payload_response.payload.full_metadata,
        )

        for key in ["petitioner_name", "respondent_name"]:
            value = getattr(submission_payload, key, None)
            quality = self.quality_gate.validate(key, value)
            if quality.status in {"accepted", "cleaned"}:
                setattr(submission_payload, key, quality.cleaned_value)

        submission_payload, extra_issues = self.validator.validate_and_clean(submission_payload)

        merged_issues = [
            SubmissionValidationIssue(
                field_key=issue.field_key,
                message=issue.message,
                severity=issue.severity,
            )
            for issue in payload_response.issues
        ]
        merged_issues.extend(extra_issues)

        document_type = self._detect_document_type(document_id)
        gate_result = self.final_gate.validate(
            payload=submission_payload.model_dump(),
            document_type=document_type,
        )
        submission_payload = FilingSubmissionPayload(**gate_result.cleaned_payload)
        merged_issues.extend(
            SubmissionValidationIssue(
                field_key=issue.field_key,
                message=issue.message,
                severity=issue.severity,
            )
            for issue in gate_result.issues
        )
        merged_issues = dedupe_validation_issues(merged_issues)
        ready_for_submit = gate_result.ready_for_submit and not any(
            issue.severity == "error" for issue in merged_issues
        )

        return FilingSubmissionPreviewResponse(
            document_id=document_id,
            extraction_job_id=payload_response.extraction_job_id,
            reviewed_session_id=payload_response.reviewed_session_id,
            dry_run=dry_run,
            ready_for_submit=ready_for_submit,
            payload=submission_payload,
            validation_issues=merged_issues,
            audit_meta={
                "source": "payload_builder",
                "review_preferred": True,
                "document_type": document_type,
            },
        )
