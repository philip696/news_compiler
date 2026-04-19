"""Tests for WeChat OAuth Service"""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.wechat_oauth import WeChatOAuthClient, WeChatOAuthError, get_wechat_oauth_client

class TestWeChatOAuthClient:
    def test_init_with_credentials(self):
        client = WeChatOAuthClient("app_id", "app_secret")
        assert client.app_id == "app_id"
        assert client.app_secret == "app_secret"
        assert not client.graceful_mode
    
    def test_init_graceful_mode(self):
        client = WeChatOAuthClient("", "")
        assert client.graceful_mode
    
    def test_generate_auth_url_success(self):
        client = WeChatOAuthClient("app_id", "app_secret")
        url = client.generate_auth_url("test_state")
        assert "app_id" in url
        assert "test_state" in url
        assert "snsapi_userinfo" in url
        assert "response_type=code" in url
    
    def test_generate_auth_url_graceful_mode_error(self):
        client = WeChatOAuthClient("", "")
        with pytest.raises(WeChatOAuthError):
            client.generate_auth_url("state")
    
    def test_generate_auth_url_empty_state(self):
        client = WeChatOAuthClient("app_id", "app_secret")
        with pytest.raises(WeChatOAuthError):
            client.generate_auth_url("")
    
    @pytest.mark.asyncio
    async def test_exchange_co    async def test_exchange
        with patch("httpx.AsyncClient") as mock_client:
                                                    mock_response.json.return_value = {
                                        3",
                                   efresh123",
                "openid": "openid123",
                "expires_in": 7200
            }
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            client = WeChatOAuthClient("app_id", "app_secret")
            result = await client.exchange_code_for_token("code123")
            
            assert result["access_token"] == "token123"
                                                  
    
    @pytest.mark.asyncio
    async def test_exchange_    async def test_exchange_    async def test_epx    async def test_exchange_    async def test_exchannse = AsyncMock()
            mock_response.json.return_value = {"errcode": 40001, "errmsg": "invalid code"}
            mo            mo            mo            mo            urn_            mo            mo            mo          t =             mo            mo            mo            mo            ures(WeChatOAuthError):
                await client.exchange_code_for_token("invalid")
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        with patch("httpx.AsyncCl        with patch("httpx.AsyncCl        with patch("httpx.AsyncCl        with patch("httpx.n.        wite = {
                "openid": "openid123",
                "nic                "nic                "nic                "nic                    ent.return_value.__aenter__.return_value.get.return_value = mock_response
            
            client = W   atOAuthClient("app_id", "ap            client = W   atOAuthClient("app_id", "ap            client = W   atOAuthClient("app_id", "ap            client = W   atOAuthClient("appr"            client = W   atOAuthClient("app_id", "ap            client = W   atOAuthClien     with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "access_token": "new_token",
                "refresh_token": "ne                "refresh_token": "ne                "refresh_t     "e                "refres                  "refresh_token": "ne         aen                "refresh_token": "ne                "refresh_token": "ne                "refresh_t     "e                "refres             esult = await client.refresh_access_token("refresh_token")
            
            assert result["access_token"] == "new_token"
    
    def test_verify_token_valid(self):
        client = WeChatOAuthClient("app_id", "app_secret        client = WeChatOAuthClient("app_id", "app_secret        client = WeChatOAuthClient("app_id", "app_secret        client = WeChatOAuthClient("app_id", "app_secret        client = WeChatOAuthClient("app_id", "app_secret        client = WeChatOAuthClient("app_id", "app_secret        client = WeChatOAuthClient("app_id", "app_secret     ("httpx.AsyncClient") as mock_client:
                                                                                            ode":                                                                                            ode":                                                                                            ode":                                                                                            ode":                                                                                     Ch           nt                                                       ke ", "                                     e

def test_factory_function():
    client = get_wechat_oauth_client()
    assert isinstance(client, WeChatOAuthClient)
