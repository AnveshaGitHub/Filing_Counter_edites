from __future__ import annotations

import uuid

from app.schemas.efiling_fetch import EFilingFetchRequest, EFilingFetchResponse


class EFilingFetchService:
    """Safe adapter shell for future real e-filing backend integration."""

    def fetch_by_provisional(self, payload: EFilingFetchRequest) -> EFilingFetchResponse:
        application_id = str(uuid.uuid4())
        diary_suffix = abs(hash(f"{payload.provisional_no}-{payload.provisional_year}")) % 10000000

        return EFilingFetchResponse(
            source="efiling_stub",
            document_id=None,
            application_id=application_id,
            diary_no=f"DRY-{payload.provisional_year}-{diary_suffix:07d}",
            provisional_no=payload.provisional_no,
            provisional_year=payload.provisional_year,
            status="stub_ready",
            message="Real e-filing backend not connected yet",
        )
