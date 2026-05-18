"""add filing extraction tables

Revision ID: 20260416_01
Revises:
Create Date: 2026-04-16 14:35:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260416_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("form_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("extractor_version", sa.String(length=50), nullable=False),
        sa.Column("triggered_by", sa.String(length=255), nullable=True),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_extraction_jobs_id", "extraction_jobs", ["id"])
    op.create_index("ix_extraction_jobs_document_id", "extraction_jobs", ["document_id"])

    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("extraction_job_id", sa.Integer(), sa.ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_key", sa.String(length=100), nullable=False),
        sa.Column("field_label", sa.String(length=255), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_page_from", sa.Integer(), nullable=True),
        sa.Column("source_page_to", sa.Integer(), nullable=True),
        sa.Column("source_chunk_id", sa.String(length=255), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_extracted_fields_id", "extracted_fields", ["id"])
    op.create_index("ix_extracted_fields_extraction_job_id", "extracted_fields", ["extraction_job_id"])
    op.create_index("ix_extracted_fields_document_id", "extracted_fields", ["document_id"])
    op.create_index("ix_extracted_fields_field_key", "extracted_fields", ["field_key"])

    op.create_table(
        "extraction_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("extraction_job_id", sa.Integer(), sa.ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_key", sa.String(length=100), nullable=False),
        sa.Column("system_value", sa.Text(), nullable=True),
        sa.Column("user_value", sa.Text(), nullable=False),
        sa.Column("correction_type", sa.String(length=50), nullable=False),
        sa.Column("corrected_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_extraction_feedback_id", "extraction_feedback", ["id"])
    op.create_index("ix_extraction_feedback_extraction_job_id", "extraction_feedback", ["extraction_job_id"])
    op.create_index("ix_extraction_feedback_document_id", "extraction_feedback", ["document_id"])
    op.create_index("ix_extraction_feedback_field_key", "extraction_feedback", ["field_key"])


def downgrade() -> None:
    op.drop_index("ix_extraction_feedback_field_key", table_name="extraction_feedback")
    op.drop_index("ix_extraction_feedback_document_id", table_name="extraction_feedback")
    op.drop_index("ix_extraction_feedback_extraction_job_id", table_name="extraction_feedback")
    op.drop_index("ix_extraction_feedback_id", table_name="extraction_feedback")
    op.drop_table("extraction_feedback")

    op.drop_index("ix_extracted_fields_field_key", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_document_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_extraction_job_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_id", table_name="extracted_fields")
    op.drop_table("extracted_fields")

    op.drop_index("ix_extraction_jobs_document_id", table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_id", table_name="extraction_jobs")
    op.drop_table("extraction_jobs")
