"""
Scheduler for background jobs like Hacker News scraping.
Run this as a separate process or in its own thread.
"""
import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from workers.hacker_news_scraper import HackerNewsScraper

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
        
        # Schedule Hacker News scraper
        # Runs every day at 2 AM UTC (customize as needed)
        self.scheduler.add_job(
            self._scrape_hacker_news,
            trigger=CronTrigger(hour=2, minute=0),
            id="hacker_news_daily",
            name="Fetch Hacker News (Daily)",
            replace_existing=True,
            max_instances=1,  # Prevent overlap
        )
        
        # Optional: Run every 6 hours instead
        # self.scheduler.add_job(
        #     self._scrape_hacker_news,
        #     trigger=CronTrigger(hour='*/6'),
        #     id="hacker_news_6hourly",
        #     name="Fetch Hacker News (Every 6 hours)",
        #     max_instances=1,
        # )
        
        self.scheduler.start()
        self.is_running = True
        logger.info("✅ Background scheduler started")
        logger.info("   📅 Job scheduled: Hacker News scraping at 02:00 UTC daily")
    
    def stop_scheduler(self):
        """Stop the background scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Background scheduler stopped")
    
    @staticmethod
    def _scrape_hacker_news():
        """
        Task: Scrape Hacker News from Firebase API.
        Runs async task in sync context.
        """
        timestamp = datetime.utcnow().isoformat()
        logger.info(f"[{timestamp}] 🚀 Starting Hacker News scrape...")
        
        try:
            scraper = HackerNewsScraper()
            
            # Run async scraper
            count = asyncio.run(scraper.fetch_and_process(
                story_type="top",  # Options: "top", "new", "best"
                limit=50            # Fetch top 50 stories
            ))
            
            logger.info(f"[{datetime.utcnow().isoformat()}] ✅ Hacker News scrape completed. Processed {count} items")
        except Exception as e:
            logger.error(f"[{datetime.utcnow().isoformat()}] ❌ Hacker News scrape failed: {e}", exc_info=True)
    
    def get_jobs(self):
        """List all scheduled jobs."""
        return self.scheduler.get_jobs()


# Global scheduler instance
_scheduler_instance = None


def get_scheduler() -> BackgroundJobScheduler:
    """Get or create scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackgroundJobScheduler()
    return _scheduler_instance
