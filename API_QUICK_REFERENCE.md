# WeWe-RSS API Quick Reference

## ✅ Endpoints Registered

All 6 endpoints properly configured with `/api/wewe-rss` prefix and `@router` decorators.

### Authentication Endpoints

#### 1️⃣ Generate QR Code
```http
POST /api/wewe-rss/auth/qrcode
Authorization: Bearer {token}
```
**Response**: `{ login_id, scan_url, expires_in: 300 }`

#### 2️⃣ Poll Login Status
```http
GET /api/wewe-rss/auth/status?login_id={uuid}
Authorization: Bearer {token}
```
**Response**: `{ status: "pending" | "completed", account?: {...} }`

### Account Management Endpoints

#### 3️⃣ List Connected Accounts
```http
GET /api/wewe-rss/accounts
Authorization: Bearer {token}
```
**Response**: `{ accounts: [{ vid, username, created_at }] }`

#### 4️⃣ Fetch Articles from WeChat
```http
POST /api/wewe-rss/accounts/{account_id}/fetch-articles
Authorization: Bearer {token}
Content-Type: application/json

{
  "article_url": "https://mp.weixin.qq.com/s/..."
}
```
**Response**: `{ official_account: {...}, articles: [...] }`

#### 5️⃣ Remove Account
```http
DELETE /api/wewe-rss/accounts/{account_id}
Authorization: Bearer {token}
```
**Response**: `{ message: "Account removed successfully" }`

### Status Endpoints

#### 6️⃣ Check Integration Status
```http
GET /api/wewe-rss/integration-status
Authorization: Bearer {token}
```
**Response**: `{ integration_enabled, connected_accounts, wewe_rss_url }`

---

## 🧪 Testing with curl

### 1. Generate QR Code
```bash
curl -X POST http://localhost:8000/api/wewe-rss/auth/qrcode \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

### 2. Check Login Status (repeat every 1 second)
```bash
# Replace {login_id} with UUID from response above
curl http://localhost:8000/api/wewe-rss/auth/status?login_id={login_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. List Accounts
```bash
curl http://localhost:8000/api/wewe-rss/accounts \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Fetch Articles
```bash
curl -X POST http://localhost:8000/api/wewe-rss/accounts/{vid}/fetch-articles \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"article_url": "https://mp.weixin.qq.com/s/..."}'
```

### 5. Get Integration Status
```bash
curl http://localhost:8000/api/wewe-rss/integration-status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 🚀 Quick Start

1. **Start Backend**
   ```bash
   cd backend
   source ../.venv/bin/activate
   python -m uvicorn app.main:app --reload
   ```

2. **Start WeWe-RSS** (in separate terminal)
   ```bash
   cd path/to/wewe-rss
   npm run dev  # Runs on http://localhost:4000
   ```

3. **Test Endpoint**
   ```bash
   curl http://localhost:8000/api/wewe-rss/integration-status \
     -H "Authorization: Bearer test_token"
   ```

---

## 📋 Implementation Checklist

### Phase 1: Backend ✅ COMPLETE
- [x] Create `wewe_rss_auth.py` service
- [x] Define all 6 endpoints
- [x] Implement WeWeRSSAuthService
- [x] Add to routers in `main.py`
- [x] Test imports

### Phase 2: Testing (NEXT)
- [ ] Start backend server
- [ ] Generate QR code (test endpoint 1)
- [ ] Scan with WeChat (manual scan)
- [ ] Poll status (test endpoint 2)
- [ ] Verify account stored (test endpoint 3)
- [ ] Fetch articles (test endpoint 4)

### Phase 3: Frontend Integration
- [ ] Import `WeWeRSSQRLogin` component
- [ ] Add to article source selection page
- [ ] Wire up `onAccountAdded` callback
- [ ] Wire up `onError` handler

### Phase 4: Reading List Integration
- [ ] Add `/articles` POST endpoint
- [ ] Integrate with article storage
- [ ] Link fetched articles to reading list
- [ ] Display in UI

---

## 🔗 Component Integration Example

```tsx
import WeWeRSSQRLogin from '@/components/WeWeRSSQRLogin';

export default function AddArticlesFromWeChatPage() {
  const handleAccountAdded = (account) => {
    // Account connected: { vid, username, created_at }
    console.log('WeChat account connected:', account);
    // TODO: Show article selection UI
  };

  const handleError = (error) => {
    console.error('Failed to connect WeChat account:', error);
    // TODO: Show error toast
  };

  return (
    <div>
      <h1>Add Articles from WeChat</h1>
      <WeWeRSSQRLogin
        onAccountAdded={handleAccountAdded}
        onError={handleError}
      />
    </div>
  );
}
```

---

## 📚 Documentation

- **Full Guide**: See `WEWE_RSS_INTEGRATION_GUIDE.md`
- **Backend Source**: `backend/app/api/wewe_rss_auth.py`
- **Frontend Source**: `frontend/components/WeWeRSSQRLogin.tsx`

---

## ⚠️ Important Prerequisites

1. **WeWe-RSS Instance Running**
   - Default: `http://localhost:4000`
   - Configure in `.env`: `WEWE_RSS_URL=...`

2. **User Authentication**
   - All endpoints require valid JWT token
   - Token passed in `Authorization: Bearer {token}` header

3. **Network Access**
   - Backend can reach WeWe-RSS instance
   - Frontend can reach backend at `http://localhost:8000`

---

## 🐛 Troubleshooting

| Issue | Solutions |
|-------|-----------|
| 400 Bad Request | Check JWT token is valid and sent in Authorization header |
| 404 Endpoints not found | Verify backend started with `--reload`, routers imported |
| WeWe-RSS unreachable | Verify WeWe-RSS running on configured URL, network access |
| Token errors | Check token not expired, JWT secret matches in settings |
| Rate limits | In-memory throttling not implemented yet |

---

## 📊 State Management (Development)

**In-memory collections** (switch to Redis/DB for production):

```python
login_sessions = {
    "uuid": {
        "created_at": datetime,
        "user_id": str,
        "account_data": None | {...}  # Set when login completes
    }
}

user_wewe_accounts = {
    "user_123": [
        {
            "vid": "account_id",
            "token": "encrypted_token",
            "username": "Account Display Name",
            "created_at": datetime
        }
    ]
}
```

⚠️ **Important**: Upgrade for production - add persistence and encryption.

