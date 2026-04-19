"""
Pydantic schemas package - API request/response serialization.
"""
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserOut,
    UserProfileOut,
    UserProfileUpdate,
    BehaviorRequest,
    SourcePreferenceRequest,
    BookmarkRequest,
)

from app.schemas.wechat import (
    # Enums
    SyncStatusSchema,
    # WeChatAuth schemas
    WeChatAuthCreate,
    WeChatAuthUpdate,
    WeChatAuthSchema,
    WeChatAuthDetailSchema,
    # WeChatAccount schemas
    WeChatAccountCreate,
    WeChatAccountUpdate,
    WeChatAccountSchema,
    WeChatAccountDetailSchema,
    # WeChatSubscription schemas
    WeChatSubscriptionCreate,
    WeChatSubscriptionUpdate,
    WeChatSubscriptionSchema,
    # WeChatArticle schemas
    WeChatArticleCreate,
    WeChatArticleSchema,
    # WeChatSyncLog schemas
    WeChatSyncLogCreate,
    WeChatSyncLogSchema,
)

# Import CORRECT schemas from root schemas.py (these have the RIGHT definitions)
# These are imported last so they override any conflicting imports above
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("root_schemas", __file__.replace("schemas/__init__.py", "schemas.py"))
if spec and spec.loader:
    root_schemas = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(root_schemas)
    
    # Override with correct schemas from root
    TopicOut = root_schemas.TopicOut
    FollowTopicRequest = root_schemas.FollowTopicRequest
    ArticleOut = root_schemas.ArticleOut
    ArticleDetailOut = root_schemas.ArticleDetailOut
    FeedResponse = root_schemas.FeedResponse
    MessageResponse = root_schemas.MessageResponse
    StoryClusterOut = root_schemas.StoryClusterOut

from app.schemas.wechat import (
    # Enums
    SyncStatusSchema,
    # WeChatAuth schemas
    WeChatAuthCreate,
    WeChatAuthUpdate,
    WeChatAuthSchema,
    WeChatAuthDetailSchema,
    # WeChatAccount schemas
    WeChatAccountCreate,
    WeChatAccountUpdate,
    WeChatAccountSchema,
    WeChatAccountDetailSchema,
    # WeChatSubscription schemas
    WeChatSubscriptionCreate,
    WeChatSubscriptionUpdate,
    WeChatSubscriptionSchema,
    # WeChatArticle schemas
    WeChatArticleCreate,
    WeChatArticleSchema,
    # WeChatSyncLog schemas
    WeChatSyncLogCreate,
    WeChatSyncLogSchema,
)

__all__ = [
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "UserOut",
    "UserProfileOut",
    "UserProfileUpdate",
    "MessageResponse",
    "TopicOut",
    "FollowTopicRequest",
    "ArticleOut",
    "ArticleDetailOut",
    "FeedResponse",
    "BehaviorRequest",
    "SourcePreferenceRequest",
    "BookmarkRequest",
    # Enums
    "SyncStatusSchema",
    # WeChatAuth
    "WeChatAuthCreate",
    "WeChatAuthUpdate",
    "WeChatAuthSchema",
    "WeChatAuthDetailSchema",
    # WeChatAccount
    "WeChatAccountCreate",
    "WeChatAccountUpdate",
    "WeChatAccountSchema",
    "WeChatAccountDetailSchema",
    # WeChatSubscription
    "WeChatSubscriptionCreate",
    "WeChatSubscriptionUpdate",
    "WeChatSubscriptionSchema",
    # WeChatArticle
    "WeChatArticleCreate",
    "WeChatArticleSchema",
    # WeChatSyncLog
    "WeChatSyncLogCreate",
    "WeChatSyncLogSchema",
]
