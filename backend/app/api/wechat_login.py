"""WeChat OAuth QR Code Login"""
import logging
import secrets
import base64
import httpx
import urllib.parse
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query

from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wechat-auth", tags=["wechat-auth"])

# In-memory store for login states (use Redis in production)
login_states = {}


class WeChatOAuthClient:
    """WeChat OAuth flow handler based on wewe-rss pattern"""
    
    def __init__(self):
        self.client_id = settings.WECHAT_APP_ID
        self.client_secret = settings.WECHAT_APP_SECRET
        self.redirect_uri = settings.OAUTH_CALLBACK_URL
    
    def generate_auth_url(self, state: str) -> str:
        """Generate WeChat OAuth authorization URL"""
        params = {
            "appid": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "snsapi_userinfo",
            "state": state,
        }
        query_string = urllib.parse.urlencode(params)
        return f"https://open.weixin.qq.com/connect/oauth2/authorize?{query_string}#wechat_redirect"
    
    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token and user info"""
        async with httpx.AsyncClient() as client:
            token_url = "https://api.weixin.qq.com/sns/oauth2/access_token"
            token_params = {
                "appid": self.client_id,
                "secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code"
            }
            
            response = await client.get(token_url, params=token_params)
            data = response.json()
            
            if "errcode" in data:
                raise ValueError(f"Failed to exchange code: {data.get('errmsg')}")
            
            access_token = data["access_token"]
            openid = data["openid"]
            
            # Get user info
            user_url = "https://api.weixin.qq.com/sns/userinfo"
            user_params = {
                "access_token": access_token,
                "openid": openid,
                "lang": "zh_CN"
            }
            
            user_response = await client.get(user_url, params=user_params)
            user_data = user_response.json()
            
            return {
                "access_token": access_token,
                "openid": openid,
                "nickname": user_data.get("nickname"),
                "avatar": user_data.get("headimgurl"),
            }


oauth_client = WeChatOAuthClient()


@router.post("/qrcode/generate")
async def generate_qrcode():
    """Generate WeChat OAuth QR code login URL"""
    try:
        # Generate unique state token
        state = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode()
        
        # Store state with timestamp (expires in 5 minutes)
        login_states[state] = {
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(minutes=5),
            "completed": False
        }
        
        # Generate auth URL
        auth_url = oauth_client.generate_auth_url(state)
        
        return {
            "status": "success",
            "auth_url": auth_url,
            "state": state,
            "expires_in": 300  # 5 minutes
        }
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback")
async def handle_callback(code: str = Query(...), state: str = Query(...)):
    """Handle WeChat OAuth callback"""
    try:
        # Validate state
        if state not in login_states:
            raise HTTPException(status_code=400, detail="Invalid or expired state")
        
        state_data = login_states[state]
        
        # Check expiration
        if datetime.now() > state_data["expires_at"]:
            del login_states[state]
            raise HTTPException(status_code=400, detail="State expired")
        
        # Exchange code for token
        user_info = await oauth_client.exchange_code_for_token(code)
        
        # Mark state as completed
        state_data["completed"] = True
        state_data["user_info"] = user_info
        
        return {
            "status": "success",
            "user": {
                "openid": user_info["openid"],
                "nickname": user_info["nickname"],
                "avatar": user_info["avatar"]
            },
            "access_token": user_info["access_token"]
        }
    except ValueError as e:
        logger.error(f"OAuth error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def check_login_status(state: str = Query(...)):
    """Check if user has completed login for given state"""
    try:
        if state not in login_states:
            return {"status": "error", "message": "Invalid state"}
        
        state_data = login_states[state]
        
        # Check expiration
        if datetime.now() > state_data["expires_at"]:
            del login_states[state]
            return {"status": "expired", "message": "Login request expired"}
        
        if state_data["completed"]:
            user_info = state_data.get("user_info", {})
            # Clean up
            del login_states[state]
            return {
                "status": "completed",
                "user": {
                    "openid": user_info.get("openid"),
                    "nickname": user_info.get("nickname"),
                    "avatar": user_info.get("avatar")
                },
                "access_token": user_info.get("access_token")
            }
        
        return {"status": "pending", "message": "Waiting for user to authorize"}
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
