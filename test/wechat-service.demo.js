// Offline smoke test for wechat-service.js against the *real* wewe-rss
// endpoint shape:
//   GET /api/v2/platform/mps/:mpId/articles?page=N
//     -> [{ id, title, picUrl, publishTime }]   (bare array, 20 per page)
//
// Error taxonomy (body.message):
//   WeReadError401 -> disable account
//   WeReadError429 -> block account for today
//   WeReadError400 -> retry after 10s
//
// Run: node test/wechat-service.demo.js

'use strict';

const assert = require('node:assert');
const {
  createWeReadService,
  WeReadSessionError,
  WeReadPoolEmptyError,
  DEFAULT_COUNT,
  statusMap,
} = require('./wechat-service');

const db = {
  accounts: [
    { id: 'acc-1', token: 'session-token-abc', name: 'Good', status: statusMap.ENABLE },
  ],
  feeds: [],
  articles: [],
};

// Build 25 articles: page 1 -> 20 items (hasMore), page 2 -> 5 items (stop).
function makePage(n, offset) {
  return Array.from({ length: n }, (_, i) => ({
    id: `art-${offset + i}`,
    title: `Article ${offset + i}`,
    picUrl: `https://img.example/${offset + i}.jpg`,
    publishTime: 1_700_000_000 + (offset + i) * 60,
  }));
}
const pages = {
  1: makePage(DEFAULT_COUNT, 1),
  2: makePage(5, DEFAULT_COUNT + 1),
};

const calls = [];

async function fakeFetch(url, init) {
  calls.push({ url, method: init.method, headers: init.headers });
  const parsed = new URL(url);

  // Simulate expired token
  if ((init.headers.Authorization || '').endsWith('expired')) {
    return {
      ok: false,
      status: 401,
      text: async () => JSON.stringify({ message: 'WeReadError401: invalid session' }),
    };
  }
  // Simulate rate limit
  if ((init.headers.Authorization || '').endsWith('ratelimited')) {
    return {
      ok: false,
      status: 429,
      text: async () => JSON.stringify({ message: 'WeReadError429: too many' }),
    };
  }

  if (parsed.pathname.startsWith('/api/v2/platform/mps/') && parsed.pathname.endsWith('/articles')) {
    const page = parseInt(parsed.searchParams.get('page') || '1', 10);
    const body = pages[page] || [];
    return { ok: true, status: 200, text: async () => JSON.stringify(body) };
  }

  if (parsed.pathname === '/api/v2/login/platform') {
    return { ok: true, status: 200, text: async () => JSON.stringify({ uuid: 'u1', scanUrl: 'https://qr/u1' }) };
  }
  if (parsed.pathname.startsWith('/api/v2/login/platform/')) {
    return {
      ok: true,
      status: 200,
      text: async () =>
        JSON.stringify({ message: 'success', vid: 4242, token: 'tk', username: 'me' }),
    };
  }

  return { ok: false, status: 404, text: async () => JSON.stringify({ message: 'not found' }) };
}

(async () => {
  const svc = createWeReadService({
    db,
    platformUrl: 'https://weread.example.test',
    fetchImpl: fakeFetch,
    logger: { log: () => {}, debug: () => {}, warn: () => {}, error: () => {} },
    updateDelayMs: 0, // no sleep between pages in the test
  });

  // 1. Login endpoints reachable with zero account auth required.
  const qr = await svc.createLoginUrl();
  assert.deepStrictEqual(qr, { uuid: 'u1', scanUrl: 'https://qr/u1' });
  const login = await svc.getLoginResult('u1');
  assert.strictEqual(login.message, 'success');
  assert.strictEqual(login.token, 'tk');
  console.log('login ->', login);

  // 2. Refresh: page 1 returns DEFAULT_COUNT -> hasHistory=1.
  const r1 = await svc.refreshMpArticlesAndUpdateFeed('mp-abc');
  assert.strictEqual(r1.count, DEFAULT_COUNT);
  assert.strictEqual(r1.hasHistory, 1);

  // Headers sent must match the real wewe-rss contract (xid + Bearer, no Cookie).
  const articleCall = calls.find((c) => c.url.includes('/mps/mp-abc/articles'));
  assert.strictEqual(articleCall.headers.xid, 'acc-1');
  assert.strictEqual(articleCall.headers.Authorization, 'Bearer session-token-abc');
  assert.strictEqual(articleCall.headers.Cookie, undefined);

  // 3. History walks page 1 + page 2 and stops (second page has <20 items).
  await svc.getHistoryMpArticles('mp-abc');
  const mpArticles = db.articles.filter((a) => a.mpId === 'mp-abc');
  assert.strictEqual(mpArticles.length, DEFAULT_COUNT + 5);
  console.log('history stored ->', mpArticles.length, 'articles');

  // Idempotent re-run.
  await svc.getHistoryMpArticles('mp-abc');
  assert.strictEqual(
    db.articles.filter((a) => a.mpId === 'mp-abc').length,
    DEFAULT_COUNT + 5,
    'upsert must be idempotent',
  );

  const feed = db.feeds.find((f) => f.id === 'mp-abc');
  assert.ok(feed.syncTime > 0);
  assert.strictEqual(feed.hasHistory, 0, 'feed marked as fully synced');

  // 4. WeReadError401 disables the account.
  db.accounts.push({ id: 'acc-dead', token: 'expired', name: 'Dead', status: statusMap.ENABLE });
  // Force deterministic selection by temporarily disabling acc-1.
  const acc1 = db.accounts.find((a) => a.id === 'acc-1');
  acc1.status = statusMap.DISABLE;
  // The first account (acc-dead) hits 401 and gets disabled; the retry then
  // finds the pool empty (acc-1 manually disabled, acc-dead now INVALID) and
  // raises WeReadPoolEmptyError. Either error is acceptable evidence the
  // session-invalidation path ran.
  await assert.rejects(
    () => svc.refreshMpArticlesAndUpdateFeed('mp-abc'),
    (err) => err instanceof WeReadPoolEmptyError || err instanceof WeReadSessionError,
  );
  const accDead = db.accounts.find((a) => a.id === 'acc-dead');
  assert.strictEqual(accDead.status, statusMap.INVALID, 'expired account disabled');
  acc1.status = statusMap.ENABLE; // restore

  // 5. WeReadError429 adds account to today's block list (no crash).
  db.accounts.push({ id: 'acc-rl', token: 'ratelimited', name: 'RL', status: statusMap.ENABLE });
  acc1.status = statusMap.DISABLE;
  accDead.status = statusMap.INVALID; // already invalid
  await assert.rejects(() => svc.refreshMpArticlesAndUpdateFeed('mp-abc'));
  assert.ok(
    svc.getBlockedAccountIds().includes('acc-rl'),
    'rate-limited account must be in daily block list',
  );
  acc1.status = statusMap.ENABLE;

  console.log('\nAll demo assertions passed against real-endpoint shapes.');
})().catch((err) => {
  console.error('Demo failed:', err);
  process.exitCode = 1;
});
