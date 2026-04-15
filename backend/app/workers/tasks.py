import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict

from app.workers.celery_app import app
from app.services.wechat_service import WeChatService
from app.db.database import SessionLocal
from app.db.models import WeChatArticle, WeChat
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


@app.task(name='app.workers.tasks.sync_wechat_articles', bind=True)
def sync_wechat_articles(self):
    """
    Periodic task: Sync WeChat articles from wewe-rss
    Runs every 10 minutes to fetch latest articles from subscribed accounts
    """
    try:
        logger.info("Starting WeChat article sync...")
        
        # Run async function in sync context
        feeds = asyncio.run(WeChatService.fetch_feeds())
        
        if not feeds:
            logger.warning("No feeds returned from wewe-rss")
            return {
                "status": "warning",
                "message": "No feeds returned",
                "articles_synced": 0,
            }

        db = SessionLocal()
        total_synced = 0
        errors = []

        try:
            # Process each feed
            for feed in feeds:
                # Skip if feed doesn't have required fields
                if not feed.get("feed_id") or not feed.get("title"):
                    logger.warning(f"Skipping invalid feed: {feed}")
                    continue

                source_id = feed["feed_id"]
                
                # Upsert WeChat source
                try:
                    wechat_source = db.query(WeChat).filter_by(account_id=source_id).first()
                    if not wechat_source:
                        wechat_source = WeChat(
                            account_id=source_id,
                            name=feed.get("title", source_id),
                            description=feed.get("description"),
                            avatar=feed.get("icon"),
                        )
                        db.add(wechat_source)
                        db.commit()
                    else:
                        # Update last sync time
                        wechat_source.last_sync = datetime.now(timezone.utc)
                        db.commit()
                except Exception as e:
                    logger.error(f"Failed to upsert WeChat source {source_id}: {e}")
                    errors.append(f"Source error: {source_id}")
                    continue

                # Process articles
                articles = feed.get("articles", [])
                logger.info(f"Processing {len(articles)} articles from {source_id}")

                for article_data in articles:
                    try:
                        # Skip if already exists
                        external_id = article_data.get("id")
                        if not external_id:
                            continue

                        existing = db.query(WeChatArticle).filter_by(
                            external_id=external_id
                        ).first()

                        if existing:
                            continue  # Article already in DB

                        # Parse and insert new article
                        parsed = WeChatService.parse_article_from_feed(article_data, source_id)
                        new_article = WeChatArticle(
                            title=parsed["title"],
                            content=parsed["content"],
                            author=parsed.get("author"),
                            source_id=source_id,
                            external_id=parsed["external_id"],
                            link=parsed["link"],
                            pub_date=parsed["pub_date"],
                        )
                        db.add(new_article)
                        total_synced += 1

                    except IntegrityError:
                        # Article already exists, skip
                        db.rollback()
                        continue
                    except Exception as e:
                        logger.error(f"Failed to process article {external_id}: {e}")
                        db.rollback()
                        errors.append(f"Article error: {external_id}")
                        continue

                # Commit all articles for this feed
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Failed to commit articles for {source_id}: {e}")
                    db.rollback()
                    errors.append(f"Commit error: {source_id}")

        finally:
            db.close()

        result = {
            "status": "success",
            "articles_synced": total_synced,
            "feeds_processed": len(feeds),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if errors:
            result["errors"] = errors
            result["status"] = "partial"

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
