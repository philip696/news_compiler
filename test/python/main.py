"""
FastAPI 1:1 port of test/server.js + test/wechat-service.js (same routes, JSON, status codes).
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Optional

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from weread_service import (
    ENABLE,
    WeReadPoolEmptyError,
    WeReadRequestError,
    WeReadService,
    WeReadSessionError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weread_api")

PORT = int(os.environ.get("PORT", "3100"))
PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://weread.111965.xyz")

db: dict[str, Any] = {"accounts": [], "feeds": [], "articles": []}
login_sessions: dict[str, dict] = {}
svc: Optional[WeReadService] = None


def _update_delay_ms() -> Optional[int]:
    if os.environ.get("UPDATE_DELAY_MS") is not None:
        return int(os.environ["UPDATE_DELAY_MS"])
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global svc
    timeout = httpx.Timeout(15.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        app.state.http = client
        svc = WeReadService(
            db,
            platform_url=PLATFORM_URL,
            client=client,
            update_delay_ms=_update_delay_ms(),
        )
        yield
        svc = None


app = FastAPI(title="WeWe-RSS test API (Python)", lifespan=lifespan)


class APIUnauthorized(Exception):
    """Same JSON as Node requireAuth: { \"error\": \"unauthorized\" }."""


@app.exception_handler(APIUnauthorized)
async def _unauthorized_handler(_request: Request, _exc: APIUnauthorized):
    return JSONResponse(status_code=401, content={"error": "unauthorized"})


def _require_auth(
    xid: Annotated[Optional[str], Header()] = None,
    token: Annotated[Optional[str], Header()] = None,
) -> dict:
    acc = next((a for a in db["accounts"] if a.get("token") == token or a.get("id") == xid), None)
    if not acc:
        raise APIUnauthorized()
    return acc


def _upsert_account(*, id: str, token: str, name: str, status: int = ENABLE) -> dict:
    for a in db["accounts"]:
        if a["id"] == id:
            a.update({"token": token, "name": name, "status": status})
            return a
    acc = {"id": id, "token": token, "name": name, "status": status}
    db["accounts"].append(acc)
    return acc


def placeholder_to_real_biz(mp_id: str) -> Optional[str]:
    m = re.match(r"^MP_WXS_(\d+)$", str(mp_id or ""))
    if not m:
        return None
    digits = m.group(1)
    b64 = base64.b64encode(digits.encode("utf-8")).decode("ascii")
    round_trip = base64.b64decode(b64.encode("ascii")).decode("utf-8")
    return b64 if round_trip == digits else None


async def resolve_biz_from_share_url(wxs_link: str, client: httpx.AsyncClient) -> dict:
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
            r"环境异常|verify_identity|weixin\.qq\.com/cgi-bin/readtemplate",
            html,
        ):
            return {"error": "anti_bot", "preview": html[:200]}
        biz_m = re.search(r'var\s+biz\s*=\s*["\']([^"\']+?)["\']', html, re.I) or re.search(
            r"__biz=([^&\"'\s]+)", html, re.I
        )
        title_m = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.I,
        )
        cover_m = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.I,
        )
        desc_m = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.I,
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


def _upsert_feed_record(mp: dict) -> dict:
    mid = str(mp["id"])
    feed = next((f for f in db["feeds"] if f["id"] == mid), None)
    if not feed:
        feed = {
            "id": mid,
            "mpName": mp.get("name") or "",
            "mpCover": mp.get("cover") or "",
            "mpIntro": mp.get("intro") or "",
            "updateTime": mp.get("updateTime") or int(time.time()),
            "syncTime": 0,
            "hasHistory": 1,
            "status": ENABLE,
            "createdAt": int(time.time()),
        }
        db["feeds"].append(feed)
    else:
        feed.update(
            {
                "mpName": mp.get("name") or feed.get("mpName"),
                "mpCover": mp.get("cover") or feed.get("mpCover"),
                "mpIntro": mp.get("intro") or feed.get("mpIntro"),
                "updateTime": mp.get("updateTime") or feed.get("updateTime"),
            }
        )
    return feed


def _article_count(mp_id: str) -> int:
    return len([a for a in db["articles"] if a.get("mpId") == mp_id])


def _serialize_feed(feed: dict) -> dict:
    return {**feed, "articleCount": _article_count(feed["id"])}


FRONTEND = Path(__file__).resolve().parent.parent / "frontend.html"


@app.get("/")
async def index():
    if not FRONTEND.is_file():
        return PlainTextResponse("frontend.html not found", status_code=404)
    return FileResponse(FRONTEND)


@app.get("/api/wechat-qr")
async def wechat_qr(request: Request):
    assert svc is not None
    try:
        data = await svc.create_login_url()
        uuid, scan_url = data.get("uuid"), data.get("scanUrl")
        if not uuid or not scan_url:
            raise RuntimeError(f"bad response from {PLATFORM_URL}")
        login_sessions[uuid] = {"status": "pending"}

        async def poll():
            deadline = time.time() + 5 * 60
            while time.time() < deadline:
                try:
                    result = await svc.get_login_result(uuid)
                    if result and result.get("token") and result.get("vid") is not None:
                        vid = str(result["vid"])
                        _upsert_account(
                            id=vid,
                            token=result["token"],
                            name=result.get("username") or f"user-{vid}",
                        )
                        login_sessions[uuid] = {
                            "status": "success",
                            "vid": vid,
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


@app.get("/api/wechat-login-status")
async def wechat_login_status(uuid: str):
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
    return {
        "message": "success",
        "vid": session["vid"],
        "token": session["token"],
        "username": session.get("username"),
    }


@app.get("/api/wechat-accounts")
async def wechat_accounts(_: dict = Depends(_require_auth)):
    assert svc is not None
    blocked = set(svc.get_blocked_account_ids())
    return [
        {
            "id": a["id"],
            "name": a.get("name"),
            "status": a.get("status"),
            "blockedToday": a["id"] in blocked,
        }
        for a in db["accounts"]
    ]


@app.post("/api/wechat-accounts/clear-block")
async def clear_block(_: dict = Depends(_require_auth)):
    assert svc is not None
    svc.clear_blocked_accounts()
    return {"ok": True}


@app.post("/api/mps")
async def post_mps(request: Request, _: dict = Depends(_require_auth)):
    assert svc is not None
    body = await request.json()
    wxs_link = (body or {}).get("wxsLink") or (body or {}).get("url") or ""
    if not re.match(r"^https://mp\.weixin\.qq\.com/s/", wxs_link):
        return JSONResponse(
            status_code=400,
            content={"error": "wxsLink must start with https://mp.weixin.qq.com/s/"},
        )
    try:
        resolved = await svc.get_mp_info(wxs_link)
        mps = resolved if isinstance(resolved, list) else [resolved]
        mps = [x for x in mps if x]
        if not mps:
            return JSONResponse(status_code=502, content={"error": "gateway returned no mp info"})

        saved_feeds = []
        warnings = []
        client: httpx.AsyncClient = request.app.state.http

        for mp in mps:
            final_mp = dict(mp)
            mpid = str(mp.get("id", ""))
            if re.match(r"^MP_WXS_\d+$", mpid):
                real_biz = placeholder_to_real_biz(mpid)
                if real_biz:
                    logger.info("[server] recovered real biz %s from placeholder %s", real_biz, mpid)
                    final_mp = {
                        "id": real_biz,
                        "name": mp.get("name") or "",
                        "cover": mp.get("cover") or "",
                        "intro": mp.get("intro") or "",
                        "updateTime": mp.get("updateTime"),
                    }
                else:
                    extracted = await resolve_biz_from_share_url(wxs_link, client)
                    if extracted.get("id"):
                        logger.info(
                            "[server] recovered real biz %s by scraping share URL",
                            extracted["id"],
                        )
                        final_mp = {
                            "id": extracted["id"],
                            "name": extracted.get("title") or mp.get("name") or "",
                            "cover": extracted.get("cover") or mp.get("cover") or "",
                            "intro": extracted.get("intro") or mp.get("intro") or "",
                            "updateTime": mp.get("updateTime"),
                        }
                    else:
                        warnings.append(
                            {
                                "mpId": mpid,
                                "message": (
                                    "Gateway returned a placeholder id and the article page couldn't be parsed "
                                    f"({extracted.get('error', 'unknown')}). Use \"Add by known official-account ID\" "
                                    "below to enter the biz id directly."
                                ),
                            }
                        )
            feed = _upsert_feed_record(final_mp)
            saved_feeds.append(feed)

        if not warnings:

            async def history_bg():
                for feed in saved_feeds:
                    try:
                        await svc.get_history_mp_articles(feed["id"])
                    except Exception as err:
                        logger.error("history fetch for mp=%s failed: %s", feed["id"], err)

            asyncio.create_task(history_bg())

        return {"feeds": [_serialize_feed(f) for f in saved_feeds], "warnings": warnings}
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


@app.get("/api/mps")
async def get_mps(_: dict = Depends(_require_auth)):
    return [_serialize_feed(f) for f in db["feeds"]]


@app.post("/api/mps/{mp_id}/sync")
async def sync_mp(mp_id: str, history: Optional[str] = None, _: dict = Depends(_require_auth)):
    assert svc is not None
    feed = next((f for f in db["feeds"] if f["id"] == mp_id), None)
    if not feed:
        return JSONResponse(status_code=404, content={"error": "mp not found"})

    if re.match(r"^MP_WXS_\d+$", mp_id):
        real_biz = placeholder_to_real_biz(mp_id)
        if real_biz:
            logger.info("[server] migrating placeholder %s -> %s", mp_id, real_biz)
            feed["id"] = real_biz
            for a in db["articles"]:
                if a.get("mpId") == mp_id:
                    a["mpId"] = real_biz
            mp_id = real_biz

    try:
        if history in ("1", "true"):
            await svc.get_history_mp_articles(mp_id)
        else:
            await svc.refresh_mp_articles_and_update_feed(mp_id)
        return _serialize_feed(feed)
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
        if re.search(r"WeReadError400", msg) and re.match(r"^MP_WXS_\d+$", mp_id):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "placeholder_mpid",
                    "message": (
                        f'mpId "{mp_id}" is a gateway placeholder and cannot be fetched. '
                        "Delete it and add a different article URL from the same official account."
                    ),
                },
            )
        if re.search(r"WeReadError400", msg):
            blocked = svc.get_blocked_account_ids()
            return JSONResponse(
                status_code=502,
                content={
                    "error": "pool_exhausted",
                    "message": (
                        "Upstream gateway rejected every account in your pool with "
                        'WeReadError400. Log in with one or more additional WeChat '
                        'accounts ("Add another account" on the login card) and try '
                        "again — the gateway rotates requests across the pool, so "
                        "having 2–3 accounts dramatically improves success rates."
                    ),
                    "upstream": msg,
                    "pool": {"total": len(db["accounts"]), "blockedToday": len(blocked)},
                },
            )
        logger.error("sync mp=%s failed: %s", mp_id, msg)
        return JSONResponse(status_code=502, content={"error": msg})
    except Exception as err:
        msg = getattr(err, "upstream_message", None) or str(err)
        logger.error("sync mp=%s failed: %s", mp_id, msg)
        return JSONResponse(status_code=502, content={"error": msg})


@app.post("/api/mps/resolve-share-url")
async def resolve_share(request: Request, _: dict = Depends(_require_auth)):
    body = await request.json()
    wxs_link = (body or {}).get("wxsLink") or (body or {}).get("url") or ""
    if not re.match(r"^https://mp\.weixin\.qq\.com/s/", wxs_link):
        return JSONResponse(
            status_code=400,
            content={"error": "wxsLink must start with https://mp.weixin.qq.com/s/"},
        )
    client: httpx.AsyncClient = request.app.state.http
    return await resolve_biz_from_share_url(wxs_link, client)


@app.post("/api/mps/by-id")
async def mps_by_id(request: Request, _: dict = Depends(_require_auth)):
    body = await request.json()
    mid = str((body or {}).get("mpId") or (body or {}).get("id") or "").strip()
    name = (body or {}).get("name") or ""
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
    feed = _upsert_feed_record({"id": mid, "name": name, "cover": "", "intro": ""})
    return _serialize_feed(feed)


@app.post("/api/mps/sync-all")
async def sync_all(_: dict = Depends(_require_auth)):
    assert svc is not None
    try:
        await svc.refresh_all_mp_articles_and_update_feed()
        return {"feeds": [_serialize_feed(f) for f in db["feeds"]]}
    except Exception as err:
        logger.error("sync-all failed: %s", err)
        return JSONResponse(status_code=502, content={"error": str(err)})


@app.delete("/api/mps/{mp_id}")
async def delete_mp(mp_id: str, _: dict = Depends(_require_auth)):
    db["feeds"] = [f for f in db["feeds"] if f["id"] != mp_id]
    db["articles"] = [a for a in db["articles"] if a.get("mpId") != mp_id]
    return {"ok": True}


@app.get("/api/articles")
async def articles(mpId: Optional[str] = None, _: dict = Depends(_require_auth)):
    lst = [a for a in db["articles"] if not mpId or a.get("mpId") == mpId]
    lst.sort(key=lambda a: a.get("publishTime") or 0, reverse=True)
    return lst


@app.get("/api/wechat-articles")
async def wechat_articles(mpId: str, history: Optional[str] = None, _: dict = Depends(_require_auth)):
    assert svc is not None
    if not mpId:
        return JSONResponse(status_code=400, content={"error": "mpId required"})
    try:
        if history in ("1", "true"):
            await svc.get_history_mp_articles(mpId)
        else:
            await svc.refresh_mp_articles_and_update_feed(mpId)
        return [a for a in db["articles"] if a.get("mpId") == mpId]
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
        logger.error("/api/wechat-articles failed: %s", err)
        return JSONResponse(status_code=502, content={"error": str(err)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
