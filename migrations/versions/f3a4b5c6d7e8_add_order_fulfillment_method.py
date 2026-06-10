"""add order fulfillment method

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("orders")}
    if "fulfillment_method" not in columns:
        op.add_column(
            "orders",
            sa.Column(
                "fulfillment_method",
                sa.String(length=20),
                nullable=False,
                server_default="delivery",
            ),
        )
    op.execute(
        sa.text(
            """
            UPDATE orders
            SET fulfillment_method = 'collection',
                total_price = total_price - delivery_fee,
                delivery_fee = 0
            WHERE lower(delivery_address) = 'collection'
              AND lower(delivery_city) = 'store'
              AND delivery_fee > 0
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("orders")}
    if "fulfillment_method" in columns:
        op.drop_column("orders", "fulfillment_method")
