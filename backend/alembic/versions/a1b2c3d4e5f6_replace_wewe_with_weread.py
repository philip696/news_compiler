"""replace wewe_rss tables with weread tables

Revision ID: a1b2c3d4e5f6
Revises: 73f0d4574c63
Create Date: 2026-04-21

Drops the old `wechat_official_accounts` and `wechat_cached_articles` tables
(which were tied to the deleted WeWe-RSS integration) and creates the new
`weread_accounts`, `weread_feeds`, and `weread_articles` tables used by the
ported test/python WeRead service.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "73f0d4574c63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # --- drop old WeWe tables if they exist ---
    existing = set(inspector.get_table_names())
    if "wechat_cached_articles" in existing:
        op.drop_table("wechat_cached_articles")
    if "wechat_official_accounts" in existing:
        op.drop_table("wechat_official_accounts")

    # --- weread_accounts ---
    op.create_table(
        "weread_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("vid", sa.String(), nullable=False, index=True),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "vid", name="uq_user_vid"),
    )

    # --- weread_feeds ---
    op.create_table(
        "weread_feeds",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("mp_id", sa.String(), nullable=False, index=True),
        sa.Column("mp_name", sa.String(), nullable=True, server_default=""),
        sa.Column("mp_cover", sa.String(), nullable=True, server_default=""),
        sa.Column("mp_intro", sa.String(), nullable=True, server_default=""),
        sa.Column("update_time", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("sync_time", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("has_history", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("status", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "mp_id", name="uq_user_mp"),
    )

    # --- weread_articles ---
    op.create_table(
        "weread_articles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("feed_id", sa.Integer(), sa.ForeignKey("weread_feeds.id"), index=True, nullable=False),
        sa.Column("article_id", sa.String(), nullable=False, index=True),
        sa.Column("mp_id", sa.String(), nullable=False, index=True),
        sa.Column("title", sa.String(), nullable=True, server_default="Untitled"),
        sa.Column("pic_url", sa.String(), nullable=True, server_default=""),
        sa.Column("publish_time", sa.Integer(), nullable=True, server_default="0", index=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("feed_id", "article_id", name="uq_feed_article"),
    )


def downgrade() -> None:
    op.drop_table("weread_articles")
    op.drop_table("weread_feeds")
    op.drop_table("weread_accounts")
