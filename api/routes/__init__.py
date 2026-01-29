"""
API Routes Package
"""
from fastapi import APIRouter

from api.routes import auth, health, form4, tracking, watchlist

# Main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(form4.router, prefix="/form4", tags=["Form 4 - Insider Trading"])
api_router.include_router(tracking.router, prefix="/track", tags=["Tracking"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["Watchlist"])
