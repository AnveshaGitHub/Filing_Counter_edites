from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.extraction_feedback import ExtractionFeedback
from app.schemas.filing_extraction import ExtractionFeedbackRequest


class FilingFeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save_feedback(self, document_id: int, extraction_job_id: int, payload: ExtractionFeedbackRequest) -> int:
        count = 0
        for item in payload.items:
            row = ExtractionFeedback(
                extraction_job_id=extraction_job_id,
                document_id=document_id,
                field_key=item.field_key,
                system_value=item.system_value,
                user_value=item.user_value,
                correction_type=item.correction_type,
                corrected_by=item.corrected_by,
            )
            self.db.add(row)
            count += 1
        self.db.commit()
        return count
