from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.benchmark import BenchmarkEvaluationResponse, GoldDraftResponse
from app.services.filing.benchmark_service import BenchmarkService

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


@router.get("/gold-files")
def list_gold_files(db: Session = Depends(get_db)):
    return {"items": BenchmarkService(db).list_gold_files()}


@router.post("/{document_id}/generate-gold-draft", response_model=GoldDraftResponse)
def generate_gold_draft(
    document_id: int,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    try:
        return BenchmarkService(db).generate_gold_draft(document_id=document_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{document_id}/evaluate", response_model=BenchmarkEvaluationResponse)
def evaluate_document(document_id: int, db: Session = Depends(get_db)):
    return BenchmarkService(db).evaluate(document_id)


@router.get("/{document_id}/latest", response_model=BenchmarkEvaluationResponse)
def get_latest_benchmark(document_id: int, db: Session = Depends(get_db)):
    result = BenchmarkService(db).latest(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="benchmark_result_not_found")
    return result
