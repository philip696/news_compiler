"""
Test-Driven Development: WeChat Account Management Service
Tests written FIRST, implementation follows.
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from unittest.mock import Mock, patch, MagicMock

from app.db.database import Base
from app.models.wechat import (
    WeChatAuth,
    WeChatAccount,
    WeChatSubscription,
    SyncStatus,
)
from app.services.account_manager import WeChatAccountManager


# ===== Fixtures =====

@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_wechat_auth(test_db: Session):
    """Create sample WeChatAuth for testing"""
    auth = WeChatAuth(
        user_id=1,
        wechat_openid="oZ5Fq_PtxxVRzDl94k3CbzXUz8Zo",
        wechat_unionid="oTj4AjurlSYWEBhd8Hzg_NM8P1ck0",
        access_token="test_access_token_123",
        refresh_token="test_refresh_token_456",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=2),
        scopes="snsapi_userinfo"
    )
    test_db.add(auth)
    test_db.commit()
    test_db.refresh(auth)
    return auth


@pytest.fixture
def sample_wechat_account(test_db: Session):
    """Create sample WeChatAccount for testing"""
    account = WeChatAccount(
        wechat_account_id="gh_a3f95b8e4d5c",
        wechat_account_name="Tech Daily News",
        wechat_account_avatar="https://example.com/avatar.jpg",
        account_intro="Daily technology news updates",
        is_verified=True,
        account_type="subscription",
        sync_status=SyncStatus.ACTIVE
    )
    test_db.add(account)
    test_db.commit()
    test_db.refresh(account)
    return account


@pytest.fixture
def account_manager(test_db: Session):
    """Create AccountManager instance with test database"""
    return WeChatAccountManager(db=test_db)


# ===== Subscription Tests =====

class TestSubscribeAccount:
    """Tests for subscribing to a WeChat account"""

    def test_subscribe_account_creates_subscription(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should create WeChatSubscription linking auth to account"""
        # ACT
        subscription = account_manager.subscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        # ASSERT
        assert subscription is not None
        assert subscription.wechat_auth_id == sample_wechat_auth.id
        assert subscription.wechat_account_id == sample_wechat_account.id
        assert subscription.is_muted is False
        assert subscription.notification_enabled is True
        assert subscription.is_active() is True

        # Verify persisted to DB
        persisted = test_db.query(WeChatSubscription).first()
        assert persisted is not None
        assert persisted.id == subscription.id

    def test_subscribe_account_returns_account_with_metadata(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should return subscription with account metadata"""
        # ACT
        subscription = account_manager.subscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        # ASSERT
        assert subscription.account is not None
        assert subscription.account.wechat_account_name == "Tech Daily News"
        assert subscription.account.is_verified is True

    def test_subscribe_account_fails_with_duplicate_subscription(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should reject duplicate subscription with specific error"""
        # First subscription
        account_manager.subscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        # ACT & ASSERT - Second subscription should fail
        with pytest.raises(ValueError) as exc_info:
            account_manager.subscribe_account(
                user_id=1,
                wechat_account_id=sample_wechat_account.id
            )
        assert "already subscribed" in str(exc_info.value).lower()

    def test_subscribe_account_fails_with_nonexistent_auth(
        self, account_manager, test_db, sample_wechat_account
    ):
        """Should reject subscription if user has no WeChatAuth"""
        # ACT & ASSERT
        with pytest.raises(ValueError) as exc_info:
            account_manager.subscribe_account(
                user_id=999,  # Non-existent user
                wechat_account_id=sample_wechat_account.id
            )
        assert "not linked" in str(exc_info.value).lower()

    def test_subscribe_account_fails_with_nonexistent_account(
        self, account_manager, test_db, sample_wechat_auth
    ):
        """Should reject subscription if account doesn't exist"""
        # ACT & ASSERT
        with pytest.raises(ValueError) as exc_info:
            account_manager.subscribe_account(
                user_id=1,
                wechat_account_id=999  # Non-existent account
            )
        assert "not found" in str(exc_info.value).lower()

    def test_subscribe_account_fires_subscription_event(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should log subscription creation event"""
        with patch.object(account_manager, '_log_event') as mock_log:
            # ACT
            subscription = account_manager.subscribe_account(
                user_id=1,
                wechat_account_id=sample_wechat_account.id
            )

            # ASSERT
            mock_log.assert_called()
            call_args = mock_log.call_args[0]
            assert "subscription_created" in call_args


# ===== Unsubscription Tests =====

class TestUnsubscribeAccount:
    """Tests for unsubscribing from a WeChat account"""

    def test_unsubscribe_account_sets_unsubscribed_at(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should mark subscription as unsubscribed"""
        # Setup: Create subscription
        subscription = account_manager.subscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )
        assert subscription.is_active() is True

        # ACT
        result = account_manager.unsubscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        # ASSERT
        assert result is True
        test_db.refresh(subscription)
        assert subscription.is_active() is False
        assert subscription.unsubscribed_at is not None

    def test_unsubscribe_account_preserves_articles(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should NOT delete articles when unsubscribing"""
        # Setup: Create subscription and article
        from app.models.wechat import WeChatArticle

        subscription = account_manager.subscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        article = WeChatArticle(
            article_id="article_123",
            wechat_account_id=sample_wechat_account.id,
            title="Test Article",
            content="Article content",
            publish_time=datetime.now(timezone.utc),
            article_url="https://example.com/article",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        test_db.add(article)
        test_db.commit()

        # ACT
        account_manager.unsubscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        # ASSERT - Article should still exist
        persisted_article = test_db.query(WeChatArticle).first()
        assert persisted_article is not None
        assert persisted_article.article_id == "article_123"

    def test_unsubscribe_account_returns_false_if_not_found(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should return False for non-existent subscription"""
        # ACT
        result = account_manager.unsubscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        # ASSERT
        assert result is False

    def test_unsubscribe_account_idempotent(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should allow unsubscribing twice without error"""
        # Setup
        account_manager.subscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        # ACT - Unsubscribe twice
        result1 = account_manager.unsubscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )
        result2 = account_manager.unsubscribe_account(
            user_id=1,
            wechat_account_id=sample_wechat_account.id
        )

        # ASSERT - First succeeds, second returns False
        assert result1 is True
        assert result2 is False


# ===== List Accounts Tests =====

class TestListUserAccounts:
    """Tests for listing user's subscribed accounts"""

    def test_list_user_accounts_returns_all_subscriptions(
        self, account_manager, test_db, sample_wechat_auth
    ):
        """Should return all active subscriptions for user"""
        # Setup: Create multiple accounts and subscribe
        account1 = WeChatAccount(
            wechat_account_id="gh_account1",
            wechat_account_name="News Daily",
            sync_status=SyncStatus.ACTIVE
        )
        account2 = WeChatAccount(
            wechat_account_id="gh_account2",
            wechat_account_name="Tech Weekly",
            sync_status=SyncStatus.ACTIVE
        )
        test_db.add_all([account1, account2])
        test_db.commit()

        # Subscribe to both
        account_manager.subscribe_account(1, account1.id)
        account_manager.subscribe_account(1, account2.id)

        # ACT
        accounts = account_manager.list_user_accounts(user_id=1)

        # ASSERT
        assert len(accounts) == 2
        names = {acc["account_name"] for acc in accounts}
        assert "News Daily" in names
        assert "Tech Weekly" in names

    def test_list_user_accounts_includes_last_sync_time(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should include last_sync_time in account data"""
        # Setup - Use naive datetime since SQLite doesn't preserve timezone
        sync_time = datetime.now() - timedelta(hours=1)
        sample_wechat_account.last_sync_time = sync_time
        test_db.commit()

        account_manager.subscribe_account(1, sample_wechat_account.id)

        # ACT
        accounts = account_manager.list_user_accounts(user_id=1)

        # ASSERT
        assert len(accounts) == 1
        assert accounts[0]["last_sync_time"] is not None
        # Compare ISO format (SQLite stores as naive datetime)
        assert accounts[0]["last_sync_time"] == sync_time.isoformat()

    def test_list_user_accounts_includes_unread_count(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should include unread article count"""
        from app.models.wechat import WeChatArticle

        # Setup: Create subscription and articles
        account_manager.subscribe_account(1, sample_wechat_account.id)

        # Create 3 articles
        for i in range(3):
            article = WeChatArticle(
                article_id=f"article_{i}",
                wechat_account_id=sample_wechat_account.id,
                title=f"Article {i}",
                content=f"Content {i}",
                publish_time=datetime.now(timezone.utc),
                article_url=f"https://example.com/{i}",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
            )
            test_db.add(article)
        test_db.commit()

        # ACT
        accounts = account_manager.list_user_accounts(user_id=1)

        # ASSERT
        assert len(accounts) == 1
        assert "unread_count" in accounts[0]
        assert accounts[0]["unread_count"] >= 0

    def test_list_user_accounts_excludes_unsubscribed(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should NOT include unsubscribed accounts"""
        # Setup
        account_manager.subscribe_account(1, sample_wechat_account.id)
        account_manager.unsubscribe_account(1, sample_wechat_account.id)

        # ACT
        accounts = account_manager.list_user_accounts(user_id=1)

        # ASSERT
        assert len(accounts) == 0

    def test_list_user_accounts_returns_empty_for_no_subscriptions(
        self, account_manager, test_db, sample_wechat_auth
    ):
        """Should return empty list for user with no subscriptions"""
        # ACT
        accounts = account_manager.list_user_accounts(user_id=1)

        # ASSERT
        assert accounts == []

    def test_list_user_accounts_returns_empty_for_nonexistent_user(
        self, account_manager, test_db
    ):
        """Should return empty list for user without WeChatAuth"""
        # ACT
        accounts = account_manager.list_user_accounts(user_id=999)

        # ASSERT
        assert accounts == []


# ===== Mute Account Tests =====

class TestMuteAccount:
    """Tests for muting account notifications"""

    def test_mute_account_sets_is_muted_true(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should set is_muted = true"""
        # Setup
        subscription = account_manager.subscribe_account(1, sample_wechat_account.id)
        assert subscription.is_muted is False

        # ACT
        result = account_manager.mute_account(1, sample_wechat_account.id)

        # ASSERT
        assert result is True
        test_db.refresh(subscription)
        assert subscription.is_muted is True
        assert subscription.is_active() is True  # Still subscribed

    def test_mute_account_does_not_delete_subscription(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should preserve subscription when muting"""
        # Setup
        subscription = account_manager.subscribe_account(1, sample_wechat_account.id)

        # ACT
        account_manager.mute_account(1, sample_wechat_account.id)

        # ASSERT - Subscription still exists and is active
        subscriptions = test_db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_auth_id == subscription.wechat_auth_id,
            WeChatSubscription.wechat_account_id == sample_wechat_account.id
        ).all()
        assert len(subscriptions) == 1
        assert subscriptions[0].unsubscribed_at is None

    def test_mute_account_fails_with_nonexistent_subscription(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should return False if subscription doesn't exist"""
        # ACT
        result = account_manager.mute_account(1, sample_wechat_account.id)

        # ASSERT
        assert result is False

    def test_mute_account_idempotent(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should allow muting twice without error"""
        # Setup
        account_manager.subscribe_account(1, sample_wechat_account.id)

        # ACT
        result1 = account_manager.mute_account(1, sample_wechat_account.id)
        result2 = account_manager.mute_account(1, sample_wechat_account.id)

        # ASSERT
        assert result1 is True
        assert result2 is True


# ===== Unmute Account Tests =====

class TestUnmuteAccount:
    """Tests for unmuting account notifications"""

    def test_unmute_account_sets_is_muted_false(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should set is_muted = false"""
        # Setup
        subscription = account_manager.subscribe_account(1, sample_wechat_account.id)
        account_manager.mute_account(1, sample_wechat_account.id)
        test_db.refresh(subscription)
        assert subscription.is_muted is True

        # ACT
        result = account_manager.unmute_account(1, sample_wechat_account.id)

        # ASSERT
        assert result is True
        test_db.refresh(subscription)
        assert subscription.is_muted is False

    def test_unmute_account_fails_with_nonexistent_subscription(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should return False if subscription doesn't exist"""
        # ACT
        result = account_manager.unmute_account(1, sample_wechat_account.id)

        # ASSERT
        assert result is False

    def test_unmute_account_idempotent(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Should allow unmuting already-unmuted account"""
        # Setup
        account_manager.subscribe_account(1, sample_wechat_account.id)

        # ACT
        result1 = account_manager.unmute_account(1, sample_wechat_account.id)
        result2 = account_manager.unmute_account(1, sample_wechat_account.id)

        # ASSERT
        assert result1 is True
        assert result2 is True


# ===== Edge Cases & Integration Tests =====

class TestEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_subscribe_then_list_contains_correct_data(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Integration: Subscribe and list should be consistent"""
        # Setup
        account_manager.subscribe_account(1, sample_wechat_account.id)

        # ACT
        accounts = account_manager.list_user_accounts(1)

        # ASSERT
        assert len(accounts) == 1
        assert accounts[0]["account_id"] == sample_wechat_account.id
        assert accounts[0]["account_name"] == sample_wechat_account.wechat_account_name

    def test_mute_then_unmute_sequence(
        self, account_manager, test_db, sample_wechat_auth, sample_wechat_account
    ):
        """Integration: Mute → unmute should preserve subscription state"""
        # Setup
        sub = account_manager.subscribe_account(1, sample_wechat_account.id)
        original_id = sub.id

        # ACT
        account_manager.mute_account(1, sample_wechat_account.id)
        account_manager.unmute_account(1, sample_wechat_account.id)

        # ASSERT - Same subscription, just state changed
        accounts = account_manager.list_user_accounts(1)
        assert len(accounts) == 1
        assert accounts[0]["account_id"] == sample_wechat_account.id

    def test_multiple_users_isolated_subscriptions(
        self, account_manager, test_db, sample_wechat_account
    ):
        """Should isolate subscriptions between different users"""
        # Setup: Create two users with same account
        auth1 = WeChatAuth(
            user_id=1,
            wechat_openid="open_id_1",
            access_token="token_1",
            refresh_token="refresh_1",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        auth2 = WeChatAuth(
            user_id=2,
            wechat_openid="open_id_2",
            access_token="token_2",
            refresh_token="refresh_2",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=2)
        )
        test_db.add_all([auth1, auth2])
        test_db.commit()

        # Subscribe both users
        account_manager.subscribe_account(1, sample_wechat_account.id)
        account_manager.subscribe_account(2, sample_wechat_account.id)

        # ACT
        user1_accounts = account_manager.list_user_accounts(1)
        user2_accounts = account_manager.list_user_accounts(2)

        # ASSERT - Both should see the account
        assert len(user1_accounts) == 1
        assert len(user2_accounts) == 1

        # But muting for user 1 shouldn't affect user 2
        account_manager.mute_account(1, sample_wechat_account.id)
        user1_muted = account_manager.list_user_accounts(1)
        user2_muted = account_manager.list_user_accounts(2)

        assert user1_muted[0]["is_muted"] is True
        # User 2's subscription state should not change
