"""add_shelf_config_to_product_3d_models

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-09-26 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'product_3d_models',
        sa.Column('shelf_count', sa.Integer(), nullable=True, server_default='5')
    )
    op.add_column(
        'product_3d_models',
        sa.Column('min_shelves', sa.Integer(), nullable=True, server_default='1')
    )
    op.add_column(
        'product_3d_models',
        sa.Column('max_shelves', sa.Integer(), nullable=True, server_default='10')
    )
    op.add_column(
        'product_3d_models',
        sa.Column('shelf_mode', sa.String(length=50), nullable=True, server_default='AUTO_SPACING')
    )


def downgrade() -> None:
    op.drop_column('product_3d_models', 'shelf_mode')
    op.drop_column('product_3d_models', 'max_shelves')
    op.drop_column('product_3d_models', 'min_shelves')
    op.drop_column('product_3d_models', 'shelf_count')
