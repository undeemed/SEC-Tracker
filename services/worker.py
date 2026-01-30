"""
Celery worker entrypoint.

Run with:
  celery -A services.worker worker --loglevel=info

This is optional. If you don't run a worker, the API can fall back to FastAPI
BackgroundTasks (not recommended for production workloads).
"""

from __future__ import annotations

import asyncio
import os
from uuid import UUID

try:
    from celery import Celery
except ModuleNotFoundError as e:  # pragma: no cover
    Celery = None  # type: ignore[assignment]
    _CELERY_IMPORT_ERROR = e


def _get_broker_url() -> str:
    return (
        os.getenv("CELERY_BROKER_URL")
        or os.getenv("REDIS_URL")
        or "redis://localhost:6379/0"
    )


def _get_result_backend() -> str:
    return (
        os.getenv("CELERY_RESULT_BACKEND")
        or os.getenv("CELERY_BROKER_URL")
        or os.getenv("REDIS_URL")
        or "redis://localhost:6379/0"
    )


def _create_celery_app() -> "Celery":
    if Celery is None:  # pragma: no cover
        raise RuntimeError(
            "Celery is not installed. Add it to requirements and rebuild the image."
        ) from _CELERY_IMPORT_ERROR

    app = Celery(
        "sec_tracker",
        broker=_get_broker_url(),
        backend=_get_result_backend(),
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
    )

    return app


# Celery application instance for `celery -A services.worker ...`
celery = _create_celery_app() if Celery is not None else None  # type: ignore[assignment]


if celery is not None:

    @celery.task(name="sec_tracker.run_tracking_job")
    def run_tracking_job_task(job_id: str) -> None:
        from services.tracking_service import TrackingService

        asyncio.run(TrackingService().run_tracking_job(UUID(job_id)))

    @celery.task(name="sec_tracker.run_analysis_job")
    def run_analysis_job_task(job_id: str) -> None:
        from services.tracking_service import TrackingService

        asyncio.run(TrackingService().run_analysis_job(UUID(job_id)))

