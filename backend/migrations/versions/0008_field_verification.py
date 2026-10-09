"""Preserve local field verification alongside the original observation."""
from alembic import op
import sqlalchemy as sa

revision = "0008_field_verification"
down_revision = "0007_manual_classification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("observations", sa.Column("verification_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("observations", "verification_json")
