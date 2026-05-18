from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.filing_payload import FilingPayloadField, FilingPayloadResponse
from app.services.filing.filing_extraction_service import FilingExtractionService
from app.services.filing.filing_review_service import FilingReviewService


class FilingPayloadService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.extraction_service = FilingExtractionService(db)
        self.review_service = FilingReviewService(db)

    def get_payload(self, document_id: int) -> FilingPayloadResponse | None:
        extraction = self.extraction_service.get_latest_result(document_id=document_id)
        review = self.review_service.get_latest_review_session(document_id=document_id)

        if extraction is None and review is None:
            return None

        grouped: dict[str, Any] = {}
        fields_by_key: dict[str, FilingPayloadField] = {}
        extraction_job_id: int | None = None
        reviewed_session_id: int | None = None
        status = "extracted"

        if extraction is not None:
            extraction_job_id = extraction.job.extraction_job_id
            grouped = extraction.grouped.model_dump() if extraction.grouped else {}
            for f in extraction.fields:
                fields_by_key[f.field_key] = FilingPayloadField(
                    field_key=f.field_key,
                    field_label=f.field_label,
                    value=f.normalized_value or f.value,
                    source=f.evidence.source_type if f.evidence and f.evidence.source_type else "system",
                    confidence=f.confidence,
                    action_taken="accepted" if f.status == "confirmed" else "suggested",
                )

        if review is not None:
            reviewed_session_id = review.session.reviewed_session_id
            status = review.session.status or "reviewed"
            for rf in review.fields:
                existing = fields_by_key.get(rf.field_key)
                fields_by_key[rf.field_key] = FilingPayloadField(
                    field_key=rf.field_key,
                    field_label=rf.field_label or (existing.field_label if existing else rf.field_key),
                    value=rf.reviewed_value if rf.reviewed_value is not None else rf.system_value,
                    source=rf.source_type or (existing.source if existing else "review"),
                    confidence=rf.confidence if rf.confidence is not None else (existing.confidence if existing else None),
                    action_taken=rf.action_taken,
                )

        if review is None and extraction is not None:
            status = extraction.job.status

        return FilingPayloadResponse(
            document_id=document_id,
            extraction_job_id=extraction_job_id,
            reviewed_session_id=reviewed_session_id,
            status=status,
            generated_at=datetime.utcnow(),
            grouped=grouped,
            fields=list(fields_by_key.values()),
        )
