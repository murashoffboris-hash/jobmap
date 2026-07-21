"""Celery application for background tasks."""

from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "jobmap",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True)
def sample_task(self):
    """Placeholder background task."""
    return "ok"
