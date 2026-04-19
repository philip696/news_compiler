"""
Scheduler for background jobs: Hacker News scraping, WeChat article sync.
Run this as a separate process or in its own thread.
"""
import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

logger = logging.getLogger(__name__)


class BackgroundJobScheduler:
    """Manages scheduled background tasks."""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def start_scheduler(self):
        """Start the background scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        # Hacker News scraper runs daily at 2 AM UTC
        self.scheduler.add_job(
            self._scrape_hacker_news,
            CronTrigger(hour=2, minute=0),
            id="hacker_news_scraper",
            name="Scrape Hacker News (Daily 2 AM UTC)",
            replace_existing=True,
            max_instances=1,
        )
        
        # WeChat sync runs every 10 minutes
        self.scheduler.add_job(
            self._sync_wechat_articles,
            CronTrigger(minute="*/10"),
            id="wechat_sync_all_accounts",
            name="Sync WeChat Articles (Every 10 minutes)",
            replace_existing=True,
            max_instances=1,
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info("✅ Background scheduler started")
        logger.info("   📅 Jobs scheduled:")
        logger.info("      - Hacker News scraper (Daily at 2 AM UTC)")
        logger.info("      - WeChat article sync (Every 10 minutes)")
    
    def stop_scheduler(self):
        """Stop the background scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Background scheduler stopped")
    
    @staticmethod
    def _scrape_hacker_news():
        """Scrape Hacker News."""
        try:
            logger.info("[SCHEDULER] Running Hacker News scraper...")
            # Import inside to avoid circular imports
            from workers.hacker_news_scraper import HackerNewsScraper
            scraper = HackerNewsScraper()
            scraper.scrape()
            logger.info("[SCHEDULER] Hacker News scraper completed")
        except Exception as e:
            logger.error(f"[SCHEDULER] Hacker News scraper error: {e}")
    
    @staticmethod
    def _sync_wechat_articles():
        """Sync WeChat articles."""
        try:
            logger.info("[SCHEDULER] Running WeChat article sync...")
            # Import inside to avoid circular imports
            from app.workers.wechat_scheduler import job_sync_all_accounts
            asyncio.run(job_sync_all_accounts())
            logger.info("[SCHEDULER] WeChat article sync completed")
        except Exception as e:
            logger.error(f"[SCHEDULER] WeChat article sync error: {e}")


_scheduler_instance = None


def get_scheduler_instance() -> BackgroundJobScheduler:
    """Get or create scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackgroundJobScheduler()
    return _scheduler_instance
