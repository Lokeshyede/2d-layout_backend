"""add_scaling_mode_to_product_3d_models

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-09-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'product_3d_models',
        sa.Column('scaling_mode', sa.String(length=50), nullable=False, server_default='stretch')
    )


def downgrade() -> None:
    op.drop_column('product_3d_models', 'scaling_mode')
