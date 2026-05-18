"""add local test document page extraction fields

Revision ID: 20260421_02
Revises: 20260421_01
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_02"
down_revision = "20260421_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "local_test_document_pages",
        sa.Column("extraction_method", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "local_test_document_pages",
        sa.Column("text_length", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("local_test_document_pages", "text_length")
    op.drop_column("local_test_document_pages", "extraction_method")
