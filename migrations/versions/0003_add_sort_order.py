"""add sort order"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_add_sort_order"
down_revision = "0002_add_recurrence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("tasks", "sort_order")
