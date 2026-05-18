from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class LocalTestDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_path: str
    status: str
    source: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
