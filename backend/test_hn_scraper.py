#!/usr/bin/env python
"""Quick test script for Hacker News scraper."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from workers.hacker_news_scraper import HackerNewsScraper


async def main():
    print("🧪 Testing Hacker News Scraper...\n")
    
    scraper = HackerNewsScraper()
    
    try:
        print("📥 Fetching top 10 HN stories...")
        stories = await scraper.fetch_stories(story_type="top", limit=10)
        print(f"✅ Got {len(stories)} stories!\n")
        
        # Show first story
        if stories:
            print("📄 Sample story:")
            story = stories[0]
            print(f"  Title: {story.get('title', 'N/A')[:70]}")
            print(f"  Score: {story.get('score', 0)} points")
            print(f"  Comments: {story.get('descendants', 0)}")
            print(f"  Author: {story.get('by', 'Anonymous')}")
            print(f"  URL: {story.get('url', 'No URL')[:60]}\n")
        
        # Transform to feed format
        print("🔄 Transforming to feed format...")
        feed_items = scraper.transform_to_feed_format(stories)
        print(f"✅ Transformed {len(feed_items)} items\n")
        
        # Show feed item
        if feed_items:
            print("📋 Sample feed item:")
            item = feed_items[0]
            for key, value in item.items():
                if isinstance(value, str) and len(str(value)) > 60:
                    print(f"  {key}: {str(value)[:60]}...")
                else:
                    print(f"  {key}: {value}")
        
        print("\n✅ Scraper test PASSED!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Scraper test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
