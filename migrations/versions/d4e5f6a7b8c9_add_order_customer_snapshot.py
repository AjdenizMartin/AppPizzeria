"""Add customer snapshot and delivery fields to orders

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-04 13:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("orders")}

    def add_if_missing(name: str, column: sa.Column) -> None:
        if name not in existing_columns:
            op.add_column("orders", column)

    add_if_missing(
        "customer_name",
        sa.Column("customer_name", sa.String(length=200), nullable=True),
    )
    add_if_missing(
        "customer_phone",
        sa.Column("customer_phone", sa.String(length=30), nullable=True),
    )
    add_if_missing(
        "delivery_address",
        sa.Column("delivery_address", sa.String(length=500), nullable=True),
    )
    add_if_missing(
        "delivery_city",
        sa.Column("delivery_city", sa.String(length=100), nullable=True),
    )
    add_if_missing(
        "delivery_postal_code",
        sa.Column("delivery_postal_code", sa.String(length=20), nullable=True),
    )
    add_if_missing(
        "delivery_notes",
        sa.Column("delivery_notes", sa.String(length=1000), nullable=True),
    )
    add_if_missing(
        "payment_method",
        sa.Column("payment_method", sa.String(length=20), nullable=True),
    )
    add_if_missing("delivery_fee", sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=True))
    add_if_missing("created_at", sa.Column("created_at", sa.DateTime(), nullable=True))
    add_if_missing("updated_at", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.execute(
        """
        UPDATE orders
        SET
          customer_name = COALESCE(customer_name, 'Guest'),
          customer_email = COALESCE(customer_email, ''),
          customer_phone = COALESCE(customer_phone, 'N/A'),
          delivery_address = COALESCE(delivery_address, 'N/A'),
          delivery_city = COALESCE(delivery_city, 'N/A'),
          delivery_postal_code = COALESCE(delivery_postal_code, 'N/A'),
          payment_method = COALESCE(payment_method, 'card'),
          delivery_fee = COALESCE(delivery_fee, 2.50),
          created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
          updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)
        """
    )

    if not is_sqlite:
        op.alter_column(
            "orders", "customer_name", existing_type=sa.String(length=200), nullable=False
        )
        op.alter_column(
            "orders", "customer_phone", existing_type=sa.String(length=30), nullable=False
        )
        op.alter_column(
            "orders", "delivery_address", existing_type=sa.String(length=500), nullable=False
        )
        op.alter_column(
            "orders", "delivery_city", existing_type=sa.String(length=100), nullable=False
        )
        op.alter_column(
            "orders", "delivery_postal_code", existing_type=sa.String(length=20), nullable=False
        )
        op.alter_column(
            "orders", "payment_method", existing_type=sa.String(length=20), nullable=False
        )
        op.alter_column(
            "orders", "delivery_fee", existing_type=sa.Numeric(10, 2), nullable=False
        )
        op.alter_column("orders", "created_at", existing_type=sa.DateTime(), nullable=False)
        op.alter_column("orders", "updated_at", existing_type=sa.DateTime(), nullable=False)


def downgrade() -> None:
    op.drop_column("orders", "updated_at")
    op.drop_column("orders", "created_at")
    op.drop_column("orders", "delivery_fee")
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "delivery_notes")
    op.drop_column("orders", "delivery_postal_code")
    op.drop_column("orders", "delivery_city")
    op.drop_column("orders", "delivery_address")
    op.drop_column("orders", "customer_phone")
    op.drop_column("orders", "customer_name")
