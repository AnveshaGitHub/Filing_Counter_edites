from __future__ import annotations

from pydantic import BaseModel, Field


class EFilingFetchRequest(BaseModel):
    provisional_no: str = Field(..., min_length=1)
    provisional_year: str = Field(..., min_length=4, max_length=4)


class EFilingFetchResponse(BaseModel):
    source: str
    document_id: int | None = None
    application_id: str | None = None
    diary_no: str | None = None
    provisional_no: str
    provisional_year: str
    status: str
    message: str | None = None
