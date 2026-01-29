"""
Form 4 Schemas
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal


class Form4Transaction(BaseModel):
    """Single Form 4 transaction."""
    date: date
    owner_name: str
    role: Optional[str] = None
    transaction_type: str = Field(..., description="buy, sell, grant, etc.")
    is_planned: bool = Field(False, description="10b5-1 planned transaction")
    shares: Optional[float] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    accession_number: Optional[str] = None
    
    class Config:
        from_attributes = True


class Form4Summary(BaseModel):
    """Summary of Form 4 activity."""
    ticker: str
    company_name: Optional[str] = None
    total_buys: float = 0
    total_sells: float = 0
    net: float = 0
    buy_count: int = 0
    sell_count: int = 0
    period_days: int = 30
    last_updated: datetime


class Form4InsiderGroup(BaseModel):
    """Transactions grouped by insider."""
    owner_name: str
    role: Optional[str] = None
    transactions: List[Form4Transaction]
    total_buys: float = 0
    total_sells: float = 0
    net: float = 0


class Form4Response(BaseModel):
    """Response for company Form 4 data."""
    ticker: str
    company_name: Optional[str] = None
    cik: Optional[str] = None
    transactions: List[Form4Transaction]
    insiders: Optional[List[Form4InsiderGroup]] = None
    summary: Form4Summary
    last_updated: datetime
    cache_hit: bool = False


class MarketCompanyActivity(BaseModel):
    """Aggregated company activity for market view."""
    ticker: str
    company_name: Optional[str] = None
    date_range: str
    buy_count: int = 0
    sell_count: int = 0
    total_buys: float = 0
    total_sells: float = 0
    net: float = 0
    signal: str = Field(..., description="↑ for net buy, ↓ for net sell, → for neutral")
    top_insiders: List[str] = []


class MarketForm4Response(BaseModel):
    """Response for market-wide Form 4 data."""
    companies: List[MarketCompanyActivity]
    total_companies: int
    buying_companies: int
    selling_companies: int
    total_transactions: int
    last_updated: datetime
    filters_applied: dict = {}
