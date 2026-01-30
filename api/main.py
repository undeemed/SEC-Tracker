"""
SEC-Tracker API - FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import get_settings
from api.routes import api_router
from db.session import init_db, close_db


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _validate_prod_settings(settings) -> None:
    """Fail fast on unsafe production configuration."""
    if settings.debug:
        return

    if not settings.sec_user_agent:
        raise RuntimeError("SEC_USER_AGENT is required in production (SEC EDGAR requires contact info).")

    if not settings.jwt_secret_key or len(settings.jwt_secret_key) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be set and at least 32 characters in production.")

    if settings.jwt_secret_key in {
        "CHANGE_ME_IN_PRODUCTION_32_CHARS_MIN",
        "dev_secret_key_change_in_production",
    }:
        raise RuntimeError("JWT_SECRET_KEY is set to an unsafe default.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup
    logger.info("Starting SEC-Tracker API...")
    settings = get_settings()
    _validate_prod_settings(settings)
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SEC-Tracker API...")
    await close_db()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## SEC-Tracker API

Track SEC filings and insider trading activity.

### Features
- **Form 4 Tracking**: Monitor insider buying/selling activity
- **Filing Tracking**: Track 10-K, 10-Q, 8-K filings
- **AI Analysis**: Get AI-powered analysis of filings
- **Watchlists**: Track multiple companies

### Authentication
Most endpoints require JWT authentication. Get a token via `/api/v1/auth/login`.
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add rate limiting middleware for million-user scale
    from api.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,      # 60 req/min per user
        requests_per_hour=1000,      # 1000 req/hr per user
        burst_limit=10,              # Max 10 req/sec burst
    )
    
    # Include API routes
    app.include_router(api_router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health"
        }
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level="info"
    )
