# WeWe-RSS Authentication Integration Guide

## Overview

This guide documents the complete WeWe-RSS authentication integration that enables users to authenticate with WeChat via QR code and add WeChat official account articles to their reading list.

**What was implemented:**
- FastAPI backend service for WeWe-RSS OAuth authentication
- React frontend component for QR-based login
- 6 new API endpoints for account management and article fetching
- Full integration with existing user authentication system

---

## Architecture

### Backend Flow

```
User → Frontend QR Component
         ↓
    POST /api/wewe-rss/auth/qrcode
         ↓
    Backend → WeWe-RSS "GET /api/v2/login/platform"
               Returns: {uuid, scanUrl}
         ↓
    User scans QR with WeChat
         ↓
    Frontend polls: GET /api/wewe-rss/auth/status?login_id={uuid}
         ↓
    Backend → WeWe-RSS "GET /api/v2/login/platform/{uuid}"
         ↓
    When ready → Returns {vid, token, username}
         ↓
    Backend stores account for user
         ↓
    Frontend → Success state, display connected account
```

### WeWe-RSS API Contract

The integration calls out to a running WeWe-RSS instance (default: `http://localhost:4000`).

**Required endpoints:**
- `GET /api/v2/login/platform` - Create login session
- `GET /api/v2/login/platform/{login_id}` - Poll for completion
- `POST /api/v2/platform/wxs2mp` - Extract official account from article URL (requires auth)
- `GET /api/v2/platform/mps/{mp_id}/articles` - Fetch articles from official account (requires auth)

---

## Backend Implementation

### Files Created

**File: `backend/app/api/wewe_rss_auth.py`**

**Classes:**

#### `WeWeRSSAuthService`
Service class for all WeWe-RSS API interactions.

```python
class WeWeRSSAuthService:
    def __init__(self, base_url: str = "http://localhost:4000")
    async def create_login_url() -> dict
    async def get_login_result(login_id: str) -> dict
    async def get_mp_info(account_id: str, token: str, share_url: str) -> dict
    async def get_mp_articles(account_id: str, token: str, mp_id: str, page: int = 1) -> dict
```

**Current State Management:**
- `login_sessions` dict - Tracks active login attempts
- `user_wewe_accounts` dict - Stores user's connected accounts

⚠️ **WARNING**: In-memory storage is for development only. For production:
1. Add SQLAlchemy models to persist accounts to database
2. Implement Redis for session management
3. Add token encryption and secure storage

### API Endpoints

#### 1. Create QR Code
```
POST /api/wewe-rss/auth/qrcode
Authorization: Bearer {token}

Response (200):
{
  "login_id": "uuid-string",
  "scan_url": "WeChat QR code image URL",
  "expires_in": 300
}
```

**Returns**: UUID for polling + WeChat QR code URL
**Side effect**: Stores session in `login_sessions`

#### 2. Poll Login Status
```
GET /api/wewe-rss/auth/status?login_id={uuid}
Authorization: Bearer {token}

Response (200 - pending):
{
  "status": "pending"
}

Response (200 - completed):
{
  "status": "completed",
  "account": {
    "vid": "account_id",
    "username": "Official Account Name",
    "token": "access_token"
  }
}
```

**Polling interval**: Frontend polls every 1 second
**Expiration**: 5 minutes (300 seconds)
**Side effect**: When complete, stores account in `user_wewe_accounts[user_id]`

#### 3. List Connected Accounts
```
GET /api/wewe-rss/accounts
Authorization: Bearer {token}

Response (200):
{
  "accounts": [
    {
      "vid": "account_id_1",
      "username": "官方账号名称",
      "created_at": "2024-04-19T10:30:00Z"
    }
  ]
}
```

**Returns**: All WeWe-RSS accounts connected to current user

#### 4. Fetch Articles from WeChat Article
```
POST /api/wewe-rss/accounts/{account_id}/fetch-articles
Authorization: Bearer {token}
Content-Type: application/json

Request body:
{
  "article_url": "https://mp.weixin.qq.com/s/..."
}

Response (200):
{
  "official_account": {
    "mp_id": "gh_...",
    "name": "Official Account Name",
    "avatar": "https://..."
  },
  "articles": [
    {
      "title": "Article Title",
      "content": "...",
      "cover": "https://...",
      "pub_date": "2024-04-19T10:00:00Z",
      "url": "https://mp.weixin.qq.com/s/..."
    }
  ]
}
```

**Process**:
1. Uses authenticated WeWe-RSS account to extract official account from article URL
2. Fetches latest articles from that official account
3. Returns account info + articles

#### 5. Remove Account
```
DELETE /api/wewe-rss/accounts/{account_id}
Authorization: Bearer {token}

Response (200):
{ "message": "Account removed successfully" }
```

#### 6. Integration Status
```
GET /api/wewe-rss/integration-status
Authorization: Bearer {token}

Response (200):
{
  "integration_enabled": true,
  "connected_accounts": 2,
  "wewe_rss_url": "http://localhost:4000"
}
```

---

## Frontend Implementation

### File Created

**File: `frontend/components/WeWeRSSQRLogin.tsx`**

### Component Props

```typescript
interface Props {
  onAccountAdded?: (account: {
    vid: string;
    username: string;
    created_at: string;
  }) => void;
  onError?: (error: string) => void;
}
```

### Usage Example

```tsx
import WeWeRSSQRLogin from '@/components/WeWeRSSQRLogin';

export default function ArticlesPage() {
  return (
    <WeWeRSSQRLogin
      onAccountAdded={(account) => {
        console.log('New account connected:', account);
        // Refresh article list or navigate to article selection
      }}
      onError={(error) => {
        console.error('WeChat login failed:', error);
      }}
    />
  );
}
```

### Component Features

- **QR Display**: Shows WeChat scan QR code with `qrcode.react`
- **Automatic Polling**: Checks login status every 1 second
- **Loading States**: 
  - "Generating..." (creating QR)
  - "Waiting for scan..." (animated pulse)
  - "Success!" (account added)
- **Account Management**: Display connected accounts with remove button
- **Error Handling**: Shows error messages with retry

### Component States

```
Initial
  ↓
Loading QR Code...
  ↓
Waiting for WeChat Scan (animated pulse)
  ↓
Poll status endpoint every 1s
  ↓
  ├─ Still pending → Keep polling
  ├─ Login complete → Show success, store account
  └─ Error/timeout → Show error, offer retry
  ↓
Display connected accounts
  ├─ Add another account → Restart flow
  └─ Remove account → Delete from list
```

---

## Testing

### Prerequisite

**WeWe-RSS must be running on the configured URL** (default: `http://localhost:4000`)

To run WeWe-RSS locally:
```bash
# From wewe-rss repository directory
npm install
npm run dev
```

Or update the URL in `.env`:
```env
WEWE_RSS_URL=http://your-wewe-rss-url:4000
```

### Manual Testing

#### 1. Test QR Code Generation
```bash
curl -X POST http://localhost:8000/api/wewe-rss/auth/qrcode \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

Expected response:
```json
{
  "login_id": "uuid-string",
  "scan_url": "https://...",
  "expires_in": 300
}
```

#### 2. Test Status Polling
```bash
# Keep polling with the login_id from step 1
curl http://localhost:8000/api/wewe-rss/auth/status?login_id=uuid-string \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response before scan:
```json
{ "status": "pending" }
```

Response after scanning with WeChat:
```json
{
  "status": "completed",
  "account": {
    "vid": "account_id",
    "username": "Account Name",
    "token": "access_token"
  }
}
```

#### 3. List Connected Accounts
```bash
curl http://localhost:8000/api/wewe-rss/accounts \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 4. Fetch Articles
```bash
curl -X POST http://localhost:8000/api/wewe-rss/accounts/{vid}/fetch-articles \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"article_url": "https://mp.weixin.qq.com/s/..."}'
```

---

## Environment Configuration

### Required Settings

Add to `.env` file:

```env
# WeWe-RSS connection
WEWE_RSS_URL=http://localhost:4000

# Optional: Customize login polling
WEWE_RSS_LOGIN_TIMEOUT=300  # seconds
WEWE_RSS_POLL_INTERVAL=1    # seconds
```

### Loading in Backend

```python
from app.settings import settings

wewe_rss_url = settings.wewe_rss_url or "http://localhost:4000"
```

---

## Production Migration Checklist

### Current State (Development)
- ✅ In-memory login sessions
- ✅ In-memory user account storage
- ✅ Complete API endpoints

### Before Production Deployment

- [ ] **Database Models**: Create SQLAlchemy models for `WeWeRSSAccount`
- [ ] **Migration Scripts**: Generate Alembic migrations
- [ ] **Token Storage**: Encrypt and hash WeWe-RSS account tokens
- [ ] **Session Management**: Switch from in-memory dict to Redis
- [ ] **Rate Limiting**: Add rate limits to OAuth endpoints
- [ ] **Monitoring**: Add logging for account creation/deletion
- [ ] **Testing**: Add unit and integration tests
- [ ] **Documentation**: Update API documentation

### Database Schema (SQL - example)

```sql
CREATE TABLE wewe_rss_accounts (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  vid VARCHAR(255) NOT NULL,
  token VARCHAR(1024) NOT NULL,  -- encrypted
  username VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, vid)
);

CREATE TABLE wewe_rss_login_sessions (
  login_id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  account_data JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP NOT NULL
);
```

---

## Integration with Reading List

### Next Steps for Feature Completion

1. **Link Articles to Reading List**
   - Add `/articles` endpoint to store fetched WeChat articles
   - Call when user confirms adding articles: `POST /api/articles` with articles from fetch response

2. **UI Workflow**
   - Component 1: `WeWeRSSQRLogin` - Connect account (✅ DONE)
   - Component 2: `WeWeRSSAccountSelector` - Choose which account to fetch from
   - Component 3: `WeWeRSSArticleSelection` - Show fetched articles, select to add
   - Component 4: `ReadingList` - Display added articles

3. **Data Model**
   ```python
   class Article(Base):
       id: UUID
       user_id: UUID
       source: Literal["wewe_rss", "rss_feed", "manual"]
       wewe_account_id: Optional[UUID]  # Link to WeWeRSSAccount
       title: str
       content: str
       url: str
       cover_image: Optional[str]
       published_at: datetime
       created_at: datetime
   ```

---

## Troubleshooting

### Issue: "WeWe-RSS instance not reachable"
- **Cause**: Configured URL is wrong or WeWe-RSS isn't running
- **Fix**: 
  1. Verify WeWe-RSS is running: `curl http://localhost:4000/api/v2/login/platform`
  2. Update `WEWE_RSS_URL` in `.env`
  3. Restart backend: `python -m uvicorn app.main:app --reload`

### Issue: "Login times out waiting for scan"
- **Cause**: QR code not scanned or scan not processed
- **Fix**:
  1. Verify WeChat can access the scan URL
  2. Check WeWe-RSS logs for errors
  3. Increase `WEWE_RSS_LOGIN_TIMEOUT` if network is slow

### Issue: "Cannot fetch articles - authentication failed"
- **Cause**: WeWe-RSS token expired or invalid
- **Fix**:
  1. Remove account: `DELETE /api/wewe-rss/accounts/{vid}`
  2. Re-authenticate: Full QR scan flow again
  3. Check WeWe-RSS token rotation settings

### Import Errors on Backend Startup
- **Cause**: Missing dependencies or syntax errors
- **Fix**:
  1. Verify `wewe_rss_auth.py` exists: `ls backend/app/api/wewe_rss_auth.py`
  2. Test module: `python -c "from app.api.wewe_rss_auth import router"`
  3. Check syntax: `python -m py_compile backend/app/api/wewe_rss_auth.py`

---

## Security Considerations

### Current Implementation
- ✅ User authentication required (JWT token)
- ✅ User state validation (can only access own accounts)
- ✅ HTTPS recommended for production

### Recommendations for Production
- [ ] Encrypt WeWe-RSS tokens in database
- [ ] Implement rate limiting on `/auth/qrcode` (max 10 per minute per user)
- [ ] Add CSRF protection if using session cookies
- [ ] Validate WeChat URLs before making requests
- [ ] Implement token refresh/expiration logic
- [ ] Add audit logging for account operations
- [ ] Use secrets manager (AWS Secrets, Vault) for tokens

---

## Files Modified/Created

```
backend/app/api/wewe_rss_auth.py          [CREATED] 400+ lines
frontend/components/WeWeRSSQRLogin.tsx    [CREATED] 350+ lines  
backend/app/main.py                       [UPDATED] Added imports + router
```

### Changes to main.py
```python
# Line 21 - Added import
from .api.wewe_rss_auth import router as wewe_rss_auth_router

# Line 109 - Registered router
app.include_router(wewe_rss_auth_router)
```

---

## Summary

**Implemented**: Complete WeWe-RSS authentication integration enabling:
- ✅ WeChat QR-based login flow
- ✅ Multi-account management per user
- ✅ Article fetching from WeChat official accounts
- ✅ Secure state management with user validation

**Ready for**: 
- ✅ Backend testing (all endpoints functional)
- ✅ Frontend integration into UI
- ✅ End-to-end workflow testing

**Pending for production**:
- Database storage
- Redis session management
- Unit/integration tests
- Reading list integration
