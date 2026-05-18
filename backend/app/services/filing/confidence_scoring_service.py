from __future__ import annotations

from app.schemas.filing_fields import FilingFieldDefinition


class ConfidenceScoringService:
    SOURCE_BONUS = {
        "index_section": 0.03,
        "regex": 0.01,
        "rule": 0.01,
        "vector_retrieval": -0.03,
        "llm": -0.02,
        "system": -0.12,
    }

    def adjust_confidence(
        self,
        base_confidence: float,
        source_type: str | None,
        candidate_count: int,
        has_conflict: bool,
        validation_note: str | None = None,
        page_type_multiplier: float | None = None,
    ) -> float:
        score = base_confidence + self.SOURCE_BONUS.get(source_type or "system", 0.0)

        if page_type_multiplier is not None:
            if page_type_multiplier >= 0.9:
                score += 0.03
            elif page_type_multiplier <= 0.6:
                score -= 0.07

        if candidate_count == 1:
            score += 0.01
        elif candidate_count >= 3:
            score -= 0.06

        if has_conflict:
            score -= 0.10

        if validation_note:
            score -= 0.12

        return max(0.0, min(0.99, score))

    def classify(self, field_def: FilingFieldDefinition, confidence: float, is_valid: bool) -> str:
        if not is_valid:
            return "missing"

        if confidence >= field_def.auto_fill_threshold:
            return "confirmed"

        if confidence >= field_def.suggestion_threshold:
            return "suggested"

        return "missing"
