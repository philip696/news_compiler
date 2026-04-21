// WeRead (WeChat Reading) article fetching service.
//
// Ports the real wewe-rss (apps/server/src/trpc/trpc.service.ts) endpoints and
// semantics onto a lightweight, framework-free module that operates on the
// in-memory DB used by test/server.js. Nothing here relies on NestJS, Prisma,
// or axios — just native `fetch` (Node 18+) and the shared `db` handle.
//
// Real endpoints (base URL = PLATFORM_URL, default https://weread.111965.xyz):
//   GET  /api/v2/login/platform                    -> { uuid, scanUrl }
//   GET  /api/v2/login/platform/:uuid              -> { message, vid, token, username }
//   GET  /api/v2/platform/mps/:mpId/articles?page  -> [{ id, title, picUrl, publishTime }]
//   POST /api/v2/platform/wxs2mp                   -> [{ id, cover, name, intro, updateTime }]
//
// Auth headers on every call:
//   xid:           <account.id>
//   Authorization: Bearer <account.token>
//
// Error contract (from the upstream gateway's response body `.message`):
//   WeReadError401 -> session expired; account.status := INVALID (0)
//   WeReadError429 -> rate-limited; account added to today's block list
//   WeReadError400 -> rotate account within this call (no daily block); see handleUpstreamError
//
// Status map mirrors wewe-rss constants.ts (`INVALID=0, ENABLE=1, DISABLE=2`).
// For compatibility with test/server.js (which uses the string "ENABLE"),
// both styles are accepted when selecting an available account.

'use strict';

const DEFAULT_PLATFORM_URL =
  process.env.PLATFORM_URL || 'https://weread.111965.xyz';

const DEFAULT_UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

const DEFAULT_REQUEST_TIMEOUT_MS = 15 * 1000;
const LOGIN_POLL_TIMEOUT_MS = 120 * 1000;
const DEFAULT_COUNT = 20; // wewe-rss constants.ts -> defaultCount
const HISTORY_MAX_PAGES = 1000; // upstream caps at 1e3 iterations
const DEFAULT_UPDATE_DELAY_MS =
  (parseInt(process.env.UPDATE_DELAY_TIME, 10) || 60) * 1000;

const statusMap = {
  INVALID: 0,
  ENABLE: 1,
  DISABLE: 2,
};

class WeReadSessionError extends Error {
  constructor(message, { accountId } = {}) {
    super(message);
    this.name = 'WeReadSessionError';
    this.accountId = accountId;
  }
}

class WeReadRequestError extends Error {
  constructor(message, { status, url, upstreamMessage } = {}) {
    super(message);
    this.name = 'WeReadRequestError';
    this.status = status;
    this.url = url;
    this.upstreamMessage = upstreamMessage;
  }
}

// Distinct from WeReadSessionError: the user's credentials are fine, but
// every account in the pool is unusable (blocked today / all rotated through
// for this call). The correct user action is "add another account" — not
// "log in again".
class WeReadPoolEmptyError extends Error {
  constructor(message, { total = 0, blocked = 0 } = {}) {
    super(message);
    this.name = 'WeReadPoolEmptyError';
    this.total = total;
    this.blocked = blocked;
  }
}

function todayKey() {
  // wewe-rss uses Asia/Shanghai; we approximate without pulling in dayjs.
  // Good enough for a per-day block-list keyspace.
  const d = new Date(Date.now() + 8 * 60 * 60 * 1000);
  return d.toISOString().slice(0, 10);
}

function isEnabled(acc) {
  if (!acc || !acc.token) return false;
  // Support both numeric (real DB) and string (test/server.js) status values.
  return (
    acc.status === statusMap.ENABLE ||
    acc.status === 'ENABLE' ||
    acc.status === undefined
  );
}

function createWeReadService({
  db,
  platformUrl = DEFAULT_PLATFORM_URL,
  userAgent = DEFAULT_UA,
  logger = console,
  fetchImpl = globalThis.fetch,
  requestTimeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
  updateDelayMs = DEFAULT_UPDATE_DELAY_MS,
  maxRetries = 3,
  sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
} = {}) {
  if (!db || !Array.isArray(db.accounts) || !Array.isArray(db.articles)) {
    throw new Error('createWeReadService: db must expose accounts[] and articles[]');
  }
  if (typeof fetchImpl !== 'function') {
    throw new Error('createWeReadService: fetch implementation is required');
  }
  if (!Array.isArray(db.feeds)) db.feeds = [];

  // Per-day block list — mirrors wewe-rss `blockedAccountsMap`.
  const blockedAccountsMap = new Map();

  const state = {
    inProgressHistoryMp: { id: '', page: 1 },
    isRefreshAllRunning: false,
  };

  // ---------- block list helpers ----------

  function getBlockedAccountIds() {
    return (blockedAccountsMap.get(todayKey()) || []).filter(Boolean);
  }

  function addBlockedAccount(id) {
    if (!id) return;
    const key = todayKey();
    const list = blockedAccountsMap.get(key) || [];
    if (!list.includes(id)) list.push(id);
    blockedAccountsMap.set(key, list);
  }

  function removeBlockedAccount(id) {
    const key = todayKey();
    const list = blockedAccountsMap.get(key);
    if (Array.isArray(list)) {
      blockedAccountsMap.set(
        key,
        list.filter((x) => x !== id),
      );
    }
  }

  // ---------- account selection ----------

  function getAvailableAccount(excludeIds = []) {
    const blocked = new Set([...getBlockedAccountIds(), ...excludeIds]);
    const pool = db.accounts.filter((a) => isEnabled(a) && !blocked.has(a.id));
    if (pool.length === 0) {
      if (db.accounts.length === 0) {
        throw new WeReadSessionError(
          '暂无可用读书账号 — log in with WeChat first.',
        );
      }
      // Not a session problem — user is logged in but every account has
      // been rotated-through or blocked. Surface a distinct error so the
      // HTTP layer returns 502 (upstream unavailable) with a useful CTA,
      // rather than 401 (which makes the UI think login expired).
      throw new WeReadPoolEmptyError(
        `Upstream rejected every account in your pool for this request ` +
          `(${db.accounts.length} total, ${getBlockedAccountIds().length} ` +
          `blocked today). Add another WeChat account — the gateway ` +
          `rotates across a pool and 2–3 accounts dramatically improve ` +
          `success.`,
        { total: db.accounts.length, blocked: getBlockedAccountIds().length },
      );
    }
    return pool[Math.floor(Math.random() * pool.length)];
  }

  function markAccountInvalid(id) {
    const acc = db.accounts.find((a) => a.id === id);
    if (!acc) return;
    acc.status = statusMap.INVALID;
    logger.warn?.(`[wechat-service] account(${id}) session invalid, disabled`);
  }

  // ---------- HTTP core ----------

  function buildHeaders(account, extra = {}) {
    return {
      Accept: 'application/json, text/plain, */*',
      'User-Agent': userAgent,
      xid: account ? account.id : '',
      ...(account ? { Authorization: `Bearer ${account.token}` } : {}),
      ...extra,
    };
  }

  async function rawRequest(method, pathname, { account, query, body, timeoutMs } = {}) {
    const url = new URL(pathname, platformUrl);
    if (query) {
      for (const [k, v] of Object.entries(query)) {
        if (v === undefined || v === null) continue;
        url.searchParams.set(k, String(v));
      }
    }

    const controller = new AbortController();
    const timer = setTimeout(
      () => controller.abort(),
      timeoutMs || requestTimeoutMs,
    );

    let response;
    try {
      response = await fetchImpl(url.toString(), {
        method,
        headers: buildHeaders(account, body ? { 'Content-Type': 'application/json' } : {}),
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
    } catch (err) {
      throw new WeReadRequestError(
        `Network error calling ${url}: ${err.message}`,
        { url: url.toString() },
      );
    } finally {
      clearTimeout(timer);
    }

    let payload = null;
    const text = await response.text();
    if (text) {
      try { payload = JSON.parse(text); } catch { /* non-JSON */ }
    }

    if (!response.ok) {
      const upstreamMessage =
        (payload && (payload.message || payload.error)) || text || '';
      const err = new WeReadRequestError(
        `HTTP ${response.status} from ${url}: ${upstreamMessage}`,
        { status: response.status, url: url.toString(), upstreamMessage },
      );
      throw err;
    }

    return payload;
  }

  // Apply the same error taxonomy wewe-rss enforces in its axios interceptor.
  function handleUpstreamError(err, account) {
    const msg =
      (err && err.upstreamMessage) ||
      (err && err.message) ||
      '';

    if (msg.includes('WeReadError401')) {
      markAccountInvalid(account.id);
      return { kind: 'session', retry: false };
    }
    if (msg.includes('WeReadError429')) {
      addBlockedAccount(account.id);
      logger.error?.(`[wechat-service] account(${account.id}) rate-limited`);
      return { kind: 'rate-limit', retry: false };
    }
    if (msg.includes('WeReadError400')) {
      // Matches wewe-rss's axios interceptor: WeReadError400 is NOT treated
      // as an account-wide failure. The account may be unable to read this
      // particular公众号 right now, but it's perfectly fine for other mps
      // and other operations (e.g. getMpInfo). We only exclude it from the
      // retry loop for *this* call via `rotate: true`; we do NOT add it to
      // the daily block list.
      logger.error?.(
        `[wechat-service] account(${account.id}) WeReadError400; rotating within this call: ${msg}`,
      );
      return { kind: 'bad-request', retry: true, rotate: true };
    }
    return { kind: 'unknown', retry: true, delayMs: 0 };
  }

  // ---------- public: login flow ----------

  async function createLoginUrl() {
    return rawRequest('GET', '/api/v2/login/platform');
  }

  async function getLoginResult(uuid) {
    return rawRequest('GET', `/api/v2/login/platform/${uuid}`, {
      timeoutMs: LOGIN_POLL_TIMEOUT_MS,
    });
  }

  // ---------- public: mp info ----------

  async function getMpInfo(wxsLink) {
    const account = getAvailableAccount();
    const url = String(wxsLink || '').trim();
    if (!url.startsWith('https://mp.weixin.qq.com/s/')) {
      throw new Error('getMpInfo: expected a https://mp.weixin.qq.com/s/... link');
    }
    try {
      return await rawRequest('POST', '/api/v2/platform/wxs2mp', {
        account,
        body: { url },
      });
    } catch (err) {
      const outcome = handleUpstreamError(err, account);
      if (outcome.kind === 'session') {
        throw new WeReadSessionError('Session expired', { accountId: account.id });
      }
      throw err;
    }
  }

  // ---------- public: article fetch (single page) ----------

  /**
   * Fetch one page of articles for `mpId`. Returns the raw array exactly as
   * the upstream platform returns it (id/title/picUrl/publishTime), mirroring
   * wewe-rss's trpcService.getMpArticles.
   *
   * Retries up to `maxRetries` times on transient failures, applying the
   * WeReadError4xx taxonomy.
   */
  async function getMpArticles(mpId, page = 1, opts = {}) {
    if (!mpId) throw new Error('getMpArticles: mpId is required');
    // `tried` lets us rotate across every account in the pool before giving
    // up. This mirrors wewe-rss's strategy of re-picking a random account
    // on each retry — except we explicitly avoid re-picking ones that
    // already failed for this call.
    const tried = opts.tried || [];
    const retriesLeft = opts.retriesLeft ?? maxRetries;
    const account = getAvailableAccount(tried);

    try {
      const data = await rawRequest(
        'GET',
        `/api/v2/platform/mps/${mpId}/articles`,
        { account, query: { page } },
      );
      const list = Array.isArray(data) ? data : data?.items || [];
      logger.log?.(
        `[wechat-service] getMpArticles(${mpId}) page=${page} via acc=${account.id} -> ${list.length}`,
      );
      return list;
    } catch (err) {
      const outcome = handleUpstreamError(err, account);
      const nextTried = outcome.rotate ? [...tried, account.id] : tried;

      if (outcome.kind === 'session') {
        // Session rejected — rotate to a fresh account if one exists.
        if (retriesLeft > 0) {
          return getMpArticles(mpId, page, {
            tried: [...tried, account.id],
            retriesLeft: retriesLeft - 1,
          });
        }
        throw new WeReadSessionError(
          `All candidate sessions rejected for mp=${mpId}`,
          { accountId: account.id },
        );
      }

      if (outcome.retry && retriesLeft > 0) {
        if (outcome.delayMs) await sleep(outcome.delayMs);
        logger.error?.(
          `[wechat-service] retry(${maxRetries - retriesLeft + 1}) getMpArticles(${mpId}) page=${page}: ${err.message}`,
        );
        return getMpArticles(mpId, page, {
          tried: nextTried,
          retriesLeft: retriesLeft - 1,
        });
      }
      throw err;
    }
  }

  // ---------- persistence ----------

  function upsertArticle({ id, mpId, title, picUrl, publishTime }) {
    const idx = db.articles.findIndex((a) => a.id === id);
    const record = { id, mpId, title, picUrl: picUrl || '', publishTime };
    if (idx >= 0) {
      db.articles[idx] = { ...db.articles[idx], ...record };
      return { inserted: false };
    }
    db.articles.push(record);
    return { inserted: true };
  }

  function upsertFeed(mpId, patch) {
    let feed = db.feeds.find((f) => (f.id || f.mpId) === mpId);
    if (!feed) {
      feed = { id: mpId, mpId, createdAt: Math.floor(Date.now() / 1000) };
      db.feeds.push(feed);
    }
    Object.assign(feed, patch);
    return feed;
  }

  // ---------- public: refresh + history ----------

  /**
   * Fetch page `page` for `mpId`, upsert articles, and update the feed's
   * `syncTime` + `hasHistory` flag. Mirrors wewe-rss refreshMpArticlesAndUpdateFeed:
   *   hasHistory = (articles.length < DEFAULT_COUNT) ? 0 : 1
   */
  async function refreshMpArticlesAndUpdateFeed(mpId, page = 1) {
    const articles = await getMpArticles(mpId, page);

    for (const a of articles) {
      if (!a || !a.id) continue;
      upsertArticle({
        id: String(a.id),
        mpId,
        title: a.title || 'Untitled',
        picUrl: a.picUrl || '',
        publishTime:
          typeof a.publishTime === 'number'
            ? a.publishTime
            : Math.floor(Date.parse(a.publishTime || 0) / 1000) || 0,
      });
    }

    const hasHistory = articles.length < DEFAULT_COUNT ? 0 : 1;
    upsertFeed(mpId, {
      syncTime: Math.floor(Date.now() / 1000),
      hasHistory,
    });

    logger.debug?.(
      `[wechat-service] refreshMpArticlesAndUpdateFeed(${mpId}) page=${page} hasHistory=${hasHistory}`,
    );
    return { hasHistory, count: articles.length };
  }

  /**
   * Walk every page until the upstream reports <20 items (hasHistory=0) or
   * the hard cap of 1000 pages is reached. Matches wewe-rss behaviour,
   * including the inter-page delay.
   */
  async function getHistoryMpArticles(mpId) {
    if (!mpId) return;
    if (state.inProgressHistoryMp.id === mpId) {
      logger.log?.(`[wechat-service] getHistoryMpArticles(${mpId}) already running`);
      return;
    }
    state.inProgressHistoryMp = { id: mpId, page: 1 };

    try {
      const feed = db.feeds.find((f) => (f.id || f.mpId) === mpId);
      if (feed && feed.hasHistory === 0) {
        logger.log?.(`[wechat-service] getHistoryMpArticles(${mpId}) no history`);
        return;
      }

      const existing = db.articles.filter((a) => a.mpId === mpId).length;
      state.inProgressHistoryMp.page = Math.max(1, Math.ceil(existing / DEFAULT_COUNT));

      for (let i = 0; i < HISTORY_MAX_PAGES; i += 1) {
        if (state.inProgressHistoryMp.id !== mpId) break;
        const { hasHistory } = await refreshMpArticlesAndUpdateFeed(
          mpId,
          state.inProgressHistoryMp.page,
        );
        if (hasHistory < 1) break;
        state.inProgressHistoryMp.page += 1;
        if (updateDelayMs > 0) await sleep(updateDelayMs);
      }
    } finally {
      state.inProgressHistoryMp = { id: '', page: 1 };
    }
  }

  async function refreshAllMpArticlesAndUpdateFeed() {
    if (state.isRefreshAllRunning) {
      logger.log?.('[wechat-service] refreshAll already running');
      return;
    }
    state.isRefreshAllRunning = true;
    try {
      const mps = [...db.feeds];
      for (const feed of mps) {
        const id = feed.id || feed.mpId;
        if (!id) continue;
        try {
          await refreshMpArticlesAndUpdateFeed(id);
        } catch (err) {
          logger.error?.(
            `[wechat-service] refreshAll: mp=${id} failed: ${err.message}`,
          );
        }
        if (updateDelayMs > 0) await sleep(updateDelayMs);
      }
    } finally {
      state.isRefreshAllRunning = false;
    }
  }

  return {
    // login
    createLoginUrl,
    getLoginResult,
    // mp info
    getMpInfo,
    // articles
    getMpArticles,
    refreshMpArticlesAndUpdateFeed,
    getHistoryMpArticles,
    refreshAllMpArticlesAndUpdateFeed,
    // introspection / ops
    getBlockedAccountIds,
    removeBlockedAccount,
    clearBlockedAccounts: () => blockedAccountsMap.clear(),
    get inProgressHistoryMp() { return { ...state.inProgressHistoryMp }; },
    get isRefreshAllMpArticlesRunning() { return state.isRefreshAllRunning; },
  };
}

module.exports = {
  createWeReadService,
  WeReadSessionError,
  WeReadRequestError,
  WeReadPoolEmptyError,
  statusMap,
  DEFAULT_PLATFORM_URL,
  DEFAULT_COUNT,
};
