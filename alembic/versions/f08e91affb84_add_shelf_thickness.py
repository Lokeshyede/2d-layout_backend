"""add_shelf_thickness

Revision ID: f08e91affb84
Revises: a1b2c3d4e5f6
Create Date: 2026-10-01 12:00:08.410672

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f08e91affb84'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'product_3d_models',
        sa.Column('shelf_thickness', sa.Float(), nullable=True, server_default='1.0')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('product_3d_models', 'shelf_thickness')
