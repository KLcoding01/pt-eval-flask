"""Add soft delete columns to pt_notes

Revision ID: 3d5f32dbaa6e
Revises: c3d0af66d038
Create Date: 2025-07-04 13:13:18.566458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d5f32dbaa6e'
down_revision: Union[str, Sequence[str], None] = 'c3d0af66d038'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
