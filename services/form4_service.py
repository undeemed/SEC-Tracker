"""
Form 4 Service - Async wrapper around existing Form 4 logic
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

from schemas.form4 import (
    Form4Response, Form4Transaction, Form4Summary, Form4InsiderGroup,
    MarketForm4Response, MarketCompanyActivity
)
from cache.redis_client import cache


# Thread pool for running sync code
_executor = ThreadPoolExecutor(max_workers=4)


class Form4Service:
    """Service for Form 4 insider trading data."""
    
    def __init__(self):
        self._tracker = None
    
    def _get_tracker(self):
        """Lazy load the tracker to avoid import issues."""
        if self._tracker is None:
            from services.form4_company import CompanyForm4Tracker
            self._tracker = CompanyForm4Tracker()
        return self._tracker
    
    async def get_company_transactions(
        self,
        ticker: str,
        count: int = 30,
        hide_planned: bool = False,
        days_back: Optional[int] = None
    ) -> Form4Response:
        """Get Form 4 transactions for a company."""
        
        # Check cache first
        cache_key = f"form4:{ticker}:{count}:{hide_planned}:{days_back}"
        cached = await cache.get(cache_key)
        
        if cached:
            return Form4Response(**cached, cache_hit=True)
        
        # Run sync code in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            self._fetch_company_transactions,
            ticker, count, hide_planned, days_back
        )
        
        # Cache the result
        await cache.set(cache_key, result.model_dump(mode='json'), ttl_seconds=1800)
        
        return result
    
    def _fetch_company_transactions(
        self,
        ticker: str,
        count: int,
        hide_planned: bool,
        days_back: Optional[int]
    ) -> Form4Response:
        """Sync method to fetch transactions using existing code."""
        from services.form4_company import process_ticker
        
        tracker = self._get_tracker()
        
        # Lookup company info
        cik, company_name = tracker.lookup_ticker(ticker)
        if not cik:
            raise ValueError(f"Unknown ticker: {ticker}")
        
        # Get transactions using existing code
        transactions = process_ticker(
            tracker=tracker,
            ticker=ticker,
            recent_count=count,
            hide_planned=hide_planned,
            days_back=days_back,
            date_range=None
        )
        
        # Convert to schema format
        trans_list = []
        total_buys = 0
        total_sells = 0
        
        for t in transactions:
            trans = Form4Transaction(
                date=t.get('datetime', datetime.now()).date() if isinstance(t.get('datetime'), datetime) else datetime.strptime(t.get('date', '2000-01-01'), '%Y-%m-%d').date(),
                owner_name=t.get('owner_name', 'Unknown'),
                role=t.get('role'),
                transaction_type=t.get('type', 'unknown'),
                is_planned=t.get('planned', False),
                shares=t.get('shares'),
                price=t.get('price'),
                amount=t.get('amount'),
                accession_number=t.get('accession')
            )
            trans_list.append(trans)
            
            amount = t.get('amount', 0) or 0
            if t.get('type') == 'buy':
                total_buys += amount
            elif t.get('type') == 'sell':
                total_sells += amount
        
        summary = Form4Summary(
            ticker=ticker,
            company_name=company_name,
            total_buys=total_buys,
            total_sells=total_sells,
            net=total_buys - total_sells,
            buy_count=len([t for t in transactions if t.get('type') == 'buy']),
            sell_count=len([t for t in transactions if t.get('type') == 'sell']),
            period_days=days_back or 365,
            last_updated=datetime.utcnow()
        )
        
        return Form4Response(
            ticker=ticker,
            company_name=company_name,
            cik=cik,
            transactions=trans_list,
            summary=summary,
            last_updated=datetime.utcnow(),
            cache_hit=False
        )
    
    async def get_market_activity(
        self,
        count: int = 50,
        hide_planned: bool = False,
        min_amount: Optional[float] = None,
        sort_by_active: bool = False
    ) -> MarketForm4Response:
        """Get market-wide Form 4 activity."""
        
        # Check cache
        cache_key = f"form4:market:{count}:{hide_planned}:{min_amount}:{sort_by_active}"
        cached = await cache.get(cache_key)
        
        if cached:
            return MarketForm4Response(**cached)
        
        # Run sync code in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            self._fetch_market_activity,
            count, hide_planned, min_amount, sort_by_active
        )
        
        # Cache for 15 minutes
        await cache.set(cache_key, result.model_dump(mode='json'), ttl_seconds=900)
        
        return result
    
    def _fetch_market_activity(
        self,
        count: int,
        hide_planned: bool,
        min_amount: Optional[float],
        sort_by_active: bool
    ) -> MarketForm4Response:
        """Sync method to fetch market activity using existing code."""
        from services.form4_market import MarketForm4Tracker
        
        tracker = MarketForm4Tracker()
        
        # Get filings
        filings = tracker.get_latest_form4_filings(count)
        
        # Process into company activities
        company_data: Dict[str, Dict] = {}
        
        for filing in filings:
            ticker = filing.get('ticker', 'UNKNOWN')
            if ticker not in company_data:
                company_data[ticker] = {
                    'ticker': ticker,
                    'company_name': filing.get('company_name'),
                    'dates': [],
                    'buys': 0,
                    'sells': 0,
                    'buy_count': 0,
                    'sell_count': 0,
                    'insiders': set()
                }
            
            cd = company_data[ticker]
            cd['dates'].append(filing.get('filing_date', 'N/A'))
            
            for trans in filing.get('transactions', []):
                if hide_planned and trans.get('planned'):
                    continue
                    
                amount = trans.get('amount', 0) or 0
                if trans.get('type') == 'buy':
                    cd['buys'] += amount
                    cd['buy_count'] += 1
                else:
                    cd['sells'] += amount
                    cd['sell_count'] += 1
                
                if trans.get('owner_name'):
                    cd['insiders'].add(trans['owner_name'])
        
        # Filter and convert
        companies = []
        for ticker, data in company_data.items():
            net = data['buys'] - data['sells']
            
            if min_amount and abs(net) < min_amount:
                continue
            
            signal = "↑" if net > 0 else ("↓" if net < 0 else "→")
            
            dates = sorted(data['dates'])
            date_range = dates[0] if len(dates) == 1 else f"{dates[0]} - {dates[-1]}"
            
            companies.append(MarketCompanyActivity(
                ticker=ticker,
                company_name=data['company_name'],
                date_range=date_range,
                buy_count=data['buy_count'],
                sell_count=data['sell_count'],
                total_buys=data['buys'],
                total_sells=data['sells'],
                net=net,
                signal=signal,
                top_insiders=list(data['insiders'])[:3]
            ))
        
        if sort_by_active:
            companies.sort(key=lambda x: abs(x.net), reverse=True)
        
        return MarketForm4Response(
            companies=companies,
            total_companies=len(companies),
            buying_companies=len([c for c in companies if c.net > 0]),
            selling_companies=len([c for c in companies if c.net < 0]),
            total_transactions=sum(c.buy_count + c.sell_count for c in companies),
            last_updated=datetime.utcnow(),
            filters_applied={
                "hide_planned": hide_planned,
                "min_amount": min_amount,
                "sort_by_active": sort_by_active
            }
        )
    
    async def get_company_summary(
        self,
        ticker: str,
        days_back: int = 30
    ) -> Form4Summary:
        """Get summary of insider activity for a company."""
        response = await self.get_company_transactions(
            ticker=ticker,
            count=100,
            hide_planned=False,
            days_back=days_back
        )
        
        return response.summary
