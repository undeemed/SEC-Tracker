"""
Watchlist Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


class WatchlistAdd(BaseModel):
    """Request to add ticker to watchlist."""
    ticker: str = Field(..., min_length=1, max_length=10)


class WatchlistItem(BaseModel):
    """Single watchlist item."""
    id: UUID
    ticker: str
    cik: Optional[str] = None
    company_name: Optional[str] = None
    added_at: datetime
    
    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    """User's complete watchlist."""
    items: List[WatchlistItem]
    total: int


class CompanySearchResult(BaseModel):
    """Company search result."""
    ticker: str
    cik: str
    name: str


class RecentFiling(BaseModel):
    """Recent filing for watchlist activity."""
    ticker: str
    company_name: Optional[str] = None
    form_type: str
    filing_date: datetime
    accession_number: str


class RecentTransaction(BaseModel):
    """Recent transaction for watchlist activity."""
    ticker: str
    company_name: Optional[str] = None
    owner_name: str
    transaction_type: str
    amount: Optional[float] = None
    transaction_date: datetime


class WatchlistActivity(BaseModel):
    """Activity for user's watchlist."""
    period_days: int
    filings: List[RecentFiling]
    transactions: List[RecentTransaction]
    total_filings: int
    total_transactions: int
    last_updated: datetime
