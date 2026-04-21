"""
WeRead (WeChat Reading) article fetching service.

Ported from test/python/weread_service.py and adapted to persist state in
Supabase/PostgreSQL (or any SQLAlchemy target) instead of in-memory dicts.

Behaviour mirrors wewe-rss 1:1:
- Account pooling with per-call rotation (WeReadError400)
- Daily block list for rate-limited accounts (WeReadError429, in-memory, process-scoped)
- Session invalidation (WeReadError401) marks account status = INVALID in DB
- publish_time normalization identical to Node.js counterpart
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from ..db.models import WeReadAccount, WeReadArticle, WeReadFeed

logger = logging.getLogger(__name__)

DEFAULT_PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://weread.111965.xyz")
# The upstream gateway fingerprints on User-Agent and serves 500 "unknown error"
# for browser-looking UAs. wewe-rss uses axios with its default `axios/<ver>` UA
# and works fine, so we mirror that exactly.
DEFAULT_UA = "axios/1.7.7"
DEFAULT_REQUEST_TIMEOUT_MS = 15 * 1000
LOGIN_POLL_TIMEOUT_MS = 120 * 1000
DEFAULT_COUNT = 20
HISTORY_MAX_PAGES = 1000


def _default_update_delay_ms() -> int:
    if os.environ.get("UPDATE_DELAY_MS") is not None:
        return int(os.environ["UPDATE_DELAY_MS"])
    return (int(os.environ.get("UPDATE_DELAY_TIME", "60") or "60")) * 1000


# --- Errors --------------------------------------------------------------- #


class WeReadSessionError(Exception):
    def __init__(self, message: str, account_id: Optional[str] = None):
        super().__init__(message)
        self.account_id = account_id


class WeReadRequestError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        url: Optional[str] = None,
        upstream_message: str = "",
    ):
        super().__init__(message)
        self.status = status
        self.url = url
        self.upstream_message = upstream_message


class WeReadPoolEmptyError(Exception):
    def __init__(self, message: str, *, total: int = 0, blocked: int = 0):
        super().__init__(message)
        self.total = total
        self.blocked = blocked


# --- Status codes --------------------------------------------------------- #

INVALID, ENABLE, DISABLE = 0, 1, 2


def _today_key() -> str:
    shanghai = timezone(timedelta(hours=8))
    return datetime.now(shanghai).date().isoformat()


@dataclass
class _State:
    in_progress_history_mp: dict[int, dict] = field(default_factory=dict)  # user_id -> {mp_id, page}
    refresh_all_running: set[int] = field(default_factory=set)              # user_ids currently refreshing


# --- Service -------------------------------------------------------------- #


class WeReadService:
    """
    Singleton WeRead service. All methods that touch user-scoped data accept a
    SQLAlchemy Session and the user_id to operate on.
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        platform_url: str = DEFAULT_PLATFORM_URL,
        user_agent: str = DEFAULT_UA,
        request_timeout_ms: int = DEFAULT_REQUEST_TIMEOUT_MS,
        update_delay_ms: Optional[int] = None,
        max_retries: int = 3,
    ):
        self._client = client
        self._platform_url = platform_url.rstrip("/")
        self._user_agent = user_agent
        self._request_timeout_ms = request_timeout_ms
        self._update_delay_ms = (
            update_delay_ms if update_delay_ms is not None else _default_update_delay_ms()
        )
        self._max_retries = max_retries
        # daily block list: { "YYYY-MM-DD": [vid, ...] }
        self._blocked_accounts_map: dict[str, list[str]] = {}
        self._state = _State()

    # ---- block list -------------------------------------------------------

    def get_blocked_account_ids(self) -> list[str]:
        return [x for x in self._blocked_accounts_map.get(_today_key(), []) if x]

    def _add_blocked_account(self, vid: str) -> None:
        if not vid:
            return
        lst = self._blocked_accounts_map.setdefault(_today_key(), [])
        if vid not in lst:
            lst.append(vid)

    def clear_blocked_accounts(self) -> None:
        self._blocked_accounts_map.clear()

    # ---- account pool -----------------------------------------------------

    def _list_enabled_accounts(self, db: Session, user_id: int) -> list[WeReadAccount]:
        return (
            db.query(WeReadAccount)
            .filter(
                WeReadAccount.user_id == user_id,
                WeReadAccount.status == ENABLE,
                WeReadAccount.token.isnot(None),
            )
            .all()
        )

    def _count_accounts(self, db: Session, user_id: int) -> int:
        return db.query(WeReadAccount).filter(WeReadAccount.user_id == user_id).count()

    def _get_available_account(
        self,
        db: Session,
        user_id: int,
        exclude_ids: Optional[list[str]] = None,
    ) -> WeReadAccount:
        exclude_ids = set(exclude_ids or [])
        blocked = set(self.get_blocked_account_ids()) | exclude_ids
        enabled = self._list_enabled_accounts(db, user_id)
        pool = [a for a in enabled if a.vid not in blocked]
        if not pool:
            total = self._count_accounts(db, user_id)
            if total == 0:
                raise WeReadSessionError("暂无可用读书账号 — log in with WeChat first.")
            bl = self.get_blocked_account_ids()
            raise WeReadPoolEmptyError(
                "Upstream rejected every account in your pool for this request "
                f"({total} total, {len(bl)} blocked today). Add another WeChat "
                "account — the gateway rotates across a pool and 2–3 accounts "
                "dramatically improve success.",
                total=total,
                blocked=len(bl),
            )
        return random.choice(pool)

    def _mark_account_invalid(self, db: Session, vid: str) -> None:
        """Session rejected with WeReadError401 — soft-disconnect.

        Mirrors wewe-rss exactly: flip status to INVALID (0) so the account is
        skipped by the pool picker. The row is kept so:
        - downstream FKs (feeds/articles) stay intact,
        - a transient 401 does not destroy a working session permanently,
        - the `/accounts` endpoint hides it (status != 0) so the UI shows it as
          disconnected and the user can simply re-scan the QR to revive it.
        """
        acc = db.query(WeReadAccount).filter(WeReadAccount.vid == vid).first()
        if not acc:
            return
        acc.status = INVALID
        db.commit()
        logger.warning("[weread] account(%s) session invalid, marked INVALID", vid)

    # ---- http -------------------------------------------------------------

    def _build_headers(
        self, account: Optional[WeReadAccount], extra: Optional[dict] = None
    ) -> dict:
        # Mirror wewe-rss axios request exactly: only xid + Authorization for
        # authenticated calls, plus the axios-style Accept header. The extra
        # Content-Type header is injected by _raw_request on POSTs with a body.
        h = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": self._user_agent,
        }
        if account:
            h["xid"] = account.vid
            if account.token:
                h["Authorization"] = f"Bearer {account.token}"
        if extra:
            h.update(extra)
        return h

    async def _raw_request(
        self,
        method: str,
        pathname: str,
        *,
        account: Optional[WeReadAccount] = None,
        query: Optional[dict] = None,
        body: Optional[dict] = None,
        timeout_ms: Optional[int] = None,
    ) -> Any:
        q = {k: str(v) for k, v in (query or {}).items() if v is not None}
        url = f"{self._platform_url}{pathname}"
        if q:
            url = f"{url}?{urlencode(q)}"
        timeout = (timeout_ms or self._request_timeout_ms) / 1000.0
        headers = self._build_headers(
            account, {"Content-Type": "application/json"} if body else {}
        )
        try:
            resp = await self._client.request(
                method, url, headers=headers, json=body, timeout=timeout
            )
        except httpx.RequestError as e:
            raise WeReadRequestError(f"Network error calling {url}: {e}", url=url) from e

        text = resp.text
        payload = None
        if text:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None

        if not resp.is_success:
            upstream = ""
            if isinstance(payload, dict):
                upstream = str(payload.get("message") or payload.get("error") or "")
            if not upstream:
                upstream = text or ""
            raise WeReadRequestError(
                f"HTTP {resp.status_code} from {url}: {upstream}",
                status=resp.status_code,
                url=url,
                upstream_message=upstream,
            )
        return payload

    async def _handle_upstream_error(
        self, err: BaseException, account: WeReadAccount, db: Session
    ) -> dict:
        """Mirror wewe-rss axios response-interceptor side effects 1:1.

        - WeReadError401  -> mark account INVALID in DB
        - WeReadError429  -> add to today's block list
        - WeReadError400  -> just sleep 10s; DO NOT remove the account from the
                             pool. wewe-rss leaves it available so the next
                             random pick can retry the same (transient) upstream.
        Everything is retryable from the caller's perspective; we never reject a
        specific account for a single bad response (that was breaking small
        pools).
        """
        msg = (
            err.upstream_message or str(err)
            if isinstance(err, WeReadRequestError)
            else str(err)
        )
        if "WeReadError401" in msg:
            self._mark_account_invalid(db, account.vid)
            logger.error("[weread] account(%s) 401, disabled", account.vid)
            return {"kind": "session", "retry": True}
        if "WeReadError429" in msg:
            self._add_blocked_account(account.vid)
            logger.error("[weread] account(%s) 429, blocked for today", account.vid)
            return {"kind": "rate-limit", "retry": True}
        if "WeReadError400" in msg:
            logger.error(
                "[weread] account(%s) WeReadError400 (sleep 10s): %s",
                account.vid, msg,
            )
            await asyncio.sleep(10)
            return {"kind": "bad-request", "retry": True}
        logger.error("[weread] unhandled upstream error (%s): %s", account.vid, msg)
        return {"kind": "unknown", "retry": True}

    # ---- public: login (no auth required) --------------------------------

    async def create_login_url(self) -> dict:
        return await self._raw_request("GET", "/api/v2/login/platform")

    async def get_login_result(self, uuid: str) -> dict:
        return await self._raw_request(
            "GET",
            f"/api/v2/login/platform/{uuid}",
            timeout_ms=LOGIN_POLL_TIMEOUT_MS,
        )

    # ---- public: mp info / articles --------------------------------------

    async def get_mp_info(self, db: Session, user_id: int, wxs_link: str) -> Any:
        url = (wxs_link or "").strip()
        if not url.startswith("https://mp.weixin.qq.com/s/"):
            raise ValueError("getMpInfo: expected a https://mp.weixin.qq.com/s/... link")
        account = self._get_available_account(db, user_id)
        try:
            return await self._raw_request(
                "POST",
                "/api/v2/platform/wxs2mp",
                account=account,
                body={"url": url},
            )
        except WeReadRequestError as err:
            # Run the same interceptor side-effects as wewe-rss (401 disables
            # account, 429 blocks for today, 400 sleeps 10s). wewe-rss does not
            # retry getMpInfo itself, so neither do we — surface the error.
            await self._handle_upstream_error(err, account, db)
            raise

    async def get_mp_articles(
        self,
        db: Session,
        user_id: int,
        mp_id: str,
        page: int = 1,
        *,
        retries_left: Optional[int] = None,
    ) -> list:
        """Fetch one page of MP articles.

        Mirrors wewe-rss.getMpArticles exactly:
        - pick a RANDOM enabled account every attempt (no "tried" exclusion
          list — the same account can be picked twice, which is fine because
          WeReadError400 is usually transient),
        - retry up to `max_retries` times on any failure,
        - the response interceptor equivalent (`_handle_upstream_error`) does
          the per-error housekeeping (mark invalid on 401, block on 429,
          sleep 10s on 400).
        """
        if not mp_id:
            raise ValueError("getMpArticles: mp_id is required")
        retries_left = self._max_retries if retries_left is None else retries_left
        account = self._get_available_account(db, user_id)
        try:
            data = await self._raw_request(
                "GET",
                f"/api/v2/platform/mps/{mp_id}/articles",
                account=account,
                query={"page": page},
            )
            lst = data if isinstance(data, list) else (data or {}).get("items") or []
            logger.info(
                "[weread] getMpArticles(%s) page=%s via acc=%s -> %s",
                mp_id, page, account.vid, len(lst),
            )
            return lst
        except WeReadPoolEmptyError:
            raise
        except BaseException as err:
            await self._handle_upstream_error(err, account, db)
            if retries_left > 0:
                logger.error(
                    "[weread] retry(%s) getMpArticles(%s) page=%s: %s",
                    self._max_retries - retries_left + 1, mp_id, page, err,
                )
                return await self.get_mp_articles(
                    db, user_id, mp_id, page,
                    retries_left=retries_left - 1,
                )
            raise

    # ---- upserts ----------------------------------------------------------

    def _upsert_article(
        self,
        db: Session,
        *,
        feed_id: int,
        mp_id: str,
        article_id: str,
        title: str,
        pic_url: str,
        publish_time: int,
    ) -> None:
        existing = (
            db.query(WeReadArticle)
            .filter(WeReadArticle.feed_id == feed_id, WeReadArticle.article_id == article_id)
            .first()
        )
        if existing:
            existing.title = title
            existing.pic_url = pic_url
            existing.publish_time = publish_time
            existing.mp_id = mp_id
        else:
            db.add(
                WeReadArticle(
                    feed_id=feed_id,
                    mp_id=mp_id,
                    article_id=article_id,
                    title=title,
                    pic_url=pic_url,
                    publish_time=publish_time,
                )
            )

    def _get_or_create_feed(
        self, db: Session, user_id: int, mp_id: str
    ) -> WeReadFeed:
        feed = (
            db.query(WeReadFeed)
            .filter(WeReadFeed.user_id == user_id, WeReadFeed.mp_id == mp_id)
            .first()
        )
        if not feed:
            feed = WeReadFeed(user_id=user_id, mp_id=mp_id)
            db.add(feed)
            db.commit()
            db.refresh(feed)
        return feed

    # ---- public: refresh / history ---------------------------------------

    async def refresh_mp_articles_and_update_feed(
        self, db: Session, user_id: int, mp_id: str, page: int = 1
    ) -> dict:
        articles = await self.get_mp_articles(db, user_id, mp_id, page)

        feed = self._get_or_create_feed(db, user_id, mp_id)

        for a in articles:
            if not a or not a.get("id"):
                continue
            pt = a.get("publishTime")
            if isinstance(pt, (int, float)):
                pub = int(pt)
            elif not pt:
                pub = 0
            else:
                pub = 0
                try:
                    s = str(pt).replace("Z", "+00:00")
                    pub = int(datetime.fromisoformat(s).timestamp())
                except (ValueError, TypeError, OSError):
                    try:
                        pub = int(time.mktime(time.strptime(str(pt)[:19], "%Y-%m-%dT%H:%M:%S")))
                    except (ValueError, TypeError, OSError):
                        pub = 0
            self._upsert_article(
                db,
                feed_id=feed.id,
                mp_id=mp_id,
                article_id=str(a["id"]),
                title=a.get("title") or "Untitled",
                pic_url=a.get("picUrl") or "",
                publish_time=pub,
            )
        has_history = 0 if len(articles) < DEFAULT_COUNT else 1
        feed.sync_time = int(time.time())
        feed.has_history = has_history
        db.commit()
        return {"hasHistory": has_history, "count": len(articles)}

    async def get_history_mp_articles(
        self, db: Session, user_id: int, mp_id: str
    ) -> None:
        if not mp_id:
            return
        existing_state = self._state.in_progress_history_mp.get(user_id, {})
        if existing_state.get("id") == mp_id:
            logger.info("[weread] getHistoryMpArticles(%s) already running", mp_id)
            return
        self._state.in_progress_history_mp[user_id] = {"id": mp_id, "page": 1}
        try:
            feed = (
                db.query(WeReadFeed)
                .filter(WeReadFeed.user_id == user_id, WeReadFeed.mp_id == mp_id)
                .first()
            )
            if feed and feed.has_history == 0:
                logger.info("[weread] getHistoryMpArticles(%s) no history", mp_id)
                return
            existing = (
                db.query(WeReadArticle).filter(WeReadArticle.mp_id == mp_id).count()
            )
            start_page = max(1, math.ceil(existing / DEFAULT_COUNT) if existing else 1)
            self._state.in_progress_history_mp[user_id] = {"id": mp_id, "page": start_page}

            for _ in range(HISTORY_MAX_PAGES):
                st = self._state.in_progress_history_mp.get(user_id, {})
                if st.get("id") != mp_id:
                    break
                page = st["page"]
                result = await self.refresh_mp_articles_and_update_feed(
                    db, user_id, mp_id, page
                )
                if result["hasHistory"] < 1:
                    break
                self._state.in_progress_history_mp[user_id] = {"id": mp_id, "page": page + 1}
                if self._update_delay_ms > 0:
                    await asyncio.sleep(self._update_delay_ms / 1000.0)
        finally:
            self._state.in_progress_history_mp.pop(user_id, None)

    async def refresh_all_mp_articles_and_update_feed(
        self, db: Session, user_id: int
    ) -> None:
        if user_id in self._state.refresh_all_running:
            logger.info("[weread] refreshAll(user=%s) already running", user_id)
            return
        self._state.refresh_all_running.add(user_id)
        try:
            feeds = db.query(WeReadFeed).filter(WeReadFeed.user_id == user_id).all()
            for feed in feeds:
                try:
                    await self.refresh_mp_articles_and_update_feed(
                        db, user_id, feed.mp_id
                    )
                except Exception as e:
                    logger.error(
                        "[weread] refreshAll: mp=%s failed: %s", feed.mp_id, e
                    )
                if self._update_delay_ms > 0:
                    await asyncio.sleep(self._update_delay_ms / 1000.0)
        finally:
            self._state.refresh_all_running.discard(user_id)

    # ---- introspection ----------------------------------------------------

    def in_progress_history_mp(self, user_id: int) -> dict:
        return dict(self._state.in_progress_history_mp.get(user_id, {"id": "", "page": 1}))

    def is_refresh_all_running(self, user_id: int) -> bool:
        return user_id in self._state.refresh_all_running
