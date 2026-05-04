"""Add product_name snapshot to order items

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-29 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("product_name", sa.String(length=200), nullable=True))

    op.execute(
        """
        UPDATE order_items
        SET product_name = products.name
        FROM products
        WHERE order_items.product_id = products.id
        """
    )

    op.execute(
        """
        UPDATE order_items
        SET product_name = 'Product #' || CAST(product_id AS TEXT)
        WHERE product_name IS NULL
        """
    )

    op.alter_column(
        "order_items",
        "product_name",
        existing_type=sa.String(length=200),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("order_items", "product_name")
