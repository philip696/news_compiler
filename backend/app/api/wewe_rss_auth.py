"""WeWe-RSS authentication and account management for WeChat article integration."""

import httpx
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from ..core.deps import get_current_user
from ..core.config import settings
from ..schemas import MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wewe-rss", tags=["wewe-rss-auth"])

WEWE_RSS_TIMEOUT = 30  # seconds


class WeWeRSSAuthService:
    """Service for WeWe-RSS authentication and account management."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.WEWE_RSS_URL
        
    async def create_login_url(self) -> dict:
        """Create a login URL for WeWe-RSS WeChat authentication.
        
        Calls: GET /api/v2/login/platform
        
        Returns:
            {
                "uuid": "login-session-id",
                "scanUrl": "https://open.weixin.qq.com/connect/oauth2/authorize?..."
            }
        """
        try:
            url = f"{self.base_url}/api/v2/login/platform"
            
            async with httpx.AsyncClient(timeout=WEWE_RSS_TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                logger.info(f"Created WeWe-RSS login URL: {data.get('uuid')}")
                return data
        except httpx.HTTPError as e:
            logger.error(f"Error creating WeWe-RSS login URL: {e}")
            raise RuntimeError("Failed to create WeWe-RSS login URL") from e

    async def get_login_result(self, login_id: str) -> dict:
        """Poll for WeChat login completion.
        
        Calls: GET /api/v2/login/platform/{login_id}
        
        Args:
            login_id: Session ID from create_login_url response
            
        Returns:
            Pending or completed with:
            {
                "message": "pending" | "success message",
                "vid": "account-id",  # Only when completed
                "token": "access-token",  # Only when completed
                "username": "display-name"  # Only when completed
            }
        """
        try:
            url = f"{self.base_url}/api/v2/login/platform/{login_id}"
            
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                if "token" in data and "vid" in data:
                    logger.info(f"WeWe-RSS login completed for account: {data.get('vid')}")
                
                return data
        except httpx.HTTPError as e:
            logger.error(f"Error polling WeWe-RSS login status: {e}")
            raise RuntimeError("Failed to poll WeWe-RSS login status") from e

    async def get_mp_info(self, account_id: str, account_token: str, share_url: str) -> dict:
        """Get WeChat official account info from a share URL.
        
        Requires authenticated WeWe-RSS account.
        Calls: POST /api/v2/platform/wxs2mp
        
        Args:
            account_id: WeWe-RSS account ID (vid)
            account_token: WeWe-RSS account token
            share_url: WeChat article share URL (https://mp.weixin.qq.com/s/...)
            
        Returns:
            List of official account infos: [{id, cover, name, intro, updateTime}]
        """
        try:
            url = f"{self.base_url}/api/v2/platform/wxs2mp"
            headers = {
                "xid": account_id,
                "Authorization": f"Bearer {account_token}"
            }
            
            async with httpx.AsyncClient(timeout=WEWE_RSS_TIMEOUT) as client:
                resp = await client.post(
                    url,
                    json={"url": share_url.strip()},
                    headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
                
                logger.info(f"Retrieved MP info from {share_url}: {len(data)} results")
                return data
        except httpx.HTTPError as e:
            logger.error(f"Error getting MP info from WeWe-RSS: {e}")
            raise RuntimeError("Failed to get WeChat official account info") from e

    async def get_mp_articles(self, account_id: str, account_token: str, mp_id: str, page: int = 1) -> dict:
        """Fetch articles from a WeChat official account.
        
        Requires authenticated WeWe-RSS account.
        Calls: GET /api/v2/platform/mps/{mp_id}/articles
        
        Args:
            account_id: WeWe-RSS account ID (vid)
            account_token: WeWe-RSS account token
            mp_id: WeChat official account ID (e.g., MP_WXS_123)
            page: Page number (default: 1)
            
        Returns:
            List of articles: [{id, title, picUrl, publishTime}]
        """
        try:
            url = f"{self.base_url}/api/v2/platform/mps/{mp_id}/articles"
            headers = {
                "xid": account_id,
                "Authorization": f"Bearer {account_token}"
            }
            
            async with httpx.AsyncClient(timeout=WEWE_RSS_TIMEOUT) as client:
                resp = await client.get(
                    url,
                    params={"page": page},
                    headers=headers
                )
                resp.raise_for_status()
                articles = resp.json()
                
                logger.info(f"Fetched {len(articles)} articles from {mp_id}, page {page}")
                return articles
        except httpx.HTTPError as e:
            logger.error(f"Error fetching MP articles from WeWe-RSS: {e}")
            raise RuntimeError("Failed to fetch articles from WeChat official account") from e


# In-memory store for login sessions (use Redis for production)
# Format: {login_id: {created_at, user_id, account_data}}
login_sessions = {}

# In-memory store for user's WeWe-RSS accounts
# Format: {user_id: [{vid, token, username, created_at}]}
user_wewe_accounts = {}

auth_service = WeWeRSSAuthService()


@router.get("/auth/login-url")
async def get_wechat_login_url(current_user: dict = Depends(get_current_user)) -> dict:
    """Get WeChat login URL from WeWe-RSS platform.
    
    Directly returns the scanUrl from WeWe-RSS's platform.createLoginUrl endpoint.
    User scans this URL's QR code with WeChat app to authenticate.
    
    Returns:
        {
            "status": "success",
            "login_id": "uuid",
            "scan_url": "https://open.weixin.qq.com/connect/oauth2/authorize?...",
            "expires_in": 300
        }
    """
    try:
        user_id = current_user.get("id")
        login_data = await auth_service.create_login_url()
        
        # Store login session
        login_sessions[login_data["uuid"]] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "account_data": None
        }
        
        return {
            "status": "success",
            "login_id": login_data["uuid"],
            "scan_url": login_data["scanUrl"],
            "expires_in": 300  # 5-minute expiration
        }
    except Exception as e:
        logger.error(f"Error getting WeChat login URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/qrcode")
async def create_wechat_login_qr(current_user: dict = Depends(get_current_user)) -> dict:
    """Create WeChat QR code (backwards compatibility alias).
    
    Alias for GET /auth/login-url. Simply calls the GET endpoint.
    """
    return await get_wechat_login_url(current_user)


@router.get("/auth/status")
async def check_wechat_login_status(
    login_id: str = Query(...),
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Poll for WeChat login completion.
    
    Frontend calls this periodically after showing QR code.
    Returns account info when user completes WeChat authorization.
    
    Returns:
        Pending: {"status": "pending"}
        Completed: {
            "status": "completed",
            "account_id": "vid",
            "account_name": "username",
            "access_token": "token"
        }
        Error: {"status": "error", "message": "..."}
    """
    try:
        user_id = current_user.get("id")
        
        # Verify login session exists and belongs to this user
        session = login_sessions.get(login_id)
        if not session:
            return {
                "status": "error",
                "message": "Invalid or expired login session"
            }
        
        if session["user_id"] != user_id:
            return {
                "status": "error",
                "message": "Unauthorized: session does not belong to this user"
            }
        
        # Already completed?
        if session["account_data"]:
            account = session["account_data"]
            return {
                "status": "completed",
                "account_id": account["vid"],
                "account_name": account["username"],
                "access_token": account["token"]
            }
        
        # Poll wewe-rss for login status
        result = await auth_service.get_login_result(login_id)
        
        # Check if login completed
        if "token" in result and "vid" in result:
            # Store account for user
            account_data = {
                "vid": result["vid"],
                "token": result["token"],
                "username": result.get("username", "Unknown"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            session["account_data"] = account_data
            
            # Add to user's account list
            if user_id not in user_wewe_accounts:
                user_wewe_accounts[user_id] = []
            
            user_wewe_accounts[user_id].append(account_data)
            logger.info(f"Added WeWe-RSS account {account_data['vid']} for user {user_id}")
            
            return {
                "status": "completed",
                "account_id": account_data["vid"],
                "account_name": account_data["username"],
                "access_token": account_data["token"]
            }
        
        # Still pending
        message = result.get("message", "Waiting for authorization...")
        return {
            "status": "pending",
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error checking WeChat login status: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/accounts")
async def list_wewe_rss_accounts(current_user: dict = Depends(get_current_user)) -> dict:
    """List all WeWe-RSS accounts connected for current user.
    
    Returns:
        {
            "status": "success",
            "accounts": [
                {
                    "vid": "account-id",
                    "username": "display-name",
                    "created_at": "2024-04-19T..."
                }
            ]
        }
    """
    try:
        user_id = current_user.get("id")
        accounts = user_wewe_accounts.get(user_id, [])
        
        return {
            "status": "success",
            "accounts": [
                {
                    "vid": acc["vid"],
                    "username": acc.get("username", "Unknown"),
                    "created_at": acc.get("created_at")
                }
                for acc in accounts
            ]
        }
    except Exception as e:
        logger.error(f"Error listing WeWe-RSS accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{account_id}/fetch-articles")
async def fetch_wechat_articles(
    account_id: str,
    wx_article_url: str = Query(...),
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Fetch articles from a WeChat official account.
    
    User provides WeChat article share URL, we extract the official account,
    and fetch all their recent articles using their WeWe-RSS account.
    
    Args:
        account_id: WeWe-RSS account ID (vid)
        wx_article_url: WeChat article URL (https://mp.weixin.qq.com/s/...)
        
    Returns:
        {
            "status": "success",
            "official_account": {
                "id": "MP_WXS_123",
                "name": "...",
                "cover": "...",
                "intro": "..."
            },
            "articles": [
                {
                    "id": "article-id",
                    "title": "...",
                    "picUrl": "...",
                    "publishTime": 1234567890
                }
            ]
        }
    """
    try:
        user_id = current_user.get("id")
        
        # Verify user owns this account
        user_accounts = user_wewe_accounts.get(user_id, [])
        account = next((acc for acc in user_accounts if acc["vid"] == account_id), None)
        
        if not account:
            raise HTTPException(
                status_code=403,
                detail="You don't have access to this WeWe-RSS account"
            )
        
        # Get official account info from share URL
        mp_infos = await auth_service.get_mp_info(
            account_id=account["vid"],
            account_token=account["token"],
            share_url=wx_article_url
        )
        
        if not mp_infos:
            raise HTTPException(
                status_code=400,
                detail="Could not extract WeChat official account from URL"
            )
        
        # Get articles from the official account
        mp_id = mp_infos[0]["id"]
        articles = await auth_service.get_mp_articles(
            account_id=account["vid"],
            account_token=account["token"],
            mp_id=mp_id
        )
        
        return {
            "status": "success",
            "official_account": {
                "id": mp_infos[0]["id"],
                "name": mp_infos[0].get("name", ""),
                "cover": mp_infos[0].get("cover", ""),
                "intro": mp_infos[0].get("intro", "")
            },
            "articles": articles
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching WeChat articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{account_id}")
async def remove_wewe_rss_account(
    account_id: str,
    current_user: dict = Depends(get_current_user)
) -> MessageResponse:
    """Remove a connected WeWe-RSS account.
    
    Args:
        account_id: WeWe-RSS account ID (vid) to remove
        
    Returns:
        {"message": "Account removed successfully"}
    """
    try:
        user_id = current_user.get("id")
        
        if user_id in user_wewe_accounts:
            user_wewe_accounts[user_id] = [
                acc for acc in user_wewe_accounts[user_id]
                if acc["vid"] != account_id
            ]
            logger.info(f"Removed WeWe-RSS account {account_id} for user {user_id}")
        
        return {"message": "Account removed successfully"}
        
    except Exception as e:
        logger.error(f"Error removing WeWe-RSS account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integration-status")
async def get_wewe_rss_integration_status(current_user: dict = Depends(get_current_user)) -> dict:
    """Get WeWe-RSS integration status and user's connected accounts.
    
    Returns:
        {
            "integrated": true,
            "enabled": true,
            "service_url": "http://localhost:4000",
            "user_accounts": [...]
        }
    """
    try:
        user_id = current_user.get("id")
        accounts = user_wewe_accounts.get(user_id, [])
        
        return {
            "integrated": True,
            "enabled": bool(settings.WEWE_RSS_URL),
            "service_url": settings.WEWE_RSS_URL,
            "user_accounts": len(accounts),
            "accounts": [
                {
                    "vid": acc["vid"],
                    "username": acc.get("username", "Unknown")
                }
                for acc in accounts
            ]
        }
    except Exception as e:
        logger.error(f"Error getting integration status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
