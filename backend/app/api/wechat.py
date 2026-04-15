from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import logging

from ..core.deps import get_current_user
from ..services.wechat_service import WeChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wechat", tags=["wechat"])
wechat_service = WeChatService()


@router.get("/articles")
async def get_all_articles(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
    title_include: str = None,
    title_exclude: str = None,
):
    """
    Get all WeChat articles from wewe-rss
    Supports title filtering
    
    Examples:
    - /api/wechat/articles?title_include=政治
    - /api/wechat/articles?title_exclude=广告
    - /api/wechat/articles?limit=50
    """
    try:
        articles = await wechat_service.get_all_articles(
            limit=limit,
            title_include=title_include,
            title_exclude=title_exclude,
        )
        return {
            "status": "success",
            "count": len(articles),
            "articles": articles,
        }
    except Exception as e:
        logger.error(f"Failed to get articles: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch articles")


@router.get("/accounts/{account_id}/articles")
async def get_account_articles(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
    title_include: str = None,
):
    """
    Get articles from a specific WeChat account
    
    Args:
        account_id: WeChat account ID (e.g., MP_WXS_123)
        limit: Number of articles to return
        title_include: Filter by title substring
    """
    try:
        articles = await wechat_service.get_account_articles(
            account_id=account_id,
            limit=limit,
            title_include=title_include,
        )
        
        if articles is None:
            raise HTTPException(status_code=404, detail="Account not found or no data")
        
        return {
            "status": "success",
            "account_id": account_id,
            "count": len(articles) if isinstance(articles, list) else 1,
            "articles": articles,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get articles for {account_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch articles")


@router.post("/accounts/{account_id}/update")
async def trigger_account_update(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger an update for a specific WeChat account"""
    try:
        success = await wechat_service.trigger_feed_update(account_id)
        if success:
            return {
                "status": "success",
                "message": f"Update triggered for {account_id}",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to trigger update")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger update: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger update")


@router.get("/rss/{account_id}", response_class=Response)
async def get_account_rss(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get articles from specific account as RSS feed
    Raw feed from wewe-rss
    """
    try:
        rss_content = await wechat_service.get_as_rss(account_id)
        if rss_content is None:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        return Response(
            content=rss_content,
            media_type="application/rss+xml; charset=utf-8"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get RSS: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch RSS")


@router.get("/atom/{account_id}", response_class=Response)
async def get_account_atom(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get articles from specific account as Atom feed
    Raw feed from wewe-rss
    """
    try:
        atom_content = await wechat_service.get_as_atom(account_id)
        if atom_content is None:
            raise HTTPException(status_code=404, detail="Feed not found")
        
        return Response(
            content=atom_content,
            media_type="application/atom+xml; charset=utf-8"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Atom: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch Atom")


@router.get("/health")
async def health_check():
    """Check wewe-rss health status"""
    try:
        is_healthy = await wechat_service.health_check()
        if is_healthy:
            return {"status": "healthy", "service": "wewe-rss"}
        else:
            return {"status": "unhealthy", "service": "wewe-rss"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "message": str(e)}
