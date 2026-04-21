from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    weread_accounts = relationship("WeReadAccount", back_populates="user", cascade="all, delete-orphan")
    weread_feeds = relationship("WeReadFeed", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    article_id = Column(String, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="bookmarks")

    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_article_bookmark"),)


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    article_id = Column(String, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="likes")

    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_article_like"),)


# ---------------------------------------------------------------------------
# WeRead / WeChat Reading integration (ported from test/python)
#
# status codes mirror the Node service: 0=INVALID, 1=ENABLE, 2=DISABLE
# ---------------------------------------------------------------------------


class WeReadAccount(Base):
    """A WeChat Reading session (pool member) owned by a GEB user."""

    __tablename__ = "weread_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    vid = Column(String, index=True, nullable=False)  # WeRead uid returned at login
    token = Column(String, nullable=False)
    name = Column(String, nullable=True)
    status = Column(Integer, default=1, nullable=False)  # 1=ENABLE
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="weread_accounts")

    __table_args__ = (UniqueConstraint("user_id", "vid", name="uq_user_vid"),)

    def __repr__(self):
        return f"<WeReadAccount user_id={self.user_id} vid={self.vid}>"


class WeReadFeed(Base):
    """A WeChat Official Account (mp) subscribed to by a GEB user."""

    __tablename__ = "weread_feeds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    mp_id = Column(String, index=True, nullable=False)  # biz id
    mp_name = Column(String, default="")
    mp_cover = Column(String, default="")
    mp_intro = Column(String, default="")
    update_time = Column(Integer, default=0)  # epoch seconds
    sync_time = Column(Integer, default=0)    # epoch seconds
    has_history = Column(Integer, default=1)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="weread_feeds")
    articles = relationship("WeReadArticle", back_populates="feed", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "mp_id", name="uq_user_mp"),)

    def __repr__(self):
        return f"<WeReadFeed user_id={self.user_id} mp_id={self.mp_id}>"


class WeReadArticle(Base):
    """An article fetched from a WeChat Official Account."""

    __tablename__ = "weread_articles"

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("weread_feeds.id"), index=True, nullable=False)
    article_id = Column(String, index=True, nullable=False)  # article id from WeRead
    mp_id = Column(String, index=True, nullable=False)
    title = Column(String, default="Untitled")
    pic_url = Column(String, default="")
    publish_time = Column(Integer, default=0, index=True)  # epoch seconds
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    feed = relationship("WeReadFeed", back_populates="articles")

    __table_args__ = (UniqueConstraint("feed_id", "article_id", name="uq_feed_article"),)

    def __repr__(self):
        return f"<WeReadArticle article_id={self.article_id} title={self.title}>"
