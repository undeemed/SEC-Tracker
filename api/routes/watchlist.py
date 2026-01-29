"""
Watchlist Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List

from api.dependencies import get_db, get_current_user
from schemas.watchlist import (
    WatchlistItem, WatchlistResponse, WatchlistAdd,
    WatchlistActivity
)
from services.watchlist_service import WatchlistService


router = APIRouter()


@router.get("/", response_model=WatchlistResponse)
async def get_watchlist(
    current_user = Depends(get_current_user),
):
    """
    Get current user's watchlist.
    
    Returns all tracked companies with basic info.
    """
    service = WatchlistService()
    
    items = await service.get_user_watchlist(current_user.id)
    
    return WatchlistResponse(
        items=items,
        total=len(items)
    )


@router.post("/", response_model=WatchlistItem, status_code=201)
async def add_to_watchlist(
    item: WatchlistAdd,
    current_user = Depends(get_current_user),
):
    """
    Add a company to watchlist.
    
    - **ticker**: Stock ticker symbol to track
    """
    service = WatchlistService()
    
    try:
        result = await service.add_to_watchlist(
            user_id=current_user.id,
            ticker=item.ticker.upper()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{ticker}", status_code=204)
async def remove_from_watchlist(
    ticker: str,
    current_user = Depends(get_current_user),
):
    """
    Remove a company from watchlist.
    """
    service = WatchlistService()
    
    removed = await service.remove_from_watchlist(
        user_id=current_user.id,
        ticker=ticker.upper()
    )
    
    if not removed:
        raise HTTPException(status_code=404, detail="Ticker not in watchlist")
    
    return None


@router.get("/activity", response_model=WatchlistActivity)
async def get_watchlist_activity(
    days: int = Query(default=7, ge=1, le=90, description="Days of activity to show"),
    current_user = Depends(get_current_user),
):
    """
    Get recent activity for all watched companies.
    
    Returns recent filings and insider transactions for
    all companies in the user's watchlist.
    """
    service = WatchlistService()
    
    activity = await service.get_watchlist_activity(
        user_id=current_user.id,
        days_back=days
    )
    
    return activity


@router.get("/search")
async def search_companies(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Search for companies by ticker or name.
    
    - **q**: Search query (ticker or partial company name)
    - **limit**: Max results
    
    Note: This endpoint is public and does not require authentication.
    """
    service = WatchlistService()
    
    results = await service.search_companies(q, limit)
    
    return {"results": results}
