from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.filing.candidate_persistence_service import CandidatePersistenceService
from app.services.filing.filing_candidate_pipeline_service import FilingCandidatePipelineService


router = APIRouter(prefix="/filing-candidates", tags=["filing-candidates"])


@router.post("/{document_id}/build")
def build_filing_candidates(document_id: int, db: Session = Depends(get_db)):
    return FilingCandidatePipelineService(db).build_candidates(document_id)


@router.get("/{document_id}")
def list_filing_candidates(document_id: int, db: Session = Depends(get_db)):
    return {
        "document_id": document_id,
        "candidates": CandidatePersistenceService(db).list_candidates(document_id),
        "merged_top": FilingCandidatePipelineService(db).rerank(document_id),
    }
