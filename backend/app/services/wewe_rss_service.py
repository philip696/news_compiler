"""Service for integrating WeWe-RSS (WeChat Official Account RSS feeds)."""

import httpx
import logging
from typing import Optional
from datetime import datetime, timezone
from ..core.config import settings
from app.utils.sanitizer import (
    sanitize_article_content,
    sanitize_article_title,
    sanitize_article_summary
)

logger = logging.getLogger(__name__)

WEWE_RSS_TIMEOUT = 30  # seconds


class WeWeRSSClient:
    """Client for WeWe-RSS API."""

    def __init__(self, base_url: str = None, auth_code: str = None):
        self.base_url = base_url or settings.WEWE_RSS_URL
        self.auth_code = auth_code or settings.WEWE_RSS_AUTH_CODE
        self.headers = {}
        if self.auth_code:
            self.headers["Authorization"] = f"Bearer {self.auth_code}"

    async def get_feeds(self, feed_id: str, format: str = "json", limit: int = 30) -> dict:
        """Fetch RSS feed from wewe-rss.
        
        Args:
            feed_id: Feed identifier (e.g., MP_WXS_123)
            format: Output format (json, rss, atom)
            limit: Number of articles to fetch
            
        Returns:
            dict containing feed data
        """
        try:
            url = f"{self.base_url}/feeds/{feed_id}.{format}"
            params = {"limit": limit}
            
            async with httpx.AsyncClient(timeout=WEWE_RSS_TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=self.headers)
            resp.raise_for_status()
                
                if format == "json":
                return resp.json()
                else:
                    # For RSS/ATOM, parse as XML
                    return {"raw": resp.text}
        except httpx.HTTPError as e:
            logger.error(f"Error fetching WeWe-RSS feed {feed_id}: {e}")
            raise RuntimeError(f"Failed to fetch WeWe-RSS feed '{feed_id}'") from e

    async def get_all_feeds(self, format: str = "json") -> dict:
        """Fetch all aggregated feeds.
        
        Args:
            format: Output format (json, rss, atom)
            
        Returns:
            dict containing all feeds
        """
        try:
            url = f"{self.base_url}/feeds/all.{format}"
            
            async with httpx.AsyncClient(timeout=WEWE_RSS_TIMEOUT) as client:
                resp = await client.get(url, headers=self.headers)
                resp.raise_for_status()
                
                if format == "json":
                    return resp.json()
                else:
                    return {"raw": resp.text}
        except httpx.HTTPError as e:
            logger.error(f"Error fetching all WeWe-RSS feeds: {e}")
            raise RuntimeError("Failed to fetch all WeWe-RSS feeds") from e

    async def trigger_feed_update(self, feed_id: str) -> dict:
        """Manually trigger an update for a specific feed.
        
        Args:
            feed_id: Feed identifier
            
        Returns:
            dict with update status
        """
        try:
            url = f"{self.base_url}/feeds/{feed_id}.json"
            params = {"update": "true"}
            
            async with httpx.AsyncClient(timeout=WEWE_RSS_TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=self.headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Error triggering WeWe-RSS update for {feed_id}: {e}")
            raise RuntimeError(f"Failed to trigger WeWe-RSS update for '{feed_id}'") from e

    async def get_feed_with_filter(
        self,
        feed_id: str,
        title_include: Optional[str] = None,
        title_exclude: Optional[str] = None,
        limit: int = 30
    ) -> dict:
        """Fetch feed with title filtering.
        
        Args:
            feed_id: Feed identifier
            title_include: Include articles with these keywords (pipe-separated)
            title_exclude: Exclude articles with these keywords (pipe-separated)
            limit: Number of articles to fetch
            
        Returns:
            dict containing filtered feed data
        """
        try:
            url = f"{self.base_url}/feeds/{feed_id}.json"
            params = {"limit": limit}
            
            if title_include:
                params["title_include"] = title_include
            if title_exclude:
                params["title_exclude"] = title_exclude
            
            async with httpx.AsyncClient(timeout=WEWE_RSS_TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=self.headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching WeWe-RSS feed with filter: {e}")
            raise RuntimeError(f"Failed to fetch filtered WeWe-RSS feed '{feed_id}'") from e

    async def get_health_status(self) -> bool:
        """Check if WeWe-RSS service is healthy.
        
        Returns:
            bool indicating service availability
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/", headers=self.headers)
                return resp.status_code == 200
        except Exception as e:
            logger.warning(f"WeWe-RSS health check failed: {e}")
            return False


def parse_wewe_rss_feed(feed_data: dict, source_id: str = "wechat_official") -> list[dict]:
    """Convert WeWe-RSS feed data to GEB article format.
    
    Args:
        feed_data: Feed data from wewe-rss API
        source_id: Source identifier for GEB
        
    Returns:
        list of article dicts in GEB format
    """
    articles = []
    
    if "error" in feed_data or not isinstance(feed_data, dict):
        raise ValueError("Invalid WeWe-RSS payload")
    
    items = feed_data.get("items", [])
    if not items and "data" in feed_data:
        items = feed_data.get("data", [])

    if not items:
        raise ValueError("WeWe-RSS payload contains no items")

    for item in items:
        try:
        article = {
                "id": item.get("id") or item.get("guid") or item.get("link", ""),
                "title": sanitize_article_title(item.get("title", "Untitled")),
                "summary": sanitize_article_summary(item.get("description") or item.get("summary", "")),
                "link": item.get("link") or item.get("url", ""),
                "source": source_id,
                "domain": "weixin",
                "image_url": item.get("image") or item.get("thumbnail", ""),
                "published_at": item.get("pubDate") or item.get("published") or datetime.now(timezone.utc).isoformat(),
                "author": item.get("author", "WeChat Official Account"),
                "category": "wechat",
        }
        articles.append(article)
        except Exception as e:
            logger.error(f"Error parsing WeWe-RSS item: {e}")
            raise ValueError("Failed to parse WeWe-RSS item") from e

    return articles
