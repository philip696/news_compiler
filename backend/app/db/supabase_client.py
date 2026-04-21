"""Supabase REST client (PostgREST) for runtime data when configured."""

from __future__ import annotations

import os
from functools import lru_cache

from supabase import Client, create_client


def use_supabase_runtime() -> bool:
    """Use Supabase HTTP API for reads/writes instead of SQLAlchemy.

    Set both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (server-side only;
    never expose the service role in the browser).
    """
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return bool(url and key)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for Supabase runtime"
        )
    return create_client(url, key)
