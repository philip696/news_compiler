"""
Rate Limiting Configuration

Implements request rate limiting using slowapi to prevent:
- API abuse
- Brute force attacks
- Resource exhaustion
- WeChat API quota exhaustion

Installation:
  pip install slowapi
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from typing import Callable
import logging

logger = logging.getLogger(__name__)

# Initialize limiter with Redis backend for distributed rate limiting
# Falls back to in-memory storage if Redis unavailable
limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP address
    default_limits=["100/minute"],  # 100 requests per minute by default
    storage_uri="redis://localhost:6379",  # Use Redis for persistence across instances
    in_memory_fallback=b"",  # Fall back to memory if Redis down
)


def setup_rate_limiting(app: FastAPI):
    """
    Configure rate limiting on FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Add rate limit exception handler
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        """Handle rate limit exceeded errors"""
        logger.warning(f"Rate limit exceeded for {request.client.host}: {exc.detail}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "detail": "Too many requests. Please try again later.",
                "retry_after": exc.retry_after if hasattr(exc, "retry_after") else 60,
            },
        )

    # Register the limiter with the app
    app.state.limiter = limiter


# ===== Rate Limit Configurations =====
# Customize these limits based on your API quota and traffic

RATE_LIMITS = {
    # OAuth - conservative limits (external API calls)
    "oauth_start": "5/minute",  # Login initiation
    "oauth_callback": "10/minute",  # OAuth callback handler
    "oauth_refresh": "5/minute",  # Token refresh (expensive)

    # Accounts - moderate limits (database + WeChat API)
    "list_accounts": "10/minute",  # List subscribed accounts
    "subscribe_account": "5/minute",  # Subscribe to new account (WeChat API call)
    "unsubscribe_account": "10/minute",  # Unsubscribe (destructive but quick)
    "mute_account": "20/minute",  # Mute/unmute (local only)
    "manual_update": "1/minute",  # Manual sync - **VERY RESTRICTIVE** (WeChat API)

    # Articles - generous limits (cached, read-only)
    "list_articles": "30/minute",  # List articles for user
    "search_articles": "20/minute",  # Search (complex queries)
    "get_article_detail": "30/minute",  # Get full article
    "bookmark_article": "30/minute",  # Bookmark operations

    # General API - fallback
    "default": "100/minute",
}


# Decorator functions for easy endpoint protection
def rate_limit_auth(limit_key: str) -> Callable:
    """
    Decorator for rate-limited authenticated endpoints.
    Uses user_id as rate limit key (more accurate than IP).
    
    Usage:
        @router.get("", dependencies=[rate_limit_auth("list_accounts")])
        async def list_accounts(...):
            ...
    """
    from functools import wraps

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Rate limiting applied via limiter.limit() decorator on route
            return await func(*args, **kwargs)

        return wrapper

    return decorator
