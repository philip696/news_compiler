"""
WeChat Article Fetching and Caching Service

Provides methods for:
- Fetching articles from WeChat API
- Caching articles with TTL
- Retrieving cached articles
- Full-text search across cached articles
- Client-side filtering by keywords
"""

import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.wechat import WeChatArticle, WeChatAuth, WeChatSubscription
from app.utils.sanitizer import (
    sanitize_article_content,
    sanitize_article_title,
    sanitize_article_summary
)

logger = logging.getLogger(__name__)

# Default cache TTL is 24 hours
DEFAULT_CACHE_TTL_HOURS = 24

# Timestamp format for parsing
ISO8601_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class WeChatAPIClient:
    """Client for fetching and caching WeChat articles"""

    def __init__(self, db: Session, wechat_api_url: Optional[str] = None):
        """
        Initialize WeChat API client
        
        Args:
            db: SQLAlchemy session for database operations
            wechat_api_url: WeChat API URL (optional, uses mock if not provided)
        """
        self.db = db
        self.wechat_api_url = wechat_api_url
        self.timeout = 30.0

    def _call_wechat_api(
        self,
        account_id: int,
        limit: int = 50,
        **kwargs
    ) -> List[Dict]:
        """
        Call WeChat API to fetch articles
        
        This is a hook for mocking in tests. In production, this would call
        the actual WeChat API or wewe-rss proxy.
        
        Args:
            account_id: WeChat account ID
            limit: Number of articles to fetch
            **kwargs: Additional parameters for the API
            
        Returns:
            List of article dicts
        """
        logger.info(f"Calling WeChat API for account {account_id} with limit {limit}")
        
        if not self.wechat_api_url:
            return []
        
        try:
            # Would call actual API here
            # For now, return empty to allow mocking
            return []
        except Exception as e:
            logger.error(f"Error calling WeChat API: {e}")
            return []

    def fetch_articles_for_account(
        self,
        wechat_account_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """
        Fetch articles from WeChat API for a specific account
        
        Args:
            wechat_account_id: WeChat account ID
            limit: Maximum articles to fetch (default 50)
            
        Returns:
            List of article dicts with:
            - article_id: Unique article ID
            - title: Article title
            - content: Full article content
            - summary: Article summary
            - author: Article author
            - publish_time: Publish timestamp (datetime object)
            - article_url: Article URL
            - image_url: Featured image URL (optional)
        """
        try:
            logger.info(f"Fetching articles for account {wechat_account_id} (limit={limit})")
            
            # Call API (can be mocked in tests)
            articles = self._call_wechat_api(
                account_id=wechat_account_id,
                limit=limit
            )
            
            # Parse timestamps from ISO8601 strings to datetime objects
            parsed_articles = []
            for article in articles:
                # Parse publish_time if it's a string
                if isinstance(article.get("publish_time"), str):
                    try:
                        # Try ISO8601 format first (e.g., "2026-04-18T10:00:00Z")
                        article["publish_time"] = datetime.fromisoformat(
                            article["publish_time"].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        logger.warning(f"Could not parse timestamp: {article.get('publish_time')}")
                        article["publish_time"] = datetime.now(timezone.utc)
                
                parsed_articles.append(article)
            
            logger.info(f"Fetched {len(parsed_articles)} articles")
            return parsed_articles
            
        except Exception as e:
            logger.error(f"Error fetching articles for account {wechat_account_id}: {e}")
            return []

    def cache_articles(
        self,
        wechat_account_id: int,
        articles: List[Dict],
        cache_ttl_hours: int = DEFAULT_CACHE_TTL_HOURS
    ) -> int:
        """
        Cache articles in database
        
        Batch inserts articles, skipping duplicates by article_url.
        Sets expires_at to now + TTL.
        
        Args:
            wechat_account_id: WeChat account ID to cache articles for
            articles: List of article dicts (from fetch_articles_for_account)
            cache_ttl_hours: Cache TTL in hours (default 24)
            
        Returns:
            Number of new articles cached
        """
        try:
            logger.info(f"Caching {len(articles)} articles for account {wechat_account_id}")
            
            # Use naive datetime for SQLite compatibility
            now = datetime.now()
            expires_at = now + timedelta(hours=cache_ttl_hours)
            cached_count = 0
            
            for article_data in articles:
                try:
                    # Check if article already exists (by article_id + account_id)
                    existing = self.db.query(WeChatArticle).filter(
                        and_(
                            WeChatArticle.article_id == article_data.get("article_id"),
                            WeChatArticle.wechat_account_id == wechat_account_id
                        )
                    ).first()
                    
                    if existing:
                        logger.debug(f"Article {article_data.get('article_id')} already cached")
                        # Refresh expiry
                        existing.expires_at = expires_at
                        self.db.commit()
                        continue
                    
                    # Parse publish_time if it's a string
                    publish_time = article_data.get("publish_time", now)
                    if isinstance(publish_time, str):
                        try:
                            parsed = datetime.fromisoformat(
                                publish_time.replace("Z", "+00:00")
                            )
                            # Convert to naive datetime for SQLite
                            publish_time = parsed.replace(tzinfo=None)
                        except (ValueError, AttributeError):
                            logger.warning(f"Could not parse timestamp: {publish_time}")
                            publish_time = now
                    elif hasattr(publish_time, 'tzinfo') and publish_time.tzinfo is not None:
                        # Convert timezone-aware to naive
                        publish_time = publish_time.replace(tzinfo=None)
                    
                    # Create new article record
                    cached_article = WeChatArticle(
                        article_id=article_data.get("article_id"),
                        wechat_account_id=wechat_account_id,
                        title=sanitize_article_title(article_data.get("title", "")),
                        content=sanitize_article_content(article_data.get("content", "")),
                        summary=sanitize_article_summary(article_data.get("summary")),
                        author=article_data.get("author"),
                        publish_time=publish_time,
                        article_url=article_data.get("article_url", ""),
                        image_url=article_data.get("image_url"),
                        video_url=article_data.get("video_url"),
                        cached_at=now,
                        expires_at=expires_at,
                        source_type="wechat"
                    )
                    
                    self.db.add(cached_article)
                    cached_count += 1
                    
                except Exception as e:
                    logger.error(f"Error caching article: {e}")
                    continue
            
            self.db.commit()
            logger.info(f"Cached {cached_count} new articles")
            return cached_count
            
        except Exception as e:
            logger.error(f"Error caching articles: {e}")
            self.db.rollback()
            return 0

    def get_cached_articles(
        self,
        wechat_account_id: int,
        limit: int = 50
    ) -> Dict:
        """
        Get cached articles for account
        
        Returns non-expired articles sorted by publish_time DESC.
        
        Args:
            wechat_account_id: WeChat account ID
            limit: Maximum articles to return (default 50)
            
        Returns:
            Dict with:
            - articles: List of article dicts
            - cached_at: When articles were cached (datetime)
            - expires_at: When cache expires (datetime)
        """
        try:
            logger.info(f"Getting cached articles for account {wechat_account_id}")
            
            now = datetime.now()
            
            # Query non-expired articles, sorted by publish_time DESC
            articles = self.db.query(WeChatArticle).filter(
                and_(
                    WeChatArticle.wechat_account_id == wechat_account_id,
                    WeChatArticle.expires_at > now
                )
            ).order_by(desc(WeChatArticle.publish_time)).limit(limit).all()
            
            # Get cache metadata from newest article
            cached_at = None
            expires_at = None
            if articles:
                cached_at = articles[0].cached_at
                expires_at = articles[0].expires_at
            else:
                # Even if no articles, return metadata
                cached_at = now
                expires_at = now + timedelta(hours=DEFAULT_CACHE_TTL_HOURS)
            
            # Convert to dict format
            articles_data = [
                {
                    "id": a.id,
                    "article_id": a.article_id,
                    "wechat_account_id": a.wechat_account_id,
                    "title": a.title,
                    "content": a.content,
                    "summary": a.summary,
                    "author": a.author,
                    "publish_time": a.publish_time.isoformat() if a.publish_time else None,
                    "article_url": a.article_url,
                    "image_url": a.image_url,
                    "video_url": a.video_url,
                }
                for a in articles
            ]
            
            result = {
                "articles": articles_data,
                "cached_at": cached_at,
                "expires_at": expires_at,
            }
            
            logger.info(f"Returned {len(articles_data)} cached articles")
            return result
            
        except Exception as e:
            logger.error(f"Error getting cached articles: {e}")
            return {"articles": [], "cached_at": None, "expires_at": None}

    def search_articles(
        self,
        user_id: int,
        query: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search cached articles for a user
        
        Performs full-text search across title, content, and summary.
        Only searches articles from accounts the user is subscribed to.
        
        Args:
            user_id: User ID to search for
            query: Search query string
            limit: Maximum results to return (default 50)
            
        Returns:
            List of matching article dicts sorted by relevance
        """
        try:
            logger.info(f"Searching articles for user {user_id} with query: {query}")
            
            # Get user's WeChat auth
            wechat_auth = self.db.query(WeChatAuth).filter(
                WeChatAuth.user_id == user_id
            ).first()
            
            if not wechat_auth:
                logger.warning(f"User {user_id} has no WeChat auth")
                return []
            
            # Get user's subscribed accounts
            subscriptions = self.db.query(WeChatSubscription).filter(
                and_(
                    WeChatSubscription.wechat_auth_id == wechat_auth.id,
                    WeChatSubscription.unsubscribed_at.is_(None)
                )
            ).all()
            
            subscribed_account_ids = [s.wechat_account_id for s in subscriptions]
            
            if not subscribed_account_ids:
                logger.info(f"User {user_id} has no subscriptions")
                return []
            
            # Search articles in subscribed accounts
            now = datetime.now()
            query_lower = query.lower()
            
            # Use SQLite's LIKE operator for case-insensitive search
            articles = self.db.query(WeChatArticle).filter(
                and_(
                    WeChatArticle.wechat_account_id.in_(subscribed_account_ids),
                    WeChatArticle.expires_at > now,
                    or_(
                        WeChatArticle.title.ilike(f"%{query_lower}%"),
                        WeChatArticle.content.ilike(f"%{query_lower}%"),
                        WeChatArticle.summary.ilike(f"%{query_lower}%"),
                        WeChatArticle.author.ilike(f"%{query_lower}%")
                    )
                )
            ).order_by(desc(WeChatArticle.publish_time)).limit(limit).all()
            
            # Convert to dict format
            results = [
                {
                    "id": a.id,
                    "article_id": a.article_id,
                    "wechat_account_id": a.wechat_account_id,
                    "title": a.title,
                    "content": a.content,
                    "summary": a.summary,
                    "author": a.author,
                    "publish_time": a.publish_time.isoformat() if a.publish_time else None,
                    "article_url": a.article_url,
                    "image_url": a.image_url,
                }
                for a in articles
            ]
            
            logger.info(f"Found {len(results)} matching articles")
            return results
            
        except Exception as e:
            logger.error(f"Error searching articles: {e}")
            return []

    def filter_articles(
        self,
        articles: List[Dict],
        include_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Client-side filtering of articles by keywords
        
        Filters articles based on include/exclude keywords.
        Searches in title, content, summary, and author.
        
        Args:
            articles: List of article dicts to filter
            include_keywords: Keywords to include (match any, case-insensitive)
            exclude_keywords: Keywords to exclude (remove if any match, case-insensitive)
            
        Returns:
            Filtered list of articles in original order
        """
        try:
            if not articles:
                return []
            
            filtered = articles
            
            # Apply include filter
            if include_keywords:
                include_lower = [kw.lower() for kw in include_keywords]
                filtered = [
                    a for a in filtered
                    if any(
                        kw in (a.get("title", "") + " " + 
                               a.get("content", "") + " " + 
                               a.get("summary", "") + " " + 
                               a.get("author", "")).lower()
                        for kw in include_lower
                    )
                ]
            
            # Apply exclude filter
            if exclude_keywords:
                exclude_lower = [kw.lower() for kw in exclude_keywords]
                filtered = [
                    a for a in filtered
                    if not any(
                        kw in (a.get("title", "") + " " + 
                               a.get("content", "") + " " + 
                               a.get("summary", "") + " " + 
                               a.get("author", "")).lower()
                        for kw in exclude_lower
                    )
                ]
            
            logger.info(f"Filtered articles: {len(articles)} → {len(filtered)}")
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering articles: {e}")
            return articles
