"""Unified persistence: SQLAlchemy session OR Supabase REST (service role).

Slow-migration path: set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY to use PostgREST;
otherwise existing DATABASE_URL / SQLite behavior unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from .models import Bookmark, Like, User, WeReadAccount, WeReadArticle, WeReadFeed
from .supabase_client import get_supabase_client, use_supabase_runtime

logger = logging.getLogger(__name__)

ENABLE = 1
INVALID = 0


@dataclass
class PoolAccount:
    """Minimal creds for WeRead upstream calls (replaces ORM row in pool)."""

    vid: str
    token: str


@dataclass
class FeedRow:
    id: int
    user_id: int
    mp_id: str
    mp_name: str
    mp_cover: str
    mp_intro: str
    update_time: int
    sync_time: int
    has_history: int
    status: int
    created_at: Optional[datetime]


@dataclass
class ArticleRow:
    article_id: str
    mp_id: str
    title: str
    pic_url: str
    publish_time: int


def _parse_ts(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            s = val.replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None
    return None


class AppRepository:
    def __init__(
        self,
        *,
        session: Optional[Session] = None,
        supabase: Optional[Any] = None,
    ):
        if (session is None) == (supabase is None):
            raise ValueError("AppRepository: pass exactly one of session= or supabase=")
        self._session = session
        self._sb = supabase

    @property
    def is_supabase(self) -> bool:
        return self._sb is not None

    # --- users ----------------------------------------------------------------
    def user_get_by_id(self, user_id: int) -> Optional[dict]:
        if self._session:
            u = self._session.query(User).filter(User.id == user_id).first()
            if not u:
                return None
            return {"id": u.id, "username": u.username, "hashed_password": u.hashed_password}
        r = (
            self._sb.table("users")
            .select("id, username, hashed_password")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = r.data or []
        return rows[0] if rows else None

    def user_get_by_username(self, username: str) -> Optional[dict]:
        if self._session:
            u = self._session.query(User).filter(User.username == username).first()
            if not u:
                return None
            return {"id": u.id, "username": u.username, "hashed_password": u.hashed_password}
        r = (
            self._sb.table("users")
            .select("id, username, hashed_password")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        rows = r.data or []
        return rows[0] if rows else None

    def user_create(self, username: str, hashed_password: str) -> dict:
        if self._session:
            u = User(username=username, hashed_password=hashed_password)
            self._session.add(u)
            self._session.commit()
            self._session.refresh(u)
            return {"id": u.id, "username": u.username}
        r = (
            self._sb.table("users")
            .insert({"username": username, "hashed_password": hashed_password})
            .select("id, username")
            .execute()
        )
        row = (r.data or [None])[0]
        if not row:
            raise RuntimeError("Supabase user insert returned no row")
        return {"id": row["id"], "username": row["username"]}

    # --- bookmarks ------------------------------------------------------------
    def bookmark_exists(self, user_id: int, article_id: str) -> bool:
        if self._session:
            return (
                self._session.query(Bookmark)
                .filter(Bookmark.user_id == user_id, Bookmark.article_id == article_id)
                .first()
                is not None
            )
        r = (
            self._sb.table("bookmarks")
            .select("id")
            .eq("user_id", user_id)
            .eq("article_id", article_id)
            .limit(1)
            .execute()
        )
        return bool(r.data)

    def bookmark_add(self, user_id: int, article_id: str) -> None:
        if self.bookmark_exists(user_id, article_id):
            return
        if self._session:
            self._session.add(Bookmark(user_id=user_id, article_id=article_id))
            self._session.commit()
            return
        self._sb.table("bookmarks").insert(
            {"user_id": user_id, "article_id": article_id}
        ).execute()

    def bookmark_remove(self, user_id: int, article_id: str) -> None:
        if self._session:
            b = (
                self._session.query(Bookmark)
                .filter(Bookmark.user_id == user_id, Bookmark.article_id == article_id)
                .first()
            )
            if b:
                self._session.delete(b)
                self._session.commit()
            return
        self._sb.table("bookmarks").delete().eq("user_id", user_id).eq(
            "article_id", article_id
        ).execute()

    def bookmark_list_article_ids(self, user_id: int) -> list[str]:
        if self._session:
            rows = (
                self._session.query(Bookmark.article_id)
                .filter(Bookmark.user_id == user_id)
                .all()
            )
            return [r[0] for r in rows]
        r = (
            self._sb.table("bookmarks")
            .select("article_id")
            .eq("user_id", user_id)
            .execute()
        )
        return [x["article_id"] for x in (r.data or [])]

    # --- likes ----------------------------------------------------------------
    def like_exists(self, user_id: int, article_id: str) -> bool:
        if self._session:
            return (
                self._session.query(Like)
                .filter(Like.user_id == user_id, Like.article_id == article_id)
                .first()
                is not None
            )
        r = (
            self._sb.table("likes")
            .select("id")
            .eq("user_id", user_id)
            .eq("article_id", article_id)
            .limit(1)
            .execute()
        )
        return bool(r.data)

    def like_add(self, user_id: int, article_id: str) -> None:
        if self.like_exists(user_id, article_id):
            return
        if self._session:
            self._session.add(Like(user_id=user_id, article_id=article_id))
            self._session.commit()
            return
        self._sb.table("likes").insert(
            {"user_id": user_id, "article_id": article_id}
        ).execute()

    def like_remove(self, user_id: int, article_id: str) -> None:
        if self._session:
            row = (
                self._session.query(Like)
                .filter(Like.user_id == user_id, Like.article_id == article_id)
                .first()
            )
            if row:
                self._session.delete(row)
                self._session.commit()
            return
        self._sb.table("likes").delete().eq("user_id", user_id).eq(
            "article_id", article_id
        ).execute()

    def like_list_article_ids(self, user_id: int) -> list[str]:
        if self._session:
            rows = (
                self._session.query(Like.article_id)
                .filter(Like.user_id == user_id)
                .all()
            )
            return [r[0] for r in rows]
        r = (
            self._sb.table("likes").select("article_id").eq("user_id", user_id).execute()
        )
        return [x["article_id"] for x in (r.data or [])]

    # --- weread accounts ------------------------------------------------------
    def weread_account_upsert(
        self, *, user_id: int, vid: str, token: str, name: str
    ) -> None:
        if self._session:
            acc = (
                self._session.query(WeReadAccount)
                .filter(WeReadAccount.user_id == user_id, WeReadAccount.vid == vid)
                .first()
            )
            if acc:
                acc.token = token
                acc.name = name
                acc.status = ENABLE
            else:
                self._session.add(
                    WeReadAccount(
                        user_id=user_id,
                        vid=vid,
                        token=token,
                        name=name,
                        status=ENABLE,
                    )
                )
            self._session.commit()
            return
        now = datetime.now(timezone.utc).isoformat()
        self._sb.table("weread_accounts").upsert(
            {
                "user_id": user_id,
                "vid": vid,
                "token": token,
                "name": name,
                "status": ENABLE,
                "updated_at": now,
            },
            on_conflict="user_id,vid",
        ).execute()

    def weread_account_delete(self, user_id: int, vid: str) -> bool:
        if self._session:
            acc = (
                self._session.query(WeReadAccount)
                .filter(WeReadAccount.user_id == user_id, WeReadAccount.vid == vid)
                .first()
            )
            if not acc:
                return False
            self._session.delete(acc)
            self._session.commit()
            return True
        r = (
            self._sb.table("weread_accounts")
            .delete()
            .eq("user_id", user_id)
            .eq("vid", vid)
            .execute()
        )
        return True

    def weread_accounts_list_for_ui(self, user_id: int) -> list[dict]:
        """status != 0 (hide INVALID)."""
        if self._session:
            rows = (
                self._session.query(WeReadAccount)
                .filter(
                    WeReadAccount.user_id == user_id,
                    WeReadAccount.status != INVALID,
                )
                .all()
            )
            return [
                {"vid": a.vid, "name": a.name, "status": a.status} for a in rows
            ]
        r = (
            self._sb.table("weread_accounts")
            .select("vid, name, status")
            .eq("user_id", user_id)
            .neq("status", INVALID)
            .execute()
        )
        return [
            {"vid": x["vid"], "name": x.get("name"), "status": x["status"]}
            for x in (r.data or [])
        ]

    def weread_pool_list_enabled(self, user_id: int) -> list[PoolAccount]:
        if self._session:
            rows = (
                self._session.query(WeReadAccount)
                .filter(
                    WeReadAccount.user_id == user_id,
                    WeReadAccount.status == ENABLE,
                    WeReadAccount.token.isnot(None),
                )
                .all()
            )
            return [PoolAccount(vid=a.vid, token=a.token) for a in rows]
        r = (
            self._sb.table("weread_accounts")
            .select("vid, token")
            .eq("user_id", user_id)
            .eq("status", ENABLE)
            .execute()
        )
        out = []
        for x in r.data or []:
            t = x.get("token")
            if t:
                out.append(PoolAccount(vid=x["vid"], token=t))
        return out

    def weread_account_count(self, user_id: int) -> int:
        if self._session:
            return (
                self._session.query(WeReadAccount)
                .filter(WeReadAccount.user_id == user_id)
                .count()
            )
        r = (
            self._sb.table("weread_accounts")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return (
            r.count
            if r.count is not None
            else len(r.data or [])
        )

    def weread_mark_invalid_by_vid(self, vid: str) -> None:
        if self._session:
            acc = (
                self._session.query(WeReadAccount)
                .filter(WeReadAccount.vid == vid)
                .first()
            )
            if acc:
                acc.status = INVALID
                self._session.commit()
            logger.warning("[weread] account(%s) session invalid, marked INVALID", vid)
            return
        self._sb.table("weread_accounts").update({"status": INVALID}).eq(
            "vid", vid
        ).execute()
        logger.warning("[weread] account(%s) session invalid, marked INVALID", vid)

    # --- weread feeds ---------------------------------------------------------
    def _feed_row_from_orm(self, f: WeReadFeed) -> FeedRow:
        return FeedRow(
            id=f.id,
            user_id=f.user_id,
            mp_id=f.mp_id,
            mp_name=f.mp_name or "",
            mp_cover=f.mp_cover or "",
            mp_intro=f.mp_intro or "",
            update_time=f.update_time or 0,
            sync_time=f.sync_time or 0,
            has_history=f.has_history or 0,
            status=f.status or 0,
            created_at=f.created_at,
        )

    def _feed_row_from_dict(self, d: dict) -> FeedRow:
        return FeedRow(
            id=d["id"],
            user_id=d["user_id"],
            mp_id=d["mp_id"],
            mp_name=d.get("mp_name") or "",
            mp_cover=d.get("mp_cover") or "",
            mp_intro=d.get("mp_intro") or "",
            update_time=d.get("update_time") or 0,
            sync_time=d.get("sync_time") or 0,
            has_history=d.get("has_history") if d.get("has_history") is not None else 1,
            status=d.get("status") if d.get("status") is not None else ENABLE,
            created_at=_parse_ts(d.get("created_at")),
        )

    def weread_feed_get(self, user_id: int, mp_id: str) -> Optional[FeedRow]:
        if self._session:
            f = (
                self._session.query(WeReadFeed)
                .filter(WeReadFeed.user_id == user_id, WeReadFeed.mp_id == mp_id)
                .first()
            )
            return self._feed_row_from_orm(f) if f else None
        r = (
            self._sb.table("weread_feeds")
            .select("*")
            .eq("user_id", user_id)
            .eq("mp_id", mp_id)
            .limit(1)
            .execute()
        )
        rows = r.data or []
        return self._feed_row_from_dict(rows[0]) if rows else None

    def weread_feed_upsert(self, user_id: int, mp: dict) -> FeedRow:
        mid = str(mp["id"])
        now = int(__import__("time").time())
        if self._session:
            feed = (
                self._session.query(WeReadFeed)
                .filter(WeReadFeed.user_id == user_id, WeReadFeed.mp_id == mid)
                .first()
            )
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
                self._session.add(feed)
            else:
                if mp.get("name"):
                    feed.mp_name = mp["name"]
                if mp.get("cover"):
                    feed.mp_cover = mp["cover"]
                if mp.get("intro"):
                    feed.mp_intro = mp["intro"]
                if mp.get("updateTime"):
                    feed.update_time = mp["updateTime"]
            self._session.commit()
            self._session.refresh(feed)
            return self._feed_row_from_orm(feed)

        existing = self.weread_feed_get(user_id, mid)
        if not existing:
            ins = {
                "user_id": user_id,
                "mp_id": mid,
                "mp_name": mp.get("name") or "",
                "mp_cover": mp.get("cover") or "",
                "mp_intro": mp.get("intro") or "",
                "update_time": mp.get("updateTime") or now,
                "sync_time": 0,
                "has_history": 1,
                "status": ENABLE,
            }
            r = self._sb.table("weread_feeds").insert(ins).select("*").execute()
            rows = r.data or []
            if not rows:
                raise RuntimeError("weread_feed insert failed")
            return self._feed_row_from_dict(rows[0])
        patch: dict = {}
        if mp.get("name"):
            patch["mp_name"] = mp["name"]
        if mp.get("cover"):
            patch["mp_cover"] = mp["cover"]
        if mp.get("intro"):
            patch["mp_intro"] = mp["intro"]
        if mp.get("updateTime"):
            patch["update_time"] = mp["updateTime"]
        if patch:
            self._sb.table("weread_feeds").update(patch).eq("id", existing.id).execute()
        g = self.weread_feed_get(user_id, mid)
        if not g:
            raise RuntimeError("weread_feed reload failed")
        return g

    def weread_feed_list_user(self, user_id: int) -> list[FeedRow]:
        if self._session:
            feeds = (
                self._session.query(WeReadFeed)
                .filter(WeReadFeed.user_id == user_id)
                .all()
            )
            return [self._feed_row_from_orm(f) for f in feeds]
        r = (
            self._sb.table("weread_feeds")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return [self._feed_row_from_dict(x) for x in (r.data or [])]

    def weread_feed_distinct_user_ids(self) -> list[int]:
        """User IDs that have at least one WeRead feed (for periodic Celery sync)."""
        if self._session:
            rows = self._session.query(WeReadFeed.user_id).distinct().all()
            return sorted({int(r[0]) for r in rows})
        r = self._sb.table("weread_feeds").select("user_id").execute()
        return sorted({int(x["user_id"]) for x in (r.data or [])})

    def weread_feed_update_sync(
        self, feed_id: int, sync_time: int, has_history: int
    ) -> None:
        if self._session:
            f = self._session.query(WeReadFeed).filter(WeReadFeed.id == feed_id).first()
            if f:
                f.sync_time = sync_time
                f.has_history = has_history
            return
        self._sb.table("weread_feeds").update(
            {"sync_time": sync_time, "has_history": has_history}
        ).eq("id", feed_id).execute()

    def weread_feed_delete_cascade(self, user_id: int, mp_id: str) -> None:
        if self._session:
            feed = (
                self._session.query(WeReadFeed)
                .filter(WeReadFeed.user_id == user_id, WeReadFeed.mp_id == mp_id)
                .first()
            )
            if feed:
                self._session.delete(feed)
                self._session.commit()
            return
        f = self.weread_feed_get(user_id, mp_id)
        if not f:
            return
        self._sb.table("weread_articles").delete().eq("feed_id", f.id).execute()
        self._sb.table("weread_feeds").delete().eq("id", f.id).execute()

    def weread_article_count_for_feed(self, feed_id: int) -> int:
        if self._session:
            return (
                self._session.query(WeReadArticle)
                .filter(WeReadArticle.feed_id == feed_id)
                .count()
            )
        r = (
            self._sb.table("weread_articles")
            .select("*", count="exact")
            .eq("feed_id", feed_id)
            .execute()
        )
        return (
            r.count
            if r.count is not None
            else len(r.data or [])
        )

    def weread_article_count_for_mp(self, mp_id: str) -> int:
        if self._session:
            return (
                self._session.query(WeReadArticle)
                .filter(WeReadArticle.mp_id == mp_id)
                .count()
            )
        r = (
            self._sb.table("weread_articles")
            .select("*", count="exact")
            .eq("mp_id", mp_id)
            .execute()
        )
        return (
            r.count
            if r.count is not None
            else len(r.data or [])
        )

    def weread_article_upsert(
        self,
        *,
        feed_id: int,
        mp_id: str,
        article_id: str,
        title: str,
        pic_url: str,
        publish_time: int,
    ) -> None:
        if self._session:
            existing = (
                self._session.query(WeReadArticle)
                .filter(
                    WeReadArticle.feed_id == feed_id,
                    WeReadArticle.article_id == article_id,
                )
                .first()
            )
            if existing:
                existing.title = title
                existing.pic_url = pic_url
                existing.publish_time = publish_time
                existing.mp_id = mp_id
            else:
                self._session.add(
                    WeReadArticle(
                        feed_id=feed_id,
                        mp_id=mp_id,
                        article_id=article_id,
                        title=title,
                        pic_url=pic_url,
                        publish_time=publish_time,
                    )
                )
            return
        now = datetime.now(timezone.utc).isoformat()
        self._sb.table("weread_articles").upsert(
            {
                "feed_id": feed_id,
                "mp_id": mp_id,
                "article_id": article_id,
                "title": title,
                "pic_url": pic_url,
                "publish_time": publish_time,
                "updated_at": now,
            },
            on_conflict="feed_id,article_id",
        ).execute()

    def weread_articles_list_user(
        self, user_id: int, mp_id: Optional[str] = None
    ) -> list[ArticleRow]:
        if self._session:
            q = (
                self._session.query(WeReadArticle)
                .join(WeReadFeed, WeReadArticle.feed_id == WeReadFeed.id)
                .filter(WeReadFeed.user_id == user_id)
            )
            if mp_id:
                q = q.filter(WeReadArticle.mp_id == mp_id)
            q = q.order_by(WeReadArticle.publish_time.desc())
            return [
                ArticleRow(
                    article_id=a.article_id,
                    mp_id=a.mp_id,
                    title=a.title or "Untitled",
                    pic_url=a.pic_url or "",
                    publish_time=a.publish_time or 0,
                )
                for a in q.all()
            ]
        fr = (
            self._sb.table("weread_feeds")
            .select("id")
            .eq("user_id", user_id)
            .execute()
        )
        ids = [x["id"] for x in (fr.data or [])]
        if not ids:
            return []
        q = (
            self._sb.table("weread_articles")
            .select("article_id, mp_id, title, pic_url, publish_time")
            .in_("feed_id", ids)
        )
        if mp_id:
            q = q.eq("mp_id", mp_id)
        r = q.order("publish_time", desc=True).execute()
        rows_out = []
        for x in r.data or []:
            pt = x.get("publish_time") or 0
            try:
                pt_i = int(pt)
            except (TypeError, ValueError):
                pt_i = 0
            rows_out.append(
                ArticleRow(
                    article_id=x["article_id"],
                    mp_id=x["mp_id"],
                    title=x.get("title") or "Untitled",
                    pic_url=x.get("pic_url") or "",
                    publish_time=pt_i,
                )
            )
        return rows_out

    def weread_article_belongs_to_user(self, user_id: int, article_id: str) -> bool:
        """True if this WeRead article row is under one of the user's subscribed feeds."""
        if self._session:
            return (
                self._session.query(WeReadArticle.id)
                .join(WeReadFeed, WeReadArticle.feed_id == WeReadFeed.id)
                .filter(
                    WeReadFeed.user_id == user_id,
                    WeReadArticle.article_id == article_id,
                )
                .first()
            ) is not None
        fr = (
            self._sb.table("weread_feeds")
            .select("id")
            .eq("user_id", user_id)
            .execute()
        )
        feed_ids = [x["id"] for x in (fr.data or [])]
        if not feed_ids:
            return False
        r = (
            self._sb.table("weread_articles")
            .select("id")
            .eq("article_id", article_id)
            .in_("feed_id", feed_ids)
            .limit(1)
            .execute()
        )
        return bool(r.data)

    def weread_articles_as_feed_dicts(
        self, user_id: int, article_ids: frozenset[str]
    ) -> dict[str, dict[str, Any]]:
        """Build main-feed-shaped dicts for WeRead articles (for /user/likes, /user/bookmarks)."""
        if not article_ids:
            return {}
        out: dict[str, dict[str, Any]] = {}
        if self._session:
            q = (
                self._session.query(WeReadArticle, WeReadFeed)
                .join(WeReadFeed, WeReadArticle.feed_id == WeReadFeed.id)
                .filter(WeReadFeed.user_id == user_id)
                .filter(WeReadArticle.article_id.in_(article_ids))
            )
            for a, feed in q.all():
                pt = a.publish_time or 0
                try:
                    published = datetime.fromtimestamp(int(pt), tz=timezone.utc)
                except (TypeError, ValueError, OSError):
                    published = datetime.now(timezone.utc)
                mp_name = feed.mp_name or feed.mp_id or "WeChat"
                wx_url = f"https://mp.weixin.qq.com/s/{a.article_id}"
                summary = f"From {mp_name} on WeChat (official account)."
                body = (
                    "Full text is available on WeChat. Use the source link below to open the original article."
                )
                out[a.article_id] = {
                    "id": a.article_id,
                    "title": a.title or "Untitled",
                    "content": f"{summary}\n\n{body}",
                    "url": wx_url,
                    "source_id": a.mp_id or "weixin",
                    "source_name": mp_name,
                    "published_at": published,
                    "topic": "wechat",
                    "topic_confidence": 1.0,
                    "logo_url": feed.mp_cover or "",
                    "main_image": a.pic_url or "",
                    "summary": summary,
                    "authors": mp_name,
                }
            return out

        fr = (
            self._sb.table("weread_feeds")
            .select("id, mp_name, mp_cover, mp_id")
            .eq("user_id", user_id)
            .execute()
        )
        feed_rows = fr.data or []
        feed_ids = [x["id"] for x in feed_rows]
        feed_map = {x["id"]: x for x in feed_rows}
        if not feed_ids:
            return {}
        id_list = list(article_ids)
        r = (
            self._sb.table("weread_articles")
            .select("*")
            .in_("article_id", id_list)
            .in_("feed_id", feed_ids)
            .execute()
        )
        for x in r.data or []:
            aid = x.get("article_id")
            if not aid or aid in out:
                continue
            f = feed_map.get(x.get("feed_id"))
            mp_name = (f.get("mp_name") if f else None) or x.get("mp_id") or "WeChat"
            mp_cover = (f.get("mp_cover") if f else None) or ""
            mp_id = (f.get("mp_id") if f else None) or x.get("mp_id") or "wechat"
            pt = x.get("publish_time") or 0
            try:
                published = datetime.fromtimestamp(int(pt), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                published = datetime.now(timezone.utc)
            wx_url = f"https://mp.weixin.qq.com/s/{aid}"
            summary = f"From {mp_name} on WeChat (official account)."
            body = (
                "Full text is available on WeChat. Use the source link below to open the original article."
            )
            out[aid] = {
                "id": aid,
                "title": x.get("title") or "Untitled",
                "content": f"{summary}\n\n{body}",
                "url": wx_url,
                "source_id": mp_id,
                "source_name": mp_name,
                "published_at": published,
                "topic": "wechat",
                "topic_confidence": 1.0,
                "logo_url": mp_cover,
                "main_image": x.get("pic_url") or "",
                "summary": summary,
                "authors": mp_name,
            }
        return out

    def session_commit(self) -> None:
        """No-op for Supabase (each call commits). Flush SQLAlchemy pending article batch."""
        if self._session:
            self._session.commit()


def get_repo():
    """FastAPI dependency: one repository per request."""
    if use_supabase_runtime():
        yield AppRepository(supabase=get_supabase_client())
    else:
        from .database import SessionLocal

        db = SessionLocal()
        try:
            yield AppRepository(session=db)
        finally:
            db.close()
