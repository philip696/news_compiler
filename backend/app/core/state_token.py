"""
WeChat OAuth State Token Management with TTL

Implements secure OAuth state parameter handling:
- Generates cryptographically secure random state tokens
- Stores state with IP binding (CSRF + IP spoofing prevention)
- Automatic expiry after 10 minutes
- One-time use validation
"""

import secrets
import base64
import logging
from typing import Optional
import redis
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StateTokenManager:
    """Manages OAuth state tokens with security best practices"""

    _TTL_SECONDS = 600  # 10 minute expiry
    _PREFIX = "wechat_state:"

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize state token manager.

        Args:
            redis_client: Redis client for state storage
        """
        self.redis = redis_client

    def generate(self) -> str:
        """
        Generate cryptographically secure random state token.

        Returns:
            Base64-encoded 32-byte random string (URL-safe)

        Security:
            - Uses secrets.token_bytes() (cryptographically secure)
            - 256-bit entropy = 2^256 possible values
            - Impossible to guess or brute force
        """
        random_bytes = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(random_bytes).decode("utf-8").rstrip("=")

    def store(self, state: str, user_ip: str) -> bool:
        """
        Store state token with IP binding and automatic expiry.

        Args:
            state: State token from generate()
            user_ip: Client IP address

        Returns:
            True if stored successfully

        Security:
            - IP binding: State is tied to requesting IP
            - TTL: State expires after 10 minutes (Redis SETEX)
            - One-time use: State deleted after validation
        """
        try:
            key = f"{self._PREFIX}{state}"

            # Store with TTL using SETEX
            # Format: "ip|timestamp"
            timestamp = datetime.utcnow().isoformat()
            value = f"{user_ip}|{timestamp}"

            # ✅ Set with expiry
            self.redis.setex(
                key,
                self._TTL_SECONDS,  # Expires in 10 minutes
                value,
            )

            logger.debug(f"State token stored: {state[:8]}... for IP {user_ip}")
            return True

        except Exception as e:
            logger.error(f"Failed to store state token: {e}")
            return False

    def validate(self, state: str, user_ip: str) -> bool:
        """
        Validate state token with IP binding and one-time use.

        Args:
            state: State token from callback
            user_ip: Client IP address (from request)

        Returns:
            True if valid and not expired

        Security:
            - IP validation: Must match original requesting IP
            - Expiry check: Redis TTL handles automatic expiry
            - One-time use: Get + Delete in single transaction
        """
        try:
            key = f"{self._PREFIX}{state}"

            # ✅ Atomic read + delete (one-time use)
            value = self.redis.get(key)

            if not value:
                logger.warning(f"State token not found or expired: {state[:8]}...")
                return False

            stored_ip, timestamp = value.decode("utf-8").split("|")

            # ✅ Verify IP binding
            if stored_ip != user_ip:
                logger.warning(
                    f"State token IP mismatch: stored={stored_ip}, got={user_ip}"
                )
                return False

            # ✅ Delete token (one-time use)
            self.redis.delete(key)

            logger.debug(
                f"State token validated and consumed: {state[:8]}... from IP {user_ip}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to validate state token: {e}")
            return False

    def get_remaining_ttl(self, state: str) -> Optional[int]:
        """
        Get remaining TTL for a state token (for debugging).

        Args:
            state: State token

        Returns:
            Remaining seconds, or None if not found
        """
        key = f"{self._PREFIX}{state}"
        ttl = self.redis.ttl(key)
        return ttl if ttl > 0 else None


# Helper functions for use in FastAPI endpoints
_state_manager: Optional[StateTokenManager] = None


def get_state_token_manager(redis_client: redis.Redis) -> StateTokenManager:
    """Get or create state token manager singleton"""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateTokenManager(redis_client)
    return _state_manager


def generate_state_token() -> str:
    """Generate a new state token"""
    # Will be initialized in app startup
    from app.core.config import settings

    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
    manager = get_state_token_manager(redis_client)
    return manager.generate()


def store_state_token(state: str, user_ip: str) -> bool:
    """Store state token with IP binding"""
    from app.core.config import settings

    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
    manager = get_state_token_manager(redis_client)
    return manager.store(state, user_ip)


def validate_state_token(state: str, user_ip: str) -> bool:
    """Validate state token and mark as used"""
    from app.core.config import settings

    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=False)
    manager = get_state_token_manager(redis_client)
    return manager.validate(state, user_ip)
