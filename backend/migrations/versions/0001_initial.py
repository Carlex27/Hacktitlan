"""Initial backend schema.

Revision ID: 0001_initial
Revises: None
"""

from alembic import op

from backend.app.infrastructure.database.models import *  # noqa: F403: registers metadata
from backend.app.infrastructure.database.session import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=False)
    op.execute(
        """
        INSERT INTO rule_sets
            (name, version, status, source_hash, valid_from, valid_to, manifest_json)
        VALUES
            ('LIGIE capítulo 72 — fuente proporcionada',
             'source-provided-756ed9e9',
             'draft',
             '756ed9e9d43676fe973e03948f3b299d3eaac998a3d13fdea7ba109e33786155',
             NULL,
             NULL,
             '{"legal_status":"SIN VIGENCIA — NO VERIFICADO",'
             '"catalog":"data/ligie/chapter-72/source-provided/catalog.json",'
             '"catalog_sha256":"c5fa60696c42187a31dec6dc7ad8e545a751642e04ae3593c0cf0d3d246b4a2b",'
             '"notes":"data/ligie/chapter-72/source-provided/classification-notes.json",'
             '"source":"data/ligie/chapter-72/source-provided/SOURCE.md"}'::json)
        """
    )


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=False)

