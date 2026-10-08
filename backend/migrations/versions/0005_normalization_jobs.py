"""Allow audited normalization jobs.

Revision ID: 0005_normalization_jobs
Revises: 0004_candidate_factors
"""

from alembic import op


revision = "0005_normalization_jobs"
down_revision = "0004_candidate_factors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("valid_kind", "jobs", type_="check")
    op.create_check_constraint(
        "valid_kind",
        "jobs",
        "kind IN ('extract_document','normalize_document','reclassify','export_xlsx','backup')",
    )
    op.drop_index("ix_documents_stored_file_id", table_name="documents")
    op.create_index("ix_documents_stored_file_id", "documents", ["stored_file_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_stored_file_id", table_name="documents")
    op.create_index(
        "ix_documents_stored_file_id", "documents", ["stored_file_id"], unique=True
    )
    op.drop_constraint("valid_kind", "jobs", type_="check")
    op.create_check_constraint(
        "valid_kind",
        "jobs",
        "kind IN ('extract_document','reclassify','export_xlsx','backup')",
    )
