from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.filing_submission import (
    FilingSubmissionPreviewResponse,
    PrepareSubmissionRequest,
    DryRunSubmissionResponse,
)
from app.services.filing.submission_mapping_service import SubmissionMappingService
from app.services.filing.submission_automation_service import SubmissionAutomationService

router = APIRouter(prefix="/filing-submission", tags=["filing-submission"])


@router.get("/{document_id}/preview", response_model=FilingSubmissionPreviewResponse)
def get_submission_preview(
    document_id: int,
    db: Session = Depends(get_db),
):
    service = SubmissionMappingService(db)
    return service.build_submission_preview(document_id=document_id, dry_run=True)


@router.post("/{document_id}/prepare", response_model=FilingSubmissionPreviewResponse)
def prepare_submission(
    document_id: int,
    payload: PrepareSubmissionRequest,
    db: Session = Depends(get_db),
):
    mapping_service = SubmissionMappingService(db)
    preview = mapping_service.build_submission_preview(document_id=document_id, dry_run=payload.dry_run)
    automation_service = SubmissionAutomationService()
    return automation_service.prepare_submission(preview)


@router.post("/{document_id}/dry-run", response_model=DryRunSubmissionResponse)
def dry_run_submission(
    document_id: int,
    payload: PrepareSubmissionRequest,
    db: Session = Depends(get_db),
):
    mapping_service = SubmissionMappingService(db)
    preview = mapping_service.build_submission_preview(document_id=document_id, dry_run=True)

    automation_service = SubmissionAutomationService()
    return automation_service.automate_submission(preview, mode="dry_run" if payload.dry_run else "real_submit")
