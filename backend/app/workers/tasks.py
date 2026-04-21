from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
import redis

from app.core.config import settings
from app.db.app_repository import AppRepository
from app.db.database import SessionLocal
from app.db.models import WeReadArticle, WeReadFeed
from app.db.supabase_client import get_supabase_client, use_supabase_runtime
from app.services.weread_service import DEFAULT_PLATFORM_URL, WeReadService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_weread_sync(
    repo: AppRepository, user_ids: list[int], platform_url: str
) -> dict[str, Any]:
    timeout = httpx.Timeout(15.0, connect=10.0)
    errors: list[dict[str, Any]] = []
    ok = 0
    async with httpx.AsyncClient(timeout=timeout) as client:
        svc = WeReadService(client=client, platform_url=platform_url)
        for uid in user_ids:
            try:
                await svc.refresh_all_mp_articles_and_update_feed(repo, uid)
                ok += 1
            except Exception as e:
                logger.error(
                    "[celery] weread sync failed user_id=%s: %s", uid, e, exc_info=True
                )
                errors.append({"user_id": uid, "error": str(e)})
    ts = datetime.now(timezone.utc).isoformat()
    if not user_ids:
        return {
            "status": "skipped",
            "message": "no users with weread_feeds",
            "users_total": 0,
            "users_ok": 0,
            "errors": [],
            "timestamp": ts,
        }
    st = "success" if not errors else ("partial" if ok else "error")
    return {
        "status": st,
        "users_total": len(user_ids),
        "users_ok": ok,
        "errors": errors,
        "timestamp": ts,
    }


@celery_app.task(name="app.workers.tasks.sync_weread_feeds")
def sync_weread_feeds() -> dict[str, Any]:
    """Periodic task: refresh WeRead articles for every user that has feeds."""
    platform_url = os.getenv("PLATFORM_URL", DEFAULT_PLATFORM_URL)
    try:
        if use_supabase_runtime():
            repo = AppRepository(supabase=get_supabase_client())
            user_ids = repo.weread_feed_distinct_user_ids()
            logger.info(
                "[celery] sync_weread_feeds (supabase) users=%s", len(user_ids)
            )
            return asyncio.run(_run_weread_sync(repo, user_ids, platform_url))

        db = SessionLocal()
        try:
            repo = AppRepository(session=db)
            user_ids = repo.weread_feed_distinct_user_ids()
            logger.info(
                "[celery] sync_weread_feeds (sqlalchemy) users=%s", len(user_ids)
            )
            return asyncio.run(_run_weread_sync(repo, user_ids, platform_url))
        finally:
            db.close()
    except Exception as e:
        logger.error("[celery] sync_weread_feeds fatal: %s", e, exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "users_total": 0,
            "users_ok": 0,
            "errors": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@celery_app.task(name="app.workers.tasks.weread_celery_health")
def weread_celery_health() -> dict[str, Any]:
    """DB row counts for WeRead tables + Redis broker ping."""
    redis_ok = False
    redis_error: str | None = None
    try:
        r = redis.from_url(settings.celery_broker_url)
        redis_ok = bool(r.ping())
    except Exception as e:
        redis_error = str(e)
        logger.warning("[celery] redis ping failed: %s", e)

    try:
        if use_supabase_runtime():
            sb = get_supabase_client()
            fr = sb.table("weread_feeds").select("id", count="exact").limit(1).execute()
            ar = (
                sb.table("weread_articles").select("id", count="exact").limit(1).execute()
            )
            feed_count = fr.count if fr.count is not None else 0
            article_count = ar.count if ar.count is not None else 0
        else:
            db = SessionLocal()
            try:
                feed_count = db.query(WeReadFeed).count()
                article_count = db.query(WeReadArticle).count()
            finally:
                db.close()

        return {
            "status": "healthy",
            "redis": redis_ok,
            "redis_error": redis_error,
            "weread_feed_rows": feed_count,
            "weread_article_rows": article_count,
        }
    except Exception as e:
        logger.error("[celery] weread_celery_health failed: %s", e, exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "redis": redis_ok,
            "redis_error": redis_error,
        }
