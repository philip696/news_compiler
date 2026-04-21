"""Celery application for GEB background jobs (WeRead feed refresh, etc.)."""

from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

_sync_mins = int(os.getenv("CELERY_WEREAD_SYNC_MINUTES", "10") or "10")
_sync_mins = max(1, min(_sync_mins, 59))

# Name must not be `app`: `import app.workers.tasks` would rebind `app` to the package.
celery_app = Celery(
    "geb",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "sync-weread-feeds": {
        "task": "app.workers.tasks.sync_weread_feeds",
        "schedule": crontab(minute=f"*/{_sync_mins}"),
    },
}

# Import task modules so @celery_app.task decorators register (non-Django app).
import app.workers.tasks  # noqa: E402, F401
