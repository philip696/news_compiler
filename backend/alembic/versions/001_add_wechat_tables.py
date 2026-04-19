"""Add WeChat integration tables

Revision ID: 001
Revises: 
Create Date: 2026-04-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create WeChat integration tables"""
    
    # Create wechat_auth table
    op.create_table(
        'wechat_auth',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('wechat_openid', sa.String(128), nullable=False),
        sa.Column('wechat_unionid', sa.String(128), nullable=True),
        sa.Column('access_token_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(), nullable=False),
        sa.Column('scopes', sa.String(255), nullable=True),
        sa.Column('raw_user_info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_wechat_auth_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_wechat_auth_user_id'),
        sa.UniqueConstraint('wechat_openid', name='uq_wechat_openid'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    
    # Create indexes for wechat_auth
    op.create_index('idx_wechat_openid', 'wechat_auth', ['wechat_openid'])
    op.create_index('idx_wechat_unionid', 'wechat_auth', ['wechat_unionid'])
    op.create_index('idx_token_expiry', 'wechat_auth', ['token_expiry'])
    op.create_index('idx_wechat_user_id', 'wechat_auth', ['user_id'])

    # Create wechat_accounts table
    op.create_table(
        'wechat_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wechat_account_id', sa.String(128), nullable=False),
        sa.Column('wechat_account_name', sa.String(255), nullable=False),
        sa.Column('wechat_account_avatar', sa.String(2048), nullable=True),
        sa.Column('account_intro', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('account_type', sa.String(50), nullable=False, server_default='unknown'),
        sa.Column('last_sync_time', sa.DateTime(), nullable=True),
        sa.Column('sync_status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('sync_retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latest_error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wechat_account_id', name='uq_wechat_account_id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    
    # Create indexes for wechat_accounts
    op.create_index('idx_account_id', 'wechat_accounts', ['wechat_account_id'])
    op.create_index('idx_account_status', 'wechat_accounts', ['sync_status'])
    op.create_index('idx_account_created', 'wechat_accounts', ['created_at'])
    op.create_index('idx_account_sync_time', 'wechat_accounts', ['last_sync_time'])

    # Create wechat_subscriptions table (junction table)
    op.create_table(
        'wechat_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wechat_auth_id', sa.Integer(), nullable=False),
        sa.Column('wechat_account_id', sa.Integer(), nullable=False),
        sa.Column('is_muted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('subscribed_at', sa.DateTime(), nullable=False),
        sa.Column('unsubscribed_at', sa.DateTime(), nullable=True),
        sa.Column('notification_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_read_article_id', sa.String(128), nullable=True),
        sa.ForeignKeyConstraint(['wechat_auth_id'], ['wechat_auth.id'], name='fk_sub_auth_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wechat_account_id'], ['wechat_accounts.id'], name='fk_sub_account_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wechat_auth_id', 'wechat_account_id', name='uq_user_account_subscription'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    
    # Create indexes for wechat_subscriptions
    op.create_index('idx_sub_auth', 'wechat_subscriptions', ['wechat_auth_id'])
    op.create_index('idx_sub_account', 'wechat_subscriptions', ['wechat_account_id'])
    op.create_index('idx_sub_muted', 'wechat_subscriptions', ['is_muted'])
    op.create_index('idx_sub_enabled', 'wechat_subscriptions', ['notification_enabled'])

    # Create wechat_articles_cache table
    op.create_table(
        'wechat_articles_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.String(128), nullable=False),
        sa.Column('wechat_account_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('publish_time', sa.DateTime(), nullable=True),
        sa.Column('article_url', sa.String(2048), nullable=True),
        sa.Column('image_url', sa.String(2048), nullable=True),
        sa.Column('video_url', sa.String(2048), nullable=True),
        sa.Column('cached_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_summarized', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('embedding_vector', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['wechat_account_id'], ['wechat_accounts.id'], name='fk_article_account_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('article_id', name='uq_article_id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    
    # Create indexes for wechat_articles_cache
    op.create_index('idx_article_id', 'wechat_articles_cache', ['article_id'])
    op.create_index('idx_article_account', 'wechat_articles_cache', ['wechat_account_id'])
    op.create_index('idx_article_title', 'wechat_articles_cache', ['title'], mysql_length={'title': 100})
    op.create_index('idx_article_publish', 'wechat_articles_cache', ['publish_time'])
    op.create_index('idx_article_expires', 'wechat_articles_cache', ['expires_at'])
    op.create_index('idx_article_cached', 'wechat_articles_cache', ['cached_at'])

    # Create wechat_sync_logs table
    op.create_table(
        'wechat_sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wechat_account_id', sa.Integer(), nullable=False),
        sa.Column('sync_status', sa.String(50), nullable=False),
        sa.Column('articles_fetched', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('articles_new', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('articles_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('articles_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('sync_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('api_call_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('rate_limit_remaining', sa.Integer(), nullable=True),
        sa.Column('sync_timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['wechat_account_id'], ['wechat_accounts.id'], name='fk_sync_account_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
    )
    
    # Create indexes for wechat_sync_logs
    op.create_index('idx_sync_account', 'wechat_sync_logs', ['wechat_account_id'])
    op.create_index('idx_sync_time', 'wechat_sync_logs', ['sync_timestamp'])
    op.create_index('idx_sync_status', 'wechat_sync_logs', ['sync_status'])


def downgrade() -> None:
    """Drop WeChat integration tables"""
    
    # Drop in reverse order of creation (respecting foreign keys)
    op.drop_table('wechat_sync_logs')
    op.drop_table('wechat_articles_cache')
    op.drop_table('wechat_subscriptions')
    op.drop_table('wechat_accounts')
    op.drop_table('wechat_auth')
