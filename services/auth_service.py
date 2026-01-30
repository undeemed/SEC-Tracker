"""
Authentication Service

SECURITY FIXES:
- Hash API keys before storing (not plaintext)
- Run bcrypt in thread pool (non-blocking)
- Validate JWT secret on startup
"""
import secrets
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from models.user import User
from schemas.auth import UserCreate, UserUpdate


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Thread pool for CPU-bound bcrypt operations
_bcrypt_executor = ThreadPoolExecutor(max_workers=4)


def _hash_api_key(api_key: str) -> str:
    """Hash API key using SHA-256 for storage.
    
    We use SHA-256 (not bcrypt) for API keys because:
    1. API keys are high-entropy random tokens (not user passwords)
    2. We need fast lookups for every request
    3. SHA-256 is sufficient for random 48-byte tokens
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


class AuthService:
    """Authentication and user management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._validate_jwt_secret()
    
    def _validate_jwt_secret(self):
        """Ensure JWT secret is properly configured."""
        import os
        import sys
        
        # Allow default in test/debug mode
        is_testing = "pytest" in sys.modules or os.getenv("TESTING") == "true"
        is_debug = os.getenv("DEBUG", "").lower() == "true"
        
        if not is_testing and not is_debug:
            if self.settings.jwt_secret_key in [
                "CHANGE_ME_IN_PRODUCTION_32_CHARS_MIN",
                "dev_secret_key_change_in_production",
                ""
            ]:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a secure value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
    
    def hash_password(self, password: str) -> str:
        """Hash a password (synchronous, for use in thread pool)."""
        return pwd_context.hash(password)
    
    async def hash_password_async(self, password: str) -> str:
        """Hash a password without blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_bcrypt_executor, pwd_context.hash, password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash (synchronous)."""
        return pwd_context.verify(plain_password, hashed_password)
    
    async def verify_password_async(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password without blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _bcrypt_executor, 
            pwd_context.verify, 
            plain_password, 
            hashed_password
        )
    
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
        """Get user by API key (legacy - for plaintext keys)."""
        result = await self.db.execute(
            select(User).where(User.api_key == api_key)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_api_key_hash(self, api_key: str) -> Optional[User]:
        """Get user by hashed API key (secure).

        Backward compatible: if a legacy plaintext key exists, auto-migrate it
        to `api_key_hash` and clear the plaintext column.
        """
        key_hash = _hash_api_key(api_key)
        result = await self.db.execute(
            select(User).where(User.api_key_hash == key_hash)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            return user

        # Legacy fallback (plaintext). Auto-migrate on successful match.
        legacy = await self.get_user_by_api_key(api_key)
        if legacy is None:
            return None

        legacy.api_key = None
        legacy.api_key_hash = key_hash
        legacy.updated_at = datetime.utcnow()
        await self.db.commit()

        return legacy
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Use async hashing to not block event loop
        password_hash = await self.hash_password_async(user_data.password)
        
        user = User(
            email=user_data.email,
            password_hash=password_hash,
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
        
        # Use async verification to not block event loop
        if not await self.verify_password_async(password, user.password_hash):
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
            user.password_hash = await self.hash_password_async(update_data.password)
        
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def generate_api_key(self, user_id: UUID) -> str:
        """Generate a new API key for user.
        
        SECURITY: API key is hashed before storage. The plaintext key
        is returned ONCE and cannot be retrieved again.
        """
        user = await self.get_user_by_id(user_id)
        
        if not user:
            raise ValueError("User not found")
        
        # Generate secure random key
        api_key = secrets.token_urlsafe(48)
        
        # Store HASH of key (not plaintext)
        # Also clear deprecated plaintext field (if present)
        user.api_key = None
        user.api_key_hash = _hash_api_key(api_key)
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        # Return plaintext key (only time it's available)
        return api_key
    
    async def revoke_api_key(self, user_id: UUID) -> bool:
        """Revoke user's API key."""
        user = await self.get_user_by_id(user_id)
        
        if not user:
            return False
        
        user.api_key = None
        user.api_key_hash = None
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        return True
