"""API endpoints for WeWe-RSS integration."""

from fastapi import APIRouter, Depends, HTTPException, Query
import logging
from typing import Optional

from .. import state
from ..core.deps import get_current_user
from ..schemas import MessageResponse
from ..services.wewe_rss_service import WeWeRSSClient, parse_wewe_rss_feed

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wewe-rss", tags=["wewe-rss"])

wewe_rss_client = WeWeRSSClient()


@router.get("/health")
async def health_check() -> dict:
    """Check if WeWe-RSS service is available."""
    is_healthy = await wewe_rss_client.get_health_status()
    if is_healthy:
        return {"status": "healthy", "service": "wewe-rss"}
    else:
        raise HTTPException(status_code=503, detail="WeWe-RSS service unavailable")


@router.get("/feeds/all")
async def get_all_feeds(
    format: str = Query("json", pattern="^(json|rss|atom)$"),
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Fetch all aggregated WeChat feeds.
    
    Args:
        format: Output format (json, rss, atom)
        
    Returns:
        All WeChat feeds aggregated
    """
    try:
        feeds = await wewe_rss_client.get_all_feeds(format=format)
        if "error" in feeds:
            raise HTTPException(status_code=502, detail=feeds["error"])
        return feeds
    except Exception as e:
        logger.error(f"Error fetching all WeWe-RSS feeds: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch feeds")


@router.get("/feeds/{feed_id}")
async def get_feed(
    feed_id: str,
    format: str = Query("json", pattern="^(json|rss|atom)$"),
    limit: int = Query(30, ge=1, le=100),
    title_include: Optional[str] = Query(None),
    title_exclude: Optional[str] = Query(None),
    update: bool = Query(False),
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Fetch a specific WeChat feed with optional filtering.
    
    Args:
        feed_id: WeChat Official Account identifier
        format: Output format (json, rss, atom)
        limit: Max articles to return (1-100)
        title_include: Keywords to include (pipe-separated)
        title_exclude: Keywords to exclude (pipe-separated)
        update: Trigger manual feed update
        
    Returns:
        Filtered feed data
    """
    try:
        if update:
            # Trigger manual update first
            await wewe_rss_client.trigger_feed_update(feed_id)
        
        feeds = await wewe_rss_client.get_feed_with_filter(
            feed_id=feed_id,
            title_include=title_include,
            title_exclude=title_exclude,
            limit=limit
        )
        
        if "error" in feeds:
            raise HTTPException(status_code=502, detail=feeds["error"])
        
        return feeds
    except Exception as e:
        logger.error(f"Error fetching WeWe-RSS feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch feed")


@router.post("/feeds/{feed_id}/update")
async def update_feed(
    feed_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """Manually trigger an update for a specific feed.
    
    Args:
        feed_id: WeChat Official Account identifier
        
    Returns:
        Update status message
    """
    try:
        result = await wewe_rss_client.trigger_feed_update(feed_id)
        if "error" in result:
            raise HTTPException(status_code=502, detail=result["error"])
        return {"message": f"Update triggered for {feed_id}"}
    except Exception as e:
        logger.error(f"Error updating WeWe-RSS feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update feed")


@router.get("/feeds/{feed_id}/articles", response_model=list)
async def get_feed_articles(
    feed_id: str,
    limit: int = Query(30, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
) -> list:
    """Get articles from a WeChat feed in GEB format.
    
    Args:
        feed_id: WeChat Official Account identifier
        limit: Max articles to return
        
    Returns:
        List of articles in GEB format
    """
    try:
        feed_data = await wewe_rss_client.get_feeds(feed_id, limit=limit)
        if "error" in feed_data:
            raise HTTPException(status_code=502, detail=feed_data["error"])
        
        articles = parse_wewe_rss_feed(feed_data)
        return articles[:limit]
    except Exception as e:
        logger.error(f"Error fetching articles from feed {feed_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch articles")


@router.get("/status")
async def get_integration_status() -> dict:
    """Get WeWe-RSS integration status."""
    is_healthy = await wewe_rss_client.get_health_status()
    return {
        "integrated": True,
        "enabled": is_healthy,
        "service_url": wewe_rss_client.base_url,
        "status": "healthy" if is_healthy else "unavailable"
    }
