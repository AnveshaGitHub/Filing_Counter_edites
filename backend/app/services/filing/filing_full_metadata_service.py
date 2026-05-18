from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.filing_full_metadata import FilingFullMetadata


class FilingFullMetadataService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_table(self) -> None:
        self.db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS filing_full_metadata (
                    document_id INTEGER PRIMARY KEY,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        self.db.commit()

    def get(self, document_id: int) -> FilingFullMetadata:
        self.ensure_table()
        row = self.db.execute(
            text("SELECT metadata_json FROM filing_full_metadata WHERE document_id = :document_id"),
            {"document_id": document_id},
        ).fetchone()

        if not row:
            return FilingFullMetadata()

        try:
            return FilingFullMetadata.model_validate(json.loads(row[0]))
        except (TypeError, ValueError):
            return FilingFullMetadata()

    def save(self, document_id: int, metadata: FilingFullMetadata) -> FilingFullMetadata:
        self.ensure_table()
        data = metadata.model_dump()
        self.db.execute(
            text(
                """
                INSERT INTO filing_full_metadata(document_id, metadata_json, updated_at)
                VALUES (:document_id, :metadata_json, CURRENT_TIMESTAMP)
                ON CONFLICT(document_id)
                DO UPDATE SET
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "document_id": document_id,
                "metadata_json": json.dumps(data, ensure_ascii=False),
            },
        )
        self.db.commit()
        return metadata

    def get_payload_metadata(self, document_id: int) -> dict[str, Any]:
        metadata = self.get(document_id)
        return metadata.model_dump(exclude_none=True, exclude_defaults=True)
