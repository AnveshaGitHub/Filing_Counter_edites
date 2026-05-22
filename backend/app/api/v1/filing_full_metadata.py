from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.filing_full_metadata import (
    FilingFullMetadata,
    FilingFullMetadataResponse,
)
from app.services.filing.filing_full_metadata_service import FilingFullMetadataService
from app.services.filing.filing_metadata_autofill_service import FilingMetadataAutofillService

router = APIRouter(prefix="/filing-full-metadata", tags=["filing-full-metadata"])


@router.get("/{document_id}", response_model=FilingFullMetadataResponse)
def get_filing_full_metadata(document_id: int, db: Session = Depends(get_db)):
    metadata = FilingFullMetadataService(db).get(document_id)
    return FilingFullMetadataResponse(document_id=document_id, metadata=metadata)


@router.post("/{document_id}", response_model=FilingFullMetadataResponse)
def save_filing_full_metadata(
    document_id: int,
    payload: FilingFullMetadata,
    db: Session = Depends(get_db),
):
    metadata = FilingFullMetadataService(db).save(document_id, payload)
    return FilingFullMetadataResponse(document_id=document_id, metadata=metadata)


@router.post("/{document_id}/autofill/{section}")
def autofill_filing_full_metadata(
    document_id: int,
    section: str,
    db: Session = Depends(get_db),
):
    try:
        return FilingMetadataAutofillService(db).autofill(document_id=document_id, section=section)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
