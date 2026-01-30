"""
Security-focused tests for services/tracking_service.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_analysis_filters_by_user_id(monkeypatch):
    import services.tracking_service as tracking_module
    from services.tracking_service import TrackingService

    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute.return_value = mock_result

    async def fake_get_db_session():
        yield mock_session

    monkeypatch.setattr(tracking_module, "get_db_session", fake_get_db_session)

    await TrackingService().get_analysis(filing_id=uuid4(), user_id=uuid4())

    stmt = mock_session.execute.call_args.args[0]
    criteria = list(stmt._where_criteria)

    assert any(
        getattr(getattr(c, "left", None), "name", None) == "user_id"
        and getattr(getattr(getattr(c, "left", None), "table", None), "name", None) == "analysis_results"
        for c in criteria
    )

