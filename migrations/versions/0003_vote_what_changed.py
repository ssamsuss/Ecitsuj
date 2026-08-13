"""Add what_changed column to votes for final-phase explanations.

Revision ID: 0003_vote_what_changed
Revises: 0002_unique_evidence_codes
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_vote_what_changed"
down_revision = "0002_unique_evidence_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("votes", sa.Column("what_changed", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("votes", "what_changed")
