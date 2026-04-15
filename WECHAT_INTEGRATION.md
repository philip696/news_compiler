# WeChat Integration Guide

GEB now integrates with **wewe-rss** to provide real-time WeChat Official Account article fetching and RSS generation.

## Quick Start

### 1. Prerequisites
- Docker (for wewe-rss service)
- Python 3.11+
- Your existing GEB setup

### 2. Start Services

```bash
# Start wewe-rss and FastAPI
docker-compose up -d wewe-rss fastapi

# Or use the convenience script
bash start-with-wechat.sh
```

This starts:
- **wewe-rss** on `http://localhost:4000` - Manages WeChat subscriptions and fetches articles
- **FastAPI backend** on `http://localhost:8000` - Your GEB backend with WeChat endpoints

### 3. Access WeChat APIs

All endpoints require authentication. Visit `http://localhost:8000/docs` for interactive API documentation.

## API Endpoints

### Get All Articles
```bash
GET /api/wechat/articles?limit=100&title_include=politics
```
Fetch all articles from all subscribed WeChat accounts with optional filtering.

**Parameters:**
- `limit` (int, default=100): Number of articles to return
- `title_include` (str, optional): Filter articles by title substring
- `title_exclude` (str, optional): Exclude articles by title substring

**Response:**
```json
{
  "status": "success",
  "count": 42,
  "articles": [
    {
      "id": "article_id",
      "title": "Article Title",
      "content": "Full HTML content",
      "link": "https://...",
      "pubDate": "2024-04-15T10:30:00Z",
      "author": "Author Name"
    }
  ]
}
```

### Get Account Articles
```bash
GET /api/wechat/accounts/{account_id}/articles?limit=50
```
Get articles from a specific WeChat account.

**Parameters:**
- `account_id` (str): WeChat account ID (e.g., `MP_WXS_123456`)
- `limit` (int, default=50): Number of articles
- `title_include` (str, optional): Filter by title

### Get as RSS/Atom Feed
```bash
GET /api/wechat/rss/{account_id}
GET /api/wechat/atom/{account_id}
```
Get articles formatted as RSS or Atom feeds from wewe-rss directly.

These can be used with RSS readers like Feedly, Inoreader, etc.

### Trigger Manual Update
```bash
POST /api/wechat/accounts/{account_id}/update
```
Force an immediate update for a specific WeChat account from wewe-rss.

### Health Check
```bash
GET /api/wechat/health
```
Check if wewe-rss is running and healthy.

## Architecture

```
GEB Backend (FastAPI)
    ↓
    └→ WeChatService (abstraction layer)
        ↓
        └→ wewe-rss API (http://localhost:4000)
            ↓
            └→ WeChat Official Accounts
```

### Key Design Decisions

1. **No Database Sync**: Articles are fetched directly from wewe-rss on demand
2. **Stateless**: GEB doesn't store WeChat data; wewe-rss manages subscriptions
3. **Real-time**: Updates every 10 minutes via wewe-rss cron (configurable)
4. **Cached**: HTTP responses can be cached by Redis (future enhancement)

## Configuration

### Environment Variables

```env
# wewe-rss API endpoint
WEWE_RSS_URL=http://localhost:4000

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000
```

### wewe-rss Configuration

Edit `docker-compose.yml` to customize:
```yaml
wewe-rss:
  environment:
    # Update frequency (cron format)
    CRON_EXPRESSION: "*/10 * * * *"
    
    # Get full article content
    FEED_MODE: fulltext
    
    # Server URL for RSS generation
    SERVER_ORIGIN_URL: "http://localhost:4000"
```

## Usage Examples

### Fetch Latest Articles
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/api/wechat/articles",
        params={"limit": 50},
        headers={"Authorization": "Bearer YOUR_TOKEN"}
    )
    articles = response.json()
```

### Search by Title
```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/wechat/articles?title_include=AI&limit=30"
```

### Get RSS Feed
```bash
# Add to RSS reader
http://localhost:8000/api/wechat/rss/MP_WXS_123456?token=YOUR_TOKEN
```

## Troubleshooting

### wewe-rss Not Responding
```bash
# Check if running
curl http://localhost:4000/

# View logs
docker logs geb-wewe-rss
```

### API Returns Empty Articles
1. Make sure you've added WeChat accounts in wewe-rss UI (`http://localhost:4000`)
2. Check wewe-rss update status (5-minute delay for first sync)
3. Verify `WEWE_RSS_URL` environment variable is correct

### Rate Limiting (小黑屋)
wewe-rss has built-in rate limiting to avoid being blocked by WeChat. If you see "小黑屋" status:
- Wait 24 hours for the block to lift
- Adjust `CRON_EXPRESSION` to reduce update frequency
- Use `UPDATE_DELAY_TIME` to add delays between account updates

## Limitations

- **No Real-time**: Updates happen on schedule (default: every 10 minutes)
- **WeChat API Limits**: Subject to WeChat's anti-scraping measures
- **Manual Subscriptions**: You must manually add accounts in wewe-rss UI
- **Rate Limiting**: Frequent updates may trigger WeChat's rate limiting

## Next Steps

1. Deploy wewe-rss separately (Zeabur, Railway, Docker)
2. Add Redis caching layer for response caching
3. Implement article clustering with existing GEB logic
4. Create user subscriptions to specific WeChat accounts
5. Add notification system for new articles

## See Also

- [wewe-rss GitHub](https://github.com/cooderl/wewe-rss)
- [wewe-rss Documentation](https://github.com/cooderl/wewe-rss/blob/main/README.md)
