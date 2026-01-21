"""add subtasks table"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_add_subtasks"
down_revision = "0003_add_sort_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subtasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_subtasks_task_id", "subtasks", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_subtasks_task_id", table_name="subtasks")
    op.drop_table("subtasks")
