"""
WeChat / WeRead API — 1:1 port of test/python/main.py routes, adapted to GEB.

All routes are user-scoped via the standard GEB JWT bearer auth
(`get_current_user`). Data is persisted via AppRepository: Supabase REST when
SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set, else SQLAlchemy (DATABASE_URL / SQLite).

Routes (prefix /api/wechat):
  GET    /qr                        -> start WeChat QR login (no auth)
  GET    /login-status?uuid=...     -> poll login status      (no auth)
  GET    /accounts                  -> list user's WeRead pool
  POST   /accounts/clear-block      -> clear today's block list
  POST   /mps                       -> add an Official Account via a wxs link
  GET    /mps                       -> list subscribed Official Accounts
  POST   /mps/{mp_id}/sync          -> refresh latest page (or full history with ?history=1)
  POST   /mps/resolve-share-url     -> resolve biz id by scraping article HTML
  POST   /mps/by-id                 -> add MP by known biz id
  POST   /mps/sync-all              -> refresh every subscribed MP
  DELETE /mps/{mp_id}               -> unsubscribe + drop cached articles
  GET    /articles?mpId=...         -> read cached articles (optionally filtered)
  GET    /wechat-articles?mpId=...  -> refresh then return (mirrors old UI hook)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from ..core.deps import get_current_user
from ..db.app_repository import AppRepository, ArticleRow, FeedRow, get_repo
from ..services.weread_service import (
    WeReadPoolEmptyError,
    WeReadRequestError,
    WeReadService,
    WeReadSessionError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wechat", tags=["wechat"])


# --- image proxy ---------------------------------------------------------- #
# WeChat's image CDN (mmbiz.qpic.cn, wx.qlogo.cn) checks the Referer header
# and serves a hotlink-protection placeholder ("未经允许不可引用") to any origin
# that isn't mp.weixin.qq.com. We proxy through the backend with the correct
# Referer so browsers can display thumbnails in our feed UI.
_IMG_ALLOWED_HOSTS = {
    "mmbiz.qpic.cn",
    "mmbiz.qlogo.cn",
    "wx.qlogo.cn",
    "wx1.sinaimg.cn",
    "wx2.sinaimg.cn",
    "thirdwx.qlogo.cn",
    "thirdwx.qpic.cn",
    "mp.weixin.qq.com",
    "res.wx.qq.com",
}


def _proxy_image_host_allowed(host: str) -> bool:
    """Tencent CDNs use many subdomains (mmbiz*, thirdwx*, …). Allow explicit list + *.qpic.cn / *.qlogo.cn."""
    h = (host or "").lower().rstrip(".")
    if not h:
        return False
    if any(h == root or h.endswith("." + root) for root in _IMG_ALLOWED_HOSTS):
        return True
    # New shard hostnames appear often; both suffixes are controlled by Tencent.
    return h.endswith(".qpic.cn") or h.endswith(".qlogo.cn")


@router.get("/img")
async def proxy_wechat_image(url: str = Query(..., min_length=8, max_length=2048)):
    """Unauthenticated image proxy for WeChat CDN images.

    Browsers can't set a custom Referer from `<img src>`, and mmbiz.qpic.cn
    serves a placeholder image ("Image sourced from WeChat Official Accounts
    Platform / Unauthorized use is prohibited") unless the Referer is a
    WeChat domain. We fetch server-side with the right header, then stream
    the bytes back with an aggressive cache so repeat views are free.
    """
    from urllib.parse import urlparse

    if not url.startswith(("http://", "https://")):
        return Response(status_code=400, content=b"bad url")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not _proxy_image_host_allowed(host):
        logger.info("wechat/img rejected host=%s url_prefix=%s", host, url[:80])
        return Response(
            status_code=400,
            content=f"host not allowed: {host}".encode(),
            media_type="text/plain",
        )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
            "MicroMessenger/8.0.45(0x18002d2f) NetType/WIFI Language/zh_CN"
        ),
        "Referer": "https://mp.weixin.qq.com/",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0), follow_redirects=True
        ) as client:
            upstream = await client.get(url, headers=headers)
    except httpx.RequestError as err:
        logger.info("wechat/img upstream error: %s", err)
        return Response(status_code=502, content=b"upstream error")

    if upstream.status_code != 200:
        return Response(status_code=upstream.status_code, content=b"")

    content_type = upstream.headers.get("content-type", "image/jpeg")
    return Response(
        content=upstream.content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


# --- in-memory login session tracking (process-scoped) -------------------- #
# Tracks only the transient QR-login polling state. Successful logins are
# persisted to the database as WeReadAccount rows.
login_sessions: dict[str, dict[str, Any]] = {}


# --- pydantic bodies ------------------------------------------------------ #


class MpAddBody(BaseModel):
    wxsLink: Optional[str] = None
    url: Optional[str] = None


# Zero-width / control characters that frequently sneak in from chat apps
# (WeChat "Copy link" on iOS, Telegram, Slack, etc.). These pass `.strip()`
# but break a plain `str.startswith` / regex check.
_INVISIBLE_CHARS = (
    "\u200b"  # zero-width space
    "\u200c"  # zero-width non-joiner
    "\u200d"  # zero-width joiner
    "\u200e"  # LTR mark
    "\u200f"  # RTL mark
    "\ufeff"  # BOM
    "\u202a\u202b\u202c\u202d\u202e"  # bidi overrides
    "\xa0"    # non-breaking space
)


def _clean_wxs_link(raw: Optional[str]) -> str:
    """Normalize a pasted WeChat share URL.

    - strip whitespace
    - remove zero-width / bidi / BOM characters
    - strip wrapping quotes, backticks, angle brackets
    - trim trailing punctuation like ')', ']', ','
    """
    if not raw:
        return ""
    s = raw.strip()
    for ch in _INVISIBLE_CHARS:
        s = s.replace(ch, "")
    # Strip one layer of wrapping quotes / brackets
    while s and s[0] in "\"'`<([":
        s = s[1:].lstrip()
    while s and s[-1] in "\"'`>)],.;":
        s = s[:-1].rstrip()
    return s


class MpByIdBody(BaseModel):
    mpId: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = ""


# --- helpers -------------------------------------------------------------- #


def _svc(request: Request) -> WeReadService:
    svc = getattr(request.app.state, "weread_service", None)
    if svc is None:
        raise RuntimeError(
            "WeReadService not initialised. Ensure lifespan handler ran."
        )
    return svc


def _http(request: Request) -> httpx.AsyncClient:
    client = getattr(request.app.state, "weread_http", None)
    if client is None:
        raise RuntimeError("WeRead http client not initialised.")
    return client


async def _resolve_biz_from_share_url(
    wxs_link: str, client: httpx.AsyncClient
) -> dict:
    ua = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
        "MicroMessenger/8.0.42(0x18002a2c) NetType/WIFI Language/zh_CN"
    )
    try:
        resp = await client.get(
            wxs_link,
            headers={
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            timeout=10.0,
            follow_redirects=True,
        )
        html = resp.text
        if re.search(
            r"环境异常|verify_identity|weixin\.qq\.com/cgi-bin/readtemplate", html
        ):
            return {"error": "anti_bot", "preview": html[:200]}
        biz_m = re.search(
            r'var\s+biz\s*=\s*["\']([^"\']+?)["\']', html, re.I
        ) or re.search(r"__biz=([^&\"'\s]+)", html, re.I)
        title_m = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.I,
        )
        cover_m = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.I,
        )
        desc_m = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.I,
        )
        if not biz_m:
            return {"error": "no_biz_in_html"}
        return {
            "id": biz_m.group(1),
            "title": title_m.group(1) if title_m else "",
            "cover": cover_m.group(1) if cover_m else "",
            "intro": desc_m.group(1) if desc_m else "",
        }
    except Exception as e:
        return {"error": f"fetch_failed: {e}"}


def _serialize_feed(repo: AppRepository, feed: FeedRow) -> dict:
    return {
        "id": feed.mp_id,
        "mpName": feed.mp_name or "",
        "mpCover": feed.mp_cover or "",
        "mpIntro": feed.mp_intro or "",
        "updateTime": feed.update_time or 0,
        "syncTime": feed.sync_time or 0,
        "hasHistory": feed.has_history,
        "status": feed.status,
        "createdAt": int(feed.created_at.timestamp()) if feed.created_at else 0,
        "articleCount": repo.weread_article_count_for_feed(feed.id),
    }


def _serialize_article(
    a: ArticleRow,
    *,
    liked: bool = False,
    bookmarked: bool = False,
) -> dict:
    return {
        "id": a.article_id,
        "mpId": a.mp_id,
        "title": a.title,
        "picUrl": a.pic_url,
        "publishTime": a.publish_time,
        "liked": liked,
        "bookmarked": bookmarked,
    }


# =========================================================================
# Login (public)
# =========================================================================


@router.get("/qr")
async def wechat_qr(request: Request):
    """Start a WeChat QR-code login. Returns {uuid, scanUrl} — the client
    renders the QR from scanUrl (qrcodejs or similar). Poll /login-status.

    When the user scans + confirms, the login completes *server-side* and the
    WeRead token is attached to the currently authenticated GEB user. If no
    GEB user is logged in when /login-status resolves, the raw token is also
    returned so the client can attach it later.
    """
    svc = _svc(request)
    try:
        data = await svc.create_login_url()
        uuid, scan_url = data.get("uuid"), data.get("scanUrl")
        if not uuid or not scan_url:
            raise RuntimeError("bad response from WeRead platform")
        login_sessions[uuid] = {"status": "pending"}

        async def poll():
            deadline = time.time() + 5 * 60
            while time.time() < deadline:
                try:
                    result = await svc.get_login_result(uuid)
                    if result and result.get("token") and result.get("vid") is not None:
                        login_sessions[uuid] = {
                            "status": "success",
                            "vid": str(result["vid"]),
                            "token": result["token"],
                            "username": result.get("username"),
                        }
                        return
                    await asyncio.sleep(1.5)
                except Exception as err:
                    logger.error("login poll failed for uuid=%s: %s", uuid, err)
                    login_sessions[uuid] = {"status": "error", "error": str(err)}
                    return
            if login_sessions.get(uuid, {}).get("status") == "pending":
                login_sessions[uuid] = {"status": "error", "error": "QR expired"}

        asyncio.create_task(poll())
        return {"uuid": uuid, "scanUrl": scan_url}
    except Exception as err:
        logger.error("createLoginUrl failed: %s", err)
        return JSONResponse(
            status_code=502,
            content={"error": f"upstream login failed: {err}"},
        )


@router.get("/login-status")
async def wechat_login_status(
    uuid: str,
    current_user: Optional[dict] = Depends(
        lambda: None  # auth is *optional* here
    ),
    repo: AppRepository = Depends(get_repo),
    request: Request = None,
):
    """Poll WeChat QR login. If a GEB user is authenticated (Bearer token)
    and login succeeded, the WeRead session is persisted to that user's pool.

    This endpoint accepts an optional Authorization header so the frontend can
    call it both before *and* after GEB login. When unauthenticated, the raw
    {vid, token, username} is returned for the client to attach later.
    """
    session = login_sessions.get(uuid)
    if not session:
        return {"message": "not_found"}
    if session["status"] == "pending":
        return {"message": "waiting"}
    if session["status"] == "error":
        return JSONResponse(
            status_code=400,
            content={"message": "error", "error": session.get("error")},
        )

    # success — try to attach to a GEB user if bearer token is present
    payload = {
        "message": "success",
        "vid": session["vid"],
        "token": session["token"],
        "username": session.get("username"),
    }

    # Opportunistic attachment: if Authorization header decodes to a user,
    # persist the WeRead account for that user automatically.
    if request is not None:
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            from ..core.security import decode_access_token
            try:
                token_payload = decode_access_token(auth.split(" ", 1)[1])
                uid_raw = token_payload.get("user_id") or token_payload.get("sub")
                if uid_raw:
                    user_id = int(uid_raw)
                    repo.weread_account_upsert(
                        user_id=user_id,
                        vid=session["vid"],
                        token=session["token"],
                        name=session.get("username") or f"user-{session['vid']}",
                    )
                    payload["attached"] = True
            except Exception as e:
                logger.debug("login-status: could not attach to user: %s", e)

    return payload


# =========================================================================
# Accounts (authenticated)
# =========================================================================


@router.get("/accounts")
async def list_accounts(
    request: Request,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    svc = _svc(request)
    blocked = set(svc.get_blocked_account_ids())
    rows = repo.weread_accounts_list_for_ui(int(current_user["sub"]))
    return [
        {
            "id": r["vid"],
            "name": r.get("name"),
            "status": r["status"],
            "blockedToday": r["vid"] in blocked,
        }
        for r in rows
    ]


@router.post("/accounts/clear-block")
async def clear_block(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    svc = _svc(request)
    svc.clear_blocked_accounts()
    return {"ok": True}


@router.delete("/accounts/{vid}")
async def delete_account(
    vid: str,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    user_id = int(current_user["sub"])
    if not repo.weread_account_delete(user_id, vid):
        return JSONResponse(status_code=404, content={"error": "account not found"})
    return {"ok": True}


# =========================================================================
# Official Accounts (MPs) / Feeds
# =========================================================================


@router.post("/mps")
async def add_mp(
    body: MpAddBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    svc = _svc(request)
    user_id = int(current_user["sub"])
    raw_link = body.wxsLink or body.url or ""
    wxs_link = _clean_wxs_link(raw_link)
    logger.info(
        "POST /mps received wxsLink len=%d repr=%r normalized=%r",
        len(raw_link or ""),
        (raw_link or "")[:300],
        wxs_link[:300],
    )
    if not re.match(r"^https://mp\.weixin\.qq\.com/s/", wxs_link):
        return JSONResponse(
            status_code=400,
            content={
                "error": "wxsLink must start with https://mp.weixin.qq.com/s/",
                "received": raw_link[:200],
                "normalized": wxs_link[:200],
                "received_repr": repr(raw_link)[:300],
            },
        )
    # ----------------------------------------------------------------------
    # 1:1 port of wewe-rss's add-feed flow:
    #   apps/server/src/trpc/trpc.service.ts   getMpInfo()
    #   apps/web/src/pages/feeds/index.tsx     handleConfirm()
    #
    #   res = await getMpInfo({ wxsLink: link })
    #   if res[0]:
    #     await addFeed({ id: item.id, mpName, mpCover, mpIntro, updateTime })
    #     await refreshMpArticles({ mpId: item.id })   // sync page 1
    #   else:
    #     toast.error('添加失败', { description: '请检查链接是否正确' })
    #
    # Whatever id the gateway returns is stored verbatim — including the
    # "MP_WXS_<digits>" placeholder form. wewe-rss does not do any placeholder
    # detection, HTML scraping fallback, or __biz derivation.
    # ----------------------------------------------------------------------
    try:
        resolved = await svc.get_mp_info(repo, user_id, wxs_link)
        mps = resolved if isinstance(resolved, list) else [resolved]
        mps = [x for x in mps if x]
        if not mps:
            return JSONResponse(
                status_code=400,
                content={"error": "添加失败", "message": "请检查链接是否正确"},
            )

        saved_feeds: list[FeedRow] = []
        for mp in mps:
            feed = repo.weread_feed_upsert(user_id, mp)
            saved_feeds.append(feed)
            try:
                await svc.refresh_mp_articles_and_update_feed(
                    repo, user_id, feed.mp_id
                )
            except Exception as err:
                logger.error("refresh on add mp=%s failed: %s", feed.mp_id, err)

        return {"feeds": [_serialize_feed(repo, f) for f in saved_feeds]}
    except WeReadPoolEmptyError as err:
        return JSONResponse(
            status_code=502,
            content={
                "error": "pool_exhausted",
                "message": str(err),
                "pool": {"total": err.total, "blockedToday": err.blocked},
            },
        )
    except WeReadSessionError as err:
        return JSONResponse(
            status_code=401,
            content={"error": "session_expired", "message": str(err)},
        )
    except Exception as err:
        logger.error("getMpInfo failed: %s", err)
        return JSONResponse(status_code=502, content={"error": str(err)})


@router.get("/mps")
async def list_mps(
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    user_id = int(current_user["sub"])
    feeds = repo.weread_feed_list_user(user_id)
    return [_serialize_feed(repo, f) for f in feeds]


@router.post("/mps/{mp_id}/sync")
async def sync_mp(
    mp_id: str,
    request: Request,
    history: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    svc = _svc(request)
    user_id = int(current_user["sub"])
    feed = repo.weread_feed_get(user_id, mp_id)
    if not feed:
        return JSONResponse(status_code=404, content={"error": "mp not found"})

    try:
        if history in ("1", "true"):
            await svc.get_history_mp_articles(repo, user_id, mp_id)
        else:
            await svc.refresh_mp_articles_and_update_feed(repo, user_id, mp_id)
        feed = repo.weread_feed_get(user_id, mp_id) or feed
        return _serialize_feed(repo, feed)
    except WeReadPoolEmptyError as err:
        return JSONResponse(
            status_code=502,
            content={
                "error": "pool_exhausted",
                "message": str(err),
                "pool": {"total": err.total, "blockedToday": err.blocked},
            },
        )
    except WeReadSessionError as err:
        return JSONResponse(
            status_code=401,
            content={"error": "session_expired", "message": str(err)},
        )
    except WeReadRequestError as err:
        msg = err.upstream_message or str(err)
        logger.error("sync mp=%s failed: %s", mp_id, msg)
        return JSONResponse(status_code=502, content={"error": msg})
    except Exception as err:
        msg = getattr(err, "upstream_message", None) or str(err)
        logger.error("sync mp=%s failed: %s", mp_id, msg)
        return JSONResponse(status_code=502, content={"error": msg})


@router.post("/mps/resolve-share-url")
async def resolve_share(
    body: MpAddBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    raw_link = body.wxsLink or body.url or ""
    wxs_link = _clean_wxs_link(raw_link)
    if not re.match(r"^https://mp\.weixin\.qq\.com/s/", wxs_link):
        return JSONResponse(
            status_code=400,
            content={
                "error": "wxsLink must start with https://mp.weixin.qq.com/s/",
                "received": raw_link[:200],
                "normalized": wxs_link[:200],
            },
        )
    return await _resolve_biz_from_share_url(wxs_link, _http(request))


@router.post("/mps/by-id")
async def mps_by_id(
    body: MpByIdBody,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    user_id = int(current_user["sub"])
    mid = str(body.mpId or body.id or "").strip()
    if not mid:
        return JSONResponse(status_code=400, content={"error": "mpId required"})
    if re.match(r"^MP_WXS_\d+$", mid):
        return JSONResponse(
            status_code=400,
            content={
                "error": "placeholder_mpid",
                "message": "That id looks like a gateway placeholder.",
            },
        )
    feed = repo.weread_feed_upsert(
        user_id, {"id": mid, "name": body.name or "", "cover": "", "intro": ""}
    )
    return _serialize_feed(repo, feed)


@router.post("/mps/sync-all")
async def sync_all(
    request: Request,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    svc = _svc(request)
    user_id = int(current_user["sub"])
    try:
        await svc.refresh_all_mp_articles_and_update_feed(repo, user_id)
        feeds = repo.weread_feed_list_user(user_id)
        return {"feeds": [_serialize_feed(repo, f) for f in feeds]}
    except Exception as err:
        logger.error("sync-all failed: %s", err)
        return JSONResponse(status_code=502, content={"error": str(err)})


@router.delete("/mps/{mp_id}")
async def delete_mp(
    mp_id: str,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    user_id = int(current_user["sub"])
    repo.weread_feed_delete_cascade(user_id, mp_id)
    return {"ok": True}


# =========================================================================
# Articles
# =========================================================================


@router.get("/articles")
async def articles(
    mpId: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    user_id = int(current_user["sub"])
    liked_ids = set(repo.like_list_article_ids(user_id))
    bookmarked_ids = set(repo.bookmark_list_article_ids(user_id))
    rows = repo.weread_articles_list_user(user_id, mpId)
    return [
        _serialize_article(
            a,
            liked=a.article_id in liked_ids,
            bookmarked=a.article_id in bookmarked_ids,
        )
        for a in rows
    ]


@router.get("/wechat-articles")
async def wechat_articles(
    mpId: str,
    request: Request,
    history: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    repo: AppRepository = Depends(get_repo),
):
    svc = _svc(request)
    user_id = int(current_user["sub"])
    if not mpId:
        return JSONResponse(status_code=400, content={"error": "mpId required"})
    try:
        if history in ("1", "true"):
            await svc.get_history_mp_articles(repo, user_id, mpId)
        else:
            await svc.refresh_mp_articles_and_update_feed(repo, user_id, mpId)
        liked_ids = set(repo.like_list_article_ids(user_id))
        bookmarked_ids = set(repo.bookmark_list_article_ids(user_id))
        rows = repo.weread_articles_list_user(user_id, mpId)
        return [
            _serialize_article(
                a,
                liked=a.article_id in liked_ids,
                bookmarked=a.article_id in bookmarked_ids,
            )
            for a in rows
        ]
    except WeReadPoolEmptyError as err:
        return JSONResponse(
            status_code=502,
            content={
                "error": "pool_exhausted",
                "message": str(err),
                "pool": {"total": err.total, "blockedToday": err.blocked},
            },
        )
    except WeReadSessionError as err:
        return JSONResponse(
            status_code=401,
            content={"error": "session_expired", "message": str(err)},
        )
    except Exception as err:
        logger.error("/wechat-articles failed: %s", err)
        return JSONResponse(status_code=502, content={"error": str(err)})
