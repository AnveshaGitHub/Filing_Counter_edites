from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.db.session import get_db
from app.schemas.local_test_document import LocalTestDocumentResponse
from app.schemas.filing_extraction import ExtractionRunRequest, ExtractionResponse
from app.services.filing.clean_ocr_debug_service import CleanOcrDebugService
from app.services.filing.local_test_document_service import LocalTestDocumentService
from app.services.filing.filing_extraction_service import FilingExtractionService
from app.services.filing.extraction_lock_service import ExtractionLockService
from app.services.filing.extraction_checkpoint_report_service import ExtractionCheckpointReportService

router = APIRouter(prefix="/test-documents", tags=["test-documents"])


@router.post("/upload", response_model=LocalTestDocumentResponse)
async def upload_test_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty_file")

    service = LocalTestDocumentService(db)
    row = service.create_uploaded_document(
        original_filename=file.filename or "uploaded.pdf",
        content=content,
    )
    return row


@router.post("/{document_id}/process")
def process_test_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    service = LocalTestDocumentService(db)
    try:
        return service.process_document(document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{document_id}", response_model=LocalTestDocumentResponse)
def get_test_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    service = LocalTestDocumentService(db)
    row = service.get_document(document_id=document_id)
    if not row:
        raise HTTPException(status_code=404, detail="local_test_document_not_found")
    return row


@router.get("/{document_id}/ocr-pdf")
def download_test_document_ocr_pdf(
    document_id: int,
    db: Session = Depends(get_db),
):
    service = LocalTestDocumentService(db)
    try:
        content, filename = service.build_ocr_pdf_file(document_id=document_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "local_test_document_not_found" else 400
        raise HTTPException(status_code=status_code, detail=detail)

    quoted_filename = quote(filename)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}",
        },
    )


@router.get("/{document_id}/clean-ocr-debug")
def download_test_document_clean_ocr_debug(
    document_id: int,
    db: Session = Depends(get_db),
):
    test_service = LocalTestDocumentService(db)
    row = test_service.get_document(document_id=document_id)
    if not row:
        raise HTTPException(status_code=404, detail="local_test_document_not_found")

    try:
        payload = CleanOcrDebugService(db).build_debug_payload(document_id=document_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    base_name = quote(f"{document_id}_{row.original_filename.rsplit('.', 1)[0]}_clean_ocr_debug.json")
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{base_name}",
        },
    )


@router.get("/{document_id}/checkpoint-report")
def download_test_document_checkpoint_report(
    document_id: int,
    refresh_candidates: bool = True,
    db: Session = Depends(get_db),
):
    try:
        content, filename = ExtractionCheckpointReportService(db).build_pdf(
            document_id=document_id,
            refresh_candidates=refresh_candidates,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if detail == "local_test_document_not_found" else 400
        raise HTTPException(status_code=status_code, detail=detail)

    quoted_filename = quote(filename)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}",
        },
    )


@router.post("/{document_id}/run-extraction", response_model=ExtractionResponse)
def run_test_document_extraction(
    document_id: int,
    payload: ExtractionRunRequest,
    db: Session = Depends(get_db),
):
    test_service = LocalTestDocumentService(db)
    row = test_service.get_document(document_id=document_id)
    if not row:
        raise HTTPException(status_code=404, detail="local_test_document_not_found")
    if row.status != "processed":
        raise HTTPException(status_code=400, detail="local_test_document_not_processed")
    if not test_service.ensure_main_document_stub(document_id=document_id):
        raise HTTPException(status_code=500, detail="unable_to_prepare_local_test_document_stub")

    lock_service = ExtractionLockService(db)
    locked, reason = lock_service.acquire_lock(
        document_id=document_id,
        locked_by=payload.triggered_by,
        reason="local_test_extraction",
    )
    if not locked:
        raise HTTPException(status_code=409, detail=reason or "document_locked")

    try:
        extraction_service = FilingExtractionService(db)
        safe_payload = ExtractionRunRequest(
            triggered_by=payload.triggered_by,
            run_async=False,
            force_recompute=payload.force_recompute,
            form_type=payload.form_type,
        )
        return extraction_service.run_sync(document_id=document_id, payload=safe_payload)
    finally:
        lock_service.release_lock(document_id=document_id)
