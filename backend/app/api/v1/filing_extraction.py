from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.filing_extraction import ExtractionRunRequest, ExtractionResponse, ExtractionFeedbackRequest
from app.services.filing.filing_extraction_service import FilingExtractionService
from app.services.filing.filing_feedback_service import FilingFeedbackService
from app.services.filing.extraction_lock_service import ExtractionLockService
from app.tasks.filing_tasks import run_filing_extraction_task

router = APIRouter(prefix="/filing-extraction", tags=["filing-extraction"])


@router.post("/{document_id}/run", response_model=ExtractionResponse | dict)
def run_filing_extraction(
    document_id: int,
    payload: ExtractionRunRequest,
    db: Session = Depends(get_db),
):
    lock_service = ExtractionLockService(db)
    locked, reason = lock_service.acquire_lock(
        document_id=document_id,
        locked_by=payload.triggered_by,
        reason="extraction",
    )
    if not locked:
        raise HTTPException(status_code=409, detail=reason or "document_locked")

    try:
        service = FilingExtractionService(db)

        if payload.run_async:
            job = service.create_job(document_id=document_id, payload=payload)
            run_filing_extraction_task.delay(document_id=document_id, extraction_job_id=job.id)
            return {
                "message": "Extraction job queued",
                "document_id": document_id,
                "extraction_job_id": job.id,
                "status": job.status,
            }

        return service.run_sync(document_id=document_id, payload=payload)
    finally:
        if not payload.run_async:
            lock_service.release_lock(document_id=document_id)


@router.get("/{document_id}", response_model=ExtractionResponse)
def get_latest_filing_extraction(document_id: int, db: Session = Depends(get_db)):
    service = FilingExtractionService(db)
    result = service.get_latest_result(document_id=document_id)
    if not result:
        raise HTTPException(status_code=404, detail="No extraction result found")
    return result


@router.post("/{document_id}/{extraction_job_id}/feedback")
def save_filing_feedback(document_id: int, extraction_job_id: int, payload: ExtractionFeedbackRequest, db: Session = Depends(get_db)):
    service = FilingFeedbackService(db)
    saved_count = service.save_feedback(document_id=document_id, extraction_job_id=extraction_job_id, payload=payload)
    return {"message": "Feedback saved successfully", "saved_count": saved_count}
