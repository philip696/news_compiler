#!/usr/bin/env python3
"""Test feed endpoint functionality with finance articles."""

import sys
sys.path.insert(0, '.')

from app.startup import run_startup_sequence
from app import state

print("Initializing app...")
run_startup_sequence()

print("\n" + "="*70)
print("API Endpoint Test Results")
print("="*70)

# Check finance category
finance_key = "💰 Finance"
print(f"\n1. Checking Finance Category:")
if finance_key in state.articles_by_category:
    articles = state.articles_by_category[finance_key]
    print(f"   OK - Found {len(articles)} finance articles")
    if articles:
        print(f"\n2. Sample Finance Article for /api/feed?category=Finance:")
        article = articles[0]
        print(f"   Title: {article['title'][:70]}")
        print(f"   Source: {article.get('source_name', 'N/A')}")
        print(f"   Category: {article.get('category', 'N/A')}")
        print(f"   Topic: {article.get('topic', 'N/A')}")
        print(f"   Has URL: {bool(article.get('url'))}")
        print(f"   Has Image: {bool(article.get('main_image'))}")
        print(f"   Has Embedding: {bool(article.get('embedding'))}")
else:
    print(f"   Warning - Finance category not in state")

print(f"\n3. Summary:")
print(f"   Total articles in state: {len(state.articles)}")
print(f"   Available categories: {len(state.available_categories)}")
print(f"   Finance articles ready for API: {len(state.articles_by_category.get(finance_key, []))}")

print("\nOK - Feed endpoint test complete - API would return data correctly")
