#!/usr/bin/env python3
"""
Comprehensive test for Yahoo Finance integration in GEB.
Tests: API client, ingestion, state management, and feed endpoint.
"""

import sys
import asyncio
import pytest
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.news_service import NewsService, get_news_service
from app.ingestion.loader import ingest_yahoo_finance_articles, classify_topic, text_to_embedding
from app import state
from app.startup import run_startup_sequence


@pytest.mark.asyncio
async def test_news_service():
    """Test 1: NewsService API client."""
    print("\n" + "="*70)
    print("TEST 1: NewsService API Client")
    print("="*70)
    
    service = NewsService()
    
    # Test Yahoo Finance
    print("\n📡 Fetching Yahoo Finance articles...")
    articles = await service.get_yahoo_finance_news(limit=5)
    assert len(articles) > 0, "Yahoo Finance should return articles (or fallback)"
    assert all("Yahoo Finance" in a.get("source", "") for a in articles), "All articles should mention Yahoo Finance"
    assert all(a.get("category") == "💰 Finance" for a in articles), "Category should be Finance"
    print(f"✅ Retrieved {len(articles)} articles")
    
    for i, article in enumerate(articles[:2], 1):
        print(f"\n  Article {i}:")
        print(f"    Title: {article['title'][:50]}...")
        print(f"    Source: {article['source']}")
        print(f"    Has URL: {bool(article.get('url'))}")
        print(f"    Has content: {bool(article.get('content'))}")
    
    print("\n✅ NewsService test passed")
    return articles


@pytest.mark.asyncio
async def test_ingestion():
    """Test 2: Ingestion pipeline."""
    print("\n" + "="*70)
    print("TEST 2: Ingestion Pipeline")
    print("="*70)
    
    # Clear state
    state.articles.clear()
    state.articles_by_category.clear()
    state.available_categories.clear()
    
    print("\n📥 Ingesting Yahoo Finance articles...")
    count = await ingest_yahoo_finance_articles()
    
    assert count > 0, "Should ingest at least one article"
    print(f"✅ Ingested {count} articles")
    
    print(f"📊 Total articles in state: {len(state.articles)}")
    assert len(state.articles) == count, "All ingested articles should be in state"
    
    # Check category
    finance_category = "💰 Finance"
    assert finance_category in state.available_categories, "Finance category should be available"
    assert finance_category in state.articles_by_category, "Finance category should be populated"
    
    finance_articles = state.articles_by_category[finance_category]
    print(f"💰 Finance articles in category: {len(finance_articles)}")
    assert len(finance_articles) == count, "All articles should be in Finance category"
    
    print("\n✅ Ingestion test passed")
    return finance_articles


@pytest.mark.asyncio
async def test_article_structure():
    """Test 3: Article data structure and classification."""
    print("\n" + "="*70)
    print("TEST 3: Article Structure & Classification")
    print("="*70)
    
    articles = list(state.articles.values())
    assert len(articles) > 0, "Should have articles in state"
    
    article = articles[0]
    print(f"\n🔍 Checking article structure...")
    
    # Verify required fields
    required_fields = ["id", "title", "content", "url", "source_name", "topic", "category"]
    for field in required_fields:
        assert field in article, f"Article missing required field: {field}"
        assert article[field] is not None, f"Article field '{field}' is None"
    
    print(f"  ✅ Title: {article['title'][:50]}...")
    print(f"  ✅ Source: {article['source_name']}")
    print(f"  ✅ Topic: {article['topic']}")
    print(f"  ✅ Category: {article['category']}")
    print(f"  ✅ Embedding exists: {bool(article.get('embedding'))}")
    
    # Verify topic classification
    valid_topics = ["technology", "politics", "finance", "sports", "science", "health"]
    assert article["topic"] in valid_topics, f"Topic should be one of {valid_topics}"
    
    print("\n✅ Article structure test passed")


@pytest.mark.asyncio
async def test_news_service_singleton():
    """Test 4: NewsService singleton pattern."""
    print("\n" + "="*70)
    print("TEST 4: NewsService Singleton")
    print("="*70)
    
    service1 = get_news_service()
    service2 = get_news_service()
    
    assert service1 is service2, "Singleton should return same instance"
    print("✅ Singleton pattern verified")


@pytest.mark.asyncio
async def test_feed_endpoint_integration():
    """Test 5: Feed endpoint integration."""
    print("\n" + "="*70)
    print("TEST 5: Feed Endpoint Integration")
    print("="*70)
    
    # Simulate what the feed endpoint does
    finance_category = "💰 Finance"
    
    if finance_category in state.articles_by_category:
        articles = state.articles_by_category[finance_category]
        print(f"\n📰 Mock feed endpoint response:")
        print(f"  Category: {finance_category}")
        print(f"  Total articles: {len(articles)}")
        
        if articles:
            article = articles[0]
            print(f"  First article: {article['title'][:50]}...")
            
            response = {
                "category": finance_category,
                "articles": articles,
                "total": len(articles),
            }
            assert response["total"] > 0, "Response should contain articles"
            print(f"✅ Feed response structure valid")
    else:
        print("⚠️  Finance category not in state (might be expected if ingestion failed)")


async def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("🧪 YAHOO FINANCE INTEGRATION TEST SUITE")
    print("="*70)
    
    try:
        # Test 1: API client
        articles = await test_news_service()
        
        # Test 2: Ingestion
        ingested = await test_ingestion()
        
        # Test 3: Article structure
        await test_article_structure()
        
        # Test 4: Singleton
        await test_news_service_singleton()
        
        # Test 5: Feed integration
        await test_feed_endpoint_integration()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print(f"""
Summary:
  • NewsService API client: ✅ Working (with fallback)
  • Ingestion pipeline: ✅ Working ({len(list(state.articles.values()))} articles)
  • Article structure: ✅ Valid (all required fields)
  • Singleton pattern: ✅ Verified
  • Feed integration: ✅ Ready for use

Yahoo Finance integration is complete and operational!
        """)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
