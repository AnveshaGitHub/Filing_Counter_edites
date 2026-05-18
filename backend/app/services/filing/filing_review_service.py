from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.reviewed_filing_session import ReviewedFilingSession
from app.models.reviewed_filing_field import ReviewedFilingField
from app.schemas.filing_review import (
    CreateReviewSessionRequest,
    ReviewSessionResponse,
    ReviewSessionSummary,
    ReviewedFieldResponse,
)


class FilingReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_review_session(
        self, document_id: int, payload: CreateReviewSessionRequest
    ) -> ReviewSessionResponse:
        session = ReviewedFilingSession(
            document_id=document_id,
            extraction_job_id=payload.extraction_job_id,
            reviewed_by=payload.reviewed_by,
            status=payload.status,
            submit_ready=payload.submit_ready,
            notes=payload.notes,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        fields: list[ReviewedFilingField] = []
        for item in payload.fields:
            row = ReviewedFilingField(
                reviewed_session_id=session.id,
                document_id=document_id,
                extraction_job_id=payload.extraction_job_id,
                field_key=item.field_key,
                field_label=item.field_label,
                system_value=item.system_value,
                reviewed_value=item.reviewed_value,
                confidence=item.confidence,
                action_taken=item.action_taken,
                evidence_text=item.evidence_text,
                source_type=item.source_type,
            )
            self.db.add(row)
            fields.append(row)

        self.db.commit()

        return ReviewSessionResponse(
            session=ReviewSessionSummary(
                reviewed_session_id=session.id,
                document_id=session.document_id,
                extraction_job_id=session.extraction_job_id,
                reviewed_by=session.reviewed_by,
                status=session.status,
                submit_ready=session.submit_ready,
                notes=session.notes,
                created_at=session.created_at,
                updated_at=session.updated_at,
            ),
            fields=[
                ReviewedFieldResponse(
                    field_key=f.field_key,
                    field_label=f.field_label,
                    system_value=f.system_value,
                    reviewed_value=f.reviewed_value,
                    confidence=f.confidence,
                    action_taken=f.action_taken,
                    evidence_text=f.evidence_text,
                    source_type=f.source_type,
                )
                for f in fields
            ],
        )

    def get_latest_review_session(self, document_id: int) -> ReviewSessionResponse | None:
        session = (
            self.db.query(ReviewedFilingSession)
            .filter(ReviewedFilingSession.document_id == document_id)
            .order_by(ReviewedFilingSession.id.desc())
            .first()
        )
        if not session:
            return None

        fields = (
            self.db.query(ReviewedFilingField)
            .filter(ReviewedFilingField.reviewed_session_id == session.id)
            .order_by(ReviewedFilingField.id.asc())
            .all()
        )

        return ReviewSessionResponse(
            session=ReviewSessionSummary(
                reviewed_session_id=session.id,
                document_id=session.document_id,
                extraction_job_id=session.extraction_job_id,
                reviewed_by=session.reviewed_by,
                status=session.status,
                submit_ready=session.submit_ready,
                notes=session.notes,
                created_at=session.created_at,
                updated_at=session.updated_at,
            ),
            fields=[
                ReviewedFieldResponse(
                    field_key=f.field_key,
                    field_label=f.field_label,
                    system_value=f.system_value,
                    reviewed_value=f.reviewed_value,
                    confidence=f.confidence,
                    action_taken=f.action_taken,
                    evidence_text=f.evidence_text,
                    source_type=f.source_type,
                )
                for f in fields
            ],
        )
