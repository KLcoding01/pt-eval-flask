"""Initial create

Revision ID: da4946deb57e
Revises: 073ab8f8da61
Create Date: 2025-07-04 12:46:22.019363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da4946deb57e'
down_revision: Union[str, Sequence[str], None] = '073ab8f8da61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
