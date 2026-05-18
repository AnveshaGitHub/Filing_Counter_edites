from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceQualityDecision:
    source_type: str
    allow_direct_submit: bool
    require_operator_review: bool
    reason: str | None = None


class SourceQualityGateService:
    LOWER_COURT_TYPES = {
        "lower_court_record",
        "order_sheet_bundle",
        "mixed_lower_court_record",
    }

    def decide(self, document_type: str | None) -> SourceQualityDecision:
        if not document_type:
            return SourceQualityDecision(
                source_type="unknown",
                allow_direct_submit=False,
                require_operator_review=True,
                reason="unknown_document_source_requires_review",
            )

        normalized = document_type.strip().lower()

        if normalized in self.LOWER_COURT_TYPES:
            return SourceQualityDecision(
                source_type=normalized,
                allow_direct_submit=False,
                require_operator_review=True,
                reason="lower_court_source_requires_operator_review",
            )

        if normalized in {"filing_form_or_mixed", "hc_filing", "high_court_filing"}:
            return SourceQualityDecision(
                source_type=normalized,
                allow_direct_submit=True,
                require_operator_review=False,
                reason=None,
            )

        return SourceQualityDecision(
            source_type=normalized,
            allow_direct_submit=False,
            require_operator_review=True,
            reason="unsupported_document_source_requires_review",
        )
