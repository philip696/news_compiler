from celery import Celery
import os
from celery.schedules import crontab

# Initialize Celery app
app = Celery(
    'geb',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
)

# Configure Celery
app.conf.update(
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_prefetch_multiplier=1,
)

# Periodic tasks schedule
app.conf.beat_schedule = {
    'sync-wechat-articles-every-10-minutes': {
        'task': 'app.workers.tasks.sync_wechat_articles',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
}

if __name__ == '__main__':
    app.start()
