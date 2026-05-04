"""Add security improvements - indexes, constraints, numeric prices

Revision ID: a1b2c3d4e5f6
Revises: f2eca5f502f6
Create Date: 2026-04-17 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f2eca5f502f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)

    op.alter_column("products", "name", existing_type=sa.String(), type_=sa.String(200))
    op.alter_column("products", "category", existing_type=sa.String(), type_=sa.String(100))
    op.alter_column(
        "products", "description", existing_type=sa.String(), type_=sa.String(1000)
    )
    op.alter_column(
        "products", "image_url", existing_type=sa.String(), type_=sa.String(500)
    )
    op.alter_column("products", "price", existing_type=sa.Float(), type_=sa.Numeric(10, 2))

    op.alter_column(
        "orders", "customer_email", existing_type=sa.String(), type_=sa.String(255)
    )
    op.alter_column("orders", "status", existing_type=sa.String(), type_=sa.String(50))
    op.alter_column(
        "orders", "total_price", existing_type=sa.Float(), type_=sa.Numeric(10, 2)
    )

    op.alter_column(
        "order_items", "extras", existing_type=sa.String(), type_=sa.String(500)
    )
    op.alter_column(
        "order_items", "price", existing_type=sa.Float(), type_=sa.Numeric(10, 2)
    )

    op.alter_column(
        "print_jobs", "status", existing_type=sa.String(), type_=sa.String(50)
    )
    op.alter_column(
        "print_jobs", "last_error", existing_type=sa.String(), type_=sa.String(1000)
    )
    op.alter_column(
        "print_jobs",
        "idempotency_key",
        existing_type=sa.String(),
        type_=sa.String(255),
    )
    op.alter_column(
        "print_jobs", "locked_by", existing_type=sa.String(), type_=sa.String(100)
    )

    op.alter_column("users", "email", existing_type=sa.String(), type_=sa.String(255))
    op.alter_column(
        "users", "hashed_password", existing_type=sa.String(), type_=sa.String(255)
    )
    op.alter_column(
        "users", "full_name", existing_type=sa.String(), type_=sa.String(200)
    )
    op.alter_column(
        "users", "address_line", existing_type=sa.String(), type_=sa.String(500)
    )
    op.alter_column("users", "city", existing_type=sa.String(), type_=sa.String(100))
    op.alter_column(
        "users", "postal_code", existing_type=sa.String(), type_=sa.String(20)
    )
    op.alter_column("users", "phone", existing_type=sa.String(), type_=sa.String(20))


def downgrade() -> None:
    op.drop_index("ix_orders_status", table_name="orders")

    op.alter_column("products", "name", existing_type=sa.String(200), type_=sa.String())
    op.alter_column(
        "products", "category", existing_type=sa.String(100), type_=sa.String()
    )
    op.alter_column(
        "products", "description", existing_type=sa.String(1000), type_=sa.String()
    )
    op.alter_column(
        "products", "image_url", existing_type=sa.String(500), type_=sa.String()
    )
    op.alter_column(
        "products", "price", existing_type=sa.Numeric(10, 2), type_=sa.Float()
    )

    op.alter_column(
        "orders", "customer_email", existing_type=sa.String(255), type_=sa.String()
    )
    op.alter_column(
        "orders", "status", existing_type=sa.String(50), type_=sa.String()
    )
    op.alter_column(
        "orders", "total_price", existing_type=sa.Numeric(10, 2), type_=sa.Float()
    )

    op.alter_column(
        "order_items", "extras", existing_type=sa.String(500), type_=sa.String()
    )
    op.alter_column(
        "order_items", "price", existing_type=sa.Numeric(10, 2), type_=sa.Float()
    )

    op.alter_column(
        "print_jobs", "status", existing_type=sa.String(50), type_=sa.String()
    )
    op.alter_column(
        "print_jobs", "last_error", existing_type=sa.String(1000), type_=sa.String()
    )
    op.alter_column(
        "print_jobs",
        "idempotency_key",
        existing_type=sa.String(255),
        type_=sa.String(),
    )
    op.alter_column(
        "print_jobs", "locked_by", existing_type=sa.String(100), type_=sa.String()
    )

    op.alter_column("users", "email", existing_type=sa.String(255), type_=sa.String())
    op.alter_column(
        "users", "hashed_password", existing_type=sa.String(255), type_=sa.String()
    )
    op.alter_column(
        "users", "full_name", existing_type=sa.String(200), type_=sa.String()
    )
    op.alter_column(
        "users", "address_line", existing_type=sa.String(500), type_=sa.String()
    )
    op.alter_column("users", "city", existing_type=sa.String(100), type_=sa.String())
    op.alter_column(
        "users", "postal_code", existing_type=sa.String(20), type_=sa.String()
    )
    op.alter_column("users", "phone", existing_type=sa.String(20), type_=sa.String())
