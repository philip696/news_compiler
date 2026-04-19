"""
WeChat Database Models using SQLAlchemy ORM
Implements encryption mixin, relationships, validation, and audit trails.
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, 
    UniqueConstraint, Index, Boolean, Text, LargeBinary, Enum, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone, timedelta
from typing import Optional
import enum
import json

from app.db.database import Base
from app.utils.encryption import encrypt_token, decrypt_token


# ===== Enumerations =====

class SyncStatus(str, enum.Enum):
    """Status of WeChat account sync operations"""
    ACTIVE = "active"
    FAILED = "failed"
    PAUSED = "paused"


class ArticleSyncStatus(str, enum.Enum):
    """Status of individual article sync"""
    SUCCESS = "success"
    FAILED = "failed"


# ===== Mixins =====

class EncryptionMixin:
    """Mixin for automatic token encryption/decryption"""
    
    def _encrypt_token(self, token: str) -> bytes:
        """Encrypt a token using Fernet"""
        return encrypt_token(token)
    
    def _decrypt_token(self, encrypted_token: bytes) -> str:
        """Decrypt a token using Fernet"""
        return decrypt_token(encrypted_token)


class TimestampMixin:
    """Mixin for automatic timestamp management"""
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )


# ===== Models =====

class WeChatAuth(Base, EncryptionMixin, TimestampMixin):
    """
    Store encrypted WeChat OAuth credentials and subscription info per user.
    
    One-to-one relationship with User.
    Tokens are encrypted at rest using Fernet (AES-128-CBC + HMAC).
    """
    __tablename__ = "wechat_auth"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        unique=True, 
        index=True,
        nullable=False
    )
    
    # OpenID and UnionID from WeChat OAuth
    wechat_openid = Column(String(128), unique=True, index=True, nullable=False)
    wechat_unionid = Column(String(128), nullable=True, index=True)
    
    # Encrypted token storage (binary format post-encryption)
    access_token_encrypted = Column(LargeBinary, nullable=False)
    refresh_token_encrypted = Column(LargeBinary, nullable=True)
    
    # Token metadata
    token_expiry = Column(DateTime, nullable=False, index=True)
    scopes = Column(String(255), nullable=True)  # Comma-separated OAuth scopes
    raw_user_info = Column(Text, nullable=True)  # JSON backup of OAuth response
    
    # Relationships
    user = relationship("User", backref="wechat_auth", uselist=False)
    subscriptions = relationship(
        "WeChatSubscription",
        back_populates="auth",
        cascade="all, delete-orphan",
        foreign_keys="WeChatSubscription.wechat_auth_id"
    )

    __table_args__ = (
        Index("idx_wechat_auth_openid", "wechat_openid"),
        Index("idx_wechat_auth_expiry", "token_expiry"),
        UniqueConstraint("user_id", name="uq_wechat_auth_user_id"),
    )

    # ===== Properties for transparent encryption/decryption =====

    @hybrid_property
    def access_token(self) -> Optional[str]:
        """Get access token (decrypted)"""
        if self.access_token_encrypted:
            return self._decrypt_token(self.access_token_encrypted)
        return None

    @access_token.setter
    def access_token(self, value: str):
        """Set access token (auto-encrypts)"""
        if value:
            self.access_token_encrypted = self._encrypt_token(value)

    @access_token.expression
    @classmethod
    def access_token(cls):
        """SQL expression for access_token (returns encrypted value for queries)"""
        return cls.access_token_encrypted

    @hybrid_property
    def refresh_token(self) -> Optional[str]:
        """Get refresh token (decrypted)"""
        if self.refresh_token_encrypted:
            return self._decrypt_token(self.refresh_token_encrypted)
        return None

    @refresh_token.setter
    def refresh_token(self, value: Optional[str]):
        """Set refresh token (auto-encrypts)"""
        if value:
            self.refresh_token_encrypted = self._encrypt_token(value)
        else:
            self.refresh_token_encrypted = None

    @refresh_token.expression
    @classmethod
    def refresh_token(cls):
        """SQL expression for refresh_token (returns encrypted value for queries)"""
        return cls.refresh_token_encrypted

    # ===== Validation Methods =====

    def is_token_expired(self) -> bool:
        """Check if access token has expired"""
        return datetime.now(timezone.utc) >= self.token_expiry

    def needs_refresh(self, buffer_seconds: int = 300) -> bool:
        """Check if token needs refresh (with buffer)"""
        return datetime.now(timezone.utc) >= (
            self.token_expiry - timedelta(seconds=buffer_seconds)
        )

    def refresh_token_expiry(self, seconds: int = 7200):
        """Update token expiry to N seconds from now"""
        self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=seconds)

    def __repr__(self):
        return f"<WeChatAuth user_id={self.user_id} openid={self.wechat_openid[:8]}...>"


class WeChatAccount(Base, TimestampMixin):
    """
    WeChat Official Account metadata and sync configuration.
    
    Tracks sync status, last sync time, and retry information.
    """
    __tablename__ = "wechat_accounts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Account identification (unique per WeChat platform)
    wechat_account_id = Column(String(128), unique=True, index=True, nullable=False)
    wechat_account_name = Column(String(255), nullable=False)
    wechat_account_avatar = Column(String(2048), nullable=True)
    account_intro = Column(Text, nullable=True)
    
    # Account metadata
    is_verified = Column(Boolean, default=False)
    account_type = Column(
        String(50), 
        default="subscription",
        nullable=False
    )  # subscription, service_account, etc.
    
    # Sync tracking
    last_sync_time = Column(DateTime, nullable=True)
    sync_status = Column(
        Enum(SyncStatus),
        default=SyncStatus.ACTIVE,
        index=True,
        nullable=False
    )
    sync_retry_count = Column(Integer, default=0, nullable=False)
    latest_error_message = Column(Text, nullable=True)

    # Relationships
    subscriptions = relationship(
        "WeChatSubscription",
        back_populates="account",
        cascade="all, delete-orphan",
        foreign_keys="WeChatSubscription.wechat_account_id"
    )
    articles = relationship(
        "WeChatArticle",
        back_populates="account",
        cascade="all, delete-orphan",
        foreign_keys="WeChatArticle.wechat_account_id"
    )
    sync_logs = relationship(
        "WeChatSyncLog",
        back_populates="account",
        cascade="all, delete-orphan",
        foreign_keys="WeChatSyncLog.wechat_account_id"
    )

    __table_args__ = (
        Index("idx_account_status", "sync_status"),
        Index("idx_account_created", "created_at"),
        Index("idx_account_sync_time", "last_sync_time"),
        UniqueConstraint("wechat_account_id", name="uq_wechat_account_id"),
    )

    # ===== Query Methods =====

    def mark_sync_start(self):
        """Mark sync as in-progress"""
        self.sync_status = SyncStatus.ACTIVE
        self.sync_retry_count = 0

    def mark_sync_success(self):
        """Mark sync as successful"""
        self.sync_status = SyncStatus.ACTIVE
        self.last_sync_time = datetime.now(timezone.utc)
        self.sync_retry_count = 0
        self.latest_error_message = None

    def mark_sync_failed(self, error_msg: str, increment_retry: bool = True):
        """Mark sync as failed with error tracking"""
        self.sync_status = SyncStatus.FAILED
        self.latest_error_message = error_msg
        if increment_retry:
            self.sync_retry_count += 1

    def can_retry_sync(self, max_retries: int = 5) -> bool:
        """Check if account can retry sync"""
        return self.sync_retry_count < max_retries

    def __repr__(self):
        return f"<WeChatAccount {self.wechat_account_name} ({self.sync_status.value})>"


class WeChatSubscription(Base, TimestampMixin):
    """
    Junction table: User's subscription to WeChat Official Accounts.
    
    Composite unique constraint prevents duplicate subscriptions.
    Supports muting notifications per subscription.
    """
    __tablename__ = "wechat_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    wechat_auth_id = Column(
        Integer,
        ForeignKey("wechat_auth.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    wechat_account_id = Column(
        Integer,
        ForeignKey("wechat_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Subscription state
    is_muted = Column(Boolean, default=False)
    notification_enabled = Column(Boolean, default=True)
    subscribed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    unsubscribed_at = Column(DateTime, nullable=True)
    
    # Track last read for notification deduplication
    last_read_article_id = Column(String(128), nullable=True)

    # Relationships
    auth = relationship(
        "WeChatAuth",
        back_populates="subscriptions",
        foreign_keys=[wechat_auth_id]
    )
    account = relationship(
        "WeChatAccount",
        back_populates="subscriptions",
        foreign_keys=[wechat_account_id]
    )

    __table_args__ = (
        # Prevent duplicate subscriptions
        UniqueConstraint(
            "wechat_auth_id",
            "wechat_account_id",
            name="uq_wechat_subscription_auth_account"
        ),
        Index("idx_subscription_muted", "is_muted"),
        Index("idx_subscription_subscribed", "subscribed_at"),
    )

    # ===== Subscription State Methods =====

    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return self.unsubscribed_at is None

    def unsubscribe(self):
        """Mark subscription as unsubscribed"""
        self.unsubscribed_at = datetime.now(timezone.utc)
        self.is_muted = False

    def resubscribe(self):
        """Reactivate a previously unsubscribed subscription"""
        self.unsubscribed_at = None
        self.subscribed_at = datetime.now(timezone.utc)

    def toggle_mute(self):
        """Toggle notification mute state"""
        self.is_muted = not self.is_muted

    def __repr__(self):
        status = "muted" if self.is_muted else "active"
        return f"<WeChatSubscription auth_id={self.wechat_auth_id} account_id={self.wechat_account_id} [{status}]>"


class WeChatArticle(Base, TimestampMixin):
    """
    Cached WeChat articles with TTL and expiry management.
    
    Articles are cached for search/summarization and automatically expired.
    """
    __tablename__ = "wechat_articles_cache"

    id = Column(Integer, primary_key=True, index=True)
    
    # Article identification
    article_id = Column(String(128), nullable=False, index=True)
    wechat_account_id = Column(
        Integer,
        ForeignKey("wechat_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Article content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    
    # Article URLs and media
    publish_time = Column(DateTime, nullable=False)
    article_url = Column(String(2048), nullable=False)
    image_url = Column(String(2048), nullable=True)
    video_url = Column(String(2048), nullable=True)
    
    # Cache management
    source_type = Column(String(50), default="wechat", nullable=False)
    cached_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Processing flags
    is_summarized = Column(Boolean, default=False)
    embedding_vector = Column(LargeBinary, nullable=True)  # For vector search

    # Relationships
    account = relationship(
        "WeChatAccount",
        back_populates="articles",
        foreign_keys=[wechat_account_id]
    )

    __table_args__ = (
        # Composite unique: article_id per account
        UniqueConstraint(
            "article_id",
            "wechat_account_id",
            name="uq_wechat_article_per_account"
        ),
        Index("idx_article_expires", "expires_at"),
        Index("idx_article_published", "publish_time"),
        Index("idx_article_summarized", "is_summarized"),
    )

    # ===== Article Lifecycle Methods =====

    def is_expired(self) -> bool:
        """Check if article has expired from cache"""
        return datetime.now(timezone.utc) >= self.expires_at

    def refresh_expiry(self, hours: int = 24):
        """Extend article expiry by N hours"""
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    def mark_summarized(self):
        """Mark article as having been summarized"""
        self.is_summarized = True

    def is_recent(self, hours: int = 24) -> bool:
        """Check if article was published recently"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return self.publish_time >= cutoff

    def __repr__(self):
        return f"<WeChatArticle {self.title[:30]}... from account_id={self.wechat_account_id}>"


class WeChatSyncLog(Base):
    """
    Audit trail for all WeChat account sync operations.
    
    Tracks articles fetched, errors, and performance metrics.
    """
    __tablename__ = "wechat_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to account being synced
    wechat_account_id = Column(
        Integer,
        ForeignKey("wechat_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    # Sync result
    sync_status = Column(
        Enum(SyncStatus),
        nullable=False,
        index=True
    )
    
    # Article statistics
    articles_fetched = Column(Integer, default=0, nullable=False)
    articles_new = Column(Integer, default=0, nullable=False)
    articles_updated = Column(Integer, default=0, nullable=False)
    articles_failed = Column(Integer, default=0, nullable=False)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Performance metrics
    sync_duration_seconds = Column(Integer, default=0, nullable=False)
    api_call_count = Column(Integer, default=0, nullable=False)
    rate_limit_remaining = Column(Integer, nullable=True)
    
    # Audit timestamp
    sync_timestamp = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False
    )

    # Relationships
    account = relationship(
        "WeChatAccount",
        back_populates="sync_logs",
        foreign_keys=[wechat_account_id]
    )

    __table_args__ = (
        Index("idx_sync_account_timestamp", "wechat_account_id", "sync_timestamp"),
        Index("idx_sync_status", "sync_status"),
        CheckConstraint("articles_fetched >= 0", name="check_articles_fetched_non_negative"),
        CheckConstraint("sync_duration_seconds >= 0", name="check_duration_non_negative"),
    )

    # ===== Query Methods =====

    def is_successful(self) -> bool:
        """Check if sync was successful"""
        return self.sync_status == SyncStatus.ACTIVE and self.error_message is None

    def get_success_rate(self) -> float:
        """Calculate success rate of article syncing"""
        if self.articles_fetched == 0:
            return 0.0
        return (self.articles_fetched - self.articles_failed) / self.articles_fetched

    def __repr__(self):
        return f"<WeChatSyncLog account_id={self.wechat_account_id} status={self.sync_status.value} fetched={self.articles_fetched}>"
