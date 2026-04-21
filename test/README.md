# Test Integration for WeWe-RSS

This folder contains a minimal Express server plus a WeRead (WeChat Reading)
service layer that:

- Gets a WeChat login QR code
- Polls login status and stores the session token
- Fetches articles from a WeRead-compatible `PLATFORM_URL` using the stored
  session cookie / bearer token
- Lists connected accounts

Code is adapted from [wewe-rss](https://github.com/cooderl/wewe-rss).

## Files

- `server.js` — Express server with in-memory DB (accounts / feeds / articles)
  and the `/api/wechat-*` routes.
- `python/` — **FastAPI** port of the same server + service (`main.py`,
  `weread_service.py`): same routes, JSON shapes, and status codes as
  `server.js` / `wechat-service.js`. Inter-request delay defaults to **60s**
  (`UPDATE_DELAY_TIME`, same as wewe-rss README); set `UPDATE_DELAY_MS` for
  a shorter dev-only delay.
- `wechat-service.js` — service-layer module: `getMpArticles`,
  `getHistoryMpArticles`, `refreshMpArticlesAndUpdateFeed` (uses the stored
  session to call WeRead over HTTP).
- `wechat-api.js` — axios-based low-level client (alternative to the native
  `fetch` used by `wechat-service.js`).
- `wechat-service.demo.js` — offline smoke test with a fake `fetch`; no
  network required.
- `frontend.html` — tiny UI to exercise the server routes.

## Prerequisites

- Node.js **18+** (Node 22 recommended — `wechat-service.js` uses the global
  `fetch` API).
- A reachable WeRead-compatible gateway (e.g. a self-hosted
  [wewe-rss](https://github.com/cooderl/wewe-rss) instance).

## Install

```bash
cd test
npm install
# optional, only needed if you use wechat-api.js (axios)
npm install axios
```

## Run the offline demo

This is the fastest way to verify the service layer works end-to-end without
any external services:

```bash
node wechat-service.demo.js
```

It will print pagination / upsert / session-expiry assertions and exit 0 on
success.

## Run against the real wewe-rss gateway

`wechat-service.js` speaks the exact endpoint contract implemented by
[wewe-rss](https://github.com/cooderl/wewe-rss) (`apps/server/src/trpc/trpc.service.ts`):

| Endpoint                                                   | Purpose                                  |
| ---------------------------------------------------------- | ---------------------------------------- |
| `GET  /api/v2/login/platform`                              | Request a QR UUID + `scanUrl`            |
| `GET  /api/v2/login/platform/:uuid`                        | Poll login, returns `{ vid, token, ... }`|
| `GET  /api/v2/platform/mps/:mpId/articles?page=N`          | One page (≤ 20) of articles              |
| `POST /api/v2/platform/wxs2mp`  body `{ url }`             | Resolve an `mp.weixin.qq.com/s/...` link |

All authenticated calls send:

```
xid:           <account.id>
Authorization: Bearer <account.token>
```

Pagination stops when a page returns fewer than **20** items (the gateway's
`defaultCount`). Upstream errors are detected via the response body's
`message` field and mapped as follows, matching wewe-rss's axios interceptor:

- `WeReadError401` → account is marked `INVALID` (status `0`); the retry
  rotates to a different account in the pool.
- `WeReadError429` → account is added to today's in-memory block list; the
  retry rotates to a different account.
- `WeReadError400` → **not** added to the daily block list (unlike `429`).
  The same request retries with a *different* account from the pool
  (`tried` rotation). If every account fails, the HTTP layer returns
  `pool_exhausted` / upstream `WeReadError400` as appropriate.

### 1. Point the client at your gateway

Set `PLATFORM_URL` to the base URL of your WeRead-compatible server. Defaults
to `https://weread.111965.xyz` if unset (the same default used by wewe-rss).

```bash
export PLATFORM_URL="https://weread.111965.xyz" #https://weread.965111.xyz

export PORT=3100
```

### 2. Start the Express server

```bash
npm start
# or:  node server.js
```

Open http://localhost:3100 — the bundled `frontend.html` will load.

### 2b. Start the FastAPI server (Python, same API)

```bash
cd test/python
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PLATFORM_URL="https://weread.111965.xyz"  # optional
export PORT=3100                                # optional
uvicorn main:app --host 0.0.0.0 --port "${PORT:-3100}"
```

The app serves the same `../frontend.html` at `/` and exposes the same `/api/*`
routes as `server.js`. Stop the Node server first if you reuse port `3100`.

### 3. Log in with WeChat (real QR)

`GET /api/wechat-qr` now delegates to the wewe-rss gateway — the returned
`uuid` and `scanUrl` come from the upstream `/api/v2/login/platform` call, so
scanning the QR works with the real WeChat app. The server long-polls
`/api/v2/login/platform/:uuid` in the background and caches the result.

1. Click **Get WeChat Login QR** on the page. The frontend renders the real
   `scanUrl` as a QR using qrcodejs.
2. Scan it with WeChat on your phone and confirm.
3. The page polls `GET /api/wechat-login-status?uuid=...`. Once the upstream
   confirms the scan, it returns `{ message: 'success', vid, token, username }`
   and the server upserts the account (with `status = ENABLE`) into the
   in-memory DB so subsequent requests can use the token.

Possible `message` values:

- `waiting` — QR not yet scanned.
- `success` — scanned and confirmed; `vid` + `token` are returned.
- `error` — upstream rejected or the QR expired (default 5-minute window).
- `not_found` — the UUID is unknown to this server.

Alternatively, curl it directly:

```bash
curl http://localhost:3100/api/wechat-qr
# -> { "uuid": "…", "scanUrl": "https://weread.qq.com/login?uuid=…" }

curl "http://localhost:3100/api/wechat-login-status?uuid=<uuid>"
```

If you keep seeing `QR expired`, the most common causes are:

- `PLATFORM_URL` points to a gateway that's offline or rate-limited. Verify
  with `curl $PLATFORM_URL/api/v2/login/platform`.
- The browser tab has been idle longer than 5 minutes after fetching the QR
  (re-click **Get WeChat Login QR** to mint a fresh one).
- The upstream gateway issued a UUID but your phone scanned a cached/old QR
  image — refresh the page and rescan.

### 4. Add an official account by link (the wewe-rss flow)

You cannot fetch articles using the account's own `vid` — that's the logged-in
user ID, not a公众号 (official account) ID. Doing so triggers
`WeReadError400` on the upstream gateway.

The real wewe-rss flow: **paste any article URL from the official account you
want to follow** (e.g. `https://mp.weixin.qq.com/s/avBcaX3MgEkNGo64dZaJZA`).
The server resolves that link via `POST /api/v2/platform/wxs2mp`, gets back
the real `mpId` + name/cover/intro, stores it as a feed, and pulls history.

#### From the UI

1. After login, a second section appears: **"Add an official account"**.
2. Paste the `mp.weixin.qq.com/s/...` link and click
   **Add & fetch history**.
3. The resolved公众号 shows up in section 3 with cover, name, intro, and an
   `articleCount` that grows as the background history fetch progresses.
4. Each mp has three buttons:
   - **View articles** — list cached articles sorted by `publishTime`.
   - **Sync** — fetch the newest page only.
   - **Full history** — walk every page until the gateway returns <20 items.
5. **Sync all** re-runs `refreshMpArticlesAndUpdateFeed` across every stored
   mp (respects `UPDATE_DELAY_TIME` / `UPDATE_DELAY_MS` between mps).

#### From curl

All routes below require `xid` + `token` headers from step 3.

```bash
XID="932596105"
TOKEN="session-token-..."

# Add an official account by link
curl -X POST -H "Content-Type: application/json" \
     -H "xid: $XID" -H "token: $TOKEN" \
     -d '{"wxsLink":"https://mp.weixin.qq.com/s/avBcaX3MgEkNGo64dZaJZA"}' \
     http://localhost:3100/api/mps

# List stored mps (with articleCount)
curl -H "xid: $XID" -H "token: $TOKEN" http://localhost:3100/api/mps

# Sync latest page for one mp
curl -X POST -H "xid: $XID" -H "token: $TOKEN" \
     http://localhost:3100/api/mps/<MP_ID>/sync

# Full historical backfill for one mp
curl -X POST -H "xid: $XID" -H "token: $TOKEN" \
     "http://localhost:3100/api/mps/<MP_ID>/sync?history=1"

# Sync all mps
curl -X POST -H "xid: $XID" -H "token: $TOKEN" \
     http://localhost:3100/api/mps/sync-all

# List articles for an mp
curl -H "xid: $XID" -H "token: $TOKEN" \
     "http://localhost:3100/api/articles?mpId=<MP_ID>"

# Remove an mp (and its cached articles)
curl -X DELETE -H "xid: $XID" -H "token: $TOKEN" \
     http://localhost:3100/api/mps/<MP_ID>
```

The old `/api/wechat-articles?mpId=...&history=1` route is still available as
a back-compat alias, but the `/api/mps/*` routes are the recommended flow.

### 5. Using the service module directly

The service is API-layer-agnostic; you can call it from any Node script:

```js
const { createWeReadService, WeReadSessionError } = require('./wechat-service');

const db = { accounts: [/* loaded from your store */], feeds: [], articles: [] };
const svc = createWeReadService({
  db,
  platformUrl: process.env.PLATFORM_URL,
});

try {
  // Login (only needed if the DB has no valid account yet):
  const { uuid, scanUrl } = await svc.createLoginUrl();
  console.log('Scan:', scanUrl);
  const login = await svc.getLoginResult(uuid); // long-polls up to 120s
  db.accounts.push({
    id: String(login.vid),
    token: login.token,
    name: login.username,
    status: 1, // statusMap.ENABLE
  });

  // Routine poll + historical backfill:
  await svc.refreshMpArticlesAndUpdateFeed('MP_BIZ_ID');
  await svc.getHistoryMpArticles('MP_BIZ_ID');
} catch (err) {
  if (err instanceof WeReadSessionError) {
    // token expired — re-run the QR login flow
  } else {
    console.error(err);
  }
}
```

## Environment variables

| Variable             | Default                     | Purpose                                               |
| -------------------- | --------------------------- | ----------------------------------------------------- |
| `PORT`               | `3100`                      | Port the Express server listens on                    |
| `PLATFORM_URL`       | `https://weread.111965.xyz` | wewe-rss-compatible gateway base URL                  |
| `UPDATE_DELAY_TIME`  | `60`                        | Seconds between history pages / feeds (wewe-rss default; reduces 小黑屋 risk) |
| `UPDATE_DELAY_MS`    | _(unset)_                 | If set, overrides `UPDATE_DELAY_TIME` with an explicit millisecond delay (dev only, e.g. `2000`) |

## Troubleshooting

- **`WeReadSessionError: HTTP 401` / `HTTP 403`** — the stored token has
  expired; the account is auto-flagged `INVALID`. Re-run the QR login.
- **`WeReadRequestError: Network error`** — `PLATFORM_URL` unreachable or DNS
  failure; verify the gateway is running and reachable from this host.
- **Empty article list** — confirm the `mpId` is correct and that the account
  has permission to read that公众号 on the upstream gateway.
- **`MP_WXS_<digits>` placeholder ids** — the public `weread.111965.xyz`
  gateway (and forks) returns synthetic ids of the form `MP_WXS_<digits>`
  where `<digits>` is the base64-decoded value of the real biz id, e.g.:

  ```
  MP_WXS_3073282833  ==  btoa("3073282833") = "MzA3MzI4MjgzMw=="  (机器之心)
  ```

  `server.js` detects this automatically and converts the placeholder back
  to the real biz id (`placeholderToRealBiz`) both when adding a new mp and
  when syncing an mp that was saved before this fix. No action required —
  just click **Sync** again on any `MP_WXS_*` feed you already have.

  If the format changes in future, there's a secondary HTML-scrape fallback
  (`resolveBizFromShareUrl`) that pulls `var biz = "..."` straight from the
  WeChat article page using a mobile WeChat User-Agent.
- **Still `WeReadError400` after recovery** — this is almost always a
  *pool size* problem, not a bug on your side. Reading wewe-rss's source
  (`getAvailableAccount` + the `getMpArticles` retry loop) confirms that
  the upstream gateway is designed around a *pool* of WeRead accounts and
  rotates randomly across them per request; when one account can't read a
  particular公众号, wewe-rss simply retries hoping a different account
  succeeds. If your pool is size 1, every retry picks the same account and
  re-fails identically.

  **Fix:** click **Add another account** on the login card and scan with a
  second (ideally a third) WeChat account. Each scan grows the server-side
  pool without replacing your client credentials. `GET /api/wechat-accounts`
  now reports `blockedToday` per account so you can see the rotation
  happen live. `POST /api/wechat-accounts/clear-block` wipes today's block
  list if you believe the gateway has cooled off.

  If you genuinely can't add more accounts, the gateway may simply be
  refusing that公众号 for WeRead policy reasons — no client-side fix will
  change that.
