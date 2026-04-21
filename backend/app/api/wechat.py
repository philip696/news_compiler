"""
WeChat / WeRead API — 1:1 port of test/python/main.py routes, adapted to GEB.

All routes are user-scoped via the standard GEB JWT bearer auth
(`get_current_user`). Data is persisted to the SQLAlchemy database
(Supabase PostgreSQL when DATABASE_URL is a postgres URL, else SQLite).

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
import base64
import logging
import re
import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..db.database import SessionLocal, get_db
from ..db.models import WeReadAccount, WeReadArticle, WeReadFeed
from ..services.weread_service import (
    ENABLE,
    WeReadPoolEmptyError,
    WeReadRequestError,
    WeReadService,
    WeReadSessionError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wechat", tags=["wechat"])


# --- in-memory login session tracking (process-scoped) -------------------- #
# Tracks only the transient QR-login polling state. Successful logins are
# persisted to the database as WeReadAccount rows.
login_sessions: dict[str, dict[str, Any]] = {}


# --- pydantic bodies ------------------------------------------------------ #


class MpAddBody(BaseModel):
    wxsLink: Optional[str] = None
    url: Optional[str] = None


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


def _placeholder_to_real_biz(mp_id: str) -> Optional[str]:
    m = re.match(r"^MP_WXS_(\d+)$", str(mp_id or ""))
    if not m:
        return None
    digits = m.group(1)
    b64 = base64.b64encode(digits.encode("utf-8")).decode("ascii")
    round_trip = base64.b64decode(b64.encode("ascii")).decode("utf-8")
    return b64 if round_trip == digits else None


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


def _upsert_account_row(
    db: Session, *, user_id: int, vid: str, token: str, name: str
) -> WeReadAccount:
    acc = (
        db.query(WeReadAccount)
        .filter(WeReadAccount.user_id == user_id, WeReadAccount.vid == vid)
        .first()
    )
    if acc:
        acc.token = token
        acc.name = name
        acc.status = ENABLE
    else:
        acc = WeReadAccount(
            user_id=user_id, vid=vid, token=token, name=name, status=ENABLE
        )
        db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


def _upsert_feed_record(
    db: Session, user_id: int, mp: dict
) -> WeReadFeed:
    mid = str(mp["id"])
    feed = (
        db.query(WeReadFeed)
        .filter(WeReadFeed.user_id == user_id, WeReadFeed.mp_id == mid)
        .first()
    )
    now = int(time.time())
    if not feed:
        feed = WeReadFeed(
            user_id=user_id,
            mp_id=mid,
            mp_name=mp.get("name") or "",
            mp_cover=mp.get("cover") or "",
            mp_intro=mp.get("intro") or "",
            update_time=mp.get("updateTime") or now,
            sync_time=0,
            has_history=1,
            status=ENABLE,
        )
        db.add(feed)
    else:
        if mp.get("name"):
            feed.mp_name = mp["name"]
        if mp.get("cover"):
            feed.mp_cover = mp["cover"]
        if mp.get("intro"):
            feed.mp_intro = mp["intro"]
        if mp.get("updateTime"):
            feed.update_time = mp["updateTime"]
    db.commit()
    db.refresh(feed)
    return feed


def _article_count(db: Session, feed_id: int) -> int:
    return db.query(WeReadArticle).filter(WeReadArticle.feed_id == feed_id).count()


def _serialize_feed(db: Session, feed: WeReadFeed) -> dict:
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
        "articleCount": _article_count(db, feed.id),
    }


def _serialize_article(a: WeReadArticle) -> dict:
    return {
        "id": a.article_id,
        "mpId": a.mp_id,
        "title": a.title,
        "picUrl": a.pic_url,
        "publishTime": a.publish_time,
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
    db: Session = Depends(get_db),
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
                    _upsert_account_row(
                        db,
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
    db: Session = Depends(get_db),
):
    svc = _svc(request)
    blocked = set(svc.get_blocked_account_ids())
    rows = (
        db.query(WeReadAccount)
        .filter(
            WeReadAccount.user_id == int(current_user["sub"]),
            WeReadAccount.status != 0,  # hide auto-disconnected/invalid sessions
        )
        .all()
    )
    return [
        {
            "id": a.vid,
            "name": a.name,
            "status": a.status,
            "blockedToday": a.vid in blocked,
        }
        for a in rows
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
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    acc = (
        db.query(WeReadAccount)
        .filter(WeReadAccount.user_id == user_id, WeReadAccount.vid == vid)
        .first()
    )
    if not acc:
        return JSONResponse(status_code=404, content={"error": "account not found"})
    db.delete(acc)
    db.commit()
    return {"ok": True}


# =========================================================================
# Official Accounts (MPs) / Feeds
# =========================================================================


@router.post("/mps")
async def add_mp(
    body: MpAddBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = _svc(request)
    user_id = int(current_user["sub"])
    wxs_link = (body.wxsLink or body.url or "").strip()
    if not re.match(r"^https://mp\.weixin\.qq\.com/s/", wxs_link):
        return JSONResponse(
            status_code=400,
            content={"error": "wxsLink must start with https://mp.weixin.qq.com/s/"},
        )
    try:
        resolved = await svc.get_mp_info(db, user_id, wxs_link)
        mps = resolved if isinstance(resolved, list) else [resolved]
        mps = [x for x in mps if x]
        if not mps:
            return JSONResponse(
                status_code=502, content={"error": "gateway returned no mp info"}
            )

        saved_feeds: list[WeReadFeed] = []
        warnings: list[dict] = []
        client = _http(request)

        for mp in mps:
            final_mp = dict(mp)
            mpid = str(mp.get("id", ""))
            if re.match(r"^MP_WXS_\d+$", mpid):
                real_biz = _placeholder_to_real_biz(mpid)
                if real_biz:
                    final_mp = {
                        "id": real_biz,
                        "name": mp.get("name") or "",
                        "cover": mp.get("cover") or "",
                        "intro": mp.get("intro") or "",
                        "updateTime": mp.get("updateTime"),
                    }
                else:
                    extracted = await _resolve_biz_from_share_url(wxs_link, client)
                    if extracted.get("id"):
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
                                    "Gateway returned a placeholder id and the article page couldn't "
                                    f"be parsed ({extracted.get('error', 'unknown')}). Use the "
                                    "'Add by known official-account ID' endpoint to enter the biz id."
                                ),
                            }
                        )
            feed = _upsert_feed_record(db, user_id, final_mp)
            saved_feeds.append(feed)

        # schedule background history fetch only if we resolved clean MPs
        if not warnings:

            async def history_bg(feed_ids: list[int], mp_ids: list[str]):
                bg_db = SessionLocal()
                try:
                    for mp_id in mp_ids:
                        try:
                            await svc.get_history_mp_articles(bg_db, user_id, mp_id)
                        except Exception as err:
                            logger.error("history fetch mp=%s failed: %s", mp_id, err)
                finally:
                    bg_db.close()

            asyncio.create_task(
                history_bg([f.id for f in saved_feeds], [f.mp_id for f in saved_feeds])
            )

        return {
            "feeds": [_serialize_feed(db, f) for f in saved_feeds],
            "warnings": warnings,
        }
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
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    feeds = db.query(WeReadFeed).filter(WeReadFeed.user_id == user_id).all()
    return [_serialize_feed(db, f) for f in feeds]


@router.post("/mps/{mp_id}/sync")
async def sync_mp(
    mp_id: str,
    request: Request,
    history: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = _svc(request)
    user_id = int(current_user["sub"])
    feed = (
        db.query(WeReadFeed)
        .filter(WeReadFeed.user_id == user_id, WeReadFeed.mp_id == mp_id)
        .first()
    )
    if not feed:
        return JSONResponse(status_code=404, content={"error": "mp not found"})

    # placeholder migration
    if re.match(r"^MP_WXS_\d+$", mp_id):
        real_biz = _placeholder_to_real_biz(mp_id)
        if real_biz:
            logger.info("[wechat] migrating placeholder %s -> %s", mp_id, real_biz)
            db.query(WeReadArticle).filter(WeReadArticle.mp_id == mp_id).update(
                {"mp_id": real_biz}
            )
            feed.mp_id = real_biz
            db.commit()
            mp_id = real_biz

    try:
        if history in ("1", "true"):
            await svc.get_history_mp_articles(db, user_id, mp_id)
        else:
            await svc.refresh_mp_articles_and_update_feed(db, user_id, mp_id)
        db.refresh(feed)
        return _serialize_feed(db, feed)
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
            total = (
                db.query(WeReadAccount)
                .filter(WeReadAccount.user_id == user_id)
                .count()
            )
            return JSONResponse(
                status_code=502,
                content={
                    "error": "pool_exhausted",
                    "message": (
                        "Upstream gateway rejected every account in your pool with "
                        "WeReadError400. Log in with one or more additional WeChat "
                        "accounts and try again."
                    ),
                    "upstream": msg,
                    "pool": {"total": total, "blockedToday": len(blocked)},
                },
            )
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
    wxs_link = (body.wxsLink or body.url or "").strip()
    if not re.match(r"^https://mp\.weixin\.qq\.com/s/", wxs_link):
        return JSONResponse(
            status_code=400,
            content={"error": "wxsLink must start with https://mp.weixin.qq.com/s/"},
        )
    return await _resolve_biz_from_share_url(wxs_link, _http(request))


@router.post("/mps/by-id")
async def mps_by_id(
    body: MpByIdBody,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
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
    feed = _upsert_feed_record(
        db, user_id, {"id": mid, "name": body.name or "", "cover": "", "intro": ""}
    )
    return _serialize_feed(db, feed)


@router.post("/mps/sync-all")
async def sync_all(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = _svc(request)
    user_id = int(current_user["sub"])
    try:
        await svc.refresh_all_mp_articles_and_update_feed(db, user_id)
        feeds = db.query(WeReadFeed).filter(WeReadFeed.user_id == user_id).all()
        return {"feeds": [_serialize_feed(db, f) for f in feeds]}
    except Exception as err:
        logger.error("sync-all failed: %s", err)
        return JSONResponse(status_code=502, content={"error": str(err)})


@router.delete("/mps/{mp_id}")
async def delete_mp(
    mp_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    feed = (
        db.query(WeReadFeed)
        .filter(WeReadFeed.user_id == user_id, WeReadFeed.mp_id == mp_id)
        .first()
    )
    if feed:
        db.delete(feed)  # cascades articles via relationship
        db.commit()
    return {"ok": True}


# =========================================================================
# Articles
# =========================================================================


@router.get("/articles")
async def articles(
    mpId: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    q = (
        db.query(WeReadArticle)
        .join(WeReadFeed, WeReadArticle.feed_id == WeReadFeed.id)
        .filter(WeReadFeed.user_id == user_id)
    )
    if mpId:
        q = q.filter(WeReadArticle.mp_id == mpId)
    q = q.order_by(WeReadArticle.publish_time.desc())
    return [_serialize_article(a) for a in q.all()]


@router.get("/wechat-articles")
async def wechat_articles(
    mpId: str,
    request: Request,
    history: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = _svc(request)
    user_id = int(current_user["sub"])
    if not mpId:
        return JSONResponse(status_code=400, content={"error": "mpId required"})
    try:
        if history in ("1", "true"):
            await svc.get_history_mp_articles(db, user_id, mpId)
        else:
            await svc.refresh_mp_articles_and_update_feed(db, user_id, mpId)
        rows = (
            db.query(WeReadArticle)
            .join(WeReadFeed, WeReadArticle.feed_id == WeReadFeed.id)
            .filter(WeReadFeed.user_id == user_id, WeReadArticle.mp_id == mpId)
            .order_by(WeReadArticle.publish_time.desc())
            .all()
        )
        return [_serialize_article(a) for a in rows]
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
