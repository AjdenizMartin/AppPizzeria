"""add restaurant settings

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "restaurant_settings" not in inspector.get_table_names():
        op.create_table(
            "restaurant_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("restaurant_name", sa.String(length=200), nullable=False),
            sa.Column("public_phone", sa.String(length=50), nullable=False),
            sa.Column("whatsapp_number", sa.String(length=50), nullable=False),
            sa.Column("address", sa.String(length=500), nullable=False),
            sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=False),
            sa.Column("minimum_order_amount", sa.Numeric(10, 2), nullable=False),
            sa.Column("estimated_delivery_minutes", sa.Integer(), nullable=False),
            sa.Column("is_accepting_orders", sa.Boolean(), nullable=False),
            sa.Column("banner_text", sa.String(length=500), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("restaurant_settings")
