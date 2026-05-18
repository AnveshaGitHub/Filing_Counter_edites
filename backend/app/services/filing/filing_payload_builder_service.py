from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.reviewed_filing_session import ReviewedFilingSession
from app.models.reviewed_filing_field import ReviewedFilingField
from app.models.extraction_job import ExtractionJob
from app.models.extracted_field import ExtractedField
from app.schemas.filing_payload import FilingFormPayload, FilingPayloadResponse, FilingPayloadValidationIssue
from app.services.filing.filing_normalization_service import FilingNormalizationService
from app.services.filing.filing_submission_validation_service import (
    FilingSubmissionValidationService,
)
from app.services.filing.validation_issue_utils import dedupe_validation_issues
from app.services.filing.field_quality_gate_service import FieldQualityGateService


class FilingPayloadBuilderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.normalizer = FilingNormalizationService()
        self.validator = FilingSubmissionValidationService()
        self.quality_gate = FieldQualityGateService()

    def _run_quality_gate(
        self, payload: FilingFormPayload
    ) -> tuple[FilingFormPayload, list[FilingPayloadValidationIssue]]:
        issues: list[FilingPayloadValidationIssue] = []
        for field_key in [
            "case_type",
            "list_type",
            "petitioner_party_type",
            "petitioner_name",
            "respondent_party_type",
            "respondent_name",
        ]:
            value = getattr(payload, field_key, None)
            quality = self.quality_gate.validate(field_key, value)
            if quality.status in {"accepted", "cleaned", "skipped"}:
                setattr(payload, field_key, quality.cleaned_value)
            else:
                setattr(payload, field_key, None)
                issues.append(
                    FilingPayloadValidationIssue(
                        field_key=field_key,
                        message=f"Rejected by quality gate: {quality.reason or 'invalid_value'}",
                        severity="error",
                    )
                )

        clean_advocates: list[dict] = []
        for idx, row in enumerate(payload.advocates or []):
            clean_row = dict(row)
            for key in list(clean_row.keys()):
                quality = self.quality_gate.validate(f"advocate_{key}", clean_row.get(key))
                if quality.status in {"accepted", "cleaned", "skipped"}:
                    clean_row[key] = quality.cleaned_value
                else:
                    clean_row[key] = None
                    issues.append(
                        FilingPayloadValidationIssue(
                            field_key=f"advocates[{idx}].{key}",
                            message=f"Rejected by quality gate: {quality.reason or 'invalid_value'}",
                            severity="warning",
                        )
                    )
            clean_advocates.append(clean_row)
        payload.advocates = clean_advocates

        return payload, issues

    def _build_raw_payload_from_review(self, session: ReviewedFilingSession) -> dict:
        rows = (
            self.db.query(ReviewedFilingField)
            .filter(ReviewedFilingField.reviewed_session_id == session.id)
            .all()
        )

        raw: dict = {"advocates": [{}]}

        for row in rows:
            value = row.reviewed_value if row.reviewed_value is not None else row.system_value

            if row.field_key == "case_type":
                raw["case_type"] = value
            elif row.field_key == "list_type":
                raw["list_type"] = value
            elif row.field_key == "with_application":
                raw["with_application"] = value
            elif row.field_key == "petitioner_name":
                raw["petitioner_name"] = value
            elif row.field_key == "petitioner_party_type":
                raw["petitioner_party_type"] = value
            elif row.field_key == "hide_party_petitioner":
                raw["hide_party_petitioner"] = value
            elif row.field_key == "differently_abled_petitioner":
                raw["differently_abled_petitioner"] = value
            elif row.field_key == "respondent_name":
                raw["respondent_name"] = value
            elif row.field_key == "respondent_party_type":
                raw["respondent_party_type"] = value
            elif row.field_key == "hide_party_respondent":
                raw["hide_party_respondent"] = value
            elif row.field_key == "differently_abled_respondent":
                raw["differently_abled_respondent"] = value
            elif row.field_key == "advocate_name":
                raw["advocates"][0]["name"] = value
            elif row.field_key == "advocate_enrol_no":
                raw["advocates"][0]["enrol_no"] = value
            elif row.field_key == "advocate_enrol_year":
                raw["advocates"][0]["enrol_year"] = value
            elif row.field_key == "advocate_mobile":
                raw["advocates"][0]["mobile"] = value
            elif row.field_key == "advocate_remark":
                raw["advocates"][0]["remark"] = value

        return raw

    def _build_raw_payload_from_extraction(self, job: ExtractionJob) -> dict:
        rows = (
            self.db.query(ExtractedField)
            .filter(ExtractedField.extraction_job_id == job.id)
            .all()
        )

        raw: dict = {"advocates": [{}]}

        for row in rows:
            value = row.normalized_value or row.raw_value

            if row.field_key == "case_type":
                raw["case_type"] = value
            elif row.field_key == "list_type":
                raw["list_type"] = value
            elif row.field_key == "with_application":
                raw["with_application"] = value
            elif row.field_key == "petitioner_name":
                raw["petitioner_name"] = value
            elif row.field_key == "petitioner_party_type":
                raw["petitioner_party_type"] = value
            elif row.field_key == "hide_party_petitioner":
                raw["hide_party_petitioner"] = value
            elif row.field_key == "differently_abled_petitioner":
                raw["differently_abled_petitioner"] = value
            elif row.field_key == "respondent_name":
                raw["respondent_name"] = value
            elif row.field_key == "respondent_party_type":
                raw["respondent_party_type"] = value
            elif row.field_key == "hide_party_respondent":
                raw["hide_party_respondent"] = value
            elif row.field_key == "differently_abled_respondent":
                raw["differently_abled_respondent"] = value
            elif row.field_key == "advocate_name":
                raw["advocates"][0]["name"] = value
            elif row.field_key == "advocate_enrol_no":
                raw["advocates"][0]["enrol_no"] = value
            elif row.field_key == "advocate_enrol_year":
                raw["advocates"][0]["enrol_year"] = value
            elif row.field_key == "advocate_mobile":
                raw["advocates"][0]["mobile"] = value
            elif row.field_key == "advocate_remark":
                raw["advocates"][0]["remark"] = value

        return raw

    def get_filing_payload(self, document_id: int) -> FilingPayloadResponse:
        review_session = (
            self.db.query(ReviewedFilingSession)
            .filter(ReviewedFilingSession.document_id == document_id)
            .order_by(ReviewedFilingSession.id.desc())
            .first()
        )

        extraction_job = (
            self.db.query(ExtractionJob)
            .filter(ExtractionJob.document_id == document_id)
            .order_by(ExtractionJob.id.desc())
            .first()
        )

        reviewed_session_id = None
        extraction_job_id = None
        raw: dict = {"advocates": [{}]}

        if review_session:
            reviewed_session_id = review_session.id
            extraction_job_id = review_session.extraction_job_id
            raw = self._build_raw_payload_from_review(review_session)
        elif extraction_job:
            extraction_job_id = extraction_job.id
            raw = self._build_raw_payload_from_extraction(extraction_job)

        normalized = self.normalizer.normalize_payload(raw)
        normalized, quality_issues = self._run_quality_gate(normalized)
        issues = dedupe_validation_issues(quality_issues + self.validator.validate(normalized))

        return FilingPayloadResponse(
            document_id=document_id,
            extraction_job_id=extraction_job_id,
            reviewed_session_id=reviewed_session_id,
            payload=normalized,
            issues=issues,
            ready_for_submit=len([i for i in issues if i.severity == "error"]) == 0,
        )
