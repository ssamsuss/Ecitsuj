"""Add estimated_cost_usd column to simulation_runs for cost tracking.

Revision ID: 0005_run_cost_tracking
Revises: 0004_deliberation_stance
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_run_cost_tracking"
down_revision = "0004_deliberation_stance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("simulation_runs", sa.Column("estimated_cost_usd", sa.Numeric(10, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("simulation_runs", "estimated_cost_usd")
