"""
Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "password": "secret123"
            }
        }
    )


class LoginRequest(BaseModel):
    """User login request"""
    username: str
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "password": "secret123"
            }
        }
    )


class TokenResponse(BaseModel):
    """OAuth token response"""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGc...",
                "refresh_token": "eyJhbGc...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
    )


class UserOut(BaseModel):
    """User output schema"""
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileOut(BaseModel):
    """User profile output"""
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """User profile update"""
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True


class TopicOut(BaseModel):
    """Topic output schema"""
    id: str
    name: str
    followed: bool = False
    interest_score: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class FollowTopicRequest(BaseModel):
    """Follow topic request"""
    topic_id: str


class ArticleOut(BaseModel):
    """Article output schema"""
    id: int
    title: str
    source: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ArticleDetailOut(BaseModel):
    """Article detail output"""
    id: int
    title: str
    content: str | None = None
    source: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FeedResponse(BaseModel):
    """Feed response schema"""
    stories: list = []  # List of story clusters
    total: int = 0
    skip: int = 0
    limit: int = 20

    model_config = ConfigDict(from_attributes=True)


class BehaviorRequest(BaseModel):
    """User behavior request"""
    article_id: str
    action: str  # like, read, dislike, etc.


class SourcePreferenceRequest(BaseModel):
    """Source preference request"""
    source_id: int
    preference: float  # 0.0 to 1.0


class BookmarkRequest(BaseModel):
    """Bookmark / like request (feed article ids are strings: UUID, webhose_*, etc.)."""

    article_id: str

