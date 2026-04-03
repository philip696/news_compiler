from workers.celery_app import celery_app
from app.ingestion.loader import ingest_webhose_jsonl
from app.clustering.engine import build_story_clusters


@celery_app.task(name="workers.tasks.ingest_task")
def ingest_task() -> str:
    inserted = ingest_webhose_jsonl()
    return f"Ingested {inserted} articles"


@celery_app.task(name="workers.tasks.cluster_task")
def cluster_task() -> str:
    total = build_story_clusters()
    return f"Built {total} clusters"
