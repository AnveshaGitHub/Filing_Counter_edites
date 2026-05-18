from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from app.schemas.field_specific_extraction import FieldSpecificCandidate

logger = logging.getLogger(__name__)


class CandidatePersistenceService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self.sqlite_path = Path(__file__).resolve().parents[3] / "filing_counter.db"

    def replace_candidates(
        self,
        document_id: int,
        candidates: Iterable[FieldSpecificCandidate],
    ) -> None:
        candidate_list = list(candidates)

        if self.db is not None:
            try:
                from app.models.extracted_field_candidate import ExtractedFieldCandidate

                self.db.query(ExtractedFieldCandidate).filter(
                    ExtractedFieldCandidate.document_id == document_id
                ).delete()

                for c in candidate_list:
                    self.db.add(
                        ExtractedFieldCandidate(
                            document_id=document_id,
                            field_key=c.field_key,
                            value=c.value,
                            normalized_value=c.normalized_value,
                            confidence=c.confidence,
                            status=c.status,
                            source_page=c.page_no,
                            page_type=c.page_type,
                            bbox_json=None,
                            evidence_text=c.evidence,
                            extractor=c.extractor,
                            validation_note=c.validation_note,
                        )
                    )

                self.db.commit()
                return
            except Exception:
                self.db.rollback()
                logger.exception("[CANDIDATE DB] SQLAlchemy persistence failed, fallback sqlite")

        self._replace_candidates_sqlite(document_id, candidate_list)

    def list_candidates(self, document_id: int) -> list[dict]:
        if self.db is not None:
            try:
                from app.models.extracted_field_candidate import ExtractedFieldCandidate

                rows = (
                    self.db.query(ExtractedFieldCandidate)
                    .filter(ExtractedFieldCandidate.document_id == document_id)
                    .order_by(ExtractedFieldCandidate.confidence.desc())
                    .all()
                )
                return [
                    {
                        "id": r.id,
                        "document_id": r.document_id,
                        "field_key": r.field_key,
                        "value": r.value,
                        "normalized_value": r.normalized_value,
                        "confidence": r.confidence,
                        "status": r.status,
                        "source_page": r.source_page,
                        "page_type": r.page_type,
                        "bbox_json": r.bbox_json,
                        "evidence_text": r.evidence_text,
                        "extractor": r.extractor,
                        "validation_note": r.validation_note,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in rows
                ]
            except Exception:
                if self.db is not None:
                    self.db.rollback()
                logger.exception("[CANDIDATE DB] SQLAlchemy list failed, fallback sqlite")

        return self._list_candidates_sqlite(document_id)

    def _replace_candidates_sqlite(self, document_id: int, candidates: list[FieldSpecificCandidate]) -> None:
        conn = sqlite3.connect(self.sqlite_path)
        cur = conn.cursor()

        cur.execute("DELETE FROM extracted_field_candidates WHERE document_id=?", (document_id,))

        for c in candidates:
            cur.execute(
                """
                INSERT INTO extracted_field_candidates (
                    document_id, field_key, value, normalized_value, confidence, status,
                    source_page, page_type, bbox_json, evidence_text, extractor, validation_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    c.field_key,
                    c.value,
                    c.normalized_value,
                    c.confidence,
                    c.status,
                    c.page_no,
                    c.page_type,
                    None,
                    c.evidence,
                    c.extractor,
                    c.validation_note,
                ),
            )

        conn.commit()
        conn.close()

    def _list_candidates_sqlite(self, document_id: int) -> list[dict]:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        rows = cur.execute(
            """
            SELECT *
            FROM extracted_field_candidates
            WHERE document_id=?
            ORDER BY confidence DESC
            """,
            (document_id,),
        ).fetchall()

        conn.close()
        return [dict(r) for r in rows]
