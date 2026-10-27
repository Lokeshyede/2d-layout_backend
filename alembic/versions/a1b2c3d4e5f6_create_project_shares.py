"""create_project_shares

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-09-30 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_shares',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('share_token', sa.String(length=100), nullable=False),
        sa.Column('share_token_hash', sa.String(length=128), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('allow_pdf_download', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('allow_png_download', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('allow_video_download', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_shares_id'), 'project_shares', ['id'], unique=False)
    op.create_index(op.f('ix_project_shares_project_id'), 'project_shares', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_shares_share_token'), 'project_shares', ['share_token'], unique=True)
    op.create_index(op.f('ix_project_shares_share_token_hash'), 'project_shares', ['share_token_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_project_shares_share_token_hash'), table_name='project_shares')
    op.drop_index(op.f('ix_project_shares_share_token'), table_name='project_shares')
    op.drop_index(op.f('ix_project_shares_project_id'), table_name='project_shares')
    op.drop_index(op.f('ix_project_shares_id'), table_name='project_shares')
    op.drop_table('project_shares')
