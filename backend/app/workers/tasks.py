import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict

from app.workers.celery_app import app
from app.services.wewe_rss_service import WeWeRSSClient, parse_wewe_rss_feed
from app.db.database import SessionLocal
from app.db.models import WeChatArticle, WeChat
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


@app.task(name='app.workers.tasks.sync_wechat_articles', bind=True)
def sync_wechat_articles(self):
    """
    Periodic task: Sync WeChat articles from wewe-rss gateway
    Runs every 10 minutes to fetch latest articles from subscribed accounts
    """
    try:
        logger.info("Starting WeChat article sync from WeWe-RSS gateway...")
        
        # Run async function in sync context using the new gateway
        wewe_client = WeWeRSSClient()
        feeds = asyncio.run(wewe_client.get_all_feeds(format="json"))
        
        if not feeds:
            logger.warning("No feeds returned from WeWe-RSS gateway")
            return {
                "status": "warning",
                "message": "No feeds returned",
                "articles_synced": 0,
            }

        db = SessionLocal()
        total_synced = 0
        errors = []

        try:
            # Parse feeds using the gateway response parser
            articles = parse_wewe_rss_feed(
                {"feeds": feeds} if not isinstance(feeds, list) else {"feeds": feeds}
            )
            
            logger.info(f"Processing {len(articles)} articles from WeWe-RSS gateway")

            for article_data in articles:
                try:
                    external_id = article_data.get("id") or article_data.get("article_id")
                    if not external_id:
                        logger.warning("Skipping article without ID")
                        continue

                    existing = db.query(WeChatArticle).filter_by(
                        external_id=external_id
                    ).first()

                    if existing:
                        continue  # Article already in DB

                    source_id = article_data.get("source_id", "wechat_official")
                    
                    new_article = WeChatArticle(
                        title=article_data.get("title"),
                        content=article_data.get("content"),
                        author=article_data.get("author"),
                        source_id=source_id,
                        external_id=external_id,
                        link=article_data.get("link") or article_data.get("url"),
                        pub_date=article_data.get("published_at") or article_data.get("pub_date"),
                    )
                    db.add(new_article)
                    total_synced += 1

                except IntegrityError:
                    db.rollback()
                    continue
                except Exception as e:
                    logger.error(f"Failed to process article {external_id}: {e}")
                    db.rollback()
                    errors.append(f"Article error: {external_id}")
                    continue

            # Commit all articles
            try:
                db.commit()
            except Exception as e:
                logger.error(f"Failed to commit articles: {e}")
                db.rollback()
                errors.append("Commit error")

        finally:
            db.close()

        result = {
            "status": "success",
            "articles_synced": total_synced,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if errors:
            result["errors"] = errors
            result["status"] = "partial" if total_synced > 0 else "error"

        logger.info(f"WeChat sync complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Fatal error in sync_wechat_articles: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "articles_synced": 0,
        }


@app.task(name='app.workers.tasks.get_wechat_health')
def get_wechat_health():
    """Health check task for wewe-rss connectivity"""
    try:
        db = SessionLocal()
        try:
            # Check if we have any WeChat data
            wechat_count = db.query(WeChat).count()
            article_count = db.query(WeChatArticle).count()
            
            return {
                "status": "healthy",
                "wechat_accounts": wechat_count,
                "articles_total": article_count,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
