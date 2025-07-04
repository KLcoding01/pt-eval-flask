"""Add deleted columns to pt_notes

Revision ID: 073ab8f8da61
Revises: 
Create Date: 2025-07-04 12:26:04.900380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '073ab8f8da61'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('pt_notes', sa.Column('deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('pt_notes', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('pt_notes', 'deleted')
    op.drop_column('pt_notes', 'deleted_at')
