from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.filing.routed_region_extractor_service import (
    FIELD_GROUP_TO_REGION,
    RoutedRegionExtractorService,
)

router = APIRouter(prefix="/region-debug", tags=["region-debug"])


@router.get("/{document_id}")
def get_regions(document_id: int, db: Session = Depends(get_db)):
    return RoutedRegionExtractorService(db).get_regions(document_id)


@router.get("/{document_id}/{field_group}")
def get_region_for_group(
    document_id: int,
    field_group: str,
    db: Session = Depends(get_db),
):
    if field_group not in FIELD_GROUP_TO_REGION:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown_field_group",
                "allowed": list(FIELD_GROUP_TO_REGION.keys()),
            },
        )

    return RoutedRegionExtractorService(db).get_region_for_group(
        document_id=document_id,
        field_group=field_group,
    )


@router.post("/{document_id}/rebuild")
def rebuild_regions(document_id: int, db: Session = Depends(get_db)):
    return RoutedRegionExtractorService(db).build_regions(document_id)
