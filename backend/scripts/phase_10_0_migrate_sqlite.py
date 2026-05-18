from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "backend" / "filing_counter.db"


def column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    page_table = "local_test_document_pages"

    for column, ddl in [
        ("ocr_words_json", "TEXT"),
        ("ocr_lines_json", "TEXT"),
        ("page_regions_json", "TEXT"),
        ("ocr_avg_confidence", "REAL"),
    ]:
        if not column_exists(cur, page_table, column):
            print(f"Adding {page_table}.{column}")
            cur.execute(f"ALTER TABLE {page_table} ADD COLUMN {column} {ddl}")

    if not table_exists(cur, "extracted_field_candidates"):
        print("Creating extracted_field_candidates")
        cur.execute(
            """
            CREATE TABLE extracted_field_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                field_key TEXT NOT NULL,
                value TEXT,
                normalized_value TEXT,
                confidence REAL,
                status TEXT,
                source_page INTEGER,
                page_type TEXT,
                bbox_json TEXT,
                evidence_text TEXT,
                extractor TEXT,
                validation_note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute("CREATE INDEX ix_efc_document_id ON extracted_field_candidates(document_id)")
        cur.execute("CREATE INDEX ix_efc_field_key ON extracted_field_candidates(field_key)")

    conn.commit()
    conn.close()
    print("Phase 10.0 SQLite migration complete.")


if __name__ == "__main__":
    main()
