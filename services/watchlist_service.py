"""
Watchlist Service
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db_session
from models.company import UserWatchlist
from models.filing import Filing
from models.transaction import Form4Transaction
from schemas.watchlist import (
    WatchlistItem, WatchlistActivity, RecentFiling, RecentTransaction,
    CompanySearchResult
)
from cache.redis_client import cache


class WatchlistService:
    """Service for managing user watchlists."""
    
    async def get_user_watchlist(self, user_id: UUID) -> List[WatchlistItem]:
        """Get all items in user's watchlist."""
        async for db in get_db_session():
            result = await db.execute(
                select(UserWatchlist)
                .where(UserWatchlist.user_id == user_id)
                .order_by(UserWatchlist.added_at.desc())
            )
            items = result.scalars().all()
            
            return [
                WatchlistItem(
                    id=item.id,
                    ticker=item.ticker,
                    cik=item.cik,
                    company_name=item.company_name,
                    added_at=item.added_at
                )
                for item in items
            ]
    
    async def add_to_watchlist(self, user_id: UUID, ticker: str) -> WatchlistItem:
        """Add a ticker to user's watchlist."""
        async for db in get_db_session():
            # Check if already in watchlist
            result = await db.execute(
                select(UserWatchlist).where(
                    UserWatchlist.user_id == user_id,
                    UserWatchlist.ticker == ticker.upper()
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                raise ValueError(f"{ticker} is already in your watchlist")
            
            # Lookup company info
            cik, company_name = await self._lookup_ticker(ticker)
            
            if not cik:
                raise ValueError(f"Unknown ticker: {ticker}")
            
            # Add to watchlist
            item = UserWatchlist(
                user_id=user_id,
                ticker=ticker.upper(),
                cik=cik,
                company_name=company_name
            )
            
            db.add(item)
            await db.commit()
            await db.refresh(item)
            
            return WatchlistItem(
                id=item.id,
                ticker=item.ticker,
                cik=item.cik,
                company_name=item.company_name,
                added_at=item.added_at
            )
    
    async def remove_from_watchlist(self, user_id: UUID, ticker: str) -> bool:
        """Remove a ticker from user's watchlist."""
        async for db in get_db_session():
            result = await db.execute(
                delete(UserWatchlist).where(
                    UserWatchlist.user_id == user_id,
                    UserWatchlist.ticker == ticker.upper()
                )
            )
            
            await db.commit()
            
            return result.rowcount > 0
    
    async def get_watchlist_activity(
        self,
        user_id: UUID,
        days_back: int = 7
    ) -> WatchlistActivity:
        """Get recent activity for user's watchlist."""
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        
        async for db in get_db_session():
            # Get watchlist tickers
            result = await db.execute(
                select(UserWatchlist.ticker)
                .where(UserWatchlist.user_id == user_id)
            )
            tickers = [r[0] for r in result.all()]
            
            if not tickers:
                return WatchlistActivity(
                    period_days=days_back,
                    filings=[],
                    transactions=[],
                    total_filings=0,
                    total_transactions=0,
                    last_updated=datetime.utcnow()
                )
            
            # Get recent filings
            filing_result = await db.execute(
                select(Filing)
                .where(
                    Filing.ticker.in_(tickers),
                    Filing.created_at >= cutoff
                )
                .order_by(Filing.filing_date.desc())
                .limit(50)
            )
            filings = filing_result.scalars().all()
            
            # Get recent transactions
            trans_result = await db.execute(
                select(Form4Transaction)
                .where(
                    Form4Transaction.ticker.in_(tickers),
                    Form4Transaction.created_at >= cutoff
                )
                .order_by(Form4Transaction.transaction_date.desc())
                .limit(50)
            )
            transactions = trans_result.scalars().all()
            
            return WatchlistActivity(
                period_days=days_back,
                filings=[
                    RecentFiling(
                        ticker=f.ticker,
                        company_name=None,
                        form_type=f.form_type,
                        filing_date=f.created_at,
                        accession_number=f.accession_number
                    )
                    for f in filings
                ],
                transactions=[
                    RecentTransaction(
                        ticker=t.ticker,
                        company_name=t.company_name,
                        owner_name=t.owner_name,
                        transaction_type=t.transaction_type,
                        amount=float(t.amount) if t.amount else None,
                        transaction_date=t.created_at
                    )
                    for t in transactions
                ],
                total_filings=len(filings),
                total_transactions=len(transactions),
                last_updated=datetime.utcnow()
            )
    
    async def search_companies(
        self,
        query: str,
        limit: int = 10
    ) -> List[CompanySearchResult]:
        """Search for companies by ticker or name."""
        # Check cache
        cache_key = f"company_search:{query.lower()}"
        cached = await cache.get(cache_key)
        
        if cached:
            return [CompanySearchResult(**r) for r in cached]
        
        # Load company tickers
        results = await self._search_company_tickers(query, limit)
        
        # Cache results
        await cache.set(
            cache_key, 
            [r.model_dump() for r in results],
            ttl_seconds=3600
        )
        
        return results
    
    async def _lookup_ticker(self, ticker: str) -> tuple[Optional[str], Optional[str]]:
        """Look up CIK and company name for a ticker."""
        from services.form4_company import CompanyForm4Tracker
        
        tracker = CompanyForm4Tracker()
        return tracker.lookup_ticker(ticker)
    
    async def _search_company_tickers(
        self,
        query: str,
        limit: int
    ) -> List[CompanySearchResult]:
        """Search company tickers database."""
        import json
        from pathlib import Path
        
        cache_file = Path("company_tickers_cache.json")
        
        if not cache_file.exists():
            return []
        
        with open(cache_file) as f:
            data = json.load(f)
        
        query_lower = query.lower()
        results = []
        
        for entry in data.values():
            ticker = entry.get("ticker", "")
            title = entry.get("title", "")
            cik = str(entry.get("cik_str", ""))
            
            if query_lower in ticker.lower() or query_lower in title.lower():
                results.append(CompanySearchResult(
                    ticker=ticker,
                    cik=cik.zfill(10),
                    name=title
                ))
                
                if len(results) >= limit:
                    break
        
        return results
