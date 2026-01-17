"""add recurrence and archive fields"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_recurrence"
down_revision = "0001_create_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("tasks", sa.Column("recurrence_rule", sa.String(length=20), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("recurrence_interval", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("tasks", sa.Column("recurrence_end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "recurrence_end_date")
    op.drop_column("tasks", "recurrence_interval")
    op.drop_column("tasks", "recurrence_rule")
    op.drop_column("tasks", "archived_at")
