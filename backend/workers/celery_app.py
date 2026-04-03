from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "news_workers",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.beat_schedule = {
    "ingest-every-5-min": {
        "task": "workers.tasks.ingest_task",
        "schedule": 300.0,
    },
    "cluster-every-10-min": {
        "task": "workers.tasks.cluster_task",
        "schedule": 600.0,
    },
}
