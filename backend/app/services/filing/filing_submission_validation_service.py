from __future__ import annotations

import re

from app.schemas.filing_payload import FilingFormPayload, FilingPayloadValidationIssue
from app.services.filing.validation_issue_utils import dedupe_validation_issues


class FilingSubmissionValidationService:
    def validate(self, payload: FilingFormPayload) -> list[FilingPayloadValidationIssue]:
        issues: list[FilingPayloadValidationIssue] = []

        if not payload.case_type:
            issues.append(
                FilingPayloadValidationIssue(
                    field_key="case_type",
                    message="Case Type is required",
                    severity="error",
                )
            )

        if not payload.petitioner_name:
            issues.append(
                FilingPayloadValidationIssue(
                    field_key="petitioner_name",
                    message="Petitioner Name is required",
                    severity="error",
                )
            )

        if not payload.respondent_name:
            issues.append(
                FilingPayloadValidationIssue(
                    field_key="respondent_name",
                    message="Respondent Name is required",
                    severity="error",
                )
            )

        if payload.advocates:
            first_adv = payload.advocates[0]
            mobile = first_adv.get("mobile")
            year = first_adv.get("enrol_year")

            if mobile and not re.fullmatch(r"[6-9]\d{9}", mobile):
                issues.append(
                    FilingPayloadValidationIssue(
                        field_key="advocates[0].mobile",
                        message="Advocate mobile format is invalid",
                        severity="error",
                    )
                )

            if year and not re.fullmatch(r"(19|20)\d{2}", year):
                issues.append(
                    FilingPayloadValidationIssue(
                        field_key="advocates[0].enrol_year",
                        message="Advocate enrol year is invalid",
                        severity="error",
                    )
                )

        return dedupe_validation_issues(issues)
