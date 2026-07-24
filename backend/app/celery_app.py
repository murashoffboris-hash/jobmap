"""Celery worker application — task queue for background jobs.

Tasks:
  - send_notification: push / email / SMS notifications
  - expire_vacancies: mark expired vacancies (cron)
  - process_geocode_batch: batch geocoding for unlocated vacancies

Usage (Docker):
    celery -A app.celery_app worker -l info -c 2
"""

from __future__ import annotations

import logging

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "jobmap",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],  # optional: task modules to auto-discover
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Minsk",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=300,
    task_time_limit=600,
    worker_max_tasks_per_child=200,
)


@celery_app.task(bind=True, max_retries=3)
def debug_task(self) -> str:
    """Debug task — verify the worker is alive."""
    logger.info("Celery worker heartbeat: request=%s", self.request)
    return "ok"
