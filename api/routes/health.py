"""
Health Check Endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import aiohttp

from api.dependencies import get_db
from api.config import get_settings, Settings
from cache.redis_client import get_redis_client


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    cache: str
    sec_api: str
    details: Optional[dict] = None


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Check health of all services.
    
    Returns status of:
    - Database connection
    - Redis cache connection  
    - SEC API reachability
    """
    status_overall = "healthy"
    details = {}
    
    # Check database
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "disconnected"
        details["database_error"] = str(e)
        status_overall = "degraded"
    
    # Check Redis
    cache_status = "connected"
    try:
        redis = await get_redis_client()
        await redis.ping()
    except Exception as e:
        cache_status = "disconnected"
        details["cache_error"] = str(e)
        status_overall = "degraded"
    
    # Check SEC API
    sec_status = "reachable"
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": settings.sec_user_agent or "SEC-Tracker/2.0"}
            async with session.get(
                "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&output=atom",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    sec_status = "error"
                    details["sec_status_code"] = resp.status
    except Exception as e:
        sec_status = "unreachable"
        details["sec_error"] = str(e)
        status_overall = "degraded"
    
    return HealthResponse(
        status=status_overall,
        version=settings.app_version,
        database=db_status,
        cache=cache_status,
        sec_api=sec_status,
        details=details if details else None
    )


@router.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "SEC-Tracker API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
