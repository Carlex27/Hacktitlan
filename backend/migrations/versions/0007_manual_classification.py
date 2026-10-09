"""Allow audited manual classifications alongside engine suggestions."""
from alembic import op

revision = "0007_manual_classification"
down_revision = "0006_rule_set_immutability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_classification_candidates_candidate_rank_range"), "classification_candidates", type_="check")
    op.create_check_constraint("candidate_rank_range", "classification_candidates", "rank >= 1")


def downgrade() -> None:
    # Refuse rollback with manual history rather than discard audited selections.
    op.drop_constraint(op.f("ck_classification_candidates_candidate_rank_range"), "classification_candidates", type_="check")
    op.create_check_constraint("candidate_rank_range", "classification_candidates", "rank BETWEEN 1 AND 3")
