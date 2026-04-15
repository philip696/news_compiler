"""
Hacker News scraper using the official Firebase API.
Free, real-time, no authentication required.
API Docs: https://github.com/HackerNews/API
"""
import logging
from datetime import datetime
from pathlib import Path
import json
from typing import Optional, List, Dict
import asyncio

import httpx

logger = logging.getLogger(__name__)


class HackerNewsScraper:
    """Scraper for official Hacker News Firebase API."""
    
    # Official HN Firebase API (free, no auth required)
    API_BASE = "https://hacker-news.firebaseio.com/v0"
    CACHE_DIR = Path(__file__).parent.parent / "data" / "hacker_news_cache"
    
    # Story types
    STORY_TYPES = {
        "top": "topstories",        # Best stories
        "new": "newstories",        # Newest stories
        "best": "beststories",      # Highest score
    }
    
    def __init__(self, timeout: int = 30):
        self.cache_dir = self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.timeout = timeout
    
    async def get_story_ids(self, story_type: str = "top", limit: int = 30) -> List[int]:
        """
        Fetch story IDs from HN Firebase API.
        
        Args:
            story_type: "top", "new", or "best"
            limit: Number of stories to fetch (max reasonable: 500)
            
        Returns:
            List of story IDs
        """
        if story_type not in self.STORY_TYPES:
            raise ValueError(f"Invalid story_type. Choose from: {list(self.STORY_TYPES.keys())}")
        
        endpoint = self.STORY_TYPES[story_type]
        url = f"{self.API_BASE}/{endpoint}.json"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                story_ids = response.json()
                return story_ids[:limit]
        except Exception as e:
            logger.error(f"Error fetching {story_type} story IDs: {e}")
            raise
    
    async def get_story_details(self, story_id: int) -> Optional[Dict]:
        """
        Fetch details for a single story.
        
        Args:
            story_id: HN story ID
            
        Returns:
            Story details dict or None if failed
        """
        url = f"{self.API_BASE}/item/{story_id}.json"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Error fetching story {story_id}: {e}")
            return None
    
    async def fetch_stories(self, story_type: str = "top", limit: int = 30) -> List[Dict]:
        """
        Fetch multiple stories in parallel.
        
        Args:
            story_type: "top", "new", or "best"
            limit: Number of stories to fetch
            
        Returns:
            List of story details
        """
        try:
            logger.info(f"Fetching {limit} {story_type} Hacker News stories...")
            
            # Get story IDs first
            story_ids = await self.get_story_ids(story_type, limit)
            logger.info(f"Got {len(story_ids)} story IDs. Fetching details...")
            
            # Fetch all story details in parallel
            tasks = [self.get_story_details(sid) for sid in story_ids]
            stories = await asyncio.gather(*tasks)
            
            # Filter out None values (failed requests)
            stories = [s for s in stories if s is not None]
            logger.info(f"Successfully fetched {len(stories)} story details")
            
            return stories
            
        except Exception as e:
            logger.error(f"Error fetching stories: {e}")
            raise
    
    def transform_to_feed_format(self, stories: List[Dict]) -> List[Dict]:
        """
        Transform HN stories to your feed schema.
        """
        transformed = []
        for story in stories:
            try:
                # Skip stories without titles (deleted/dead items)
                if "title" not in story:
                    continue
                
                # HN timestamps are Unix epoch (seconds)
                published_at = datetime.fromtimestamp(story.get("time", 0)).isoformat()
                
                transformed.append({
                    "title": story.get("title", ""),
                    "url": story.get("url", ""),
                    "source": "Hacker News",
                    "description": story.get("title", ""),  # HN doesn't have descriptions
                    "published_at": published_at,
                    "author": story.get("by", "Anonymous"),
                    "score": story.get("score", 0),
                    "comments": story.get("descendants", 0),
                    "external_id": f"hn_{story.get('id')}",
                    "category": "technology",
                    "external_source": "hacker_news",
                })
            except Exception as e:
                logger.warning(f"Error transforming story: {e}")
                continue
        
        return transformed
    
    def save_checkpoint(self):
        """Record last successful fetch time."""
        metadata = {
            "last_sync": datetime.utcnow().isoformat(),
            "source": "Hacker News Firebase API",
            "api": self.API_BASE,
        }
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f)
    
    async def fetch_and_process(self, story_type: str = "top", limit: int = 50) -> int:
        """
        Main scraper method. Returns count of feed items processed.
        
        Args:
            story_type: "top", "new", or "best"
            limit: Number of stories to fetch
        """
        try:
            # Fetch stories from HN Firebase API
            stories = await self.fetch_stories(story_type, limit)
            
            if not stories:
                logger.warning("No stories fetched")
                return 0
            
            # Transform to your feed format
            feed_items = self.transform_to_feed_format(stories)
            
            # TODO: Save to database via your existing services
            # from app.services.news_service import NewsService
            # news_service = NewsService()
            # for item in feed_items:
            #     news_service.create_news(item)
            
            # Save checkpoint
            self.save_checkpoint()
            
            logger.info(f"Processed {len(feed_items)} Hacker News items")
            return len(feed_items)
            
        except Exception as e:
            logger.error(f"Scraper failed: {e}", exc_info=True)
            return 0


if __name__ == "__main__":
    # Direct run for testing
    import asyncio
    logging.basicConfig(level=logging.INFO)
    scraper = HackerNewsScraper()
    count = asyncio.run(scraper.fetch_and_process())
    print(f"Scraped {count} stories")
