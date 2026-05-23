"""add opening hours and temporary closure

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('restaurant_settings')}
    if 'temporary_closed' not in cols:
        op.add_column(
            'restaurant_settings',
            sa.Column(
                'temporary_closed',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if 'temporary_closed_message' not in cols:
        op.add_column(
            'restaurant_settings',
            sa.Column('temporary_closed_message', sa.String(length=500), nullable=True),
        )

    if 'opening_hours' not in inspector.get_table_names():
        op.create_table(
            'opening_hours',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('day_of_week', sa.Integer(), nullable=False),
            sa.Column('opens_at', sa.String(length=5), nullable=False),
            sa.Column('closes_at', sa.String(length=5), nullable=False),
            sa.Column('is_closed', sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade() -> None:
    op.drop_table('opening_hours')
    op.drop_column('restaurant_settings', 'temporary_closed_message')
    op.drop_column('restaurant_settings', 'temporary_closed')
