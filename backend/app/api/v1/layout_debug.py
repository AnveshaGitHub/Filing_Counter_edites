from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.filing.candidate_persistence_service import CandidatePersistenceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/layout-debug", tags=["layout-debug"])


@router.get("/{document_id}/pages")
def list_layout_pages(document_id: int, db: Session = Depends(get_db)):
    rows = _load_pages(db, document_id)

    return {
        "document_id": document_id,
        "pages": [
            {
                "page_no": getattr(r, "page_no", None),
                "has_ocr_text": bool(getattr(r, "ocr_text", None)),
                "has_ocr_words_json": bool(getattr(r, "ocr_words_json", None)),
                "has_ocr_lines_json": bool(getattr(r, "ocr_lines_json", None)),
                "has_page_regions_json": bool(getattr(r, "page_regions_json", None)),
                "ocr_avg_confidence": getattr(r, "ocr_avg_confidence", None),
                "text_preview": (getattr(r, "ocr_text", "") or "")[:220],
            }
            for r in rows
        ],
    }


@router.get("/{document_id}/page/{page_no}")
def get_layout_page(document_id: int, page_no: int, db: Session = Depends(get_db)):
    rows = _load_pages(db, document_id)
    row = next((r for r in rows if int(getattr(r, "page_no", 0)) == page_no), None)

    if not row:
        raise HTTPException(status_code=404, detail="page_not_found")

    return {
        "document_id": document_id,
        "page_no": page_no,
        "ocr_text": getattr(row, "ocr_text", None),
        "ocr_words": _json(getattr(row, "ocr_words_json", None)),
        "ocr_lines": _json(getattr(row, "ocr_lines_json", None)),
        "page_regions": _json(getattr(row, "page_regions_json", None)),
        "ocr_avg_confidence": getattr(row, "ocr_avg_confidence", None),
    }


@router.get("/{document_id}/candidates")
def get_extracted_candidates(document_id: int, db: Session = Depends(get_db)):
    return {
        "document_id": document_id,
        "candidates": CandidatePersistenceService(db).list_candidates(document_id),
    }


def _load_pages(db: Session, document_id: int) -> list[Any]:
    try:
        from app.models.local_test_document_page import LocalTestDocumentPage

        return (
            db.query(LocalTestDocumentPage)
            .filter(LocalTestDocumentPage.document_id == document_id)
            .order_by(LocalTestDocumentPage.page_no.asc())
            .all()
        )
    except Exception:
        db.rollback()
        logger.exception("[LAYOUT DEBUG] page load failed")
        return []


def _json(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []
