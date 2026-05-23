"""add delivery zones

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'delivery_zones' not in inspector.get_table_names():
        op.create_table(
            'delivery_zones',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=120), nullable=False),
            sa.Column('postal_code_prefix', sa.String(length=20), nullable=False),
            sa.Column('delivery_fee', sa.Numeric(10, 2), nullable=False),
            sa.Column('minimum_order_amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('display_order', sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(
            'ix_delivery_zones_postal_code_prefix',
            'delivery_zones',
            ['postal_code_prefix'],
        )


def downgrade() -> None:
    op.drop_index('ix_delivery_zones_postal_code_prefix', table_name='delivery_zones')
    op.drop_table('delivery_zones')
