from __future__ import annotations

from fastapi import APIRouter

from app.schemas.efiling_fetch import EFilingFetchRequest, EFilingFetchResponse
from app.services.filing.efiling_fetch_service import EFilingFetchService

router = APIRouter(prefix="/efiling", tags=["efiling"])


@router.post("/fetch", response_model=EFilingFetchResponse)
def fetch_efiling_data(payload: EFilingFetchRequest):
    service = EFilingFetchService()
    return service.fetch_by_provisional(payload)
