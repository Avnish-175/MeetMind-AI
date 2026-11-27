"""add pgvector extension and meeting_embeddings table

Revision ID: d853b02e4c1f
Revises: c742a91f3b0e
Create Date: 2026-11-27 23:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd853b02e4c1f'
down_revision: Union[str, Sequence[str], None] = 'c742a91f3b0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable pgvector extension and create meeting_embeddings table."""
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        'meeting_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_meeting_embeddings_id'), 'meeting_embeddings', ['id'], unique=False)
    op.create_index(op.f('ix_meeting_embeddings_meeting_id'), 'meeting_embeddings', ['meeting_id'], unique=False)
    op.create_index(op.f('ix_meeting_embeddings_user_id'), 'meeting_embeddings', ['user_id'], unique=False)
    op.create_index('ix_meeting_embeddings_user_meeting', 'meeting_embeddings', ['user_id', 'meeting_id'], unique=False)
    op.execute(
        'CREATE INDEX ix_meeting_embeddings_embedding_hnsw '
        'ON meeting_embeddings USING hnsw (embedding vector_cosine_ops)'
    )


def downgrade() -> None:
    """Drop meeting_embeddings table and indexes."""
    op.execute('DROP INDEX IF EXISTS ix_meeting_embeddings_embedding_hnsw')
    op.drop_index('ix_meeting_embeddings_user_meeting', table_name='meeting_embeddings')
    op.drop_index(op.f('ix_meeting_embeddings_user_id'), table_name='meeting_embeddings')
    op.drop_index(op.f('ix_meeting_embeddings_meeting_id'), table_name='meeting_embeddings')
    op.drop_index(op.f('ix_meeting_embeddings_id'), table_name='meeting_embeddings')
    op.drop_table('meeting_embeddings')
