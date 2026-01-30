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
    
    Pool Configuration:
    - pool_size: Base connections per process
    - max_overflow: Extra connections per process during peak load
    - pool_timeout: Fail fast if pool exhausted
    - pool_recycle: Recycle connections periodically
    - pool_pre_ping: Verify connections before use
    """
    global _engine, _async_session_factory
    
    settings = get_settings()
    
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
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
