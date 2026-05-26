"""add extracted field candidate table

Revision ID: 20260526_02
Revises: 20260526_01
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260526_02"
down_revision = "20260526_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extracted_field_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("field_key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("page_type", sa.String(length=120), nullable=True),
        sa.Column("bbox_json", sa.Text(), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("extractor", sa.String(length=160), nullable=True),
        sa.Column("validation_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_extracted_field_candidates_id", "extracted_field_candidates", ["id"])
    op.create_index(
        "ix_extracted_field_candidates_document_id",
        "extracted_field_candidates",
        ["document_id"],
    )
    op.create_index(
        "ix_extracted_field_candidates_field_key",
        "extracted_field_candidates",
        ["field_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_extracted_field_candidates_field_key", table_name="extracted_field_candidates")
    op.drop_index("ix_extracted_field_candidates_document_id", table_name="extracted_field_candidates")
    op.drop_index("ix_extracted_field_candidates_id", table_name="extracted_field_candidates")
    op.drop_table("extracted_field_candidates")
