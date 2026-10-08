"""Add candidate-specific factors and evidence ownership.

Revision ID: 0004_candidate_factors
Revises: 0003_evidence_links
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_candidate_factors"
down_revision = "0003_evidence_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("candidate_factors"):
        op.create_table(
            "candidate_factors",
            sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
            sa.Column(
                "candidate_id", sa.BigInteger(),
                sa.ForeignKey("classification_candidates.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("rule_code", sa.String(length=200), nullable=False),
            sa.Column("outcome", sa.String(length=30), nullable=False),
            sa.Column("operator", sa.String(length=100)),
            sa.Column("expected_json", sa.JSON(), nullable=False),
            sa.Column("observed_json", sa.JSON(), nullable=False),
            sa.Column("unit", sa.String(length=50)),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("required_for_selection", sa.Boolean(), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "candidate_id", "sequence", name="uq_factor_candidate_sequence"
            ),
            sa.CheckConstraint("sequence >= 1", name="candidate_factor_sequence_positive"),
            sa.CheckConstraint(
                "outcome IN ('matched','not_matched','missing','ambiguous','unknown','conflict')",
                name="candidate_factor_outcome",
            ),
        )
        op.create_index(
            "ix_candidate_factors_candidate_id", "candidate_factors", ["candidate_id"]
        )

    inspector = sa.inspect(bind)
    evidence_columns = {column["name"] for column in inspector.get_columns("evidence_links")}
    if "candidate_factor_id" not in evidence_columns:
        op.add_column(
            "evidence_links",
            sa.Column("candidate_factor_id", sa.BigInteger(), nullable=True),
        )
        op.create_foreign_key(
            "fk_evidence_links_candidate_factor_id",
            "evidence_links",
            "candidate_factors",
            ["candidate_factor_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(
            "ix_evidence_links_candidate_factor_id",
            "evidence_links",
            ["candidate_factor_id"],
        )
        op.alter_column("evidence_links", "decision_step_id", nullable=True)
        op.create_unique_constraint(
            "uq_evidence_factor_observation",
            "evidence_links",
            ["candidate_factor_id", "observation_id"],
        )
        op.create_check_constraint(
            "evidence_exactly_one_owner",
            "evidence_links",
            "(decision_step_id IS NOT NULL AND candidate_factor_id IS NULL) OR "
            "(decision_step_id IS NULL AND candidate_factor_id IS NOT NULL)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("evidence_links"):
        columns = {column["name"] for column in inspector.get_columns("evidence_links")}
        if "candidate_factor_id" in columns:
            op.drop_constraint(
                "evidence_exactly_one_owner", "evidence_links", type_="check"
            )
            op.drop_constraint(
                "uq_evidence_factor_observation", "evidence_links", type_="unique"
            )
            op.drop_index(
                "ix_evidence_links_candidate_factor_id", table_name="evidence_links"
            )
            op.drop_constraint(
                "fk_evidence_links_candidate_factor_id",
                "evidence_links",
                type_="foreignkey",
            )
            op.drop_column("evidence_links", "candidate_factor_id")
            op.alter_column("evidence_links", "decision_step_id", nullable=False)
    if sa.inspect(bind).has_table("candidate_factors"):
        op.drop_table("candidate_factors")
