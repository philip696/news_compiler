// Minimal Express server that mirrors the wewe-rss flow:
//   1. QR login against the real PLATFORM_URL gateway.
//   2. User pastes an https://mp.weixin.qq.com/s/<...> link.
//   3. We resolve that link to a real official-account (mp) via
//      POST /api/v2/platform/wxs2mp, store it as a feed, and pull history.
//   4. "Sync" re-runs refresh for one mp or all mps.

const express = require('express');
const path = require('path');
const {
  createWeReadService,
  WeReadSessionError,
  WeReadPoolEmptyError,
  statusMap,
} = require('./wechat-service');

const app = express();
const PORT = process.env.PORT || 3100;
const PLATFORM_URL = process.env.PLATFORM_URL || 'https://weread.111965.xyz';

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// In-memory DB (shape matches what wechat-service.js expects).
const db = {
  accounts: [], // { id, token, name, status }
  feeds: [],    // { id, mpName, mpCover, mpIntro, updateTime, syncTime, hasHistory, status }
  articles: [], // { id, mpId, title, picUrl, publishTime }
};

// Pending QR login sessions keyed by upstream uuid.
const loginSessions = new Map();

const svc = createWeReadService({
  db,
  platformUrl: PLATFORM_URL,
  // Match wewe-rss README: UPDATE_DELAY_TIME defaults to 60s between pages /
  // feeds to reduce 小黑屋 risk. Override with UPDATE_DELAY_MS (milliseconds)
  // for local dev only, e.g. UPDATE_DELAY_MS=2000.
  updateDelayMs:
    process.env.UPDATE_DELAY_MS !== undefined
      ? parseInt(process.env.UPDATE_DELAY_MS, 10)
      : (parseInt(process.env.UPDATE_DELAY_TIME, 10) || 60) * 1000,
  logger: {
    log: () => {},
    debug: () => {},
    warn: (m) => console.warn(m),
    error: (m) => console.error(m),
  },
});

function requireAuth(req, res) {
  const xid = req.headers['xid'];
  const token = req.headers['token'];
  const account = db.accounts.find((a) => a.token === token || a.id === xid);
  if (!account) {
    res.status(401).json({ error: 'unauthorized' });
    return null;
  }
  return account;
}

function upsertAccount({ id, token, name, status = statusMap.ENABLE }) {
  const existing = db.accounts.find((a) => a.id === id);
  if (existing) {
    Object.assign(existing, { token, name, status });
    return existing;
  }
  const acc = { id, token, name, status };
  db.accounts.push(acc);
  return acc;
}

// The weread.111965.xyz gateway (and forks) mint placeholder ids of the
// form `MP_WXS_<digits>` where `<digits>` is the *decoded* value of the
// real base64 biz id. We can recover the real biz id offline by base64-
// encoding the digits again.
//   MP_WXS_3073282833  <->  btoa("3073282833") = "MzA3MzI4MjgzMw=="
// This has been empirically verified against 机器之心 (MzA3MzI4MjgzMw==).
function placeholderToRealBiz(mpId) {
  const m = /^MP_WXS_(\d+)$/.exec(String(mpId || ''));
  if (!m) return null;
  const digits = m[1];
  const b64 = Buffer.from(digits, 'utf8').toString('base64');
  // Sanity: decoding must round-trip back to the same digits.
  const roundTrip = Buffer.from(b64, 'base64').toString('utf8');
  return roundTrip === digits ? b64 : null;
}

// Secondary fallback: scrape the real biz id from a WeChat article share
// page (https://mp.weixin.qq.com/s/...). WeChat's article HTML embeds:
//   var biz = "MzI0NDg2NzEzMQ==" || "";
// Only needed if the placeholder→biz deterministic path fails (e.g. a
// future gateway starts using a different id scheme).
async function resolveBizFromShareUrl(wxsLink) {
  const UA =
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) ' +
    'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 ' +
    'MicroMessenger/8.0.42(0x18002a2c) NetType/WIFI Language/zh_CN';
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);
  try {
    const resp = await fetch(wxsLink, {
      method: 'GET',
      redirect: 'follow',
      headers: {
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
      },
      signal: controller.signal,
    });
    const html = await resp.text();
    // Fast-path check: WeChat anti-bot interstitial.
    if (/环境异常|verify_identity|weixin\.qq\.com\/cgi-bin\/readtemplate/.test(html)) {
      return { error: 'anti_bot', preview: html.slice(0, 200) };
    }
    // biz: base64 string ending in "==" or a hex-ish token.
    const bizMatch =
      html.match(/var\s+biz\s*=\s*["']([^"']+?)["']/i) ||
      html.match(/__biz=([^&"'\s]+)/i);
    const titleMatch = html.match(/<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i);
    const coverMatch = html.match(/<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i);
    const descMatch = html.match(/<meta[^>]+name=["']description["'][^>]+content=["']([^"']+)["']/i);
    if (!bizMatch) return { error: 'no_biz_in_html' };
    return {
      id: bizMatch[1],
      title: titleMatch ? titleMatch[1] : '',
      cover: coverMatch ? coverMatch[1] : '',
      intro: descMatch ? descMatch[1] : '',
    };
      } catch (err) {
    return { error: `fetch_failed: ${err.message}` };
  } finally {
    clearTimeout(timer);
  }
}

function upsertFeedRecord(mp) {
  const id = String(mp.id);
  let feed = db.feeds.find((f) => f.id === id);
  if (!feed) {
    feed = {
      id,
      mpName: mp.name || '',
      mpCover: mp.cover || '',
      mpIntro: mp.intro || '',
      updateTime: mp.updateTime || Math.floor(Date.now() / 1000),
      syncTime: 0,
      hasHistory: 1,
      status: statusMap.ENABLE,
      createdAt: Math.floor(Date.now() / 1000),
    };
    db.feeds.push(feed);
  } else {
    Object.assign(feed, {
      mpName: mp.name || feed.mpName,
      mpCover: mp.cover || feed.mpCover,
      mpIntro: mp.intro || feed.mpIntro,
      updateTime: mp.updateTime || feed.updateTime,
    });
  }
  return feed;
}

function articleCount(mpId) {
  return db.articles.filter((a) => a.mpId === mpId).length;
}

function serializeFeed(feed) {
  return { ...feed, articleCount: articleCount(feed.id) };
}

// ---------------------------------------------------------------------------
// Static frontend
// ---------------------------------------------------------------------------
app.get('/', (_req, res) => {
  res.sendFile(path.join(__dirname, 'frontend.html'));
});

// ---------------------------------------------------------------------------
// Login: real QR via wewe-rss gateway
// ---------------------------------------------------------------------------
app.get('/api/wechat-qr', async (_req, res) => {
  try {
    const { uuid, scanUrl } = await svc.createLoginUrl();
    if (!uuid || !scanUrl) throw new Error(`bad response from ${PLATFORM_URL}`);

    loginSessions.set(uuid, { status: 'pending' });

    (async () => {
      const deadline = Date.now() + 5 * 60 * 1000;
      while (Date.now() < deadline) {
        try {
          const result = await svc.getLoginResult(uuid);
          if (result && result.token && result.vid !== undefined) {
            const vid = String(result.vid);
            upsertAccount({
              id: vid,
              token: result.token,
              name: result.username || `user-${vid}`,
            });
            loginSessions.set(uuid, {
              status: 'success',
              vid,
              token: result.token,
              username: result.username,
            });
            return;
          }
          await new Promise((r) => setTimeout(r, 1500));
        } catch (err) {
          console.error(`[server] login poll failed for uuid=${uuid}:`, err.message);
          loginSessions.set(uuid, { status: 'error', error: err.message });
          return;
        }
      }
      if (loginSessions.get(uuid)?.status === 'pending') {
        loginSessions.set(uuid, { status: 'error', error: 'QR expired' });
      }
    })();

    res.json({ uuid, scanUrl });
  } catch (err) {
    console.error('[server] createLoginUrl failed:', err.message);
    res.status(502).json({ error: `upstream login failed: ${err.message}` });
  }
});

app.get('/api/wechat-login-status', (req, res) => {
    const { uuid } = req.query;
    const session = loginSessions.get(uuid);
    if (!session) return res.json({ message: 'not_found' });
  if (session.status === 'pending') return res.json({ message: 'waiting' });
  if (session.status === 'error') {
    return res.status(400).json({ message: 'error', error: session.error });
  }
  const { vid, token, username } = session;
  res.json({ message: 'success', vid, token, username });
});

// ---------------------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------------------
app.get('/api/wechat-accounts', (req, res) => {
  if (!requireAuth(req, res)) return;
  const blocked = new Set(svc.getBlockedAccountIds());
  res.json(
    db.accounts.map(({ id, name, status }) => ({
      id,
      name,
      status,
      blockedToday: blocked.has(id),
    })),
  );
});

// Clear today's account block list so every account becomes eligible again.
// Useful after adding a new account or when you believe the gateway has
// cooled off a previously-blocked one.
app.post('/api/wechat-accounts/clear-block', (req, res) => {
  if (!requireAuth(req, res)) return;
  svc.clearBlockedAccounts();
  res.json({ ok: true });
});

// ---------------------------------------------------------------------------
// Official accounts (mps) — the wewe-rss flow
// ---------------------------------------------------------------------------

// Resolve an mp.weixin.qq.com/s/... link, save the mp as a feed, then pull
// history. This is the exact pattern used by wewe-rss's "添加公众号" button.
app.post('/api/mps', async (req, res) => {
  if (!requireAuth(req, res)) return;
  const wxsLink = (req.body && (req.body.wxsLink || req.body.url)) || '';

  if (!/^https:\/\/mp\.weixin\.qq\.com\/s\//.test(wxsLink)) {
    return res
      .status(400)
      .json({ error: 'wxsLink must start with https://mp.weixin.qq.com/s/' });
  }

  try {
    const resolved = await svc.getMpInfo(wxsLink);
    const mps = Array.isArray(resolved) ? resolved : [resolved].filter(Boolean);
    if (mps.length === 0) {
      return res.status(502).json({ error: 'gateway returned no mp info' });
    }

    const savedFeeds = [];
    const warnings = [];
    for (const mp of mps) {
      let finalMp = mp;

      // The upstream gateway sometimes returns a synthetic `MP_WXS_<digits>`
      // id. The digits are the base64-decoded real biz, so we can recover
      // it offline in one line. Fall back to HTML scraping only if the
      // deterministic decode fails (shouldn't happen on the current
      // gateway, but guards against future schema drift).
      if (/^MP_WXS_\d+$/.test(String(mp.id))) {
        const realBiz = placeholderToRealBiz(mp.id);
        if (realBiz) {
          console.log(
            `[server] recovered real biz ${realBiz} from placeholder ${mp.id}`,
          );
          finalMp = {
            id: realBiz,
            name: mp.name || '',
            cover: mp.cover || '',
            intro: mp.intro || '',
            updateTime: mp.updateTime,
          };
        } else {
          const extracted = await resolveBizFromShareUrl(wxsLink);
          if (extracted.id) {
            console.log(
              `[server] recovered real biz ${extracted.id} by scraping share URL`,
            );
            finalMp = {
              id: extracted.id,
              name: extracted.title || mp.name || '',
              cover: extracted.cover || mp.cover || '',
              intro: extracted.intro || mp.intro || '',
              updateTime: mp.updateTime,
            };
          } else {
            warnings.push({
              mpId: String(mp.id),
              message:
                `Gateway returned a placeholder id and the article page couldn't be parsed ` +
                `(${extracted.error || 'unknown'}). Use "Add by known official-account ID" ` +
                `below to enter the biz id directly.`,
            });
          }
        }
      }

      const feed = upsertFeedRecord(finalMp);
      savedFeeds.push(feed);
    }

    // Only auto-backfill when every resolved id looks real. Otherwise the
    // background loop would just spam WeReadError400. The client can still
    // click "Sync" / "Full history" manually.
    if (warnings.length === 0) {
      (async () => {
        for (const feed of savedFeeds) {
          try {
            await svc.getHistoryMpArticles(feed.id);
          } catch (err) {
            console.error(
              `[server] history fetch for mp=${feed.id} failed:`,
              err.message,
            );
          }
        }
      })();
    }

    res.json({ feeds: savedFeeds.map(serializeFeed), warnings });
  } catch (err) {
    if (err instanceof WeReadPoolEmptyError) {
      return res.status(502).json({
        error: 'pool_exhausted',
        message: err.message,
        pool: { total: err.total, blockedToday: err.blocked },
      });
    }
    if (err instanceof WeReadSessionError) {
      return res.status(401).json({ error: 'session_expired', message: err.message });
    }
    console.error('[server] getMpInfo failed:', err.message);
    res.status(502).json({ error: err.message });
  }
});

app.get('/api/mps', (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json(db.feeds.map(serializeFeed));
});

app.post('/api/mps/:mpId/sync', async (req, res) => {
  if (!requireAuth(req, res)) return;
  let { mpId } = req.params;
  let feed = db.feeds.find((f) => f.id === mpId);
  if (!feed) return res.status(404).json({ error: 'mp not found' });

  // Auto-migrate a placeholder id that was saved before the fix landed.
  if (/^MP_WXS_\d+$/.test(mpId)) {
    const realBiz = placeholderToRealBiz(mpId);
    if (realBiz) {
      console.log(`[server] migrating placeholder ${mpId} -> ${realBiz}`);
      // Re-key the feed and any cached articles.
      feed.id = realBiz;
      for (const a of db.articles) {
        if (a.mpId === mpId) a.mpId = realBiz;
      }
      mpId = realBiz;
    }
  }

  try {
    const { history } = req.query;
    if (history === '1' || history === 'true') {
      await svc.getHistoryMpArticles(mpId);
    } else {
      await svc.refreshMpArticlesAndUpdateFeed(mpId);
    }
    res.json(serializeFeed(feed));
  } catch (err) {
    if (err instanceof WeReadPoolEmptyError) {
      return res.status(502).json({
        error: 'pool_exhausted',
        message: err.message,
        pool: { total: err.total, blockedToday: err.blocked },
      });
    }
    if (err instanceof WeReadSessionError) {
      return res.status(401).json({ error: 'session_expired', message: err.message });
    }
    const msg = err.upstreamMessage || err.message;
    if (/WeReadError400/.test(msg) && /^MP_WXS_\d+$/.test(mpId)) {
      return res.status(400).json({
        error: 'placeholder_mpid',
        message:
          `mpId "${mpId}" is a gateway placeholder and cannot be fetched. ` +
          `Delete it and add a different article URL from the same official account.`,
      });
    }
    if (/WeReadError400/.test(msg)) {
      // The gateway rejected every account in the pool. This is the normal
      // failure mode when you only have one account: that account's WeRead
      // session on weread.111965.xyz is rate-limited / not privileged for
      // this公众号. Telling the user to add another account matches
      // wewe-rss's own multi-account design.
      const blocked = svc.getBlockedAccountIds();
      return res.status(502).json({
        error: 'pool_exhausted',
        message:
          `Upstream gateway rejected every account in your pool with ` +
          `WeReadError400. Log in with one or more additional WeChat ` +
          `accounts ("Add another account" on the login card) and try ` +
          `again — the gateway rotates requests across the pool, so ` +
          `having 2–3 accounts dramatically improves success rates.`,
        upstream: msg,
        pool: {
          total: db.accounts.length,
          blockedToday: blocked.length,
        },
      });
    }
    console.error(`[server] sync mp=${mpId} failed:`, msg);
    res.status(502).json({ error: msg });
  }
});

// Diagnostic / recovery: given a mp.weixin.qq.com/s/ URL, return what our
// in-process biz extractor sees (useful when the gateway returned a
// placeholder and you want to verify the real biz id before adding it).
app.post('/api/mps/resolve-share-url', async (req, res) => {
  if (!requireAuth(req, res)) return;
  const wxsLink = (req.body && (req.body.wxsLink || req.body.url)) || '';
  if (!/^https:\/\/mp\.weixin\.qq\.com\/s\//.test(wxsLink)) {
    return res
      .status(400)
      .json({ error: 'wxsLink must start with https://mp.weixin.qq.com/s/' });
  }
  const extracted = await resolveBizFromShareUrl(wxsLink);
  res.json(extracted);
});

// Manual path: add an mp by known biz id (for users who already know the
// official-account ID and want to skip wxs2mp resolution entirely).
app.post('/api/mps/by-id', async (req, res) => {
  if (!requireAuth(req, res)) return;
  const id = (req.body && (req.body.mpId || req.body.id) || '').trim();
  const name = (req.body && req.body.name) || '';
  if (!id) return res.status(400).json({ error: 'mpId required' });
  if (/^MP_WXS_\d+$/.test(id)) {
    return res
      .status(400)
      .json({ error: 'placeholder_mpid', message: 'That id looks like a gateway placeholder.' });
  }
  const feed = upsertFeedRecord({ id, name, cover: '', intro: '' });
  res.json(serializeFeed(feed));
});

app.post('/api/mps/sync-all', async (req, res) => {
  if (!requireAuth(req, res)) return;
  try {
    await svc.refreshAllMpArticlesAndUpdateFeed();
    res.json({ feeds: db.feeds.map(serializeFeed) });
  } catch (err) {
    console.error('[server] sync-all failed:', err.message);
    res.status(502).json({ error: err.message });
  }
});

app.delete('/api/mps/:mpId', (req, res) => {
  if (!requireAuth(req, res)) return;
  const { mpId } = req.params;
  db.feeds = db.feeds.filter((f) => f.id !== mpId);
  db.articles = db.articles.filter((a) => a.mpId !== mpId);
  res.json({ ok: true });
});

// ---------------------------------------------------------------------------
// Articles
// ---------------------------------------------------------------------------
app.get('/api/articles', (req, res) => {
  if (!requireAuth(req, res)) return;
  const { mpId } = req.query;
  let list = mpId ? db.articles.filter((a) => a.mpId === mpId) : db.articles;
  list = [...list].sort((a, b) => (b.publishTime || 0) - (a.publishTime || 0));
  res.json(list);
});

// Back-compat alias used by the original frontend
app.get('/api/wechat-articles', async (req, res) => {
  if (!requireAuth(req, res)) return;
  const { mpId, history } = req.query;
  if (!mpId) return res.status(400).json({ error: 'mpId required' });
  try {
    if (history === '1' || history === 'true') {
      await svc.getHistoryMpArticles(mpId);
    } else {
      await svc.refreshMpArticlesAndUpdateFeed(mpId);
    }
    res.json(db.articles.filter((a) => a.mpId === mpId));
  } catch (err) {
    if (err instanceof WeReadPoolEmptyError) {
      return res.status(502).json({
        error: 'pool_exhausted',
        message: err.message,
        pool: { total: err.total, blockedToday: err.blocked },
      });
    }
    if (err instanceof WeReadSessionError) {
      return res.status(401).json({ error: 'session_expired', message: err.message });
    }
    console.error('[server] /api/wechat-articles failed:', err.message);
    res.status(502).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Test frontend running at http://localhost:${PORT}`);
  console.log(`Using WeRead gateway: ${PLATFORM_URL}`);
});
