"""add rag fields to meetings and chat_messages

Revision ID: e964c13f5d2a
Revises: d853b02e4c1f
Create Date: 2026-11-27 23:57:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e964c13f5d2a'
down_revision: Union[str, Sequence[str], None] = 'd853b02e4c1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add embedding indexing status fields to meetings and RAG fields to chat_messages."""
    op.add_column(
        'meetings',
        sa.Column('embedding_status', sa.String(length=32), server_default='not_indexed', nullable=False),
    )
    op.add_column(
        'meetings',
        sa.Column('embedding_error', sa.Text(), nullable=True),
    )
    op.add_column(
        'meetings',
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        'chat_messages',
        sa.Column('mode', sa.String(length=20), server_default='general', nullable=False),
    )
    op.add_column(
        'chat_messages',
        sa.Column('meeting_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'chat_messages',
        sa.Column('citations', sa.JSON(), nullable=True),
    )
    op.create_index(op.f('ix_chat_messages_meeting_id'), 'chat_messages', ['meeting_id'], unique=False)
    op.create_foreign_key(
        'fk_chat_messages_meeting_id',
        'chat_messages',
        'meetings',
        ['meeting_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Remove RAG fields from chat_messages and embedding status fields from meetings."""
    op.drop_constraint('fk_chat_messages_meeting_id', 'chat_messages', type_='foreignkey')
    op.drop_index(op.f('ix_chat_messages_meeting_id'), table_name='chat_messages')
    op.drop_column('chat_messages', 'citations')
    op.drop_column('chat_messages', 'meeting_id')
    op.drop_column('chat_messages', 'mode')

    op.drop_column('meetings', 'indexed_at')
    op.drop_column('meetings', 'embedding_error')
    op.drop_column('meetings', 'embedding_status')
