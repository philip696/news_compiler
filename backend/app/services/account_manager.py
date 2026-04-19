"""
WeChat Account Management Service
Business logic layer for managing user subscriptions to WeChat accounts.

Provides:
- Subscribe/unsubscribe from accounts
- Mute/unmute notifications
- List user's accounts with metadata
- Subscription state management
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.wechat import (
    WeChatAuth,
    WeChatAccount,
    WeChatSubscription,
    WeChatArticle,
)

logger = logging.getLogger(__name__)


class WeChatAccountManager:
    """Manages WeChat account subscriptions and notifications"""

    def __init__(self, db: Session):
        """
        Initialize account manager with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    # ===== Subscription Management =====

    def subscribe_account(self, user_id: int, wechat_account_id: int) -> WeChatSubscription:
        """
        Subscribe user to a WeChat account.

        Creates a new WeChatSubscription linking the user's WeChatAuth to an account.
        Validates that both user and account exist, and prevents duplicate subscriptions.

        Args:
            user_id: User ID to subscribe
            wechat_account_id: Account ID to subscribe to

        Returns:
            Created WeChatSubscription object

        Raises:
            ValueError: If user not linked to WeChat, account not found, or already subscribed
            IntegrityError: If database constraint violated
        """
        # Validate user has WeChat auth
        wechat_auth = self.db.query(WeChatAuth).filter(
            WeChatAuth.user_id == user_id
        ).first()

        if not wechat_auth:
            self._log_event("subscription_failed_no_auth", user_id=user_id)
            raise ValueError(f"User {user_id} is not linked to WeChat. Please login with WeChat first.")

        # Validate account exists
        account = self.db.query(WeChatAccount).filter(
            WeChatAccount.id == wechat_account_id
        ).first()

        if not account:
            self._log_event("subscription_failed_account_not_found", 
                          user_id=user_id, account_id=wechat_account_id)
            raise ValueError(f"WeChat account {wechat_account_id} not found.")

        # Check for duplicate subscription
        existing = self.db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_auth_id == wechat_auth.id,
            WeChatSubscription.wechat_account_id == wechat_account_id
        ).first()

        if existing:
            self._log_event("subscription_duplicate_attempt", 
                          user_id=user_id, account_id=wechat_account_id)
            raise ValueError(f"User already subscribed to this account.")

        # Create subscription
        try:
            subscription = WeChatSubscription(
                wechat_auth_id=wechat_auth.id,
                wechat_account_id=wechat_account_id,
                is_muted=False,
                notification_enabled=True,
                subscribed_at=datetime.now(timezone.utc),
                unsubscribed_at=None
            )
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)

            self._log_event(
                "subscription_created",
                user_id=user_id,
                account_id=wechat_account_id,
                subscription_id=subscription.id
            )

            return subscription

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database error creating subscription: {e}")
            raise ValueError("Failed to create subscription. Account may already be subscribed.")

    def unsubscribe_account(self, user_id: int, wechat_account_id: int) -> bool:
        """
        Unsubscribe user from a WeChat account.

        Marks subscription as unsubscribed but preserves article history.

        Args:
            user_id: User ID to unsubscribe
            wechat_account_id: Account ID to unsubscribe from

        Returns:
            True if unsubscribed, False if subscription not found
        """
        # Find subscription
        wechat_auth = self.db.query(WeChatAuth).filter(
            WeChatAuth.user_id == user_id
        ).first()

        if not wechat_auth:
            return False

        subscription = self.db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_auth_id == wechat_auth.id,
            WeChatSubscription.wechat_account_id == wechat_account_id,
            WeChatSubscription.unsubscribed_at.is_(None)  # Only find active subscriptions
        ).first()

        if not subscription:
            self._log_event("unsubscribe_not_found", 
                          user_id=user_id, account_id=wechat_account_id)
            return False

        # Mark as unsubscribed (don't delete - preserve article history)
        subscription.unsubscribe()  # Sets unsubscribed_at and clears mute
        self.db.commit()

        self._log_event(
            "subscription_deleted",
            user_id=user_id,
            account_id=wechat_account_id,
            subscription_id=subscription.id
        )

        return True

    def list_user_accounts(self, user_id: int) -> List[Dict]:
        """
        Get all WeChat accounts subscribed by user.

        Returns subscriptions for active (not unsubscribed) accounts with metadata.

        Args:
            user_id: User ID to list accounts for

        Returns:
            List of dicts with account info:
            - account_id: Account ID
            - account_name: Account name
            - account_avatar: Account avatar URL
            - account_intro: Account description
            - is_verified: Whether account is verified
            - is_muted: Whether user has muted this account
            - last_sync_time: Last sync timestamp (ISO8601) or None
            - unread_count: Number of unread articles
            - subscribed_at: When user subscribed (ISO8601)
        """
        # Find user's WeChat auth
        wechat_auth = self.db.query(WeChatAuth).filter(
            WeChatAuth.user_id == user_id
        ).first()

        if not wechat_auth:
            return []

        # Get all active subscriptions
        subscriptions = self.db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_auth_id == wechat_auth.id,
            WeChatSubscription.unsubscribed_at.is_(None)  # Only active subscriptions
        ).all()

        if not subscriptions:
            return []

        # Build account info for each subscription
        accounts = []
        for subscription in subscriptions:
            account = subscription.account

            # Count unread articles (excluding expired ones)
            unread_count = self.db.query(WeChatArticle).filter(
                WeChatArticle.wechat_account_id == account.id,
                WeChatArticle.expires_at > datetime.now(timezone.utc)
            ).count()

            account_info = {
                "account_id": account.id,
                "account_name": account.wechat_account_name,
                "account_avatar": account.wechat_account_avatar,
                "account_intro": account.account_intro,
                "is_verified": account.is_verified,
                "is_muted": subscription.is_muted,
                "last_sync_time": account.last_sync_time.isoformat() if account.last_sync_time else None,
                "unread_count": unread_count,
                "subscribed_at": subscription.subscribed_at.isoformat(),
            }
            accounts.append(account_info)

        return accounts

    def mute_account(self, user_id: int, wechat_account_id: int) -> bool:
        """
        Mute notifications for an account.

        Does not delete subscription - just suppresses notifications.

        Args:
            user_id: User ID
            wechat_account_id: Account ID to mute

        Returns:
            True if muted, False if subscription not found
        """
        # Find subscription
        wechat_auth = self.db.query(WeChatAuth).filter(
            WeChatAuth.user_id == user_id
        ).first()

        if not wechat_auth:
            return False

        subscription = self.db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_auth_id == wechat_auth.id,
            WeChatSubscription.wechat_account_id == wechat_account_id,
            WeChatSubscription.unsubscribed_at.is_(None)  # Only for active subscriptions
        ).first()

        if not subscription:
            self._log_event("mute_not_found",
                          user_id=user_id, account_id=wechat_account_id)
            return False

        # Mute notifications
        subscription.is_muted = True
        self.db.commit()

        self._log_event(
            "account_muted",
            user_id=user_id,
            account_id=wechat_account_id
        )

        return True

    def unmute_account(self, user_id: int, wechat_account_id: int) -> bool:
        """
        Unmute notifications for an account.

        Args:
            user_id: User ID
            wechat_account_id: Account ID to unmute

        Returns:
            True if unmuted, False if subscription not found
        """
        # Find subscription
        wechat_auth = self.db.query(WeChatAuth).filter(
            WeChatAuth.user_id == user_id
        ).first()

        if not wechat_auth:
            return False

        subscription = self.db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_auth_id == wechat_auth.id,
            WeChatSubscription.wechat_account_id == wechat_account_id,
            WeChatSubscription.unsubscribed_at.is_(None)  # Only for active subscriptions
        ).first()

        if not subscription:
            self._log_event("unmute_not_found",
                          user_id=user_id, account_id=wechat_account_id)
            return False

        # Unmute notifications
        subscription.is_muted = False
        self.db.commit()

        self._log_event(
            "account_unmuted",
            user_id=user_id,
            account_id=wechat_account_id
        )

        return True

    # ===== Private Helpers =====

    def _log_event(self, event_name: str, **kwargs):
        """
        Log event for monitoring and debugging.

        Args:
            event_name: Name of event
            **kwargs: Additional event data
        """
        logger.info(f"Account Manager Event: {event_name}", extra=kwargs)
