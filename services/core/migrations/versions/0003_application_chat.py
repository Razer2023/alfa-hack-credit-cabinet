"""application chat

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'messages',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('author_role', sa.Enum('CLIENT', 'MANAGER', 'UNDERWRITER', 'SYSTEM', name='role', native_enum=False, length=32), nullable=False),
        sa.Column('text', sa.String(length=2000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name='fk_messages_application_id_applications'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], name='fk_messages_author_id_users'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_messages_application_id', 'messages', ['application_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_messages_application_id', table_name='messages')
    op.drop_table('messages')
