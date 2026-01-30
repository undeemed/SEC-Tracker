"""Add api_key_hash column for secure API key storage

Revision ID: 002_add_api_key_hash
Revises: 001_initial_schema
Create Date: 2026-01-29

Security fix: Store hashed API keys instead of plaintext
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_api_key_hash'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add api_key_hash column
    op.add_column('users', sa.Column('api_key_hash', sa.String(64), nullable=True))

    # Create a UNIQUE index for fast lookups (nullable column; Postgres allows multiple NULLs)
    op.create_index('ix_users_api_key_hash', 'users', ['api_key_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_api_key_hash', table_name='users')
    op.drop_column('users', 'api_key_hash')
