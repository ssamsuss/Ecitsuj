"""Add stance column to deliberation_messages for contradiction detection.

Revision ID: 0004_deliberation_stance
Revises: 0003_vote_what_changed
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_deliberation_stance"
down_revision = "0003_vote_what_changed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deliberation_messages", sa.Column("stance", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("deliberation_messages", "stance")
