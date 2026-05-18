from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ecourt_payload import ECourtPreviewResponse
from app.services.filing.ecourt_payload_mapper_service import ECourtPayloadMapperService
from app.services.filing.ecourt_payload_validation_service import ECourtPayloadValidationService

router = APIRouter(prefix="/ecourt-payload", tags=["ecourt-payload"])


@router.get("/{document_id}/official-preview", response_model=ECourtPreviewResponse)
def get_official_ecourt_payload_preview(document_id: int, db: Session = Depends(get_db)):
    payload = ECourtPayloadMapperService(db).build(document_id)
    issues = ECourtPayloadValidationService().validate(payload)
    ready = not any(issue.severity == "error" for issue in issues)

    return ECourtPreviewResponse(
        document_id=document_id,
        ready_for_ecourt=ready,
        issues=issues,
        payload=payload,
    )
