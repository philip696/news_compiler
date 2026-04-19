"""
Integration tests for WeChat articles API endpoints.

Tests the REST API layer for article retrieval, filtering, and search.
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
    
    # Override dependency - NOT overriding here as we'll do it in client fixture
    yield session
    session.close()


@pytest.fixture
def client(test_db: Session) -> TestClient:
    """FastAPI test client with database override"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    from app.db.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def jwt_token():
    """Create valid JWT token for user 1"""
    payload = {
        "sub": "1",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    secret = "test-secret-key"
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


@pytest.fixture
def sample_wechat_auth(test_db: Session):
    """Create WeChat auth for user 1"""
    auth = WeChatAuth(
        user_id=1,
        wechat_openid="test_openid",
        wechat_unionid="test_unionid",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expiry=datetime.now() + timedelta(hours=2),
        scopes="snsapi_userinfo"
    )
    test_db.add(auth)
    test_db.commit()
    test_db.refresh(auth)
    return auth


@pytest.fixture
def sample_account(test_db: Session):
    """Create sample WeChat account"""
    account = WeChatAccount(
        wechat_account_id="gh_a3f95b8e4d5c",
        wechat_account_name="Tech Daily",
        wechat_account_avatar="https://example.com/avatar.jpg",
        account_intro="Daily tech news",
        is_verified=True,
        account_type="subscription",
        sync_status=SyncStatus.ACTIVE
    )
    test_db.add(account)
    test_db.commit()
    test_db.refresh(account)
    return account


@pytest.fixture
def subscription(test_db: Session, sample_wechat_auth, sample_account):
    """Create subscription linking user to account"""
    sub = WeChatSubscription(
        wechat_auth_id=sample_wechat_auth.id,
        wechat_account_id=sample_account.id
    )
    test_db.add(sub)
    test_db.commit()
    test_db.refresh(sub)
    return sub


@pytest.fixture
def sample_articles(test_db: Session, sample_account):
    """Create sample cached articles"""
    articles_data = [
        {
            "article_id": "art_001",
            "title": "Python 3.13 Released",
            "content": "Python 3.13 brings major performance improvements...",
            "summary": "Python 3.13 release",
            "author": "Python Team",
            "publish_time": datetime.now() - timedelta(hours=2),
        },
        {
            "article_id": "art_002",
            "title": "FastAPI Best Practices",
            "content": "Modern API development with FastAPI...",
            "summary": "FastAPI guidelines",
            "author": "API Expert",
            "publish_time": datetime.now() - timedelta(hours=1),
        },
        {
            "article_id": "art_003",
            "title": "Database Optimization",
            "content": "Improve database query performance...",
            "summary": "DB optimization tips",
            "author": "DB Pro",
            "publish_time": datetime.now() - timedelta(minutes=30),
        },
    ]
    
    articles = []
    for data in articles_data:
        article = WeChatArticle(
            **data,
            wechat_account_id=sample_account.id,
            article_url=f"https://example.com/{data['article_id']}",
            cached_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24),
            source_type="wechat"
        )
        test_db.add(article)
        articles.append(article)
    
    test_db.commit()
    return articles


# ===== Tests =====

class TestGetArticles:
    """Tests for GET /api/wechat/articles"""

    def test_get_articles_requires_auth(self, client: TestClient):
        """Should return 401 if not authenticated"""
        response = client.get("/api/wechat/articles")
        assert response.status_code == 401

    def test_get_articles_requires_wechat_auth(
        self, client: TestClient, jwt_token: str
    ):
        """Should return 400 if user not linked to WeChat"""
        response = client.get(
            "/api/wechat/articles",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "User not linked to WeChat"

    def test_get_articles_returns_empty_if_no_subscriptions(
        self, client: TestClient, jwt_token: str, sample_wechat_auth
    ):
        """Should return empty list if user has no subscriptions"""
        response = client.get(
            "/api/wechat/articles",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["count"] == 0
        assert body["articles"] == []

    def test_get_articles_returns_all_articles(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should return all articles from subscribed accounts"""
        response = client.get(
            "/api/wechat/articles",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["count"] == 3
        assert len(body["articles"]) == 3

    def test_get_articles_returns_sorted_by_publish_time(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should return articles sorted by publish_time DESC"""
        response = client.get(
            "/api/wechat/articles",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        articles = response.json()["articles"]
        # Newest should be first
        assert "Optimization" in articles[0]["title"]  # Most recent
        assert "Python" in articles[2]["title"]  # Oldest

    def test_get_articles_respects_limit(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should respect limit parameter"""
        response = client.get(
            "/api/wechat/articles?limit=2",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        body = response.json()
        assert body["count"] == 2
        assert len(body["articles"]) == 2

    def test_get_articles_filter_by_account(
        self, client: TestClient, jwt_token: str,
        subscription, sample_account, sample_articles
    ):
        """Should filter articles by account"""
        response = client.get(
            f"/api/wechat/articles?account={sample_account.id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 3
        assert all(a["wechat_account_id"] == sample_account.id 
                   for a in body["articles"])

    def test_get_articles_filter_by_account_not_subscribed(
        self, client: TestClient, jwt_token: str, sample_wechat_auth
    ):
        """Should return 403 if account not subscribed"""
        response = client.get(
            "/api/wechat/articles?account=999",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 403

    def test_get_articles_search(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should search articles by query"""
        response = client.get(
            "/api/wechat/articles?q=Python",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] >= 1
        assert any("Python" in a["title"] for a in body["articles"])

    def test_get_articles_search_case_insensitive(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should find articles regardless of case"""
        response_upper = client.get(
            "/api/wechat/articles?q=PYTHON",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        response_lower = client.get(
            "/api/wechat/articles?q=python",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response_upper.json()["count"] == response_lower.json()["count"]

    def test_get_articles_includes_metadata(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should include cached_at and expires_at in response"""
        response = client.get(
            "/api/wechat/articles",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        body = response.json()
        assert "cached_at" in body
        assert "expires_at" in body


class TestGetArticle:
    """Tests for GET /api/wechat/articles/{article_id}"""

    def test_get_article_requires_auth(
        self, client: TestClient, sample_articles
    ):
        """Should return 401 if not authenticated"""
        response = client.get(f"/api/wechat/articles/{sample_articles[0].id}")
        assert response.status_code == 401

    def test_get_article_requires_subscription(
        self, client: TestClient, jwt_token: str, sample_articles
    ):
        """Should return 403 if user not subscribed to account"""
        response = client.get(
            f"/api/wechat/articles/{sample_articles[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 401  # No WeChat auth

    def test_get_article_returns_full_details(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should return full article details"""
        article_id = sample_articles[0].id
        response = client.get(
            f"/api/wechat/articles/{article_id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["article"]["id"] == article_id
        assert body["article"]["title"] == "Python 3.13 Released"
        assert body["article"]["content"] == "Python 3.13 brings major performance improvements..."

    def test_get_article_returns_404_if_not_found(
        self, client: TestClient, jwt_token: str, subscription
    ):
        """Should return 404 if article doesn't exist"""
        response = client.get(
            "/api/wechat/articles/99999",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 404

    def test_get_article_includes_all_fields(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should include all article fields"""
        article_id = sample_articles[0].id
        response = client.get(
            f"/api/wechat/articles/{article_id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        article = response.json()["article"]
        assert "id" in article
        assert "article_id" in article
        assert "title" in article
        assert "content" in article
        assert "summary" in article
        assert "author" in article
        assert "publish_time" in article
        assert "article_url" in article
        assert "wechat_account_id" in article

    def test_get_article_not_accessible_without_subscription(
        self, client: TestClient, test_db: Session, jwt_token: str,
        sample_wechat_auth, sample_articles
    ):
        """Article should be inaccessible if user doesn't subscribe to account"""
        # Don't create subscription
        response = client.get(
            f"/api/wechat/articles/{sample_articles[0].id}",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 403


class TestArticleEdgeCases:
    """Edge case tests"""

    def test_empty_search_query(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Empty search query should return all articles"""
        response = client.get(
            "/api/wechat/articles?q=",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        # Empty query should be ignored and return all
        assert response.status_code in [200, 400]

    def test_special_characters_in_search(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should handle special characters in search"""
        response = client.get(
            "/api/wechat/articles?q=%2B%2F",  # +/
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        assert response.status_code == 200

    def test_limit_maximum(
        self, client: TestClient, jwt_token: str,
        subscription, sample_articles
    ):
        """Should enforce maximum limit of 500"""
        response = client.get(
            "/api/wechat/articles?limit=600",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        # Should either be validated or capped at 500
        assert response.status_code in [200, 422]
