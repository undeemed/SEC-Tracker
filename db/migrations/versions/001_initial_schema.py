"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('api_key', sa.String(64), nullable=True, unique=True, index=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # User watchlists table
    op.create_table(
        'user_watchlists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('ticker', sa.String(10), nullable=False, index=True),
        sa.Column('cik', sa.String(20), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'ticker', name='uq_user_watchlist_ticker'),
    )
    
    # Filings table
    op.create_table(
        'filings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticker', sa.String(10), nullable=False, index=True),
        sa.Column('cik', sa.String(20), nullable=False, index=True),
        sa.Column('accession_number', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('form_type', sa.String(20), nullable=False, index=True),
        sa.Column('filing_date', sa.Date(), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('document_url', sa.Text(), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_filings_ticker_form', 'filings', ['ticker', 'form_type'])
    op.create_index('idx_filings_date_form', 'filings', ['filing_date', 'form_type'])
    
    # Form 4 transactions table
    op.create_table(
        'form4_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('filings.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('ticker', sa.String(10), nullable=False, index=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('owner_name', sa.String(255), nullable=False, index=True),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('transaction_type', sa.String(10), nullable=False, index=True),
        sa.Column('is_planned', sa.Boolean(), default=False),
        sa.Column('shares', sa.Numeric(20, 4), nullable=True),
        sa.Column('price', sa.Numeric(20, 4), nullable=True),
        sa.Column('amount', sa.Numeric(20, 2), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=True, index=True),
        sa.Column('filing_date', sa.Date(), nullable=True),
        sa.Column('accession_number', sa.String(30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_transactions_ticker_date', 'form4_transactions', ['ticker', 'transaction_date'])
    op.create_index('idx_transactions_type_date', 'form4_transactions', ['transaction_type', 'transaction_date'])
    
    # Analysis results table
    op.create_table(
        'analysis_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('filings.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('analysis_text', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('key_findings', postgresql.JSONB(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Tracking jobs table
    op.create_table(
        'tracking_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='queued', index=True),
        sa.Column('ticker', sa.String(10), nullable=True),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('result', postgresql.JSONB(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('tracking_jobs')
    op.drop_table('analysis_results')
    op.drop_table('form4_transactions')
    op.drop_table('filings')
    op.drop_table('user_watchlists')
    op.drop_table('users')
