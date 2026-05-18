from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.filing_review import CreateReviewSessionRequest, ReviewSessionResponse
from app.services.filing.filing_review_service import FilingReviewService

router = APIRouter(prefix="/filing-review", tags=["filing-review"])


@router.post("/{document_id}", response_model=ReviewSessionResponse)
def create_review_session(
    document_id: int,
    payload: CreateReviewSessionRequest,
    db: Session = Depends(get_db),
):
    service = FilingReviewService(db)
    return service.create_review_session(document_id=document_id, payload=payload)


@router.get("/{document_id}", response_model=ReviewSessionResponse)
def get_latest_review_session(
    document_id: int,
    db: Session = Depends(get_db),
):
    service = FilingReviewService(db)
    result = service.get_latest_review_session(document_id=document_id)
    if not result:
        raise HTTPException(status_code=404, detail="No review session found")
    return result
