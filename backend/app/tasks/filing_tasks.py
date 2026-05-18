from __future__ import annotations

from datetime import datetime

from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.extraction_job import ExtractionJob
from app.services.filing.filing_extraction_service import FilingExtractionService
from app.services.filing.extraction_lock_service import ExtractionLockService


@celery_app.task(name="filing.run_filing_extraction")
def run_filing_extraction_task(document_id: int, extraction_job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(ExtractionJob).filter(ExtractionJob.id == extraction_job_id).first()
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        service = FilingExtractionService(db)
        service.run_existing_job(extraction_job_id=extraction_job_id)

    except Exception as exc:
        job = db.query(ExtractionJob).filter(ExtractionJob.id == extraction_job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            db.commit()
        raise
    finally:
        try:
            lock_service = ExtractionLockService(db)
            lock_service.release_lock(document_id=document_id)
        except Exception:
            pass
        db.close()
