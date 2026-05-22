from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.filing.field_page_router_service import FIELD_ALIASES, FIELD_RULES, FieldPageRouterService

router = APIRouter(prefix="/field-router-debug", tags=["field-router-debug"])


@router.get("/{document_id}")
def get_field_routes(document_id: int, db: Session = Depends(get_db)):
    return FieldPageRouterService(db).get_routes(document_id)


@router.get("/{document_id}/{field_key}")
def get_field_route_for_key(
    document_id: int,
    field_key: str,
    db: Session = Depends(get_db),
):
    if field_key not in FIELD_RULES and field_key not in FIELD_ALIASES:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown_field_key",
                "allowed": [*FIELD_RULES.keys(), *FIELD_ALIASES.keys()],
            },
        )

    return FieldPageRouterService(db).get_route_for_field(
        document_id=document_id,
        field_key=field_key,
    )


@router.post("/{document_id}/rebuild")
def rebuild_field_routes(document_id: int, db: Session = Depends(get_db)):
    return FieldPageRouterService(db).build_routes(document_id)
