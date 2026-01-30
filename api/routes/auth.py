"""
Authentication Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, get_current_user, get_auth_service
from schemas.auth import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    APIKeyResponse, UserUpdate, RefreshRequest
)
from services.auth_service import AuthService


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.
    
    - **email**: Valid email address (unique)
    - **password**: Minimum 8 characters
    """
    existing = await auth_service.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = await auth_service.create_user(user_data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Login and get access token.
    
    Returns JWT access token and refresh token.
    """
    user = await auth_service.authenticate_user(credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.
    """
    user = await auth_service.get_user_from_refresh_token(payload.refresh_token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    new_access_token = auth_service.create_access_token(user.id)
    new_refresh_token = auth_service.create_refresh_token(user.id)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user),
):
    """
    Get current authenticated user's information.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Update current user's information.
    """
    updated_user = await auth_service.update_user(current_user.id, update_data)
    return updated_user


@router.post("/api-key", response_model=APIKeyResponse)
async def generate_api_key(
    current_user = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Generate a new API key for programmatic access.
    
    Note: This will invalidate any existing API key.
    """
    api_key = await auth_service.generate_api_key(current_user.id)
    return APIKeyResponse(api_key=api_key)


@router.delete("/api-key", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    current_user = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Revoke current API key.
    """
    await auth_service.revoke_api_key(current_user.id)
    return None
