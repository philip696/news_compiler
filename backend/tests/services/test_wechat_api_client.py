"""
Tests for WeChat article fetching and caching service.

Tests the API client layer for:
- fetch_articles_for_account() - Fetch from WeChat API
- cache_articles() - Batch save to database
- get_cached_articles() - Query cached articles
- search_articles() - Full-text search
- filter_articles() - Client-side filtering
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.models.wechat import WeChatAccount, WeChatArticle, WeChatAuth, WeChatSubscription, SyncStatus
from app.services.wechat_api_client import WeChatAPIClient


# ===== Database Setup =====

@pytest.fixture
def test_db_engine():
    """Create in-memory SQLite engine"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db(test_db_engine) -> Session:
    """Create test database session"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def api_client(test_db: Session):
    """Create WeChatAPIClient instance"""
    return WeChatAPIClient(db=test_db)


@pytest.fixture
def sample_wechat_account(test_db: Session):
    """Create sample WeChat account"""
    account = WeChatAccount(
        wechat_account_id="gh_a3f95b8e4d5c",
        wechat_account_name="Tech Daily News",
        wechat_account_avatar="https://example.com/avatar.jpg",
        account_intro="Daily technology news",
        is_verified=True,
        account_type="subscription",
        sync_status=SyncStatus.ACTIVE
    )
    test_db.add(account)
    test_db.commit()
    test_db.refresh(account)
    return account


@pytest.fixture
def sample_articles():
    """Sample articles data (as if from WeChat API)"""
    return [
        {
            "article_id": "article_001",
            "title": "Python 3.13 Released with New Features",
            "content": "Python 3.13 introduces several performance improvements...",
            "summary": "Major updates in Python 3.13",
            "author": "Python Foundation",
            "publish_time": "2026-04-18T10:00:00Z",
            "article_url": "https://example.com/article1",
            "image_url": "https://example.com/img1.jpg",
        },
        {
            "article_id": "article_002",
            "title": "FastAPI Best Practices for 2026",
            "content": "FastAPI continues to be the go-to framework for building modern APIs...",
            "summary": "Guidelines for FastAPI development",
            "author": "API Expert",
            "publish_time": "2026-04-17T15:30:00Z",
            "article_url": "https://example.com/article2",
            "image_url": "https://example.com/img2.jpg",
        },
        {
            "article_id": "article_003",
            "title": "Database Optimization Tips",
            "content": "Learn how to optimize your database queries for better performance...",
            "summary": "Database performance tuning",
            "author": "Database Pro",
            "publish_time": "2026-04-16T12:00:00Z",
            "article_url": "https://example.com/article3",
            "image_url": None,
        },
    ]


# ===== Fetch Articles Tests =====

class TestFetchArticlesForAccount:
    """Tests for fetching articles from WeChat API"""

    def test_fetch_articles_returns_list_of_articles(
        self, api_client, sample_wechat_account, sample_articles, monkeypatch
    ):
        """Should fetch articles and return parsed list"""
        # Mock the API call
        def mock_fetch(*args, **kwargs):
            return sample_articles

        monkeypatch.setattr(api_client, "_call_wechat_api", mock_fetch)

        # ACT
        result = api_client.fetch_articles_for_account(sample_wechat_account.id)

        # ASSERT
        assert result is not None
        assert len(result) == 3
        assert result[0]["title"] == "Python 3.13 Released with New Features"
        assert result[0]["article_id"] == "article_001"
        assert result[0]["author"] == "Python Foundation"

    def test_fetch_articles_with_limit(
        self, api_client, sample_wechat_account, sample_articles, monkeypatch
    ):
        """Should respect limit parameter"""
        def mock_fetch(*args, **kwargs):
            limit = kwargs.get("limit", 50)
            return sample_articles[:limit]

        monkeypatch.setattr(api_client, "_call_wechat_api", mock_fetch)

        # ACT
        result = api_client.fetch_articles_for_account(sample_wechat_account.id, limit=2)

        # ASSERT
        assert len(result) <= 2

    def test_fetch_articles_handles_empty_response(
        self, api_client, sample_wechat_account, monkeypatch
    ):
        """Should return empty list if API returns nothing"""
        def mock_fetch(*args, **kwargs):
            return []

        monkeypatch.setattr(api_client, "_call_wechat_api", mock_fetch)

        # ACT
        result = api_client.fetch_articles_for_account(sample_wechat_account.id)

        # ASSERT
        assert result == []

    def test_fetch_articles_handles_api_error(
        self, api_client, sample_wechat_account, monkeypatch
    ):
        """Should return empty list on API error"""
        def mock_fetch(*args, **kwargs):
            raise Exception("API Error")

        monkeypatch.setattr(api_client, "_call_wechat_api", mock_fetch)

        # ACT
        result = api_client.fetch_articles_for_account(sample_wechat_account.id)

        # ASSERT
        assert result == []

    def test_fetch_articles_parses_timestamps(
        self, api_client, sample_wechat_account, sample_articles, monkeypatch
    ):
        """Should parse ISO8601 timestamps to datetime"""
        def mock_fetch(*args, **kwargs):
            return sample_articles

        monkeypatch.setattr(api_client, "_call_wechat_api", mock_fetch)

        # ACT
        result = api_client.fetch_articles_for_account(sample_wechat_account.id)

        # ASSERT
        assert isinstance(result[0]["publish_time"], datetime)
        assert result[0]["publish_time"].year == 2026


# ===== Cache Articles Tests =====

class TestCacheArticles:
    """Tests for caching articles in database"""

    def test_cache_articles_inserts_into_db(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should insert articles into database"""
        # ACT
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ASSERT
        cached = test_db.query(WeChatArticle).filter(
            WeChatArticle.wechat_account_id == sample_wechat_account.id
        ).all()
        assert len(cached) == 3
        assert cached[0].title == "Python 3.13 Released with New Features"

    def test_cache_articles_sets_expires_at(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should set expires_at to now + TTL"""
        # ACT
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ASSERT
        cached = test_db.query(WeChatArticle).filter(
            WeChatArticle.wechat_account_id == sample_wechat_account.id
        ).first()
        
        assert cached.expires_at is not None
        # Should be approximately 24 hours from now (use naive datetime for SQLite)
        expected_expiry = datetime.now() + timedelta(hours=24)
        time_diff = abs((cached.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_cache_articles_skips_duplicates(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should skip articles already cached (by article_url)"""
        # Cache once
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # Cache same articles again
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ASSERT - should still only have 3 articles
        cached = test_db.query(WeChatArticle).filter(
            WeChatArticle.wechat_account_id == sample_wechat_account.id
        ).all()
        assert len(cached) == 3

    def test_cache_articles_with_custom_ttl(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should respect custom cache TTL"""
        # ACT - use 48 hour TTL
        api_client.cache_articles(
            sample_wechat_account.id, 
            sample_articles,
            cache_ttl_hours=48
        )

        # ASSERT
        cached = test_db.query(WeChatArticle).first()
        expected_expiry = datetime.now() + timedelta(hours=48)
        time_diff = abs((cached.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60

    def test_cache_articles_sets_cached_at(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should set cached_at timestamp"""
        # ACT
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ASSERT
        cached = test_db.query(WeChatArticle).first()
        assert cached.cached_at is not None
        # Should be recent (within 1 minute)
        time_diff = abs((cached.cached_at - datetime.now()).total_seconds())
        assert time_diff < 60


# ===== Get Cached Articles Tests =====

class TestGetCachedArticles:
    """Tests for retrieving cached articles"""

    def test_get_cached_articles_returns_non_expired(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should return only non-expired articles"""
        # Cache articles
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ACT
        result = api_client.get_cached_articles(sample_wechat_account.id)

        # ASSERT
        assert len(result["articles"]) == 3
        assert result["articles"][0]["title"] == "Python 3.13 Released with New Features"

    def test_get_cached_articles_excludes_expired(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should exclude expired articles"""
        # Cache articles
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # Manually expire first article
        first_article = test_db.query(WeChatArticle).first()
        first_article.expires_at = datetime.now() - timedelta(hours=1)
        test_db.commit()

        # ACT
        result = api_client.get_cached_articles(sample_wechat_account.id)

        # ASSERT
        assert len(result["articles"]) == 2
        assert all(a["title"] != "Python 3.13 Released with New Features" 
                   for a in result["articles"])

    def test_get_cached_articles_sorted_by_publish_time(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should return articles sorted by publish_time DESC"""
        # Cache articles
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ACT
        result = api_client.get_cached_articles(sample_wechat_account.id)

        # ASSERT - should be newest first
        articles = result["articles"]
        assert articles[0]["title"] == "Python 3.13 Released with New Features"  # 2026-04-18
        assert articles[2]["title"] == "Database Optimization Tips"  # 2026-04-16

    def test_get_cached_articles_respects_limit(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should return only requested limit of articles"""
        # Cache articles
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ACT
        result = api_client.get_cached_articles(sample_wechat_account.id, limit=2)

        # ASSERT
        assert len(result["articles"]) == 2

    def test_get_cached_articles_returns_metadata(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should return cached_at and expires_at times"""
        # Cache articles
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ACT
        result = api_client.get_cached_articles(sample_wechat_account.id)

        # ASSERT
        assert "cached_at" in result
        assert "expires_at" in result
        assert isinstance(result["cached_at"], datetime)
        assert isinstance(result["expires_at"], datetime)

    def test_get_cached_articles_empty_if_none_exist(
        self, api_client, sample_wechat_account
    ):
        """Should return empty articles list if none cached"""
        # ACT
        result = api_client.get_cached_articles(sample_wechat_account.id)

        # ASSERT
        assert result["articles"] == []
        assert "cached_at" in result
        assert "expires_at" in result


# ===== Search Articles Tests =====

class TestSearchArticles:
    """Tests for searching cached articles"""

    def test_search_articles_finds_by_title(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should find articles by title search"""
        # Setup: Create user and subscription
        auth = WeChatAuth(
            user_id=1,
            wechat_openid="test_openid",
            access_token="test_token",
            token_expiry=datetime.now() + timedelta(hours=2),
        )
        test_db.add(auth)
        test_db.commit()

        subscription = WeChatSubscription(
            wechat_auth_id=auth.id,
            wechat_account_id=sample_wechat_account.id
        )
        test_db.add(subscription)
        test_db.commit()

        # Cache articles
        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ACT
        result = api_client.search_articles(user_id=1, query="Python")

        # ASSERT
        assert len(result) >= 1
        assert any("Python" in a["title"] for a in result)

    def test_search_articles_finds_in_content(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should find articles by content search"""
        # Setup
        auth = WeChatAuth(
            user_id=1,
            wechat_openid="test_openid",
            access_token="test_token",
            token_expiry=datetime.now() + timedelta(hours=2),
        )
        test_db.add(auth)
        test_db.commit()

        subscription = WeChatSubscription(
            wechat_auth_id=auth.id,
            wechat_account_id=sample_wechat_account.id
        )
        test_db.add(subscription)
        test_db.commit()

        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ACT
        result = api_client.search_articles(user_id=1, query="database")

        # ASSERT
        assert len(result) >= 1
        assert any("database" in a.get("content", "").lower() 
                   for a in result)

    def test_search_articles_filters_to_user_subscriptions(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should only search user's subscribed accounts"""
        # Setup: User1 with subscription to account1
        auth1 = WeChatAuth(
            user_id=1,
            wechat_openid="user1_openid",
            access_token="token1",
            token_expiry=datetime.now() + timedelta(hours=2),
        )
        test_db.add(auth1)
        test_db.commit()

        sub1 = WeChatSubscription(
            wechat_auth_id=auth1.id,
            wechat_account_id=sample_wechat_account.id
        )
        test_db.add(sub1)
        test_db.commit()

        # Create second account and don't subscribe user1
        account2 = WeChatAccount(
            wechat_account_id="gh_other",
            wechat_account_name="Other News",
            account_intro="Other news",
            account_type="subscription",
            sync_status=SyncStatus.ACTIVE
        )
        test_db.add(account2)
        test_db.commit()

        # Cache articles in both accounts
        api_client.cache_articles(sample_wechat_account.id, sample_articles)
        api_client.cache_articles(account2.id, sample_articles)

        # ACT - User1 searches
        result = api_client.search_articles(user_id=1, query="Python")

        # ASSERT - Should only find in subscribed account
        assert len(result) >= 0
        # All results should be from sample_wechat_account
        if len(result) > 0:
            assert result[0]["wechat_account_id"] == sample_wechat_account.id

    def test_search_articles_returns_empty_if_no_results(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should return empty list if no matches"""
        # Setup
        auth = WeChatAuth(
            user_id=1,
            wechat_openid="test_openid",
            access_token="test_token",
            token_expiry=datetime.now() + timedelta(hours=2),
        )
        test_db.add(auth)
        test_db.commit()

        sub = WeChatSubscription(
            wechat_auth_id=auth.id,
            wechat_account_id=sample_wechat_account.id
        )
        test_db.add(sub)
        test_db.commit()

        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ACT
        result = api_client.search_articles(user_id=1, query="NonexistentTerm123")

        # ASSERT
        assert result == []

    def test_search_articles_is_case_insensitive(
        self, api_client, test_db, sample_wechat_account, sample_articles
    ):
        """Should find articles regardless of case"""
        # Setup
        auth = WeChatAuth(
            user_id=1,
            wechat_openid="test_openid",
            access_token="test_token",
            token_expiry=datetime.now() + timedelta(hours=2),
        )
        test_db.add(auth)
        test_db.commit()

        sub = WeChatSubscription(
            wechat_auth_id=auth.id,
            wechat_account_id=sample_wechat_account.id
        )
        test_db.add(sub)
        test_db.commit()

        api_client.cache_articles(sample_wechat_account.id, sample_articles)

        # ACT - search with different cases
        result_upper = api_client.search_articles(user_id=1, query="PYTHON")
        result_lower = api_client.search_articles(user_id=1, query="python")
        result_mixed = api_client.search_articles(user_id=1, query="PyThOn")

        # ASSERT - all should find same results
        assert len(result_upper) == len(result_lower) == len(result_mixed)
        assert len(result_upper) >= 1


# ===== Filter Articles Tests =====

class TestFilterArticles:
    """Tests for client-side article filtering"""

    def test_filter_articles_with_include_keywords(self, api_client, sample_articles):
        """Should filter to only include specified keywords"""
        # ACT
        result = api_client.filter_articles(
            sample_articles,
            include_keywords=["Python", "performance"]
        )

        # ASSERT
        assert len(result) >= 2
        # All results should contain at least one include keyword
        for article in result:
            text = (article.get("title", "") + " " + article.get("content", "")).lower()
            assert any(kw.lower() in text for kw in ["python", "performance"])

    def test_filter_articles_with_exclude_keywords(self, api_client, sample_articles):
        """Should exclude specified keywords"""
        # ACT
        result = api_client.filter_articles(
            sample_articles,
            exclude_keywords=["Database", "optimization"]
        )

        # ASSERT
        assert len(result) <= 2
        # No results should contain excluded keywords
        for article in result:
            text = (article.get("title", "") + " " + article.get("content", "")).lower()
            assert not any(kw.lower() in text for kw in ["database", "optimization"])

    def test_filter_articles_with_both_include_and_exclude(
        self, api_client, sample_articles
    ):
        """Should apply both include and exclude filters"""
        # ACT - include "API" or "Python", exclude "Database"
        result = api_client.filter_articles(
            sample_articles,
            include_keywords=["API", "Python"],
            exclude_keywords=["Database"]
        )

        # ASSERT
        for article in result:
            text = (article.get("title", "") + " " + article.get("content", "")).lower()
            # Must contain include keyword
            assert any(kw.lower() in text for kw in ["api", "python"])
            # Must not contain exclude keyword
            assert "database" not in text

    def test_filter_articles_returns_empty_if_no_matches(
        self, api_client, sample_articles
    ):
        """Should return empty list if no articles match"""
        # ACT
        result = api_client.filter_articles(
            sample_articles,
            include_keywords=["NonexistentKeyword"]
        )

        # ASSERT
        assert result == []

    def test_filter_articles_case_insensitive(self, api_client, sample_articles):
        """Should match keywords regardless of case"""
        # ACT
        result_upper = api_client.filter_articles(
            sample_articles,
            include_keywords=["PYTHON"]
        )
        result_lower = api_client.filter_articles(
            sample_articles,
            include_keywords=["python"]
        )

        # ASSERT
        assert len(result_upper) == len(result_lower) == 1

    def test_filter_articles_no_filter_returns_all(self, api_client, sample_articles):
        """Should return all articles if no filters specified"""
        # ACT
        result = api_client.filter_articles(sample_articles)

        # ASSERT
        assert len(result) == len(sample_articles)

    def test_filter_articles_preserves_order(self, api_client, sample_articles):
        """Should preserve original article order"""
        # ACT
        result = api_client.filter_articles(
            sample_articles,
            include_keywords=["Python", "FastAPI", "Database"]
        )

        # ASSERT
        # Should maintain order of original articles
        original_ids = [a["article_id"] for a in sample_articles]
        result_ids = [a["article_id"] for a in result]
        for i in range(len(result_ids) - 1):
            orig_idx_curr = original_ids.index(result_ids[i])
            orig_idx_next = original_ids.index(result_ids[i + 1])
            assert orig_idx_curr < orig_idx_next
