"""Draft templates, prepared layouts and isolated preview jobs."""
from alembic import op
import sqlalchemy as sa

revision = "0010_certificate_formats"
down_revision = "0009_certificate_deletion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("certificate_formats", *timestamps(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False))
    op.create_table("certificate_format_versions", *timestamps(),
        sa.Column("format_id", sa.BigInteger(), sa.ForeignKey("certificate_formats.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("configuration_sha256", sa.String(64), nullable=False),
        sa.Column("person_name", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(4000), nullable=False),
        sa.UniqueConstraint("format_id", "version_number"),
        sa.CheckConstraint("version_number > 0 AND revision > 0", name="positive_revision"),
        sa.CheckConstraint("status = 'draft'", name="draft_only"))
    op.create_index("ix_certificate_format_versions_format_id", "certificate_format_versions", ["format_id"])
    op.create_table("prepared_document_layouts", *timestamps(),
        sa.Column("document_id", sa.BigInteger(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), unique=True),
        sa.Column("document_sha256", sa.String(64), nullable=False),
        sa.Column("layout_json", sa.JSON(), nullable=False))
    op.create_index("ix_prepared_document_layouts_document_id", "prepared_document_layouts", ["document_id"])
    op.create_table("certificate_format_tests", *timestamps(),
        sa.Column("version_id", sa.BigInteger(), sa.ForeignKey("certificate_format_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_id", sa.BigInteger(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("layout_id", sa.BigInteger(), sa.ForeignKey("prepared_document_layouts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), unique=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("configuration_sha256", sa.String(64), nullable=False),
        sa.Column("extractor_sha256", sa.String(64), nullable=False),
        sa.Column("result_json", sa.JSON()))
    for column in ("version_id", "document_id", "layout_id"):
        op.create_index(f"ix_certificate_format_tests_{column}", "certificate_format_tests", [column])
    op.drop_constraint("valid_kind", "jobs", type_="check")
    op.create_check_constraint("valid_kind", "jobs",
                               "kind IN ('extract_document','normalize_document','reclassify',"
                               "'export_xlsx','backup','prepare_layout','test_certificate_format')")
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hacktitlan_app') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON certificate_formats,
                certificate_format_versions, prepared_document_layouts, certificate_format_tests TO hacktitlan_app;
            GRANT USAGE, SELECT ON SEQUENCE certificate_formats_id_seq, certificate_format_versions_id_seq,
                prepared_document_layouts_id_seq, certificate_format_tests_id_seq TO hacktitlan_app;
        END IF;
    END $$;""")


def downgrade() -> None:
    # Downgrade cannot preserve work of kinds unknown to the previous worker.
    op.execute("DELETE FROM jobs WHERE kind IN ('prepare_layout','test_certificate_format')")
    for table in ("certificate_format_tests", "prepared_document_layouts", "certificate_format_versions", "certificate_formats"):
        op.drop_table(table)
    op.drop_constraint("valid_kind", "jobs", type_="check")
    op.create_check_constraint("valid_kind", "jobs",
                               "kind IN ('extract_document','normalize_document','reclassify','export_xlsx','backup')")


def timestamps():
    return (sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
