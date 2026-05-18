from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.extraction_feedback import ExtractionFeedback


class FeedbackRerankService:
    """
    Phase 4:
    simple feedback memory hook.
    Future phase can use this for source/alias reweighting.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_field_feedback_counts(self, field_key: str) -> dict[str, int]:
        rows = (
            self.db.query(ExtractionFeedback)
            .filter(ExtractionFeedback.field_key == field_key)
            .all()
        )

        counts: dict[str, int] = {}
        for row in rows:
            key = row.user_value.strip().lower()
            counts[key] = counts.get(key, 0) + 1
        return counts

    def adjust_candidate_scores(self, field_key: str, candidates: list[dict]) -> list[dict]:
        feedback_counts = self.get_field_feedback_counts(field_key)
        if not feedback_counts:
            return candidates

        adjusted: list[dict] = []
        for c in candidates:
            value_key = str(c.get("normalized_value") or c.get("value") or "").strip().lower()
            boost = min(0.03, feedback_counts.get(value_key, 0) * 0.005)
            item = dict(c)
            item["confidence"] = min(0.99, float(item.get("confidence", 0.0)) + boost)
            adjusted.append(item)

        adjusted.sort(key=lambda x: float(x.get("confidence", 0.0)), reverse=True)
        return adjusted
