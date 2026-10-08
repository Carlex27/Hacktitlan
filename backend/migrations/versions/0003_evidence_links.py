"""Link decision factors to exact observations and rule sources.

Revision ID: 0003_evidence_links
Revises: 0002_classification_candidates
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_evidence_links"
down_revision = "0002_classification_candidates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("evidence_links"):
        return
    op.create_table(
        "evidence_links",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "decision_step_id", sa.BigInteger(),
            sa.ForeignKey("decision_steps.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "observation_id", sa.BigInteger(),
            sa.ForeignKey("observations.id", ondelete="RESTRICT"),
        ),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("field_path", sa.String(length=500)),
        sa.Column("source_reference_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "decision_step_id", "observation_id", name="uq_evidence_step_observation"
        ),
        sa.CheckConstraint(
            "source_type IN ('observation','rule_source')",
            name="evidence_source_type",
        ),
        sa.CheckConstraint(
            "(source_type = 'observation' AND observation_id IS NOT NULL) OR "
            "(source_type = 'rule_source' AND observation_id IS NULL)",
            name="evidence_source_reference",
        ),
    )
    op.create_index(
        "ix_evidence_links_decision_step_id", "evidence_links", ["decision_step_id"]
    )
    op.create_index(
        "ix_evidence_links_observation_id", "evidence_links", ["observation_id"]
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("evidence_links"):
        op.drop_table("evidence_links")
