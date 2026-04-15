import httpx
from typing import Optional, List, Any
import os
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

WEWE_RSS_URL = os.getenv("WEWE_RSS_URL", "http://localhost:4000")
CACHE_TIMEOUT = 300  # 5 minutes


class WeChatService:
    """Simple service to fetch WeChat articles directly from wewe-rss API"""

    def __init__(self):
        self.base_url = WEWE_RSS_URL
        self.timeout = 30.0

    async def get_all_articles(
        self,
        limit: int = 100,
        title_include: Optional[str] = None,
        title_exclude: Optional[str] = None,
    ) -> List[dict]:
        """
        Get all WeChat articles from wewe-rss
        Returns JSON format articles directly from the API
        """
        try:
            params = {"limit": limit}
            if title_include:
                params["title_include"] = title_include
            if title_exclude:
                params["title_exclude"] = title_exclude

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/feeds/all.json",
                    params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, list) else [data]
                else:
                    logger.warning(f"wewe-rss returned status {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch all articles: {e}")
            return []

    async def get_account_articles(
        self,
        account_id: str,
        limit: int = 50,
        title_include: Optional[str] = None,
    ) -> Optional[List[dict]]:
        """Get articles from specific WeChat account"""
        try:
            params = {"limit": limit}
            if title_include:
                params["title_include"] = title_include

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/feeds/{account_id}.json",
                    params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, list) else [data]
                return None
        except Exception as e:
            logger.error(f"Failed to fetch articles for {account_id}: {e}")
            return None

    async def trigger_feed_update(self, account_id: str) -> bool:
        """Manually trigger update for a specific feed"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/feeds/{account_id}.rss",
                    params={"update": "true"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to trigger update for {account_id}: {e}")
            return False

    async def get_as_rss(self, account_id: Optional[str] = None) -> Optional[str]:
        """Get articles as RSS feed"""
        try:
            if account_id:
                endpoint = f"{self.base_url}/feeds/{account_id}.rss"
            else:
                endpoint = f"{self.base_url}/feeds/all.rss"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint)
                return response.text if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Failed to fetch RSS: {e}")
            return None

    async def get_as_atom(self, account_id: Optional[str] = None) -> Optional[str]:
        """Get articles as Atom feed"""
        try:
            if account_id:
                endpoint = f"{self.base_url}/feeds/{account_id}.atom"
            else:
                endpoint = f"{self.base_url}/feeds/all.atom"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint)
                return response.text if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Failed to fetch Atom: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if wewe-rss is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"wewe-rss health check failed: {e}")
            return False
