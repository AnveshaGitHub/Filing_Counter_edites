from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.page_classification import DocumentClassificationResult
from app.services.filing.page_classifier_service import PageClassifierService

router = APIRouter(tags=["page-classification"])


@router.get("/documents/{document_id}/page-classification", response_model=DocumentClassificationResult)
def get_page_classification(document_id: int, db: Session = Depends(get_db)):
    service = PageClassifierService(db)
    return service.classify_document_from_db(document_id)
