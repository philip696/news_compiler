"""
WeRead (WeChat Reading) article fetching service.

Persisted via AppRepository: SQLAlchemy (local/DATABASE_URL) or Supabase REST
when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set.

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
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from ..db.app_repository import AppRepository, FeedRow, PoolAccount

logger = logging.getLogger(__name__)

DEFAULT_PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://weread.111965.xyz")
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
    in_progress_history_mp: dict[int, dict] = field(default_factory=dict)
    refresh_all_running: set[int] = field(default_factory=set)


# --- Service -------------------------------------------------------------- #


class WeReadService:
    """WeRead gateway client; persistence through AppRepository."""

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
        self._blocked_accounts_map: dict[str, list[str]] = {}
        self._state = _State()

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

    def _list_enabled_accounts(
        self, repo: AppRepository, user_id: int
    ) -> list[PoolAccount]:
        return repo.weread_pool_list_enabled(user_id)

    def _count_accounts(self, repo: AppRepository, user_id: int) -> int:
        return repo.weread_account_count(user_id)

    def _get_available_account(
        self,
        repo: AppRepository,
        user_id: int,
        exclude_ids: Optional[list[str]] = None,
    ) -> PoolAccount:
        exclude_ids = set(exclude_ids or [])
        blocked = set(self.get_blocked_account_ids()) | exclude_ids
        enabled = self._list_enabled_accounts(repo, user_id)
        pool = [a for a in enabled if a.vid not in blocked]
        if not pool:
            total = self._count_accounts(repo, user_id)
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

    def _mark_account_invalid(self, repo: AppRepository, vid: str) -> None:
        repo.weread_mark_invalid_by_vid(vid)

    def _build_headers(
        self, account: Optional[PoolAccount], extra: Optional[dict] = None
    ) -> dict:
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
        account: Optional[PoolAccount] = None,
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
        self, err: BaseException, account: PoolAccount, repo: AppRepository
    ) -> dict:
        msg = (
            err.upstream_message or str(err)
            if isinstance(err, WeReadRequestError)
            else str(err)
        )
        if "WeReadError401" in msg:
            self._mark_account_invalid(repo, account.vid)
            logger.error("[weread] account(%s) 401, disabled", account.vid)
            return {"kind": "session", "retry": True}
        if "WeReadError429" in msg:
            self._add_blocked_account(account.vid)
            logger.error("[weread] account(%s) 429, blocked for today", account.vid)
            return {"kind": "rate-limit", "retry": True}
        if "WeReadError400" in msg:
            logger.error(
                "[weread] account(%s) WeReadError400 (sleep 10s): %s",
                account.vid,
                msg,
            )
            await asyncio.sleep(10)
            return {"kind": "bad-request", "retry": True}
        logger.error("[weread] unhandled upstream error (%s): %s", account.vid, msg)
        return {"kind": "unknown", "retry": True}

    async def create_login_url(self) -> dict:
        return await self._raw_request("GET", "/api/v2/login/platform")

    async def get_login_result(self, uuid: str) -> dict:
        return await self._raw_request(
            "GET",
            f"/api/v2/login/platform/{uuid}",
            timeout_ms=LOGIN_POLL_TIMEOUT_MS,
        )

    async def get_mp_info(self, repo: AppRepository, user_id: int, wxs_link: str) -> Any:
        url = (wxs_link or "").strip()
        if not url.startswith("https://mp.weixin.qq.com/s/"):
            raise ValueError("getMpInfo: expected a https://mp.weixin.qq.com/s/... link")
        account = self._get_available_account(repo, user_id)
        try:
            return await self._raw_request(
                "POST",
                "/api/v2/platform/wxs2mp",
                account=account,
                body={"url": url},
            )
        except WeReadRequestError as err:
            await self._handle_upstream_error(err, account, repo)
            raise

    async def get_mp_articles(
        self,
        repo: AppRepository,
        user_id: int,
        mp_id: str,
        page: int = 1,
        *,
        retries_left: Optional[int] = None,
    ) -> list:
        if not mp_id:
            raise ValueError("getMpArticles: mp_id is required")
        retries_left = self._max_retries if retries_left is None else retries_left
        account = self._get_available_account(repo, user_id)
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
                mp_id,
                page,
                account.vid,
                len(lst),
            )
            return lst
        except WeReadPoolEmptyError:
            raise
        except BaseException as err:
            await self._handle_upstream_error(err, account, repo)
            if retries_left > 0:
                logger.error(
                    "[weread] retry(%s) getMpArticles(%s) page=%s: %s",
                    self._max_retries - retries_left + 1,
                    mp_id,
                    page,
                    err,
                )
                return await self.get_mp_articles(
                    repo,
                    user_id,
                    mp_id,
                    page,
                    retries_left=retries_left - 1,
                )
            raise

    def _get_or_create_feed(
        self, repo: AppRepository, user_id: int, mp_id: str
    ) -> FeedRow:
        f = repo.weread_feed_get(user_id, mp_id)
        if f:
            return f
        return repo.weread_feed_upsert(
            user_id, {"id": mp_id, "name": "", "cover": "", "intro": ""}
        )

    async def refresh_mp_articles_and_update_feed(
        self, repo: AppRepository, user_id: int, mp_id: str, page: int = 1
    ) -> dict:
        articles = await self.get_mp_articles(repo, user_id, mp_id, page)

        feed = self._get_or_create_feed(repo, user_id, mp_id)

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
                        pub = int(
                            time.mktime(
                                time.strptime(str(pt)[:19], "%Y-%m-%dT%H:%M:%S")
                            )
                        )
                    except (ValueError, TypeError, OSError):
                        pub = 0
            repo.weread_article_upsert(
                feed_id=feed.id,
                mp_id=mp_id,
                article_id=str(a["id"]),
                title=a.get("title") or "Untitled",
                pic_url=a.get("picUrl") or "",
                publish_time=pub,
            )
        has_history = 0 if len(articles) < DEFAULT_COUNT else 1
        repo.weread_feed_update_sync(feed.id, int(time.time()), has_history)
        repo.session_commit()
        return {"hasHistory": has_history, "count": len(articles)}

    async def get_history_mp_articles(
        self, repo: AppRepository, user_id: int, mp_id: str
    ) -> None:
        if not mp_id:
            return
        existing_state = self._state.in_progress_history_mp.get(user_id, {})
        if existing_state.get("id") == mp_id:
            logger.info("[weread] getHistoryMpArticles(%s) already running", mp_id)
            return
        self._state.in_progress_history_mp[user_id] = {"id": mp_id, "page": 1}
        try:
            feed = repo.weread_feed_get(user_id, mp_id)
            if feed and feed.has_history == 0:
                logger.info("[weread] getHistoryMpArticles(%s) no history", mp_id)
                return
            existing = repo.weread_article_count_for_mp(mp_id)
            start_page = max(1, math.ceil(existing / DEFAULT_COUNT) if existing else 1)
            self._state.in_progress_history_mp[user_id] = {
                "id": mp_id,
                "page": start_page,
            }

            for _ in range(HISTORY_MAX_PAGES):
                st = self._state.in_progress_history_mp.get(user_id, {})
                if st.get("id") != mp_id:
                    break
                page = st["page"]
                result = await self.refresh_mp_articles_and_update_feed(
                    repo, user_id, mp_id, page
                )
                if result["hasHistory"] < 1:
                    break
                self._state.in_progress_history_mp[user_id] = {
                    "id": mp_id,
                    "page": page + 1,
                }
                if self._update_delay_ms > 0:
                    await asyncio.sleep(self._update_delay_ms / 1000.0)
        finally:
            self._state.in_progress_history_mp.pop(user_id, None)

    async def refresh_all_mp_articles_and_update_feed(
        self, repo: AppRepository, user_id: int
    ) -> None:
        if user_id in self._state.refresh_all_running:
            logger.info("[weread] refreshAll(user=%s) already running", user_id)
            return
        self._state.refresh_all_running.add(user_id)
        try:
            feeds = repo.weread_feed_list_user(user_id)
            for feed in feeds:
                try:
                    await self.refresh_mp_articles_and_update_feed(
                        repo, user_id, feed.mp_id
                    )
                except Exception as e:
                    logger.error(
                        "[weread] refreshAll: mp=%s failed: %s", feed.mp_id, e
                    )
                if self._update_delay_ms > 0:
                    await asyncio.sleep(self._update_delay_ms / 1000.0)
        finally:
            self._state.refresh_all_running.discard(user_id)

    def in_progress_history_mp(self, user_id: int) -> dict:
        return dict(
            self._state.in_progress_history_mp.get(user_id, {"id": "", "page": 1})
        )

    def is_refresh_all_running(self, user_id: int) -> bool:
        return user_id in self._state.refresh_all_running
