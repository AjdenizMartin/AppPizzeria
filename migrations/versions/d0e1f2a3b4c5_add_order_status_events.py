"""add order status events

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "order_status_events" not in inspector.get_table_names():
        op.create_table(
            "order_status_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("old_status", sa.String(length=50), nullable=True),
            sa.Column("new_status", sa.String(length=50), nullable=False),
            sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
            sa.Column("source", sa.String(length=50), nullable=False),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_order_status_events_order_id",
            "order_status_events",
            ["order_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_order_status_events_order_id", table_name="order_status_events")
    op.drop_table("order_status_events")
