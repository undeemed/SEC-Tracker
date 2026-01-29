"""
FastAPI Dependency Injection
"""
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings, Settings
from db.session import get_db_session
from services.auth_service import AuthService


# Security scheme for JWT
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_db_session():
        yield session


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get current authenticated user from JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    user = await auth_service.get_user_from_token(token)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None
    
    try:
        return await auth_service.get_user_from_token(credentials.credentials)
    except Exception:
        return None


def get_settings_dep() -> Settings:
    """Get settings dependency."""
    return get_settings()
