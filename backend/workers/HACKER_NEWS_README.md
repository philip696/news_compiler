# Hacker News Scraper

Free real-time Hacker News scraper using the official Firebase API.

**Cost**: FREE ✅ (No authentication, no limits)

---

## How It Works

1. **Daily Scheduler** – Automatically scrapes HN at 2 AM UTC
2. **Firebase API** – Real-time, official HN API (no rate limiting)
3. **Async Fetching** – Fetches 50 stories in parallel for speed
4. **Feed Integration** – Transforms to your feed schema

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Test the Scraper Directly
```bash
cd backend
python -m workers.hacker_news_scraper
```

### 3. It's Automatic!
- Scheduler starts automatically with your FastAPI app
- Runs daily at 2 AM UTC
- Logs to startup:
  ```
  ✅ Background scheduler started
     📅 Job scheduled: Hacker News scraping at 02:00 UTC daily
  ```

---

## Configuration

Edit `workers/scheduler.py` to customize:

### Change Schedule Time
```python
# Daily at 2 AM UTC
trigger=CronTrigger(hour=2, minute=0)

# Or every 6 hours:
trigger=CronTrigger(hour='*/6')

# Or every 4 hours:
trigger=CronTrigger(hour='*/4')

# Or every day at 3 PM UTC:
trigger=CronTrigger(hour=15, minute=0)
```

### Change Story Type
```python
# In _scrape_hacker_news() method:
count = asyncio.run(scraper.fetch_and_process(
    story_type="top",   # Options: "top", "new", "best"
    limit=50            # Change how many stories
))
```

**Story Types:**
- `"top"` – Highest ranked (default, best quality)
- `"new"` – Newest stories first
- `"best"` – Highest upvoted

---

## API Details

**Endpoint:** `https://hacker-news.firebaseio.com/v0`

**Available Endpoints:**
- `/topstories.json` – Top stories IDs
- `/newstories.json` – Newest stories IDs  
- `/beststories.json` – Best stories IDs
- `/item/{id}.json` – Story details

**Story Data:**
```json
{
  "id": 123456,
  "title": "...",
  "url": "...",
  "author": "...",
  "score": 100,
  "descendants": 45,  // comments
  "time": 1234567890  // Unix timestamp
}
```

---

## Logging

Monitor the scheduler with:
```bash
tail -f /tmp/geb_startup.log | grep "Hacker News"
```

Or check logs in your application:
```python
import logging
logger = logging.getLogger("workers.hacker_news_scraper")
logger.info("Check this")
```

---

## Integration with Your Feed

Once you have feed items, save to database:

```python
# In hacker_news_scraper.py, uncomment:
from app.services.news_service import NewsService
news_service = NewsService()
for item in feed_items:
    news_service.create_news(item)
```

---

## Rate Limits

**HN Firebase API: NONE** ✅

- Publicly available
- No authentication needed
- No rate limiting (be respectful, use reasonable limits like 50-100 stories)
- Official maintained API

---

## Troubleshooting

### Stories not appearing?
1. Check scheduler is running: Look for `✅ Background scheduler started` in logs
2. Check next run time: `GET /api/admin/scheduler/jobs` (if you add this endpoint)
3. Test manually: `python -m workers.hacker_news_scraper`

### Want to run immediately (not wait for schedule)?
```python
# In FastAPI route or anywhere:
from workers.hacker_news_scraper import HackerNewsScraper
import asyncio

scraper = HackerNewsScraper()
count = await scraper.fetch_and_process()
```

### Want to run in separate service?
```bash
# Standalone daemon
python -c "
from workers.scheduler import get_scheduler
import time
scheduler = get_scheduler()
scheduler.start_scheduler()
while True:
    time.sleep(60)
"
```

---

## What Data You Get

Transform example:
```python
{
    "title": "How to build X",
    "url": "https://example.com",
    "source": "Hacker News",
    "author": "dang",
    "score": 234,
    "comments": 45,
    "published_at": "2024-04-16T12:34:56",
    "external_id": "hn_39234234",
    "category": "technology",
    "external_source": "hacker_news"
}
```

---

## References

- **Official HN API Docs**: https://github.com/HackerNews/API
- **APScheduler Docs**: https://apscheduler.readthedocs.io/
- **HTTPX Async**: https://www.python-httpx.org/
