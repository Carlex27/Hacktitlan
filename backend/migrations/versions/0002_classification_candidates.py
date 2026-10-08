"""Add ranked classification candidates and audited selections.

Revision ID: 0002_classification_candidates
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_classification_candidates"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Migration 0001 historically used live metadata. The guards also support
    # fresh databases where 0001 may already have created these newer tables.
    if not inspector.has_table("classification_candidates"):
        op.create_table(
            "classification_candidates",
            sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
            sa.Column(
                "classification_result_id", sa.BigInteger(),
                sa.ForeignKey("classification_results.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("fraction", sa.String(length=8), nullable=False),
            sa.Column("nico", sa.String(length=2), nullable=False),
            sa.Column("description", sa.Text()),
            sa.Column("support_level", sa.String(length=30), nullable=False),
            sa.Column("details_json", sa.JSON(), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True),
                nullable=False, server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True),
                nullable=False, server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "classification_result_id", "rank", name="uq_candidate_result_rank"
            ),
            sa.UniqueConstraint(
                "classification_result_id", "fraction", "nico",
                name="uq_candidate_result_code",
            ),
            sa.CheckConstraint("rank BETWEEN 1 AND 3", name="candidate_rank_range"),
            sa.CheckConstraint("fraction ~ '^[0-9]{8}$'", name="candidate_fraction_format"),
            sa.CheckConstraint("nico ~ '^[0-9]{2}$'", name="candidate_nico_format"),
            sa.CheckConstraint(
                "support_level IN ('fully_supported','conditional')",
                name="candidate_support_level",
            ),
        )
        op.create_index(
            "ix_classification_candidates_classification_result_id",
            "classification_candidates", ["classification_result_id"],
        )
        op.create_index(
            "ix_classification_candidates_fraction",
            "classification_candidates", ["fraction"],
        )
        op.create_index(
            "ix_classification_candidates_nico",
            "classification_candidates", ["nico"],
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("classification_selections"):
        op.create_table(
            "classification_selections",
            sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
            sa.Column(
                "classification_result_id", sa.BigInteger(),
                sa.ForeignKey("classification_results.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "candidate_id", sa.BigInteger(),
                sa.ForeignKey("classification_candidates.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "supersedes_selection_id", sa.BigInteger(),
                sa.ForeignKey("classification_selections.id", ondelete="RESTRICT"),
            ),
            sa.Column("person_name", sa.String(length=200), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("workstation_name", sa.String(length=200), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True),
                nullable=False, server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True),
                nullable=False, server_default=sa.func.now(),
            ),
        )
        for column in (
            "classification_result_id", "candidate_id", "supersedes_selection_id"
        ):
            op.create_index(
                f"ix_classification_selections_{column}",
                "classification_selections", [column],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("classification_selections"):
        op.drop_table("classification_selections")
    inspector = sa.inspect(bind)
    if inspector.has_table("classification_candidates"):
        op.drop_table("classification_candidates")
