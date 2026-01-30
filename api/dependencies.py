"""
FastAPI Dependency Injection
"""
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings, Settings
from db.session import get_db_session
from services.auth_service import AuthService


# Security scheme for JWT
security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_db_session():
        yield session


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get current authenticated user from JWT token or API key."""
    # Prefer JWT if present
    if credentials is not None:
        token = credentials.credentials
        user = await auth_service.get_user_from_token(token)
        if user is not None:
            return user

    # Fall back to API key auth
    if api_key:
        user = await auth_service.get_user_by_api_key_hash(api_key)
        if user is not None and user.is_active:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Depends(api_key_header),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get current user if authenticated, None otherwise."""
    if credentials is not None:
        try:
            user = await auth_service.get_user_from_token(credentials.credentials)
            if user is not None:
                return user
        except Exception:
            pass

    if api_key:
        try:
            user = await auth_service.get_user_by_api_key_hash(api_key)
            if user is not None and user.is_active:
                return user
        except Exception:
            pass

    return None


def get_settings_dep() -> Settings:
    """Get settings dependency."""
    return get_settings()
