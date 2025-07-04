"""Add deleted and deleted_at columns to pt_notes

Revision ID: 0a38d29e8b36
Revises: 
Create Date: 2025-07-04 14:23:39.115755

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a38d29e8b36'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pt_notes', sa.Column('deleted', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('pt_notes', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('pt_notes', 'deleted')
    op.drop_column('pt_notes', 'deleted_at')
