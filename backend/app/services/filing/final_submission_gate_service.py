from __future__ import annotations

from dataclasses import dataclass, field

from app.services.filing.field_quality_gate_service import FieldQualityGateService
from app.services.filing.source_quality_gate_service import SourceQualityGateService


@dataclass
class FinalSubmissionIssue:
    field_key: str
    message: str
    severity: str = "error"


@dataclass
class FinalSubmissionGateResult:
    ready_for_submit: bool
    cleaned_payload: dict
    issues: list[FinalSubmissionIssue] = field(default_factory=list)


class FinalSubmissionGateService:
    REQUIRED_FIELDS = ["case_type", "petitioner_name", "respondent_name"]

    OPTIONAL_FIELDS = [
        "list_type",
        "special_case",
        "petitioner_party_type",
        "respondent_party_type",
        "relation",
        "father_or_husband",
        "occupation",
        "gender",
        "date_of_birth",
        "age",
        "country",
        "state",
        "district",
        "tehsil",
        "village",
        "phone_mobile",
        "email_id",
        "pincode",
        "address",
        "caste",
        "identity_proof",
    ]

    def __init__(self) -> None:
        self.quality_gate = FieldQualityGateService()
        self.source_gate = SourceQualityGateService()

    def validate(self, payload: dict, document_type: str | None = None) -> FinalSubmissionGateResult:
        cleaned: dict = dict(payload or {})
        issues: list[FinalSubmissionIssue] = []
        source_decision = self.source_gate.decide(document_type)

        if not source_decision.allow_direct_submit:
            issues.append(
                FinalSubmissionIssue(
                    field_key="document_source",
                    message=source_decision.reason or "document_source_requires_review",
                    severity="warning",
                )
            )

        for field_key in self.REQUIRED_FIELDS:
            quality = self.quality_gate.validate(field_key, cleaned.get(field_key))
            if quality.status in {"accepted", "cleaned"} and quality.cleaned_value:
                cleaned[field_key] = quality.cleaned_value
                continue

            cleaned[field_key] = None
            issues.append(
                FinalSubmissionIssue(
                    field_key=field_key,
                    message=f"{self._label(field_key)} is required or failed quality gate: {quality.reason}",
                    severity="error",
                )
            )

        for field_key in self.OPTIONAL_FIELDS:
            if field_key not in cleaned:
                continue

            quality = self.quality_gate.validate(field_key, cleaned.get(field_key))
            if quality.status in {"accepted", "cleaned", "skipped"}:
                cleaned[field_key] = quality.cleaned_value
                continue

            cleaned[field_key] = None
            issues.append(
                FinalSubmissionIssue(
                    field_key=field_key,
                    message=f"{self._label(field_key)} rejected by quality gate: {quality.reason}",
                    severity="warning",
                )
            )

        ready = (
            source_decision.allow_direct_submit
            and not any(issue.severity == "error" for issue in issues)
            and all(cleaned.get(f) for f in self.REQUIRED_FIELDS)
        )
        return FinalSubmissionGateResult(
            ready_for_submit=ready,
            cleaned_payload=cleaned,
            issues=self._dedupe(issues),
        )

    def _label(self, field_key: str) -> str:
        return field_key.replace("_", " ").title()

    def _dedupe(self, issues: list[FinalSubmissionIssue]) -> list[FinalSubmissionIssue]:
        seen: set[tuple[str, str, str]] = set()
        out: list[FinalSubmissionIssue] = []
        for issue in issues:
            key = (
                issue.field_key.strip().lower(),
                issue.message.strip().lower().rstrip("."),
                issue.severity.strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(issue)
        return out
