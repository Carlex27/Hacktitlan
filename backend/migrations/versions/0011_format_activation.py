"""Immutable activated versions and reviewed validation examples."""
from alembic import op
import sqlalchemy as sa

revision = "0011_format_activation"
down_revision = "0010_certificate_formats"
branch_labels = depends_on = None


def upgrade():
    op.drop_constraint("draft_only", "certificate_format_versions", type_="check")
    op.create_check_constraint("valid_format_status", "certificate_format_versions", "status IN ('draft','active','retired')")
    op.create_index("uq_format_active_version", "certificate_format_versions", ["format_id"], unique=True,
                    postgresql_where=sa.text("status = 'active'"))
    op.add_column("certificate_format_versions", sa.Column("lifecycle_json", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("certificate_format_tests", sa.Column("reviewed_by", sa.String(200)))
    op.add_column("certificate_format_tests", sa.Column("review_reason", sa.String(4000)))


def downgrade():
    # Refuse to silently erase activation history.
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM certificate_format_versions WHERE status <> 'draft') THEN RAISE EXCEPTION 'Retain activated format history: downgrade refused'; END IF; END $$;")
    op.drop_column("certificate_format_tests", "review_reason")
    op.drop_column("certificate_format_tests", "reviewed_by")
    op.drop_column("certificate_format_versions", "lifecycle_json")
    op.drop_index("uq_format_active_version", table_name="certificate_format_versions")
    op.drop_constraint("valid_format_status", "certificate_format_versions", type_="check")
    op.create_check_constraint("draft_only", "certificate_format_versions", "status = 'draft'")
