"""add filing review and lock tables

Revision ID: 20260418_01
Revises: 20260416_01
Create Date: 2026-04-18 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260418_01"
down_revision = "20260416_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_locks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("lock_reason", sa.String(length=100), nullable=False),
        sa.Column("locked_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index("ix_extraction_locks_id", "extraction_locks", ["id"])
    op.create_index("ix_extraction_locks_document_id", "extraction_locks", ["document_id"])

    op.create_table(
        "reviewed_filing_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extraction_job_id", sa.Integer(), sa.ForeignKey("extraction_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("submit_ready", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_reviewed_filing_sessions_id", "reviewed_filing_sessions", ["id"])
    op.create_index("ix_reviewed_filing_sessions_document_id", "reviewed_filing_sessions", ["document_id"])
    op.create_index("ix_reviewed_filing_sessions_extraction_job_id", "reviewed_filing_sessions", ["extraction_job_id"])

    op.create_table(
        "reviewed_filing_fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reviewed_session_id", sa.Integer(), sa.ForeignKey("reviewed_filing_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extraction_job_id", sa.Integer(), sa.ForeignKey("extraction_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("field_key", sa.String(length=100), nullable=False),
        sa.Column("field_label", sa.String(length=255), nullable=False),
        sa.Column("system_value", sa.Text(), nullable=True),
        sa.Column("reviewed_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("action_taken", sa.String(length=50), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_reviewed_filing_fields_id", "reviewed_filing_fields", ["id"])
    op.create_index("ix_reviewed_filing_fields_reviewed_session_id", "reviewed_filing_fields", ["reviewed_session_id"])
    op.create_index("ix_reviewed_filing_fields_document_id", "reviewed_filing_fields", ["document_id"])
    op.create_index("ix_reviewed_filing_fields_extraction_job_id", "reviewed_filing_fields", ["extraction_job_id"])
    op.create_index("ix_reviewed_filing_fields_field_key", "reviewed_filing_fields", ["field_key"])


def downgrade() -> None:
    op.drop_index("ix_reviewed_filing_fields_field_key", table_name="reviewed_filing_fields")
    op.drop_index("ix_reviewed_filing_fields_extraction_job_id", table_name="reviewed_filing_fields")
    op.drop_index("ix_reviewed_filing_fields_document_id", table_name="reviewed_filing_fields")
    op.drop_index("ix_reviewed_filing_fields_reviewed_session_id", table_name="reviewed_filing_fields")
    op.drop_index("ix_reviewed_filing_fields_id", table_name="reviewed_filing_fields")
    op.drop_table("reviewed_filing_fields")

    op.drop_index("ix_reviewed_filing_sessions_extraction_job_id", table_name="reviewed_filing_sessions")
    op.drop_index("ix_reviewed_filing_sessions_document_id", table_name="reviewed_filing_sessions")
    op.drop_index("ix_reviewed_filing_sessions_id", table_name="reviewed_filing_sessions")
    op.drop_table("reviewed_filing_sessions")

    op.drop_index("ix_extraction_locks_document_id", table_name="extraction_locks")
    op.drop_index("ix_extraction_locks_id", table_name="extraction_locks")
    op.drop_table("extraction_locks")
