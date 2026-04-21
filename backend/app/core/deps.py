from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from ..db.database import get_db
from ..db.models import User
from .security import decode_access_token, is_jwt_error

logger = logging.getLogger(__name__)
http_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> dict:
    """Resolve the current user from the Authorization header.

    Adds debug logging for missing/invalid tokens to help diagnose 401s.
    """
    # Log some request context useful for debugging auth failures
    try:
        auth_header_present = bool(request.headers.get("authorization") or request.headers.get("Authorization"))
    except Exception:
        auth_header_present = False

    if not credentials:
        logger.warning(
            "Unauthorized request (missing bearer token): path=%s method=%s client=%s auth_header_present=%s",
            request.url.path,
            request.method,
            getattr(request.client, "host", None),
            auth_header_present,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        # Log JWT decode errors for debugging (without printing token value)
        logger.warning(
            "Invalid JWT for request %s from client=%s: %s",
            request.url.path,
            getattr(request.client, "host", None),
            str(exc),
        )
        if is_jwt_error(exc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        raise

    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        logger.warning(
            "JWT missing user_id/sub claim for request %s from client=%s: payload_keys=%s",
            request.url.path,
            getattr(request.client, "host", None),
            list(payload.keys()) if isinstance(payload, dict) else type(payload),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Query database for user
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        logger.warning(
            "Authenticated token references missing user id=%s for request %s",
            user_id,
            request.url.path,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Return a payload compatible with existing code (include 'sub' and 'id')
    return {"sub": str(user.id), "id": user.id, "username": user.username}
