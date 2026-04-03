from fastapi import APIRouter

from ..ingestion.loader import ingest_webhose_jsonl
from ..clustering.engine import build_story_clusters
from ..schemas import MessageResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/ingest", response_model=MessageResponse)
def ingest_dataset():
    inserted = ingest_webhose_jsonl()
    return {"message": f"Ingested {inserted} articles"}


@router.post("/cluster", response_model=MessageResponse)
def cluster_articles():
    total = build_story_clusters()
    return {"message": f"Built {total} clusters"}


@router.post("/rebuild", response_model=MessageResponse)
def rebuild_all():
    inserted = ingest_webhose_jsonl()
    total = build_story_clusters()
    return {"message": f"Ingested {inserted} articles and built {total} clusters"}
