-- =============================================================================
-- GEB unified schema (PostgreSQL / Supabase SQL Editor)
-- =============================================================================
-- One database for: users, bookmarks, likes, and WeChat / WeRead (accounts,
-- feeds, articles). Matches backend/app/db/models.py + SQLAlchemy defaults.
--
-- How to use:
--   1. Supabase Dashboard → SQL → New query → paste this file → Run.
--   2. Set backend/.env DATABASE_URL to your Supabase Postgres connection string.
--   3. Prefer `alembic upgrade head` for ongoing migrations; this file is the
--      bootstrap / manual equivalent for a fresh project.
--
-- Optional cleanup (only if you still have the old WeWe-RSS tables):
--   DROP TABLE IF EXISTS wechat_cached_articles CASCADE;
--   DROP TABLE IF EXISTS wechat_official_accounts CASCADE;
-- =============================================================================

BEGIN;

-- ----------------------------------------------------------------------------- users
CREATE TABLE IF NOT EXISTS public.users (
    id          SERIAL PRIMARY KEY,
    username    TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_username UNIQUE (username)
);

-- ----------------------------------------------------------------------------- bookmarks
CREATE TABLE IF NOT EXISTS public.bookmarks (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    article_id  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_article_bookmark UNIQUE (user_id, article_id)
);

CREATE INDEX IF NOT EXISTS ix_bookmarks_user_id ON public.bookmarks (user_id);
CREATE INDEX IF NOT EXISTS ix_bookmarks_article_id ON public.bookmarks (article_id);

-- ----------------------------------------------------------------------------- likes
CREATE TABLE IF NOT EXISTS public.likes (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    article_id  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_article_like UNIQUE (user_id, article_id)
);

CREATE INDEX IF NOT EXISTS ix_likes_user_id ON public.likes (user_id);
CREATE INDEX IF NOT EXISTS ix_likes_article_id ON public.likes (article_id);

-- ----------------------------------------------------------------------------- weread_accounts (WeChat Reading pool per GEB user)
CREATE TABLE IF NOT EXISTS public.weread_accounts (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    vid         TEXT NOT NULL,
    token       TEXT NOT NULL,
    name        TEXT,
    status      INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_vid UNIQUE (user_id, vid)
);

CREATE INDEX IF NOT EXISTS ix_weread_accounts_user_id ON public.weread_accounts (user_id);
CREATE INDEX IF NOT EXISTS ix_weread_accounts_vid ON public.weread_accounts (vid);

-- ----------------------------------------------------------------------------- weread_feeds (subscribed 公众号 per user)
CREATE TABLE IF NOT EXISTS public.weread_feeds (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    mp_id        TEXT NOT NULL,
    mp_name      TEXT DEFAULT ''::TEXT,
    mp_cover     TEXT DEFAULT ''::TEXT,
    mp_intro     TEXT DEFAULT ''::TEXT,
    update_time  INTEGER DEFAULT 0,
    sync_time    INTEGER DEFAULT 0,
    has_history  INTEGER DEFAULT 1,
    status       INTEGER DEFAULT 1,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_mp UNIQUE (user_id, mp_id)
);

CREATE INDEX IF NOT EXISTS ix_weread_feeds_user_id ON public.weread_feeds (user_id);
CREATE INDEX IF NOT EXISTS ix_weread_feeds_mp_id ON public.weread_feeds (mp_id);

-- ----------------------------------------------------------------------------- weread_articles (cached articles per feed)
CREATE TABLE IF NOT EXISTS public.weread_articles (
    id            SERIAL PRIMARY KEY,
    feed_id       INTEGER NOT NULL REFERENCES public.weread_feeds (id) ON DELETE CASCADE,
    article_id    TEXT NOT NULL,
    mp_id         TEXT NOT NULL,
    title         TEXT DEFAULT 'Untitled'::TEXT,
    pic_url       TEXT DEFAULT ''::TEXT,
    publish_time  INTEGER DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_feed_article UNIQUE (feed_id, article_id)
);

CREATE INDEX IF NOT EXISTS ix_weread_articles_feed_id ON public.weread_articles (feed_id);
CREATE INDEX IF NOT EXISTS ix_weread_articles_article_id ON public.weread_articles (article_id);
CREATE INDEX IF NOT EXISTS ix_weread_articles_mp_id ON public.weread_articles (mp_id);
CREATE INDEX IF NOT EXISTS ix_weread_articles_publish_time ON public.weread_articles (publish_time);

COMMIT;
