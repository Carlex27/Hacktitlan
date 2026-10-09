"""Allow the local service role to remove certificate test data."""
from alembic import op

revision = "0009_certificate_deletion"
down_revision = "0008_field_verification"
branch_labels = None
depends_on = None

TABLES = (
    "jobs, documents, mill_certificates, stored_files, exports, extraction_runs, "
    "heats, products, observations, chemical_compositions, classification_runs, "
    "classification_results, classification_candidates, classification_selections, "
    "candidate_factors, decision_steps, evidence_links, corrections, approval_events"
)


def upgrade() -> None:
    op.execute(f"""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hacktitlan_app') THEN
                GRANT DELETE ON {TABLES} TO hacktitlan_app;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute(f"""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hacktitlan_app') THEN
                REVOKE DELETE ON {TABLES} FROM hacktitlan_app;
            END IF;
        END $$;
    """)
