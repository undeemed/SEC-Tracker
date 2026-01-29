"""
Tests for Authentication Service and API Endpoints
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


# Test fixtures
@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_user_data():
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "password": "securepassword123"
    }


@pytest.fixture
def sample_user():
    """Sample user model."""
    from models.user import User
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.password_hash = "$2b$12$test_hash"
    user.is_active = True
    user.api_key = None
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    return user


# Auth Service Tests
class TestAuthService:
    """Tests for AuthService."""
    
    def test_hash_password(self, mock_db_session):
        """Test password hashing."""
        from services.auth_service import AuthService
        
        service = AuthService(mock_db_session)
        
        password = "testpassword123"
        hashed = service.hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")
    
    def test_verify_password_valid(self, mock_db_session):
        """Test password verification with correct password."""
        from services.auth_service import AuthService
        
        service = AuthService(mock_db_session)
        
        password = "testpassword123"
        hashed = service.hash_password(password)
        
        assert service.verify_password(password, hashed) is True
    
    def test_verify_password_invalid(self, mock_db_session):
        """Test password verification with wrong password."""
        from services.auth_service import AuthService
        
        service = AuthService(mock_db_session)
        
        password = "testpassword123"
        hashed = service.hash_password(password)
        
        assert service.verify_password("wrongpassword", hashed) is False
    
    def test_create_access_token(self, mock_db_session):
        """Test JWT access token creation."""
        from services.auth_service import AuthService
        
        service = AuthService(mock_db_session)
        user_id = uuid4()
        
        token = service.create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self, mock_db_session):
        """Test JWT refresh token creation."""
        from services.auth_service import AuthService
        
        service = AuthService(mock_db_session)
        user_id = uuid4()
        
        token = service.create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    @pytest.mark.asyncio
    async def test_create_user(self, mock_db_session, sample_user_data):
        """Test user creation."""
        from services.auth_service import AuthService
        from schemas.auth import UserCreate
        
        service = AuthService(mock_db_session)
        user_create = UserCreate(**sample_user_data)
        
        mock_db_session.add = MagicMock()
        
        user = await service.create_user(user_create)
        
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self, mock_db_session, sample_user):
        """Test getting user by email when user exists."""
        from services.auth_service import AuthService
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        service = AuthService(mock_db_session)
        
        user = await service.get_user_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, mock_db_session):
        """Test getting user by email when user doesn't exist."""
        from services.auth_service import AuthService
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        service = AuthService(mock_db_session)
        
        user = await service.get_user_by_email("nonexistent@example.com")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, mock_db_session, sample_user):
        """Test successful user authentication."""
        from services.auth_service import AuthService
        
        service = AuthService(mock_db_session)
        
        # Hash the password properly
        password = "testpassword123"
        sample_user.password_hash = service.hash_password(password)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        user = await service.authenticate_user("test@example.com", password)
        
        assert user is not None
        assert user.email == sample_user.email
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, mock_db_session, sample_user):
        """Test authentication with wrong password."""
        from services.auth_service import AuthService
        
        service = AuthService(mock_db_session)
        sample_user.password_hash = service.hash_password("correctpassword")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        user = await service.authenticate_user("test@example.com", "wrongpassword")
        
        assert user is None
    
    @pytest.mark.asyncio
    async def test_generate_api_key(self, mock_db_session, sample_user):
        """Test API key generation."""
        from services.auth_service import AuthService
        
        service = AuthService(mock_db_session)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        api_key = await service.generate_api_key(sample_user.id)
        
        assert api_key is not None
        assert len(api_key) > 32
        mock_db_session.commit.assert_called()


class TestAuthSchemas:
    """Tests for auth Pydantic schemas."""
    
    def test_user_create_valid(self):
        """Test valid user creation schema."""
        from schemas.auth import UserCreate
        
        user = UserCreate(
            email="test@example.com",
            password="securepassword123"
        )
        
        assert user.email == "test@example.com"
        assert user.password == "securepassword123"
    
    def test_user_create_invalid_email(self):
        """Test user creation with invalid email."""
        from schemas.auth import UserCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="securepassword123"
            )
    
    def test_user_create_short_password(self):
        """Test user creation with short password."""
        from schemas.auth import UserCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="short"
            )
    
    def test_login_request(self):
        """Test login request schema."""
        from schemas.auth import LoginRequest
        
        login = LoginRequest(
            email="test@example.com",
            password="securepassword123"
        )
        
        assert login.email == "test@example.com"
        assert login.password == "securepassword123"
    
    def test_token_response(self):
        """Test token response schema."""
        from schemas.auth import TokenResponse
        
        response = TokenResponse(
            access_token="abc123",
            refresh_token="xyz789",
            token_type="bearer"
        )
        
        assert response.access_token == "abc123"
        assert response.refresh_token == "xyz789"
        assert response.token_type == "bearer"
