from __future__ import annotations

import re

from app.schemas.filing_submission import FilingSubmissionPayload, SubmissionValidationIssue
from app.services.filing.field_quality_gate_service import FieldQualityGateService
from app.services.filing.validation_issue_utils import dedupe_validation_issues


class SubmissionValidationService:
    def __init__(self) -> None:
        self.quality_gate = FieldQualityGateService()

    def _append_rejected_issue(
        self,
        issues: list[SubmissionValidationIssue],
        field_key: str,
        reason: str | None,
        severity: str = "error",
    ) -> None:
        issues.append(
            SubmissionValidationIssue(
                field_key=field_key,
                message=f"Rejected by quality gate: {reason or 'invalid_value'}",
                severity=severity,
            )
        )

    def validate_and_clean(
        self, payload: FilingSubmissionPayload
    ) -> tuple[FilingSubmissionPayload, list[SubmissionValidationIssue]]:
        issues: list[SubmissionValidationIssue] = []

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
                self._append_rejected_issue(issues, field_key, quality.reason, "error")

        if not payload.case_type:
            issues.append(SubmissionValidationIssue(field_key="case_type", message="Case type is required."))

        if not payload.petitioner_name:
            issues.append(SubmissionValidationIssue(field_key="petitioner_name", message="Petitioner name is required."))

        if not payload.respondent_name:
            issues.append(SubmissionValidationIssue(field_key="respondent_name", message="Respondent name is required."))

        cleaned_advocates: list[dict] = []
        for idx, row in enumerate(payload.advocates):
            cleaned = dict(row)
            for key in list(cleaned.keys()):
                quality = self.quality_gate.validate(f"advocate_{key}", cleaned.get(key))
                if quality.status in {"accepted", "cleaned", "skipped"}:
                    cleaned[key] = quality.cleaned_value
                else:
                    cleaned[key] = None
                    self._append_rejected_issue(
                        issues,
                        f"advocates[{idx}].{key}",
                        quality.reason,
                        "warning",
                    )

            mobile = cleaned.get("mobile")
            if isinstance(mobile, str) and mobile and not re.fullmatch(r"[6-9]\d{9}", mobile):
                issues.append(
                    SubmissionValidationIssue(
                        field_key=f"advocates[{idx}].mobile",
                        message="Advocate mobile format is invalid.",
                    )
                )

            enrol_year = cleaned.get("enrol_year")
            if isinstance(enrol_year, str) and enrol_year and not re.fullmatch(r"(19|20)\d{2}", enrol_year):
                issues.append(
                    SubmissionValidationIssue(
                        field_key=f"advocates[{idx}].enrol_year",
                        message="Advocate enrol year is invalid.",
                        severity="warning",
                    )
                ) 

            cleaned_advocates.append(cleaned)

        payload.advocates = cleaned_advocates
        return payload, dedupe_validation_issues(issues)
