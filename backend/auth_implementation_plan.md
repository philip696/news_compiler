# WeChat OAuth 2.0 Integration Plan - GEB Backend

**Date**: April 18, 2026  
**Status**: Phase 6+ Planning  
**Reference**: [WeChat OAuth Official Spec](https://developers.weixin.qq.com/doc/offiaccount/OA_Web_Apps/Web_interface_authorization.html)

---

## Table of Contents

1. [OAuth 2.0 Flow Overview](#oauth-20-flow-overview)
2. [Endpoint Specifications](#endpoint-specifications)
3. [Error Handling Strategy](#error-handling-strategy)
4. [Token Storage & Encryption](#token-storage--encryption)
5. [Security Considerations](#security-considerations)
6. [Graceful Fallback Strategy](#graceful-fallback-strategy)
7. [Implementation Checklist](#implementation-checklist)

---

## OAuth 2.0 Flow Overview

### Complete Authorization Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        WECHAT OAUTH 2.0 AUTHORIZATION FLOW                      │
└─────────────────────────────────────────────────────────────────────────────────┘

FRONTEND/CLIENT                    GEB BACKEND                      WECHAT SERVER
    │                                 │                                  │
    │  1. Click "Login with WeChat"   │                                  │
    │────────────────────────────────>│ POST /api/wechat/auth/start      │
    │                                 │ ├─ Generate state token          │
    │                                 │ ├─ Store in Redis (5 min TTL)    │
    │                                 │ └─ Return auth URL               │
    │                                 │                                  │
    │ 2. Redirect to WeChat Login     │                                  │
    │────────────────────────────────────────────────────────────────────>
    │                                 │  https://open.weixin.qq.com/    │
    │                                 │  connect/oauth2/authorize        │
    │                                 │  ?appid=xxx                      │
    │                                 │  &redirect_uri=xxx               │
    │                                 │  &response_type=code             │
    │                                 │  &scope=snsapi_userinfo          │
    │                                 │  &state=xxx                      │
    │                                 │                                  │
    │ 3. User Scans QR / Logs In      │                                  │
    │ 4. Redirects back with code     │                                  │
    │<────────────────────────────────────────────────────────────────────
    │ GET /api/wechat/auth/callback   │                                  │
    │ ?code=xxx&state=xxx             │                                  │
    │                                 │ 5. Validate state                │
    │                                 ├─ Query Redis for state           │
    │                                 │ ├─ Ensure IP match (CSRF check)  │
    │                                 │ └─ Delete state from Redis       │
    │                                 │                                  │
    │                                 │ 6. Exchange code → tokens        │
    │                                 ├─ POST auth2/access_token        │
    │                                 │  {appid, secret, code}           │
    │                                 │                                  │
    │                                 │ 7. Get user info                 │
    │                                 ├─ GET sns/userinfo               │
    │                                 │  (access_token, openid)          │
    │                                 │                                  │
    │                                 │ 8. Store/Update DB               │
    │                                 ├─ Find WeChatAuth(openid)        │
    │                                 ├─ Create or Update w/ tokens     │
    │                                 │ └─ Encrypt tokens with Fernet    │
    │                                 │                                  │
    │                                 │ 9. Generate session              │
    │                                 ├─ Create JWT session token       │
    │                                 │ └─ Set in HTTP-only cookie      │
    │                                 │                                  │
    │ Response: Redirect to dashboard │                                  │
    │<────────────────────────────────                                   │
    │ Set-Cookie: session=JWT_TOKEN   │                                  │
    │                                 │                                  │
    │ Authenticated & Ready           │                                  │
    └─────────────────────────────────────────────────────────────────────────────


KEY PARAMETERS PASSED:
├─ appid          : WeChat Official Account App ID
├─ code           : Single-use authorization code (10 min expiry)
├─ access_token   : Oauth 2.0 token (2 hours expiry)
├─ refresh_token  : Long-lived token (30 days expiry)
├─ openid         : Unique WeChat ID per app
├─ unionid        : Unique across all official accounts
└─ state          : CSRF protection token


SECURITY CHECKPOINTS:
✓ State validation (prevent code injection attacks)
✓ IP verification (prevent replay attacks)
✓ Token encryption (protect stored credentials)
✓ HTTPS only (prevent man-in-the-middle)
└─ Scope limited to snsapi_userinfo (minimal permissions)
```

---

## Endpoint Specifications

### 1. POST /api/wechat/auth/start

**Purpose**: Generate login URL and initialize OAuth flow

**Request**:
```http
POST /api/wechat/auth/start
Content-Type: application/json

{
  "redirectAfterAuth": "/dashboard"  # Optional: where to send user after login
}
```

**Response (200 OK)**:
```json
{
  "authUrl": "https://open.weixin.qq.com/connect/oauth2/authorize?appid=xxx&redirect_uri=xxx&response_type=code&scope=snsapi_userinfo&state=yyy&connect_redirect=1#wechat_redirect",
  "state": "yyy",
  "expiresAt": "2026-04-18T10:35:00Z"
}
```

**Error Responses**:
```json
// 400 Bad Request - Missing APP_ID
{
  "error": "OAUTH_NOT_CONFIGURED",
  "detail": "WeChat OAuth credentials not configured"
}

// 503 Service Unavailable - Graceful mode
{
  "error": "WECHAT_OAUTH_DISABLED",
  "detail": "WeChat OAuth temporarily unavailable. Please use alternative login method."
}
```

**Implementation Details**:
```
1. Generate state token
   ├─ Length: 32+ bytes (base64 min)
   ├─ Method: secrets.token_bytes(32) → base64 encode
   └─ Entropy: cryptographically secure

2. Store state in Redis
   ├─ Key: wechat_state:{state}
   ├─ Value: {
   │   "issued_at": ISO8601,
   │   "client_ip": client_ip,
   │   "user_agent": user_agent_hash,
   │   "user_id": null (not yet bound)
   │ }
   ├─ TTL: 5 minutes (state code expiry)
   └─ Atomic: SETEX wechat_state:{state} 300 json_value

3. Generate auth URL
   ├─ Base URL: https://open.weixin.qq.com/connect/oauth2/authorize
   ├─ Parameters:
   │  ├─ appid: settings.WECHAT_APP_ID
   │  ├─ redirect_uri: settings.OAUTH_CALLBACK_URL
   │  ├─ response_type: "code"
   │  ├─ scope: "snsapi_userinfo"
   │  ├─ state: generated_state
   │  └─ connect_redirect: "1" (always 1 for official accounts)
   └─ Fragment: #wechat_redirect (mobile detection)

4. Return to client
   └─ Client redirects browser to authUrl
```

**Security Controls**:
- ✅ State prevents CSRF (browser cannot guess)
- ✅ IP tracking prevents token replay (different IP = reject)
- ✅ TTL prevents old state reuse
- ✅ Secure random generation (no predictability)

---

### 2. GET /api/wechat/auth/callback

**Purpose**: Complete OAuth flow by exchanging code for tokens

**Request**:
```http
GET /api/wechat/auth/callback?code=CODE_FROM_WECHAT&state=STATE_FROM_REDIRECT
```

**Response (302 Redirect)**:
```http
Location: /dashboard
Set-Cookie: session=JWT_TOKEN; HttpOnly; Secure; SameSite=Strict; Max-Age=604800
```

**Response Body** (if following redirect):
```json
{
  "success": true,
  "userId": 123,
  "weChatAuth": {
    "openid": "oZ5Fq_PtxxVRzDl94k3CbzXUz8Zo",
    "unionid": "oTj4AjurlSYWEBhd8Hzg_NM8P1ck0",
    "nickName": "User Name",
    "avatar": "https://thirdwx.qpic.cn/...",
    "linkedAt": "2026-04-18T10:30:00Z"
  },
  "sessionToken": "eyJhbGc..."
}
```

**Error Responses**:
```json
// 400 Bad Request - State validation failed
{
  "error": "INVALID_STATE",
  "detail": "State token not found or expired. Please start login again.",
  "code": "STATE_EXPIRED"
}

// 400 Bad Request - Code exchange failed
{
  "error": "CODE_EXCHANGE_FAILED",
  "detail": "WeChat refused code exchange. Code may be expired or already used.",
  "weChatError": "40029"
}

// 400 Bad Request - CSRF detected
{
  "error": "CSRF_DETECTED",
  "detail": "Request IP differs from state issuance IP. Possible replay attack.",
  "code": "IP_MISMATCH"
}

// 403 Forbidden - User not allowed
{
  "error": "USER_NOT_AUTHORIZED",
  "detail": "Your WeChat account is not authorized to use this service.",
  "openid": "oZ5Fq_PtxxVRzDl94k3CbzXUz8Zo"
}

// 500 Internal Server Error
{
  "error": "OAUTH_CALLBACK_FAILED",
  "detail": "Internal error processing callback",
  "traceId": "abc123xyz"
}
```

**Implementation Details**:

```
STEP 1: Validate Input Parameters
├─ Validate query params present: code, state
├─ Validate format:
│  ├─ code: string, 100-500 chars
│  ├─ state: base64 format, 40+ chars
│  └─ Return 400 if invalid
└─ NEVER log code (sensitive)

STEP 2: Validate State Token
├─ Lookup: Redis GET wechat_state:{state}
├─ If missing/expired:
│  ├─ Return 400 with STATE_EXPIRED
│  ├─ Log: state_validation_failed event
│  └─ Redirect to /auth/start
├─ Extract from Redis:
│  ├─ issued_at, client_ip, user_agent_hash
│  ├─ Verify issued_at within 5 minutes
│  └─ Verify client_ip matches request IP
├─ On IP mismatch:
│  ├─ Log: csrf_detected event + IPs
│  ├─ Block request
│  ├─ Alert security monitoring
│  └─ Return 403 CSRF_DETECTED
└─ Delete from Redis:
   └─ Redis DEL wechat_state:{state} (prevent reuse)

STEP 3: Exchange Code for Tokens
├─ Call WeChat API: POST auth2/access_token
│  └─ Params: {
│     "appid": settings.WECHAT_APP_ID,
│     "secret": settings.WECHAT_APP_SECRET,  # NEVER log
│     "code": code,
│     "grant_type": "authorization_code"
│  }
├─ Parse response:
│  └─ {
│     "access_token": "...",
│     "expires_in": 7200,
│     "refresh_token": "...",
│     "openid": "oZ5Fq_...",
│     "scope": "snsapi_userinfo",
│     "unionid": "oTj4Aju..."  # Optional
│  }
├─ Error handling:
│  ├─ 40001: Invalid appid/secret (config error)
│  ├─ 40029: Invalid code (expired/reused)
│  ├─ 43004: Code missing (bad request)
│  └─ Network timeout → retry 3x, then fail
└─ Validate response:
   ├─ access_token not empty
   ├─ expires_in > 0
   └─ openid not empty

STEP 4: Fetch User Information
├─ Call WeChat API: GET sns/userinfo
│  └─ Params: {
│     "access_token": access_token,
│     "openid": openid,
│     "lang": "zh_CN"
│  }
├─ Parse response:
│  └─ {
│     "openid": "oZ5Fq_...",
│     "unionid": "oTj4Aju...",
│     "nickname": "用户昵称",
│     "sex": 1,
│     "province": "guangdong",
│     "city": "shenzhen",
│     "country": "中国",
│     "headimgurl": "https://thirdwx.qpic.cn/...",
│     "privilege": [...]
│  }
├─ Error handling:
│  ├─ 40001: Invalid access_token (refresh needed)
│  ├─ 42001: Token expired
│  └─ Network timeout → retry 1x, then fail
└─ Validate response:
   ├─ openid not empty
   └─ nickname not empty

STEP 5: Persist to Database
├─ Transaction start
├─ Query: SELECT * FROM wechat_auth WHERE openid = ?
├─ If exists (returning user):
│  ├─ Update WeChatAuth:
│  │  ├─ access_token_encrypted = Fernet.encrypt(access_token)
│  │  ├─ refresh_token_encrypted = Fernet.encrypt(refresh_token)
│  │  ├─ token_expiry = now + 7200 seconds
│  │  ├─ raw_user_info = JSON(user_info)
│  │  ├─ updated_at = now (automatic via mixin)
│  │  └─ scopes = "snsapi_userinfo"
│  ├─ Log: user_oauth_updated event
│  └─ Proceed to Step 6
├─ If not exists (new user):
│  ├─ Query: SELECT * FROM users WHERE id = ? (if user_id in session)
│  ├─ Create User if not exists:
│  │  ├─ username = generate_from_openid(openid)
│  │  ├─ email = "{}@wechat.local".format(openid)
│  │  ├─ is_active = true
│  │  └─ is_verified = false (email not verified)
│  ├─ Create WeChatAuth:
│  │  ├─ user_id = created_user.id
│  │  ├─ wechat_openid = openid (UNIQUE)
│  │  ├─ wechat_unionid = unionid
│  │  ├─ access_token_encrypted = Fernet.encrypt(access_token)
│  │  ├─ refresh_token_encrypted = Fernet.encrypt(refresh_token)
│  │  ├─ token_expiry = now + 7200 seconds
│  │  ├─ raw_user_info = JSON(user_info)
│  │  ├─ scopes = "snsapi_userinfo"
│  │  └─ created_at = now
│  ├─ Log: user_oauth_created event
│  └─ Proceed to Step 6
└─ Transaction commit

STEP 6: Generate Session Token
├─ Create JWT with:
│  ├─ sub: user_id
│  ├─ openid: wechat_auth.openid
│  ├─ iat: now
│  ├─ exp: now + 7 days
│  ├─ aud: "geb-backend"
│  ├─ scope: "snsapi_userinfo"
│  └─ Signature: HS256(secret=settings.JWT_SECRET)
├─ Store in Redis:
│  ├─ Key: session:user:{user_id}
│  ├─ Value: {
│  │   "jwt": jwt_token,
│  │   "issued_at": ISO8601,
│  │   "expires_at": ISO8601,
│  │   "user_agent": hash(user_agent),
│  │   "client_ip": client_ip
│  │ }
│  └─ TTL: 7 days
└─ Set HTTP-only cookie:
   └─ Set-Cookie: session={jwt}; HttpOnly; Secure; SameSite=Strict; Max-Age=604800

STEP 7: Return Response
├─ Redirect to /dashboard
├─ Set cookie in response headers
└─ Include session token in body for SPA consumption
```

**Security Controls**:
- ✅ Code exchange validates appid/secret
- ✅ IP mismatch detection prevents replays
- ✅ State deletion prevents reuse
- ✅ Tokens encrypted before storage
- ✅ JWT includes IP/User-Agent for validation
- ✅ HTTP-only cookies prevent XSS token theft

---

### 3. POST /api/wechat/auth/refresh

**Purpose**: Renew access token before expiry

**Request**:
```http
POST /api/wechat/auth/refresh
Authorization: Bearer JWT_SESSION_TOKEN
Content-Type: application/json

{
  "refreshToken": "REFRESH_TOKEN_ENCRYPTED"  # Optional: explicit refresh
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "accessToken": "NEW_ACCESS_TOKEN",
  "expiresIn": 7200,
  "expiresAt": "2026-04-18T12:30:00Z",
  "refreshToken": "NEW_REFRESH_TOKEN",
  "sessionToken": "NEW_JWT_TOKEN"
}
```

**Error Responses**:
```json
// 401 Unauthorized - Invalid session
{
  "error": "INVALID_SESSION",
  "detail": "Session token invalid or expired"
}

// 400 Bad Request - Refresh failed
{
  "error": "TOKEN_REFRESH_FAILED",
  "detail": "WeChat refused token refresh",
  "weChatError": "42001"
}

// 429 Too Many Requests - Refresh rate limit
{
  "error": "REFRESH_RATE_LIMIT",
  "detail": "Token refreshed too frequently. Wait 1 hour.",
  "retryAfter": 3600
}

// 503 Service Unavailable - Graceful degradation
{
  "error": "REFRESH_TEMPORARILY_UNAVAILABLE",
  "detail": "Token refresh unavailable. Existing token is still valid.",
  "expiresAt": "2026-04-18T11:30:00Z"
}
```

**Implementation Details**:

```
STEP 1: Validate Session
├─ Extract JWT from Authorization header
├─ Verify JWT signature
├─ Check JWT not expired
├─ Lookup in Redis: session:user:{user_id}
├─ Verify stored JWT matches request JWT
├─ Verify IP/User-Agent match (replay detection)
└─ Return 401 if any check fails

STEP 2: Fetch Current WeChatAuth
├─ Query: SELECT * FROM wechat_auth WHERE user_id = ?
├─ If exists:
│  ├─ Decrypt current tokens
│  ├─ Check if token still valid (not past expiry)
│  └─ Determine refresh strategy
├─ If not exists:
│  ├─ Return 404: User not linked to WeChat
│  └─ Suggest POST /api/wechat/auth/start

STEP 3: Validate Refresh Eligibility
├─ Check refresh token expiry (refresh tokens valid 30 days)
├─ Check refresh rate:
│  ├─ Get last_refresh_time from Redis
│  ├─ If refreshed < 1 hour ago:
│  │  ├─ Return 429 Too Many Requests
│  │  ├─ Header: Retry-After: 3600
│  │  └─ Log: refresh_rate_limit_exceeded
│  └─ If refreshed >= 1 hour ago:
│     └─ Proceed to refresh
├─ Check if access token near expiry:
│  ├─ If expires_in > 3600 seconds:
│  │  ├─ Return 200 OK (no refresh needed)
│  │  └─ Send current token + extended time
│  └─ If expires_in <= 3600 seconds:
│     └─ Proceed with refresh

STEP 4: Refresh Access Token via WeChat
├─ Call WeChat API: POST sns/oauth2/refresh_token
│  └─ Params: {
│     "appid": settings.WECHAT_APP_ID,
│     "grant_type": "refresh_token",
│     "refresh_token": decrypt(refresh_token_encrypted)
│  }
├─ Parse response:
│  └─ {
│     "access_token": "NEW_ACCESS_TOKEN",
│     "expires_in": 7200,
│     "refresh_token": "NEW_REFRESH_TOKEN",
│     "openid": "oZ5Fq_...",
│     "scope": "snsapi_userinfo"
│  }
├─ Error handling:
│  ├─ 40001: Invalid appid
│  ├─ 40025: Invalid refresh_token (expired)
│  ├─ 42001: Token expired (need re-auth)
│  └─ Network timeout → fail gracefully
└─ Validate new tokens not empty

STEP 5: Update Database
├─ Transaction start
├─ Update WeChatAuth:
│  ├─ access_token_encrypted = Fernet.encrypt(new_access_token)
│  ├─ refresh_token_encrypted = Fernet.encrypt(new_refresh_token)
│  ├─ token_expiry = now + new_expires_in
│  └─ updated_at = now (automatic)
├─ Store refresh timestamp:
│  ├─ Redis SET last_refresh:{user_id} now
│  ├─ TTL: 30 days
│  └─ Prevents refresh rate abuse
└─ Transaction commit

STEP 6: Generate New Session
├─ Create new JWT:
│  └─ exp: now + 7 days
├─ Update Redis:
│  └─ SET session:user:{user_id} new_jwt
└─ Return new tokens

STEP 7: Return Response
├─ Return new access_token
├─ Return new refresh_token
├─ Return expiry time
└─ Return new session JWT
```

**Timing Strategy**:
```
Access Token Lifecycle:
├─ Issued at: T0
├─ Expiry: T0 + 7200 seconds (2 hours)
├─ Last Refresh Window: T0 + 5400 seconds (1.5 hours) ← User can refresh
├─ Warn User: T0 + 5400 seconds (show "Session expiring" UI)
└─ Hard Expiry: T0 + 7200 seconds (force re-login)

Refresh Token Lifecycle:
├─ Issued at: T0
├─ Expiry: T0 + 2592000 seconds (30 days)
├─ Auto Refresh: When access token issued
└─ Hard Expiry: T0 + 2592000 seconds (force OAuth login)

Rate Limits:
├─ Minimum between refreshes: 1 hour
├─ Maximum refreshes per day: 23 (distributed)
├─ Reset: Midnight UTC
└─ Enforcement: Redis counter with TTL
```

**Security Controls**:
- ✅ Session JWT must be valid (no token bypass)
- ✅ IP/User-Agent checked (prevent session hijacking)
- ✅ Refresh rate limited (prevent DOS)
- ✅ Refresh token expiry checked (prevent reuse of old tokens)
- ✅ New tokens encrypted before storage
- ✅ Old tokens securely invalidated

---

### 4. POST /api/wechat/auth/revoke

**Purpose**: Logout and revoke WeChat authorization

**Request**:
```http
POST /api/wechat/auth/revoke
Authorization: Bearer JWT_SESSION_TOKEN
Content-Type: application/json

{
  "revokeWeChat": true  # Optional: also revoke on WeChat side
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Authorization revoked successfully",
  "revokedAt": "2026-04-18T10:30:00Z",
  "weChatRevoked": true
}
```

**Error Responses**:
```json
// 401 Unauthorized
{
  "error": "INVALID_SESSION",
  "detail": "Session token invalid or expired"
}

// 500 Internal Server Error
{
  "error": "REVOKE_FAILED",
  "detail": "Revo failed"
}
```

**Implementation Details**:

```
STEP 1: Validate Session
├─ Extract and verify JWT
├─ Lookup user in Redis
└─ Return 401 if invalid

STEP 2: Fetch WeChatAuth
├─ Query: SELECT * FROM wechat_auth WHERE user_id = ?
├─ If not exists:
│  └─ Return success (idempotent)
└─ Continue

STEP 3: Revoke on WeChat Side (Optional)
├─ Call WeChat API: GET sns/oauth2/revoke
│  └─ Params: {
│     "appid": settings.WECHAT_APP_ID,
│     "grant_type": "client_credential",
│     "access_token": decrypt(access_token_encrypted)
│  }
├─ Handle errors gracefully:
│  ├─ 40001: Invalid token (already expired)
│  ├─ 50001: WeChat internal error (retry)
│  └─ Network error: Continue anyway (fail open)
└─ Log result

STEP 4: Delete from Local Database
├─ Transaction start
├─ DELETE FROM wechat_auth WHERE user_id = ?
├─ Log: user_oauth_revoked event
└─ Transaction commit

STEP 5: Invalidate Session
├─ Delete from Redis:
│  ├─ Redis DEL session:user:{user_id}
│  ├─ Redis DEL last_refresh:{user_id}
│  └─ Redis DEL wechat_state:*
└─ Clear cookies via Set-Cookie response

STEP 6: Return Response
└─ Inform client revocation complete
```

---

## Error Handling Strategy

### Error Classification & Responses

| Category | Error Code | Status | Action | User Message |
|----------|-----------|--------|--------|--------------|
| **Configuration** | OAUTH_NOT_CONFIGURED | 503 | Alert DevOps | "WeChat login temporarily unavailable" |
| | INVALID_CREDENTIALS | 500 | Check config | "Service configuration error" |
| **Authentication** | INVALID_STATE | 400 | Restart flow | "Login session expired. Please try again." |
| | STATE_EXPIRED | 400 | Restart flow | "Login took too long. Please start over." |
| | CSRF_DETECTED | 403 | Block & alert | "Possible security issue detected" |
| | CODE_EXCHANGE_FAILED | 400 | Restart flow | "WeChat login failed. Please try again." |
| **Authorization** | IP_MISMATCH | 403 | Block & alert | "Possible replay attack detected" |
| | USER_NOT_AUTHORIZED | 403 | Reject | "Your WeChat account is not authorized" |
| | TOKEN_INVALID | 401 | Prompt re-auth | "Session expired. Please login again." |
| **WeChat API** | WECHAT_API_ERROR | 502 | Retry & fallback | "WeChat service unavailable" |
| | RATE_LIMIT_EXCEEDED | 429 | Retry later | "Too many requests. Try in 1 hour." |
| | NETWORK_TIMEOUT | 504 | Retry | "Connection timeout. Retry in 30s." |
| **Server** | INTERNAL_ERROR | 500 | Log & alert | "Internal server error. Contact support." |

### Retry Strategy

```
Transient Errors (Retry):
├─ WECHAT_API_ERROR (502)
│  └─ Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
├─ NETWORK_TIMEOUT (504)
│  └─ Retry: 3 attempts with exponential backoff
├─ RATE_LIMIT_EXCEEDED (429)
│  └─ Retry: After Retry-After header or 60 seconds
└─ Graceful degradation:
   └─ If all retries fail: Use cached tokens or redirect to fallback

Permanent Errors (Don't Retry):
├─ INVALID_CODE (40029)
│  └─ User must restart login
├─ INVALID_STATE (400)
│  └─ User must restart login
├─ CSRF_DETECTED (403)
│  └─ Block & alert security
└─ USER_NOT_AUTHORIZED (403)
   └─ User cannot access this service

Configuration Errors (Don't Retry):
├─ OAUTH_NOT_CONFIGURED (503)
│  └─ Alert DevOps immediately
└─ INVALID_CREDENTIALS (500)
   └─ Need manual debugging
```

### Error Logging & Monitoring

```
Log Level Strategy:
├─ DEBUG
│  └─ State generated, tokens refreshed
├─ INFO
│  ├─ User OAuth completed
│  ├─ Session created
│  └─ Token refresh successful
├─ WARNING
│  ├─ Token refresh rate limited
│  ├─ Unusually high refresh rate
│  └─ IP mismatch (CSRF-like pattern)
├─ ERROR
│  ├─ Code exchange failed
│  ├─ User info fetch failed
│  ├─ Database update failed
│  └─ Invalid state token
└─ CRITICAL
   ├─ CSRF attack possible (block IP)
   ├─ OAuth not configured
   └─ Credential compromise suspected

Metrics to Track:
├─ oauth_flow_started (counter)
├─ oauth_flow_completed (counter)
├─ oauth_flow_failed (counter, by error type)
├─ token_refresh_count (counter)
├─ token_refresh_failed (counter)
├─ csrf_attempts_blocked (counter)
├─ state_validation_failures (counter)
└─ average_oauth_latency (histogram)
```

---

## Token Storage & Encryption

### Encryption Architecture

```
STORAGE LAYOUT:

WeChatAuth Table:
├─ id (int, PK)
├─ user_id (int, FK, UNIQUE)
├─ wechat_openid (string, UNIQUE, indexed)
├─ wechat_unionid (string, nullable)
├─ access_token_encrypted (bytes) ← Fernet cipher
├─ refresh_token_encrypted (bytes) ← Fernet cipher
├─ token_expiry (datetime, indexed)
├─ scopes (string, e.g., "snsapi_userinfo")
├─ raw_user_info (jsonb)
├─ created_at (datetime, auto)
└─ updated_at (datetime, auto)


ENCRYPTION FLOW:

Plain Token (in memory):
"50a2f8c0adb1aecc4eea44992466e1cd"
         ↓
    Fernet.encrypt()
    [AES-128-CBC + HMAC-SHA256]
         ↓
Encrypted Bytes (stored in DB):
b'gAAAAABl7-M0-KhL6a8...encrypted_payload...'
         ↓
    Database
         ↓
Retrieve from DB:
b'gAAAAABl7-M0-KhL6a8...encrypted_payload...'
         ↓
    Fernet.decrypt()
    [Verify MAC + AES-128-CBC decrypt]
         ↓
Plain Token (in memory):
"50a2f8c0adb1aecc4eea44992466e1cd"
         ↓
    Use in HTTP request to WeChat API
         ↓
    Request complete
         ↓
    Token cleared from memory
         ↓
    (Any compromise only has encrypted bytes)
```

### Key Management

```
Encryption Key:
├─ Source: settings.ENCRYPTION_KEY (environment variable)
├─ Length: 32 bytes minimum for Fernet
├─ Format: Base64 encoded
├─ Generation: Fernet.generate_key()
├─ Rotation: Cryptographically complex (requires migration)
└─ Storage: Only in environment variables

Key Security:
├─ NEVER log the key
├─ NEVER commit key to git
├─ Store in platform secrets:
│  ├─ Production: Vercel Environment Variables
│  ├─ Staging: Railway Environment Variables
│  └─ Local: .env.local (in .gitignore)
├─ Access control:
│  └─ Only backend process can read
└─ Rotation procedure:
   ├─ Generate new key
   ├─ Deploy with both keys (old + new)
   ├─ Re-encrypt all tokens with new key
   ├─ Verify all tokens decryptable
   └─ Remove old key from config
```

### Hybrid Property Implementation

```python
# From models/wechat.py

class WeChatAuth(Base):
    __tablename__ = "wechat_auth"
    
    # Encrypted storage
    access_token_encrypted = Column(LargeBinary, nullable=True)
    refresh_token_encrypted = Column(LargeBinary, nullable=True)
    
    # Transparent encryption/decryption via @hybrid_property
    @hybrid_property
    def access_token(self) -> Optional[str]:
        """Get access token (decrypted on-the-fly)"""
        if self.access_token_encrypted:
            return self._decrypt_token(self.access_token_encrypted)
        return None
    
    @access_token.setter
    def access_token(self, value: str):
        """Set access token (auto-encrypts)"""
        if value:
            self.access_token_encrypted = self._encrypt_token(value)
    
    def _encrypt_token(self, token: str) -> bytes:
        """Encrypt token using Fernet cipher"""
        from ..utils.encryption import encrypt_token
        return encrypt_token(token)
    
    def _decrypt_token(self, encrypted_token: bytes) -> str:
        """Decrypt token using Fernet cipher"""
        from ..utils.encryption import decrypt_token
        return decrypt_token(encrypted_token)


# Usage:
auth = WeChatAuth()
auth.access_token = "raw_token_from_api"    # Auto-encrypted
print(auth.access_token)                     # Auto-decrypted
# Database only stores: b'gAAAAABl7-M0...'
```

---

## Security Considerations

### 1. CSRF Protection (State Token)

```
Vulnerability: Code Injection Attack

Scenario 1: Attacker Injects Code
┌─ Attacker crafts malicious code: "ATTACKER_CODE"
├─ Attacker sends link: /callback?code=ATTACKER_CODE&state=ATTACKER_STATE
└─ Result: User gets Attacker's credentials

Prevention:
├─ Generate cryptographically secure state token
├─ Store state in backend protected storage (Redis)
├─ Verify state matches on callback
└─ Delete state after use (single-use)

Scenario 2: Replay Attack
┌─ Attacker intercepts valid code: "CODE_123"
├─ Attacker can reuse: /callback?code=CODE_123&state=STATE_123
├─ WeChat validates code once, then rejects
└─ Result: Attacker cannot hijack session

Prevention:
├─ WeChat codes expire in 10 minutes
├─ Delete state from Redis after validation
├─ Track attempted replays (metric)
└─ Rate limit callback endpoint
```

### 2. HTTPS Enforcement

```
Requirement: ALL endpoints MUST be HTTPS

Why:
├─ Tokens transmitted in URL (callback?code=...)
├─ Tokens in Authorization header
└─ Credentials in response

Implementation:
├─ Production: HTTPS enforced by load balancer
├─ Development: Use ngrok/mkcert for local HTTPS
├─ Middleware: Redirect HTTP → HTTPS
├─ Headers: Strict-Transport-Security (HSTS)
└─ Cookies: Secure flag set
```

### 3. Token Refresh Timing

```
Vulnerability: Expired Token Usage

Scenario:
├─ access_token expires at 10:00 AM
├─ User makes request at 9:59 AM (1 sec before expiry)
├─ API processes request, token expires at 9:59:30 AM
├─ WeChat API rejects token
└─ User session broken

Prevention - Early Refresh Window:
├─ Token validity: 7200 seconds (2 hours)
├─ Refresh window opens: 3600 seconds before expiry (1 hour before)
├─ When user makes request with token < 3600s remaining:
│  └─ Automatically refresh in background
├─ Warn UI when token < 1800s remaining:
│  └─ "Your session expires in 30 minutes"
└─ Force re-login when token entirely expired

Implementation:
└─ Middleware checks token expiry on every request:
   ```
   token_remaining = token_expiry - now
   if token_remaining < 3600 seconds:
       refresh_token_silently()
   elif token_remaining < 1800 seconds:
       return 401 with hint: "refresh recommended"
   else:
       proceed normally
   ```
```

### 4. IP-Based Replay Attack Prevention

```
Vulnerability: Session Hijacking

Scenario:
├─ Attacker intercepts JWT from user's browser
├─ Attacker makes request from different IP
├─ Server accepts request (why wouldn't it?)
└─ Attacker gains unauthorized access

Prevention - IP Pinning:
├─ Store IP when state generated
│  └─ Redis: wechat_state:{state} → {ip: "1.2.3.4"}
├─ Verify IP matches on callback
│  ├─ If IP differs: CSRF detected, reject
│  └─ Log as potential attack
├─ Store IP when session created
│  └─ Redis: session:user:{id} → {ip: "1.2.3.4"}
└─ Verify IP on every authenticated request
   ├─ If matches: Proceed
   └─ If differs: Reject + log

Limitations:
├─ Corporate networks (proxy)
│  └─ IP may change frequently
├─ Mobile networks (ISP rotation)
│  └─ Same phone, different IP
└─ VPN/proxies
   └─ Different IP, same user

Mitigation:
├─ Use User-Agent hash as secondary signal
├─ Track IP changes per session (alerts)
├─ Allow grace period (few minutes)
└─ Require re-auth if IP changes frequently
```

### 5. Graceful Degradation

```
Scenario: WeChat API is down

Option A: Reject (Poor UX)
└─ Return 503 Service Unavailable
   └─ Users cannot login

Option B: Graceful Degradation (Better)
├─ Check if user already has valid token:
│  ├─ Token not expired? → Allow access
│  └─ Token expired? → Prompt re-auth later
├─ Allow OAuth flows to be skipped:
│  └─ If database token still valid, use it
├─ Queue background refresh:
│  └─ When WeChat recovers, refresh tokens
└─ Monitor and alert ops

Implementation:
├─ Cache user info with TTL:
│  ├─ On next successful OAuth: Store cache
│  ├─ On WeChat down: Serve from cache
│  └─ Cache TTL: 24 hours
└─ Feature flag: WECHAT_GRACEFUL_MODE
   ├─ true: Allow access if cache/token valid
   └─ false: Strict validation (default)
```

---

## Graceful Fallback Strategy

### Scenario 1: WeChat OAuth Disabled/Missing Config

```
Client Flow:
├─ User clicks "Login with WeChat"
├─ Frontend requests: POST /api/wechat/auth/start
└─ Backend response (503):
   ```json
   {
     "enabled": false,
     "fallbackMethods": ["email", "google", "github"],
     "message": "WeChat login temporarily unavailable"
   }
   ```
├─ Frontend hides "WeChat" button
├─ Frontend shows alternative login methods
└─ User logs in via email/Google/GitHub instead

Implementation:
├─ Config check at startup:
│  ├─ If WECHAT_APP_ID missing: graceful_mode = true
│  ├─ If WECHAT_APP_SECRET missing: graceful_mode = true
│  └─ Log warning: "WeChat OAuth not configured"
├─ All OAuth endpoints return 503 with fallback methods
└─ User can still access service via other methods
```

### Scenario 2: WeChat API Temporarily Down

```
Client Flow:
├─ User logs in (OAuth flow)
├─ Exchange code for token: WeChat API returns error (502)
├─ Backend handles:
   ├─ Retry 3 times with backoff
   ├─ If all fail: Check for cached data
   └─ If cache exists:
      └─ Allow temporary access with warning
├─ Frontend shows notification:
   "WeChat service unavailable. Using cached data."
└─ Session created with shorter TTL (1 hour vs 7 days)

Implementation:
├─ Cache user info from previous OAuth:
│  └─ Redis: wechat_cache:{openid} → JSON user_info
├─ On API failure:
│  ├─ If cache exists: Use it
│  ├─ Log: wechat_api_fallback_used
│  ├─ Queue background job to retry
│  └─ Require re-login in 1 hour
└─ When service recovers:
   └─ Background job updates tokens
```

### Scenario 3: Token Expired, Refresh Failed

```
Token Lifecycle:
├─ access_token expires at X seconds
├─ User makes request at X -30 seconds
├─ Backend tries to refresh token
├─ WeChat API returns error (502)

Handling:
├─ Check if token still valid:
│  ├─ If valid (not past expiry): Use existing token
│  ├─ If invalid (past expiry): Require re-auth
│  └─ If unsure: Prompt graceful re-login
├─ User sees notification:
   "Session refresh failed. Please login again."
├─ Frontend redirects to login
└─ User can restart OAuth flow or use email login

Implementation:
├─ Middleware flow:
   ```
   if token_past_expiry:
       try refresh() 3x with backoff
       if all fail:
           if fallback_tokens_valid:
               use_fallback_token()
           else:
               require_reauth()
   ```
└─ Queue background repair:
   └─ When WeChat recovers, refresh all expired tokens
```

### Scenario 4: User Account Compromised

```
Situation:
├─ Attacker obtains user's encrypted tokens (database breach)
├─ Attacker cannot decrypt (Fernet cipher)
│  └─ Key is environment variable, not in DB
└─ Attacker cannot use tokens (wrong secret?)

Response:
├─ Revoke all existing tokens:
│  ├─ Delete WeChatAuth records
│  ├─ Delete sessions from Redis
│  └─ Force all users to re-login
├─ Rotate encryption key:
│  ├─ Generate new Fernet key
│  ├─ Deploy new key
│  ├─ All new tokens use new key
│  └─ Old encrypted tokens become unrecoverable
├─ Force password reset:
│  └─ Require strong password on re-auth
└─ Alert affected users:
   └─ Email/SMS: "Please re-login due to security incident"
```

---

## Implementation Checklist

### Phase 1: Setup & Configuration

- [ ] **Environment Variables**
  - [ ] Add `WECHAT_APP_ID` to production config
  - [ ] Add `WECHAT_APP_SECRET` to production config
  - [ ] Add `OAUTH_CALLBACK_URL` (e.g., `https://geb-app.com/api/wechat/auth/callback`)
  - [ ] Add `ENCRYPTION_KEY` (Fernet key from `Fernet.generate_key()`)
  - [ ] Add `JWT_SECRET` for session tokens
  - [ ] Add `REDIS_URL` for state/session storage
  - [ ] Verify no secrets in `.env.example`

- [ ] **WeChat Developer Setup**
  - [ ] Log in to [WeChat Developer Platform](https://developers.weixin.qq.com/)
  - [ ] Navigate to Official Account settings
  - [ ] Configure OAuth redirect URI: `https://geb-app.com/api/wechat/auth/callback`
  - [ ] Note down `App ID` and `App Secret`
  - [ ] Test environment: Set sandbox mode if available

- [ ] **Redis Setup**
  - [ ] Ensure Redis running (`redis-cli ping`)
  - [ ] Test connection from backend
  - [ ] Verify TTL support (for state/session expiry)
  - [ ] Set up monitoring for memory usage

- [ ] **Database Models**
  - [x] WeChatAuth table created (already done in Phase 6)
  - [x] Indices on openid, token_expiry, user_id
  - [x] Encryption mixin implemented
  - [x] Timestamp mixin applied

### Phase 2: Core Implementation

- [ ] **OAuth Service** (`app/services/wechat_oauth.py`)
  - [x] WeChatOAuthClient class with Fernet encryption
  - [ ] generate_auth_url() method
  - [ ] exchange_code_for_token() method
  - [ ] get_user_info() method
  - [ ] refresh_access_token() method
  - [ ] revoke_token() method
  - [ ] Error handling with WeChatOAuthError
  - [ ] Graceful mode support

- [ ] **API Routes** (`app/api/wechat_auth.py`)
  - [ ] POST /api/wechat/auth/start
  - [ ] GET /api/wechat/auth/callback
  - [ ] POST /api/wechat/auth/refresh
  - [ ] POST /api/wechat/auth/revoke
  - [ ] POST /api/wechat/auth/status
  - [ ] All error responses implemented
  - [ ] HTTPS enforcement

- [ ] **State Token Management**
  - [ ] StateToken.generate() using secrets module
  - [ ] StateToken.store() in Redis with TTL
  - [ ] StateToken.validate() with IP check
  - [ ] Single-use enforcement (delete after validation)

- [ ] **Session Management**
  - [ ] JWT generation with claims
  - [ ] Session storage in Redis
  - [ ] IP/User-Agent tracking
  - [ ] Session validation middleware

### Phase 3: Security Hardening

- [ ] **HTTPS Enforcement**
  - [ ] Redirect HTTP → HTTPS middleware
  - [ ] Set Strict-Transport-Security header
  - [ ] Secure flag on all cookies
  - [ ] Test with SSL Labs

- [ ] **CSRF Protection**
  - [ ] State token validation
  - [ ] IP mismatch detection
  - [ ] Rate limiting on callback endpoint
  - [ ] Detailed CSRF attack logging

- [ ] **Token Encryption**
  - [ ] Fernet cipher configured
  - [ ] Key rotation procedure documented
  - [ ] Verify all tokens properly encrypted in DB
  - [ ] Test encryption/decryption round-trip

- [ ] **Rate Limiting**
  - [ ] Auth start: 10 req/hour per IP
  - [ ] Callback: 5 req/hour per IP
  - [ ] Refresh: 1 req/hour per user
  - [ ] Alert on suspicious patterns

### Phase 4: Error Handling & Fallback

- [ ] **Error Classification**
  - [ ] Implement error response enums
  - [ ] Map WeChat errors to app errors
  - [ ] Graceful fallback messages

- [ ] **Retry Logic**
  - [ ] Exponential backoff for transient errors
  - [ ] Max retry limits
  - [ ] Circuit breaker for persistent failures
  - [ ] Fallback to cached tokens

- [ ] **Graceful Degradation**
  - [ ] Check config at startup
  - [ ] Feature flag for graceful mode
  - [ ] Alternative login methods available
  - [ ] Cache mechanism implemented

- [ ] **Monitoring & Alerts**
  - [ ] Log all OAuth events
  - [ ] Track success/failure metrics
  - [ ] Alert on CSRF attempts
  - [ ] Monitor refresh rate anomalies

### Phase 5: Testing

- [ ] **Unit Tests**
  - [ ] State token generation & validation
  - [ ] Token encryption/decryption
  - [ ] JWT generation & validation
  - [ ] Error handling for each error code

- [ ] **Integration Tests**
  - [ ] Mock WeChat API responses
  - [ ] Test complete OAuth flow
  - [ ] Test token refresh flow
  - [ ] Test logout flow

- [ ] **Security Tests**
  - [ ] CSRF attack simulation
  - [ ] Replay attack simulation
  - [ ] Invalid state token checks
  - [ ] IP mismatch detection
  - [ ] Expired token handling

- [ ] **Load Tests**
  - [ ] Concurrent login attempts
  - [ ] Token refresh under load
  - [ ] Rate limiting effectiveness
  - [ ] Redis connection pooling

### Phase 6: Documentation & Deployment

- [ ] **API Documentation**
  - [ ] Swagger/OpenAPI spec
  - [ ] Error code reference
  - [ ] Example requests/responses
  - [ ] Rate limit info

- [ ] **Deployment**
  - [ ] Secrets configured in production
  - [ ] OAuth callback URL updated in WeChat admin
  - [ ] Redis deployed and monitored
  - [ ] Alarms set up for failures

- [ ] **Monitoring**
  - [ ] Dashboard for OAuth metrics
  - [ ] Alerts for error rates > 5%
  - [ ] CSRF attempt alerts
  - [ ] Token refresh statistics

- [ ] **Documentation**
  - [ ] Troubleshooting guide
  - [ ] Key rotation procedure
  - [ ] Incident response plan
  - [ ] Architecture diagram

---

## Future Enhancements

### 1. Multi-Account Support
```
Allow user to link multiple WeChat accounts:
├─ Same user_id, multiple wechat_openid
├─ Select which account for current session
└─ Aggregate subscriptions from all accounts
```

### 2. WeChat Payment Integration
```
Once OAuth is working, integrate:
├─ Unified order API
├─ Payment notifications
├─ Refund processing
└─ Reconciliation
```

### 3. WeChat Content APIs
```
Access additional WeChat capabilities:
├─ Account info API
├─ Media upload API
├─ Template message API
└─ Analytics API
```

### 4. Social Features
```
Leverage WeChat user data:
├─ Display user avatar from WeChat
├─ Show user's WeChat groups/accounts
├─ Friend recommendations
└─ Social sharing to WeChat moments
```

---

## References

- [WeChat OAuth Official Spec](https://developers.weixin.qq.com/doc/offiaccount/OA_Web_Apps/Web_interface_authorization.html)
- [OWASP OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Fernet (Cryptography)](https://cryptography.io/en/latest/fernet/)
- [Redis Documentation](https://redis.io/documentation)

