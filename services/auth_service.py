"""
Authentication Service
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from models.user import User
from schemas.auth import UserCreate, UserUpdate


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication and user management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, user_id: UUID) -> str:
        """Create JWT access token."""
        expires = datetime.utcnow() + timedelta(
            minutes=self.settings.jwt_access_token_expire_minutes
        )
        
        payload = {
            "sub": str(user_id),
            "exp": expires,
            "type": "access"
        }
        
        return jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm
        )
    
    def create_refresh_token(self, user_id: UUID) -> str:
        """Create JWT refresh token."""
        expires = datetime.utcnow() + timedelta(
            days=self.settings.jwt_refresh_token_expire_days
        )
        
        payload = {
            "sub": str(user_id),
            "exp": expires,
            "type": "refresh"
        }
        
        return jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm
        )
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key."""
        result = await self.db.execute(
            select(User).where(User.api_key == api_key)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=user_data.email,
            password_hash=self.hash_password(user_data.password),
            is_active=True
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    async def get_user_from_token(self, token: str) -> Optional[User]:
        """Get user from JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if not user_id or token_type != "access":
                return None
            
            return await self.get_user_by_id(UUID(user_id))
            
        except JWTError:
            return None
    
    async def get_user_from_refresh_token(self, token: str) -> Optional[User]:
        """Get user from refresh token."""
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if not user_id or token_type != "refresh":
                return None
            
            return await self.get_user_by_id(UUID(user_id))
            
        except JWTError:
            return None
    
    async def update_user(self, user_id: UUID, update_data: UserUpdate) -> Optional[User]:
        """Update user fields."""
        user = await self.get_user_by_id(user_id)
        
        if not user:
            return None
        
        if update_data.email is not None:
            user.email = update_data.email
        
        if update_data.password is not None:
            user.password_hash = self.hash_password(update_data.password)
        
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def generate_api_key(self, user_id: UUID) -> str:
        """Generate a new API key for user."""
        user = await self.get_user_by_id(user_id)
        
        if not user:
            raise ValueError("User not found")
        
        # Generate secure random key
        api_key = secrets.token_urlsafe(48)
        
        user.api_key = api_key
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        return api_key
    
    async def revoke_api_key(self, user_id: UUID) -> bool:
        """Revoke user's API key."""
        user = await self.get_user_by_id(user_id)
        
        if not user:
            return False
        
        user.api_key = None
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        return True
