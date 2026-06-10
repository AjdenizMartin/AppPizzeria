"""add is_active to products

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("products")}
    if "is_active" not in columns:
        op.add_column(
            "products",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    op.execute(sa.text("UPDATE products SET is_active = true WHERE is_active IS NULL"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("products")}
    if "is_active" in columns:
        op.drop_column("products", "is_active")
