"""Ensure evidence codes are unique within a case.

Revision ID: 0002_unique_evidence_codes
Revises: 0001_initial
"""
from alembic import op

revision = "0002_unique_evidence_codes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_evidence_items_case_code",
        "evidence_items",
        ["case_id", "evidence_code"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_evidence_items_case_code",
        "evidence_items",
        type_="unique",
    )
