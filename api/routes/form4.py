"""
Form 4 (Insider Trading) Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta, date

from api.dependencies import get_db, get_current_user_optional
from schemas.form4 import (
    Form4Response, Form4Transaction, Form4Summary,
    MarketForm4Response, MarketCompanyActivity
)
from services.form4_service import Form4Service


router = APIRouter()


@router.get("/{ticker}", response_model=Form4Response)
async def get_company_form4(
    ticker: str,
    count: int = Query(default=30, ge=1, le=100, description="Number of recent insiders to return"),
    hide_planned: bool = Query(default=False, description="Hide 10b5-1 planned transactions"),
    days: Optional[int] = Query(default=None, ge=1, le=365, description="Limit to transactions within N days"),
    start_date: Optional[date] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(default=None, description="End date (YYYY-MM-DD)"),
    current_user = Depends(get_current_user_optional),
):
    """
    Get Form 4 insider trading data for a specific company.
    
    - **ticker**: Stock ticker symbol (e.g., AAPL, NVDA)
    - **count**: Number of recent insiders to show (default: 30)
    - **hide_planned**: Exclude 10b5-1 planned transactions
    - **days**: Only show transactions from the last N days
    - **start_date**: Filter transactions from this date (overrides days)
    - **end_date**: Filter transactions until this date
    
    Returns transactions grouped by insider with buy/sell totals.
    """
    service = Form4Service()
    
    try:
        result = await service.get_company_transactions(
            ticker=ticker.upper(),
            count=count,
            hide_planned=hide_planned,
            days=days,
            start_date=start_date,
            end_date=end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Form 4 data: {str(e)}")
    
    return result


@router.get("/", response_model=MarketForm4Response)
async def get_latest_form4(
    count: int = Query(default=50, ge=1, le=200, description="Number of filings to process"),
    days: Optional[int] = Query(default=30, ge=1, le=365, description="Days to look back"),
    start_date: Optional[date] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(default=None, description="End date (YYYY-MM-DD)"),
    hide_planned: bool = Query(default=False, description="Hide 10b5-1 planned transactions"),
    min_amount: Optional[float] = Query(default=None, description="Minimum net activity threshold"),
    max_amount: Optional[float] = Query(default=None, description="Maximum net activity threshold"),
    sort_by_active: bool = Query(default=False, alias="active", description="Sort by most active"),
    current_user = Depends(get_current_user_optional),
):
    """
    Get latest Form 4 filings across all companies.
    
    - **count**: Number of recent filings to process (default: 50)
    - **days**: Days to look back (default: 30)
    - **start_date**: Filter filings from this date (overrides days)
    - **end_date**: Filter filings until this date
    - **hide_planned**: Exclude 10b5-1 planned transactions
    - **min_amount**: Filter to companies with net activity above this amount
    - **max_amount**: Filter to companies with net activity below this amount
    - **active**: Sort by most active companies first
    
    Returns aggregated insider activity across the market.
    """
    service = Form4Service()
    
    try:
        result = await service.get_market_activity(
            count=count,
            days=days,
            start_date=start_date,
            end_date=end_date,
            hide_planned=hide_planned,
            min_amount=min_amount,
            max_amount=max_amount,
            sort_by_active=sort_by_active
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")
    
    return result


@router.get("/{ticker}/summary", response_model=Form4Summary)
async def get_company_form4_summary(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365, description="Days to analyze"),
    current_user = Depends(get_current_user_optional),
):
    """
    Get a summary of insider trading activity for a company.
    
    Returns aggregated buy/sell totals and key metrics.
    """
    service = Form4Service()
    
    try:
        result = await service.get_company_summary(
            ticker=ticker.upper(),
            days_back=days
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")
    
    return result
