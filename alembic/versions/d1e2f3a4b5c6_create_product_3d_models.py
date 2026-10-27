"""create_product_3d_models

Revision ID: d1e2f3a4b5c6
Revises: c3f4bd64236f
Create Date: 2026-09-13 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c3f4bd64236f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'product_3d_models',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.String(length=50), nullable=False),
        sa.Column('product_name', sa.String(length=255), nullable=False),
        sa.Column('product_type', sa.String(length=100), nullable=False, server_default='Wall Rack'),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True, server_default='Display Racks'),
        sa.Column('width', sa.Float(), nullable=False),
        sa.Column('height', sa.Float(), nullable=False),
        sa.Column('depth', sa.Float(), nullable=False),
        sa.Column('glb_url', sa.String(length=500), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_3d_models_id'), 'product_3d_models', ['id'], unique=False)
    op.create_index(op.f('ix_product_3d_models_product_id'), 'product_3d_models', ['product_id'], unique=True)
    op.create_index(op.f('ix_product_3d_models_sku'), 'product_3d_models', ['sku'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_product_3d_models_sku'), table_name='product_3d_models')
    op.drop_index(op.f('ix_product_3d_models_product_id'), table_name='product_3d_models')
    op.drop_index(op.f('ix_product_3d_models_id'), table_name='product_3d_models')
    op.drop_table('product_3d_models')
