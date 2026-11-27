"""noop migration replacing unapplied pgvector migration

Revision ID: d853b02e4c1f
Revises: c742a91f3b0e
Create Date: 2026-11-27 23:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd853b02e4c1f'
down_revision: Union[str, Sequence[str], None] = 'c742a91f3b0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: vector storage migrated to ChromaDB."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
