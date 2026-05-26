"""add local page layout OCR fields

Revision ID: 20260526_01
Revises: 20260421_02
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260526_01"
down_revision = "20260421_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "local_test_document_pages",
        sa.Column("ocr_words_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "local_test_document_pages",
        sa.Column("ocr_lines_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "local_test_document_pages",
        sa.Column("page_regions_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "local_test_document_pages",
        sa.Column("ocr_avg_confidence", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("local_test_document_pages", "ocr_avg_confidence")
    op.drop_column("local_test_document_pages", "page_regions_json")
    op.drop_column("local_test_document_pages", "ocr_lines_json")
    op.drop_column("local_test_document_pages", "ocr_words_json")
