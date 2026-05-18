from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.filing_payload import FilingPayloadResponse
from app.services.filing.filing_payload_builder_service import FilingPayloadBuilderService

router = APIRouter(prefix="/filing-payload", tags=["filing-payload"])


@router.get("/{document_id}", response_model=FilingPayloadResponse)
def get_filing_payload(
    document_id: int,
    db: Session = Depends(get_db),
):
    service = FilingPayloadBuilderService(db)
    return service.get_filing_payload(document_id=document_id)
