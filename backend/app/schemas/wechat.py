"""
Pydantic schemas for WeChat models - API request/response serialization.
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SyncStatusSchema(str, Enum):
    """Sync status enum for schemas"""
    ACTIVE = "active"
    FAILED = "failed"
    PAUSED = "paused"


# ===== WeChatAuth Schemas =====

class WeChatAuthCreate(BaseModel):
    """Create user WeChat auth - used for OAuth callback"""
    user_id: int
    wechat_openid: str
    wechat_unionid: Optional[str] = None
    access_token: str
    refresh_token: Optional[str] = None
    token_expiry: datetime
    scopes: Optional[str] = None

    @field_validator("wechat_openid")
    @classmethod
    def openid_not_empty(cls, v):
        assert v and len(v) > 0, "WeChat openid cannot be empty"
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "wechat_openid": "oZ5Fq_PtxxVRzDl94k3CbzXUz8Zo",
                "wechat_unionid": "oTj4AjurlSYWEBhd8Hzg_NM8P1ck0",
                "access_token": "ACCESS_TOKEN_123456789",
                "refresh_token": "REFRESH_TOKEN_987654321",
                "token_expiry": "2024-04-19T10:30:00Z",
                "scopes": "snsapi_userinfo,snsapi_friend_check",
            }
        }
    )


class WeChatAuthUpdate(BaseModel):
    """Update user WeChat auth - typically after token refresh"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None


class WeChatAuthSchema(BaseModel):
    """Response schema for WeChatAuth - NO token fields for security"""
    id: int
    user_id: int
    wechat_openid: str
    wechat_unionid: Optional[str] = None
    token_expiry: datetime
    scopes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeChatAuthDetailSchema(WeChatAuthSchema):
    """Detailed auth schema with subscription info"""
    subscriptions: List["WeChatSubscriptionSchema"] = []

    model_config = ConfigDict(from_attributes=True)


# ===== WeChatAccount Schemas =====

class WeChatAccountCreate(BaseModel):
    """Create WeChat account"""
    wechat_account_id: str
    wechat_account_name: str
    wechat_account_avatar: Optional[str] = None
    account_intro: Optional[str] = None
    account_type: str = "subscription"
    is_verified: bool = False

    @field_validator("wechat_account_id")
    @classmethod
    def account_id_not_empty(cls, v):
        assert v and len(v) > 0, "WeChat account_id cannot be empty"
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wechat_account_id": "gh_a3f95b8e4d5c",
                "wechat_account_name": "TechNews Daily",
                "wechat_account_avatar": "https://example.com/avatar.jpg",
                "account_intro": "Daily technology news",
                "account_type": "subscription",
                "is_verified": True,
            }
        }
    )


class WeChatAccountUpdate(BaseModel):
    """Update WeChat account fields"""
    wechat_account_name: Optional[str] = None
    wechat_account_avatar: Optional[str] = None
    account_intro: Optional[str] = None
    sync_status: Optional[SyncStatusSchema] = None
    last_sync_time: Optional[datetime] = None


class WeChatAccountSchema(BaseModel):
    """Response schema for WeChatAccount"""
    id: int
    wechat_account_id: str
    wechat_account_name: str
    wechat_account_avatar: Optional[str] = None
    account_intro: Optional[str] = None
    account_type: str = Field(default="subscription")
    is_verified: bool = Field(default=False)
    sync_status: str = Field(default="active")
    last_sync_time: Optional[datetime] = None
    sync_retry_count: int = Field(default=0)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeChatAccountDetailSchema(WeChatAccountSchema):
    """Detailed account schema with articles and logs"""
    articles: List["WeChatArticleSchema"] = []
    sync_logs: List["WeChatSyncLogSchema"] = []
    subscriber_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ===== WeChatSubscription Schemas =====

class WeChatSubscriptionCreate(BaseModel):
    """Create subscription"""
    wechat_auth_id: int
    wechat_account_id: int
    is_muted: bool = False


class WeChatSubscriptionUpdate(BaseModel):
    """Update subscription"""
    is_muted: Optional[bool] = None
    notification_enabled: Optional[bool] = None


class WeChatSubscriptionSchema(BaseModel):
    """Response schema for subscription"""
    id: int
    wechat_auth_id: int
    wechat_account_id: int
    is_muted: bool
    notification_enabled: bool
    subscribed_at: datetime
    unsubscribed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ===== WeChatArticle Schemas =====

class WeChatArticleCreate(BaseModel):
    """Create article cache entry"""
    article_id: str
    wechat_account_id: int
    title: str
    content: str
    summary: Optional[str] = None
    author: Optional[str] = None
    publish_time: datetime
    article_url: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    expires_at: datetime

    @field_validator("article_id")
    @classmethod
    def article_id_not_empty(cls, v):
        assert v and len(v) > 0, "Article ID cannot be empty"
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "article_id": "article_123",
                "wechat_account_id": 1,
                "title": "Breaking Tech News",
                "content": "Article content here...",
                "summary": "Article summary",
                "author": "Author Name",
                "publish_time": "2024-04-18T10:30:00Z",
                "article_url": "https://example.com/article",
                "expires_at": "2024-04-19T10:30:00Z",
            }
        }
    )


class WeChatArticleSchema(BaseModel):
    """Response schema for article"""
    id: int
    article_id: str
    wechat_account_id: int
    title: str
    content: str
    summary: Optional[str] = None
    author: Optional[str] = None
    publish_time: datetime
    article_url: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    cached_at: datetime
    expires_at: datetime
    is_summarized: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===== WeChatSyncLog Schemas =====

class WeChatSyncLogCreate(BaseModel):
    """Create sync log entry"""
    wechat_account_id: int
    sync_status: SyncStatusSchema
    articles_fetched: int = 0
    articles_new: int = 0
    articles_updated: int = 0
    articles_failed: int = 0
    error_message: Optional[str] = None
    sync_duration_seconds: int = 0
    api_call_count: int = 0
    rate_limit_remaining: Optional[int] = None


class WeChatSyncLogSchema(BaseModel):
    """Response schema for sync log"""
    id: int
    wechat_account_id: int
    sync_status: str
    articles_fetched: int
    articles_new: int
    articles_updated: int
    articles_failed: int
    error_message: Optional[str] = None
    sync_duration_seconds: int
    api_call_count: int
    rate_limit_remaining: Optional[int] = None
    sync_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Update forward refs
WeChatAuthDetailSchema.model_rebuild()
WeChatAccountDetailSchema.model_rebuild()
