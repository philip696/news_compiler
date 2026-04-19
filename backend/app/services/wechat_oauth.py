"""WeChat OAuth 2.0 Client Service - Clean Version"""
import logging
from typing import Dict, Any
import httpx
from ..core.config import settings

logger = logging.getLogger(__name__)

class WeChatOAuthError(Exception):
    """WeChat OAuth error"""
    pass

class WeChatOAuthClient:
    """WeChat OAuth 2.0 Client"""
    AUTHORIZE_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
    ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    REFRESH_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/refresh_token"
    USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"
    REVOKE_URL = "https://api.weixin.qq.com/sns/oauth2/revoke"
    
    def __init__(self, app_id=None, app_secret=None):
        self.app_id = app_id or settings.WECHAT_APP_ID or ""
        self.app_secret = app_secret or settings.WECHAT_APP_SECRET or ""
        self.callback_url = settings.OAUTH_CALLBACK_URL
                                                                                                          ta                                                                   eC                           no    nfigured"                                                                       red")
        params = {
            "appid": self.app_id,
            "redirect_uri": self.callback_url,
            "response_type": "code",
            "scope": "snsapi_userinfo",
            "state": state,
            "connect_redirect": "1"
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTHORIZE_URL}?{query_string}#wechat_redirect"
    
    async def excha    async def excha    async def excha    async  Any]:
        if self.graceful_mode:
            raise WeChatOAuthError("            raise WeChatOAuthError("            raise WeChaf.app_id, "secret": self.app_secret, "code": code, "grant_type": "authorization_code"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.ACCESS_TOKEN_URL, params=params, timeout=10.0)
                response.raise_for_status()
            data = response.json()
            if "errcode" in data:
                raise WeChatOAuthError(f"API error: {data.get('errmsg')}")
            return {"access_token": data.get("access_token"), "refresh_token": data.get("            return {"access_token":  "openid": data.get("openid"), "unionid":            return {"acces              return {"access_toke.get("expires_in", 7200), "scope": data.get("scope", "")}
        except httpx.HTTPEr        except httpx.HTTPEr        except httpx.HTTPEr        except 
    a    a    a    a    a    a    a    a    a    a    a    a    a    a    a  ,     a    a    a    a    a  cess_token": access_token, "openid": openid, "lang": "zh_CN"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.USERINFO_URL, params=                response = await client.get(selfaise_for_status()
            data = response.json()
            if "errcode" in data:
                raise WeChatOAuthError(f"User info error: {data.get('errmsg')}")
            return data
        except httpx.HTTPError as e:
            raise WeChatOAuthError(f"HTTP error: {e}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        params = {"appid": self.app_id, "grant_type": "refresh_token", "refresh_token": refresh_token}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.REFRESH_TOKEN_URL, params=params, timeout=10.0)
                response.raise_for_                response.raise_for_                response.raise_for_                response.raise_for_                response.raise_for_                response.r   return {"access_token": data.get("access_token"), "refresh_token":                response.raise_for_                response.raise_for_                response.raise_for_                response.raiept httpx.HTTPError as e:
                                            ror: {e}")
    
    def verify_token(self, access_token: str) -> bool:
        return bool(access_token and isinstance(access_token, str))
    
    async def revoke_token(self, access_token: str, openid:     async def revoke_token(self, access_token: str, openid:     async def revo}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.REVOKE_URL, params=params, timeout=5.0)
                response.raise_for_status()
            data = response.json()
            return "errcode" not in data or data["errcode"] == 0
        except:
            return False

def get_wechat_oauth_client() -> WeChatOAuthClient:
    return WeChatOAuthClient()
