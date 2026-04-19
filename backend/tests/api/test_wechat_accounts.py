"""
Tests for WeChat account management API endpoints.

Tests the REST API layer for:
- POST /api/wechat/accounts - Subscribe to account
- GET /api/wechat/accounts - List subscriptions
- DELETE /api/wechat/accounts/{id} - Unsubscribe
- POST /api/wechat/accounts/{id}/mute - Mute notifications
- POST /api/wechat/accounts/{id}/unmute - Unmute notifications
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.models.base import Base
from app.models.wechat import (
    WeChatAuth, WeChatAccount, WeChatSubscription, WeChatArticle,
    SyncStatus
)


# ===== Database Setup =====

@pytest.fixture
def test_db_engine():
    """Create in-memory SQLite engine"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db(test_db_engine) -> Generator[Session, None, None]:
    """Create test database session"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )
    session = TestingSessionLocal()
    
    # Override dependency
    def override_get_db():
        yield session
    
    app.dependency_overrides[lambda: None] = override_get_db
    
    yield session
    session.close()


@pytest.fixture
def client(test_db: Session) -> TestClient:
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def jwt_token():
    """Create valid JWT token"""
    payload = {
        "sub": "1",  # user_id
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    secret = "test-secret-key"
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


@pytest.fixture
def sample_wechat_auth(test_db: Session):
    """Create sample WeChatAuth"""
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
    """Create sample WeChatAccount"""
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


# ===== Subscribe Tests =====

class TestSubscribeEndpoint:
    """Tests for POST /api/wechat/accounts"""

    def test_subscribe_creates_subscription(
        self, client: TestClient, test_db: Session,
        jwt_token: str, sample_wechat_auth, sample_wechat_account
    ):
        """Subscribe endpoint creates subscription and returns 201"""
        response = client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["subscription"]["account_id"] == sample_wechat_account.id
        assert body["subscription"]["account_name"] == "Tech Daily News"

    def test_subscribe_fails_without_auth(
        self, client: TestClient, sample_wechat_account
    ):
        """Subscribe requires JWT token"""
        response = client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}"
        )
        
        assert response.status_code == 401

    def test_subscribe_fails_user_not_linked_to_wechat(
        self, client: TestClient, jwt_token: str, sample_wechat_account
    ):
        """Subscribe returns 400 if user has no WeChatAuth"""
        response = client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400
        body = response.json()
        assert "error" in body

    def test_subscribe_fails_account_not_found(
        self, client: TestClient, jwt_token: str,
        sample_wechat_auth
    ):
        """Subscribe returns 404 if account doesn't exist"""
        response = client.post(
            "/api/wechat/accounts?account_id=99999",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 400

    def test_subscribe_fails_duplicate(
        self, client: TestClient, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """Subscribe returns 400 if already subscribed"""
        # First subscription succeeds
        response1 = client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response1.status_code == 201

        # Second subscription fails
        response2 = client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response2.status_code == 400
        body = response2.json()
        assert "error" in body


# ===== List Tests =====

class TestListEndpoint:
    """Tests for GET /api/wechat/accounts"""

    def test_list_returns_subscriptions(
        self, client: TestClient, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """List endpoint returns user's subscriptions"""
        # Subscribe to account
        client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        # List accounts
        response = client.get(
            "/api/wechat/accounts",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["count"] == 1
        assert len(body["accounts"]) == 1
        assert body["accounts"][0]["account_name"] == "Tech Daily News"

    def test_list_returns_empty_for_no_subscriptions(
        self, client: TestClient, jwt_token: str,
        sample_wechat_auth
    ):
        """List returns empty array if no subscriptions"""
        response = client.get(
            "/api/wechat/accounts",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 0
        assert body["accounts"] == []

    def test_list_fails_without_auth(self, client: TestClient):
        """List requires JWT token"""
        response = client.get("/api/wechat/accounts")
        assert response.status_code == 401

    def test_list_includes_metadata(
        self, client: TestClient, test_db: Session, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """List includes all account metadata"""
        # Subscribe and add an article
        client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        article = WeChatArticle(
            wechat_account_id=sample_wechat_account.id,
            title="Test Article",
            content="Test content",
            author="Test Author",
            cover_img="https://example.com/img.jpg",
            article_url="https://example.com/article",
            create_time=datetime.now(timezone.utc),
            update_time=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        test_db.add(article)
        test_db.commit()

        # List and verify metadata
        response = client.get(
            "/api/wechat/accounts",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == 200
        body = response.json()
        account = body["accounts"][0]
        assert "account_id" in account
        assert "account_name" in account
        assert "account_avatar" in account
        assert "is_verified" in account
        assert "is_muted" in account
        assert "last_sync_time" in account
        assert "unread_count" in account
        assert account["unread_count"] == 1


# ===== Unsubscribe Tests =====

class TestUnsubscribeEndpoint:
    """Tests for DELETE /api/wechat/accounts/{account_id}"""

    def test_unsubscribe_removes_subscription(
        self, client: TestClient, test_db: Session, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """Unsubscribe marks subscription as unsubscribed"""
        # Subscribe
        client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        # Unsubscribe
        response = client.delete(
            f"/api/wechat/accounts/{sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["account_id"] == sample_wechat_account.id

        # Verify subscription is marked unsubscribed
        subscription = test_db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_account_id == sample_wechat_account.id
        ).first()
        assert subscription is not None
        assert subscription.unsubscribed_at is not None

    def test_unsubscribe_fails_not_subscribed(
        self, client: TestClient, jwt_token: str,
        sample_wechat_auth
    ):
        """Unsubscribe returns 404 if not subscribed"""
        response = client.delete(
            "/api/wechat/accounts/99999",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == 404

    def test_unsubscribe_fails_without_auth(
        self, client: TestClient, sample_wechat_account
    ):
        """Unsubscribe requires JWT token"""
        response = client.delete(
            f"/api/wechat/accounts/{sample_wechat_account.id}"
        )

        assert response.status_code == 401


# ===== Mute Tests =====

class TestMuteEndpoint:
    """Tests for POST /api/wechat/accounts/{account_id}/mute"""

    def test_mute_suppresses_notifications(
        self, client: TestClient, test_db: Session, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """Mute endpoint sets is_muted flag"""
        # Subscribe
        client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        # Mute
        response = client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/mute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["is_muted"] is True

        # Verify in database
        subscription = test_db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_account_id == sample_wechat_account.id
        ).first()
        assert subscription.is_muted is True

    def test_mute_idempotent(
        self, client: TestClient, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """Mute can be called multiple times"""
        # Subscribe
        client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        # Mute twice
        response1 = client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/mute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        response2 = client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/mute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_mute_fails_not_subscribed(
        self, client: TestClient, jwt_token: str,
        sample_wechat_auth
    ):
        """Mute returns 404 if not subscribed"""
        response = client.post(
            "/api/wechat/accounts/99999/mute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == 404


# ===== Unmute Tests =====

class TestUnmuteEndpoint:
    """Tests for POST /api/wechat/accounts/{account_id}/unmute"""

    def test_unmute_restores_notifications(
        self, client: TestClient, test_db: Session, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """Unmute endpoint clears is_muted flag"""
        # Subscribe and mute
        client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/mute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        # Unmute
        response = client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/unmute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["is_muted"] is False

        # Verify in database
        subscription = test_db.query(WeChatSubscription).filter(
            WeChatSubscription.wechat_account_id == sample_wechat_account.id
        ).first()
        assert subscription.is_muted is False

    def test_unmute_idempotent(
        self, client: TestClient, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """Unmute can be called multiple times"""
        # Subscribe
        client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        # Unmute twice (not muted initially)
        response1 = client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/unmute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        response2 = client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/unmute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200


# ===== Edge Cases =====

class TestEdgeCases:
    """Integration tests for complex scenarios"""

    def test_full_subscription_lifecycle(
        self, client: TestClient, test_db: Session, jwt_token: str,
        sample_wechat_auth, sample_wechat_account
    ):
        """Full cycle: subscribe → list → mute → unmute → unsubscribe"""
        # Subscribe
        resp1 = client.post(
            f"/api/wechat/accounts?account_id={sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert resp1.status_code == 201

        # List (should show unmuted)
        resp2 = client.get(
            "/api/wechat/accounts",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert resp2.json()["accounts"][0]["is_muted"] is False

        # Mute
        resp3 = client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/mute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert resp3.status_code == 200

        # Unmute
        resp4 = client.post(
            f"/api/wechat/accounts/{sample_wechat_account.id}/unmute",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert resp4.status_code == 200

        # Unsubscribe
        resp5 = client.delete(
            f"/api/wechat/accounts/{sample_wechat_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert resp5.status_code == 200

        # List (should be empty)
        resp6 = client.get(
            "/api/wechat/accounts",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert resp6.json()["count"] == 0
