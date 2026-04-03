from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str


class UserProfileOut(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class TopicOut(BaseModel):
    id: str
    name: str
    followed: bool
    interest_score: float


class FollowTopicRequest(BaseModel):
    topic_id: str


class SourcePreferenceRequest(BaseModel):
    source_id: str


class BookmarkRequest(BaseModel):
    article_id: str


class BehaviorRequest(BaseModel):
    article_id: str
    reading_time: int = 0
    clicked: bool = False
    bookmarked: bool = False
    skipped: bool = False


class ArticleOut(BaseModel):
    id: str
    title: str
    content: str
    url: str
    source_id: str
    source_name: str
    published_at: datetime
    topic: str
    topic_confidence: float = 0.0
    logo_url: str = ""
    main_image: str = ""


class StoryClusterOut(BaseModel):
    cluster_id: str
    topic: str
    headline: str
    summary: str
    article_count: int
    sources: list[str]
    score: float
    articles: list[ArticleOut]


class FeedResponse(BaseModel):
    stories: list[StoryClusterOut]
    total: int = 0
    skip: int = 0
    limit: int = 20


class MessageResponse(BaseModel):
    message: str


class ArticleRecord(BaseModel):
    id: str
    title: str
    content: str
    url: str
    source_id: str
    source_name: str
    published_at: datetime
    topic: str
    embedding: list[float]


class UserTopicRecord(BaseModel):
    topic_id: str
    followed: bool
    interest_score: float
    updated_at: datetime


class ArticleActionStatus(BaseModel):
    article_id: str
    liked: bool
    bookmarked: bool


class ArticleDetailOut(ArticleOut):
    liked: bool = False
    bookmarked: bool = False

PreferenceValue = Literal["preferred", "neutral", "muted"]
