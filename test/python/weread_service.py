"""
WeRead (WeChat Reading) article fetching — 1:1 port of test/wechat-service.js.
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
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PLATFORM_URL = os.environ.get("PLATFORM_URL", "https://weread.111965.xyz")
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_REQUEST_TIMEOUT_MS = 15 * 1000
LOGIN_POLL_TIMEOUT_MS = 120 * 1000
DEFAULT_COUNT = 20
HISTORY_MAX_PAGES = 1000


def _default_update_delay_ms() -> int:
    if os.environ.get("UPDATE_DELAY_MS") is not None:
        return int(os.environ["UPDATE_DELAY_MS"])
    return (int(os.environ.get("UPDATE_DELAY_TIME", "60") or "60")) * 1000


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


status_map = {"INVALID": 0, "ENABLE": 1, "DISABLE": 2}
INVALID, ENABLE, DISABLE = 0, 1, 2


def _today_key() -> str:
    from datetime import datetime, timedelta, timezone

    shanghai = timezone(timedelta(hours=8))
    return datetime.now(shanghai).date().isoformat()


def _is_enabled(acc: dict) -> bool:
    if not acc or not acc.get("token"):
        return False
    st = acc.get("status")
    return st in (ENABLE, "ENABLE", None, "enable")


@dataclass
class _State:
    in_progress_history_mp: dict = field(
        default_factory=lambda: {"id": "", "page": 1}
    )
    is_refresh_all_running: bool = False


class WeReadService:
    """
    Mirrors createWeReadService() from wechat-service.js.
    """

    def __init__(
        self,
        db: dict[str, Any],
        *,
        platform_url: str = DEFAULT_PLATFORM_URL,
        user_agent: str = DEFAULT_UA,
        client: httpx.AsyncClient,
        request_timeout_ms: int = DEFAULT_REQUEST_TIMEOUT_MS,
        update_delay_ms: Optional[int] = None,
        max_retries: int = 3,
    ):
        if not isinstance(db.get("accounts"), list) or not isinstance(
            db.get("articles"), list
        ):
            raise ValueError("db must expose accounts[] and articles[]")
        if "feeds" not in db or not isinstance(db["feeds"], list):
            db["feeds"] = []
        self._db = db
        self._platform_url = platform_url.rstrip("/")
        self._user_agent = user_agent
        self._client = client
        self._request_timeout_ms = request_timeout_ms
        self._update_delay_ms = (
            update_delay_ms if update_delay_ms is not None else _default_update_delay_ms()
        )
        self._max_retries = max_retries
        self._blocked_accounts_map: dict[str, list[str]] = {}
        self._state = _State()

    # --- block list (mirrors blockedAccountsMap) ---

    def get_blocked_account_ids(self) -> list[str]:
        return [x for x in self._blocked_accounts_map.get(_today_key(), []) if x]

    def _add_blocked_account(self, acc_id: str) -> None:
        if not acc_id:
            return
        key = _today_key()
        lst = self._blocked_accounts_map.setdefault(key, [])
        if acc_id not in lst:
            lst.append(acc_id)

    def remove_blocked_account(self, acc_id: str) -> None:
        key = _today_key()
        lst = self._blocked_accounts_map.get(key)
        if lst:
            self._blocked_accounts_map[key] = [x for x in lst if x != acc_id]

    def clear_blocked_accounts(self) -> None:
        self._blocked_accounts_map.clear()

    def _get_available_account(self, exclude_ids: Optional[list[str]] = None) -> dict:
        exclude_ids = exclude_ids or []
        blocked = set(self.get_blocked_account_ids()) | set(exclude_ids)
        pool = [a for a in self._db["accounts"] if _is_enabled(a) and a["id"] not in blocked]
        if not pool:
            if not self._db["accounts"]:
                raise WeReadSessionError("暂无可用读书账号 — log in with WeChat first.")
            bl = self.get_blocked_account_ids()
            raise WeReadPoolEmptyError(
                "Upstream rejected every account in your pool for this request "
                f"({len(self._db['accounts'])} total, {len(bl)} "
                "blocked today). Add another WeChat account — the gateway "
                "rotates across a pool and 2–3 accounts dramatically improve "
                "success.",
                total=len(self._db["accounts"]),
                blocked=len(bl),
            )
        return random.choice(pool)

    def _mark_account_invalid(self, acc_id: str) -> None:
        for a in self._db["accounts"]:
            if a["id"] == acc_id:
                a["status"] = INVALID
                logger.warning("[wechat-service] account(%s) session invalid, disabled", acc_id)
                return

    def _build_headers(self, account: Optional[dict], extra: Optional[dict] = None) -> dict:
        h = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": self._user_agent,
            "xid": account["id"] if account else "",
        }
        if account and account.get("token"):
            h["Authorization"] = f"Bearer {account['token']}"
        if extra:
            h.update(extra)
        return h

    async def _raw_request(
        self,
        method: str,
        pathname: str,
        *,
        account: Optional[dict] = None,
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
                method,
                url,
                headers=headers,
                json=body,
                timeout=timeout,
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

    def _handle_upstream_error(self, err: BaseException, account: dict) -> dict:
        msg = ""
        if isinstance(err, WeReadRequestError):
            msg = err.upstream_message or str(err)
        else:
            msg = str(err)
        if "WeReadError401" in msg:
            self._mark_account_invalid(account["id"])
            return {"kind": "session", "retry": False}
        if "WeReadError429" in msg:
            self._add_blocked_account(account["id"])
            logger.error("[wechat-service] account(%s) rate-limited", account["id"])
            return {"kind": "rate-limit", "retry": False}
        if "WeReadError400" in msg:
            logger.error(
                "[wechat-service] account(%s) WeReadError400; rotating within this call: %s",
                account["id"],
                msg,
            )
            return {"kind": "bad-request", "retry": True, "rotate": True}
        return {"kind": "unknown", "retry": True, "delay_ms": 0}

    async def create_login_url(self) -> dict:
        return await self._raw_request("GET", "/api/v2/login/platform")

    async def get_login_result(self, uuid: str) -> dict:
        return await self._raw_request(
            "GET",
            f"/api/v2/login/platform/{uuid}",
            timeout_ms=LOGIN_POLL_TIMEOUT_MS,
        )

    async def get_mp_info(self, wxs_link: str) -> Any:
        account = self._get_available_account()
        url = (wxs_link or "").strip()
        if not url.startswith("https://mp.weixin.qq.com/s/"):
            raise ValueError("getMpInfo: expected a https://mp.weixin.qq.com/s/... link")
        try:
            return await self._raw_request(
                "POST",
                "/api/v2/platform/wxs2mp",
                account=account,
                body={"url": url},
            )
        except WeReadRequestError as err:
            outcome = self._handle_upstream_error(err, account)
            if outcome["kind"] == "session":
                raise WeReadSessionError("Session expired", account_id=account["id"]) from err
            raise

    async def get_mp_articles(
        self,
        mp_id: str,
        page: int = 1,
        *,
        tried: Optional[list[str]] = None,
        retries_left: Optional[int] = None,
    ) -> list:
        if not mp_id:
            raise ValueError("getMpArticles: mpId is required")
        tried = list(tried or [])
        retries_left = self._max_retries if retries_left is None else retries_left
        account = self._get_available_account(tried)
        try:
            data = await self._raw_request(
                "GET",
                f"/api/v2/platform/mps/{mp_id}/articles",
                account=account,
                query={"page": page},
            )
            lst = data if isinstance(data, list) else (data or {}).get("items") or []
            logger.info(
                "[wechat-service] getMpArticles(%s) page=%s via acc=%s -> %s",
                mp_id,
                page,
                account["id"],
                len(lst),
            )
            return lst
        except BaseException as err:
            if isinstance(err, WeReadPoolEmptyError):
                raise
            outcome = self._handle_upstream_error(err, account)
            next_tried = tried + [account["id"]] if outcome.get("rotate") else tried

            if outcome["kind"] == "session":
                if retries_left > 0:
                    return await self.get_mp_articles(
                        mp_id,
                        page,
                        tried=tried + [account["id"]],
                        retries_left=retries_left - 1,
                    )
                raise WeReadSessionError(
                    f"All candidate sessions rejected for mp={mp_id}",
                    account_id=account["id"],
                ) from err

            if outcome.get("retry") and retries_left > 0:
                delay_ms = outcome.get("delay_ms") or 0
                if delay_ms:
                    await asyncio.sleep(delay_ms / 1000.0)
                logger.error(
                    "[wechat-service] retry(%s) getMpArticles(%s) page=%s: %s",
                    self._max_retries - retries_left + 1,
                    mp_id,
                    page,
                    err,
                )
                return await self.get_mp_articles(
                    mp_id,
                    page,
                    tried=next_tried,
                    retries_left=retries_left - 1,
                )
            raise

    def _upsert_article(self, *, id: str, mp_id: str, title: str, pic_url: str, publish_time: int):
        articles: list = self._db["articles"]
        for i, a in enumerate(articles):
            if a["id"] == id:
                articles[i] = {**a, "id": id, "mpId": mp_id, "title": title, "picUrl": pic_url, "publishTime": publish_time}
                return {"inserted": False}
        articles.append(
            {"id": id, "mpId": mp_id, "title": title, "picUrl": pic_url, "publishTime": publish_time}
        )
        return {"inserted": True}

    def _upsert_feed(self, mp_id: str, patch: dict) -> dict:
        feeds: list = self._db["feeds"]
        feed = next((f for f in feeds if (f.get("id") or f.get("mpId")) == mp_id), None)
        if not feed:
            feed = {"id": mp_id, "mpId": mp_id, "createdAt": int(__import__("time").time())}
            feeds.append(feed)
        feed.update(patch)
        return feed

    async def refresh_mp_articles_and_update_feed(self, mp_id: str, page: int = 1) -> dict:
        articles = await self.get_mp_articles(mp_id, page)

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
                id=str(a["id"]),
                mp_id=mp_id,
                title=a.get("title") or "Untitled",
                pic_url=a.get("picUrl") or "",
                publish_time=pub,
            )
        has_history = 0 if len(articles) < DEFAULT_COUNT else 1
        self._upsert_feed(mp_id, {"syncTime": int(time.time()), "hasHistory": has_history})
        return {"hasHistory": has_history, "count": len(articles)}

    async def get_history_mp_articles(self, mp_id: str) -> None:
        if not mp_id:
            return
        if self._state.in_progress_history_mp.get("id") == mp_id:
            logger.info("[wechat-service] getHistoryMpArticles(%s) already running", mp_id)
            return
        self._state.in_progress_history_mp = {"id": mp_id, "page": 1}
        try:
            feed = next((f for f in self._db["feeds"] if (f.get("id") or f.get("mpId")) == mp_id), None)
            if feed and feed.get("hasHistory") == 0:
                logger.info("[wechat-service] getHistoryMpArticles(%s) no history", mp_id)
                return
            existing = len([a for a in self._db["articles"] if a.get("mpId") == mp_id])
            self._state.in_progress_history_mp["page"] = max(
                1, math.ceil(existing / DEFAULT_COUNT) if existing else 1
            )

            for _ in range(HISTORY_MAX_PAGES):
                if self._state.in_progress_history_mp.get("id") != mp_id:
                    break
                page = self._state.in_progress_history_mp["page"]
                result = await self.refresh_mp_articles_and_update_feed(mp_id, page)
                if result["hasHistory"] < 1:
                    break
                self._state.in_progress_history_mp["page"] = page + 1
                if self._update_delay_ms > 0:
                    await asyncio.sleep(self._update_delay_ms / 1000.0)
        finally:
            self._state.in_progress_history_mp = {"id": "", "page": 1}

    async def refresh_all_mp_articles_and_update_feed(self) -> None:
        if self._state.is_refresh_all_running:
            logger.info("[wechat-service] refreshAll already running")
            return
        self._state.is_refresh_all_running = True
        try:
            for feed in list(self._db["feeds"]):
                fid = feed.get("id") or feed.get("mpId")
                if not fid:
                    continue
                try:
                    await self.refresh_mp_articles_and_update_feed(fid)
                except Exception as e:
                    logger.error("[wechat-service] refreshAll: mp=%s failed: %s", fid, e)
                if self._update_delay_ms > 0:
                    await asyncio.sleep(self._update_delay_ms / 1000.0)
        finally:
            self._state.is_refresh_all_running = False

    @property
    def in_progress_history_mp(self) -> dict:
        return dict(self._state.in_progress_history_mp)

    @property
    def is_refresh_all_mp_articles_running(self) -> bool:
        return self._state.is_refresh_all_running
