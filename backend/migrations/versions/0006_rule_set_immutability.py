"""Prevent mutation of approved or retired rule sets.

Revision ID: 0006_rule_set_immutability
Revises: 0005_normalization_jobs
"""

from alembic import op


revision = "0006_rule_set_immutability"
down_revision = "0005_normalization_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION prevent_immutable_rule_set_update() RETURNS trigger AS $$
        BEGIN
            IF OLD.status IN ('approved', 'retired') AND (
                NEW.name IS DISTINCT FROM OLD.name OR
                NEW.version IS DISTINCT FROM OLD.version OR
                NEW.source_hash IS DISTINCT FROM OLD.source_hash OR
                NEW.valid_from IS DISTINCT FROM OLD.valid_from OR
                NEW.valid_to IS DISTINCT FROM OLD.valid_to OR
                NEW.manifest_json IS DISTINCT FROM OLD.manifest_json
            ) THEN
                RAISE EXCEPTION 'approved or retired rule sets are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_rule_sets_immutable
        BEFORE UPDATE ON rule_sets
        FOR EACH ROW EXECUTE FUNCTION prevent_immutable_rule_set_update();
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_rule_sets_immutable ON rule_sets;
        DROP FUNCTION IF EXISTS prevent_immutable_rule_set_update();
    """)
