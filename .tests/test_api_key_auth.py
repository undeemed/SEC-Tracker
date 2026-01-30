"""
Tests for API key authentication support in api/dependencies.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException


@pytest.mark.asyncio
async def test_get_current_user_accepts_api_key():
    from api.dependencies import get_current_user

    auth_service = MagicMock()
    auth_service.get_user_from_token = AsyncMock(return_value=None)

    user = MagicMock()
    user.is_active = True
    auth_service.get_user_by_api_key_hash = AsyncMock(return_value=user)

    result = await get_current_user(credentials=None, api_key="test-key", auth_service=auth_service)
    assert result == user


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_api_key():
    from api.dependencies import get_current_user

    auth_service = MagicMock()
    auth_service.get_user_from_token = AsyncMock(return_value=None)
    auth_service.get_user_by_api_key_hash = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=None, api_key="bad-key", auth_service=auth_service)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_api_key_user():
    from api.dependencies import get_current_user

    auth_service = MagicMock()
    auth_service.get_user_from_token = AsyncMock(return_value=None)

    user = MagicMock()
    user.is_active = False
    auth_service.get_user_by_api_key_hash = AsyncMock(return_value=user)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=None, api_key="test-key", auth_service=auth_service)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_optional_accepts_api_key():
    from api.dependencies import get_current_user_optional

    auth_service = MagicMock()
    auth_service.get_user_from_token = AsyncMock(return_value=None)

    user = MagicMock()
    user.is_active = True
    auth_service.get_user_by_api_key_hash = AsyncMock(return_value=user)

    result = await get_current_user_optional(credentials=None, api_key="test-key", auth_service=auth_service)
    assert result == user


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_for_invalid_api_key():
    from api.dependencies import get_current_user_optional

    auth_service = MagicMock()
    auth_service.get_user_from_token = AsyncMock(return_value=None)
    auth_service.get_user_by_api_key_hash = AsyncMock(return_value=None)

    result = await get_current_user_optional(credentials=None, api_key="bad-key", auth_service=auth_service)
    assert result is None

