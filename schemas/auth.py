"""
Authentication Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class UserCreate(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class UserUpdate(BaseModel):
    """User update request."""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(BaseModel):
    """User response (no password)."""
    id: UUID
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime
    has_api_key: bool = False
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class APIKeyResponse(BaseModel):
    """API key response."""
    api_key: str
    message: str = "Store this key securely. It cannot be retrieved again."
