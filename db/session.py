"""
Database Session Management - Million User Scale
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    AsyncEngine, 
    create_async_engine, 
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase

from api.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# Engine and session factory (initialized on startup)
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker] = None


async def init_db():
    """
    Initialize database connection pool.
    
    Pool Configuration for Million-User Scale:
    - pool_size=100: Base connections always open
    - max_overflow=200: Extra connections during peak load  
    - pool_timeout=30: Fail fast if no connection available
    - pool_recycle=1800: Recycle connections every 30 min
    - pool_pre_ping=True: Verify connections before use
    """
    global _engine, _async_session_factory
    
    settings = get_settings()
    
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=100,          # 100 base connections for high concurrency
        max_overflow=200,       # 200 extra during peak = 300 max
        pool_timeout=30,        # Fail fast if pool exhausted
        pool_recycle=1800,      # Recycle connections every 30 min
        pool_pre_ping=True,     # Verify connections before use
    )
    
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def close_db():
    """Close database connection pool."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection."""
    if _async_session_factory is None:
        await init_db()
    
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables():
    """Create all database tables (for development/testing)."""
    if _engine is None:
        await init_db()
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables():
    """Drop all database tables (for testing only)."""
    if _engine is None:
        await init_db()
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
