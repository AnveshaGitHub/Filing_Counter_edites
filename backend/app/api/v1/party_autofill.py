from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.party_autofill import PartyAutofillResponse
from app.services.filing.strict_party_autofill_service import StrictPartyAutofillService

router = APIRouter(prefix="/party-autofill", tags=["party-autofill"])


@router.post("/{document_id}/petitioner", response_model=PartyAutofillResponse)
def autofill_petitioner(document_id: int, db: Session = Depends(get_db)):
    service = StrictPartyAutofillService(db)
    return service.autofill(document_id=document_id, side="petitioner")


@router.post("/{document_id}/respondent", response_model=PartyAutofillResponse)
def autofill_respondent(document_id: int, db: Session = Depends(get_db)):
    service = StrictPartyAutofillService(db)
    return service.autofill(document_id=document_id, side="respondent")
