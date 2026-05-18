"""add local test document tables

Revision ID: 20260421_01
Revises: 20260418_01
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_01"
down_revision = "20260418_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "local_test_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("stored_path", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_local_test_documents_id", "local_test_documents", ["id"])

    op.create_table(
        "local_test_document_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("local_test_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_local_test_document_pages_id", "local_test_document_pages", ["id"])
    op.create_index("ix_local_test_document_pages_document_id", "local_test_document_pages", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_local_test_document_pages_document_id", table_name="local_test_document_pages")
    op.drop_index("ix_local_test_document_pages_id", table_name="local_test_document_pages")
    op.drop_table("local_test_document_pages")

    op.drop_index("ix_local_test_documents_id", table_name="local_test_documents")
    op.drop_table("local_test_documents")
