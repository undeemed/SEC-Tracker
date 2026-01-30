"""
Tests for TrackingService analysis job execution.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_run_analysis_job_completes_and_saves_result(monkeypatch):
    import services.tracking_service as tracking_module
    from services.tracking_service import TrackingService

    job_id = uuid4()
    user_id = uuid4()
    filing_id = uuid4()

    job = SimpleNamespace(
        id=job_id,
        user_id=user_id,
        job_type="analyze",
        status="queued",
        progress=0,
        message=None,
        result={"filing_id": str(filing_id), "force": False},
        error=None,
        started_at=None,
        completed_at=None,
    )

    filing = SimpleNamespace(
        id=filing_id,
        ticker="AAPL",
        cik="0000320193",
        form_type="10-K",
        filing_date=date(2025, 1, 10),
        accession_number="0001234567-25-000001",
        raw_content="<html><body><p>Revenue increased.</p></body></html>",
        document_url=None,
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(side_effect=[_Result(job), _Result(filing), _Result(None)])
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def fake_get_db_session():
        yield mock_session

    monkeypatch.setattr(tracking_module, "get_db_session", fake_get_db_session)
    monkeypatch.setattr(tracking_module, "_get_openrouter_api_key", lambda: "sk-or-v1-test")

    async def fake_choose_model():
        return "test/model-a"

    monkeypatch.setattr(tracking_module, "_choose_openrouter_model", fake_choose_model)
    monkeypatch.setattr(
        tracking_module,
        "_openrouter_chat_completion",
        lambda **kwargs: ("Analysis: Revenue increased and outlook is positive.", 123),
    )

    await TrackingService().run_analysis_job(job_id)

    assert job.status == "complete"
    assert job.progress == 100
    assert job.error is None
    assert job.result["filing_id"] == str(filing_id)
    assert job.result["model_used"] == "test/model-a"

    assert mock_session.add.call_count == 1
    added = mock_session.add.call_args.args[0]
    assert getattr(added, "filing_id") == filing_id
    assert getattr(added, "user_id") == user_id
    assert getattr(added, "model_used") == "test/model-a"
    assert getattr(added, "tokens_used") == 123
    assert getattr(added, "analysis_text")


@pytest.mark.asyncio
async def test_run_analysis_job_fails_when_openrouter_key_missing(monkeypatch):
    import services.tracking_service as tracking_module
    from services.tracking_service import TrackingService

    job_id = uuid4()
    user_id = uuid4()
    filing_id = uuid4()

    job = SimpleNamespace(
        id=job_id,
        user_id=user_id,
        job_type="analyze",
        status="queued",
        progress=0,
        message=None,
        result={"filing_id": str(filing_id), "force": False},
        error=None,
        started_at=None,
        completed_at=None,
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(return_value=_Result(job))
    mock_session.commit = AsyncMock()

    async def fake_get_db_session():
        yield mock_session

    monkeypatch.setattr(tracking_module, "get_db_session", fake_get_db_session)
    monkeypatch.setattr(tracking_module, "_get_openrouter_api_key", lambda: None)

    await TrackingService().run_analysis_job(job_id)

    assert job.status == "failed"
    assert job.progress == 100
    assert "OPENROUTER_API_KEY" in (job.error or "")


@pytest.mark.asyncio
async def test_run_analysis_job_uses_requested_model_slot(monkeypatch):
    import services.tracking_service as tracking_module
    from services.tracking_service import TrackingService

    monkeypatch.setenv("OPENROUTER_MODEL_SLOT_2", "slot/model-2")

    job_id = uuid4()
    user_id = uuid4()
    filing_id = uuid4()

    job = SimpleNamespace(
        id=job_id,
        user_id=user_id,
        job_type="analyze",
        status="queued",
        progress=0,
        message=None,
        result={"filing_id": str(filing_id), "force": False, "model_slot": 2},
        error=None,
        started_at=None,
        completed_at=None,
    )

    filing = SimpleNamespace(
        id=filing_id,
        ticker="AAPL",
        cik="0000320193",
        form_type="8-K",
        filing_date=date(2025, 1, 15),
        accession_number="0001234567-25-000002",
        raw_content="<html><body><p>Material event.</p></body></html>",
        document_url=None,
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(side_effect=[_Result(job), _Result(filing), _Result(None)])
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def fake_get_db_session():
        yield mock_session

    monkeypatch.setattr(tracking_module, "get_db_session", fake_get_db_session)
    monkeypatch.setattr(tracking_module, "_get_openrouter_api_key", lambda: "sk-or-v1-test")

    async def should_not_be_called():
        raise AssertionError("_choose_openrouter_model should not be called when model_slot is provided")

    monkeypatch.setattr(tracking_module, "_choose_openrouter_model", should_not_be_called)

    called = {}

    def fake_chat_completion(*, api_key, model, prompt):
        called["api_key"] = api_key
        called["model"] = model
        called["prompt"] = prompt
        return ("Analysis text", 10)

    monkeypatch.setattr(tracking_module, "_openrouter_chat_completion", fake_chat_completion)

    await TrackingService().run_analysis_job(job_id)

    assert called["model"] == "slot/model-2"
    assert job.status == "complete"


@pytest.mark.asyncio
async def test_run_analysis_job_uses_explicit_model_override(monkeypatch):
    import services.tracking_service as tracking_module
    from services.tracking_service import TrackingService

    monkeypatch.setenv("OPENROUTER_MODEL_SLOT_1", "slot/model-1")

    job_id = uuid4()
    user_id = uuid4()
    filing_id = uuid4()

    job = SimpleNamespace(
        id=job_id,
        user_id=user_id,
        job_type="analyze",
        status="queued",
        progress=0,
        message=None,
        result={"filing_id": str(filing_id), "force": False, "model_slot": 1, "model": "explicit/model-x"},
        error=None,
        started_at=None,
        completed_at=None,
    )

    filing = SimpleNamespace(
        id=filing_id,
        ticker="AAPL",
        cik="0000320193",
        form_type="8-K",
        filing_date=date(2025, 1, 15),
        accession_number="0001234567-25-000003",
        raw_content="<html><body><p>Event.</p></body></html>",
        document_url=None,
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(side_effect=[_Result(job), _Result(filing), _Result(None)])
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def fake_get_db_session():
        yield mock_session

    monkeypatch.setattr(tracking_module, "get_db_session", fake_get_db_session)
    monkeypatch.setattr(tracking_module, "_get_openrouter_api_key", lambda: "sk-or-v1-test")

    async def should_not_be_called():
        raise AssertionError("_choose_openrouter_model should not be called when model is provided")

    monkeypatch.setattr(tracking_module, "_choose_openrouter_model", should_not_be_called)

    called = {}

    def fake_chat_completion(*, api_key, model, prompt):
        called["model"] = model
        return ("Analysis text", 10)

    monkeypatch.setattr(tracking_module, "_openrouter_chat_completion", fake_chat_completion)

    await TrackingService().run_analysis_job(job_id)

    assert called["model"] == "explicit/model-x"
    assert job.status == "complete"
