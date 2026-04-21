import logging
import os
import socket
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

from .supabase_client import use_supabase_runtime

logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
db_dir = Path(__file__).parent.parent.parent / "data"
db_dir.mkdir(parents=True, exist_ok=True)

# Database URL - supports both SQLite (local) and PostgreSQL (production)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_dir}/geb.db")

_sql_echo = os.getenv("SQL_ECHO", "false").lower() == "true"


def _use_ipv4_hostaddr_for_postgres() -> bool:
    """Prefer IPv4 libpq hostaddr for hosts that often resolve AAAA-first (unreachable on Railway etc.)."""
    flag = os.getenv("DATABASE_IPV4_ONLY", "").strip().lower()
    if flag in ("0", "false", "no"):
        return False
    if flag in ("1", "true", "yes"):
        return True
    # Auto: Supabase direct DB URLs (db.<ref>.supabase.co) → IPv6-first DNS breaks many PaaS egress.
    u = DATABASE_URL.lower()
    return "postgresql" in u and "db." in u and ".supabase.co" in u


def _first_ipv4(host: str, port: int) -> str:
    """Return first IPv4 for host, or raise if DNS exposes none (common for db.*.supabase.co from some resolvers)."""
    infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    for fam, _, _, _, sockaddr in infos:
        if fam == socket.AF_INET:
            return sockaddr[0]
    raise OSError(
        socket.EAI_NONAME,
        f"no IPv4 address in DNS for {host!r} (only IPv6 or no data). "
        "Supabase direct db.* hostnames often require the Transaction pooler URI (port 6543) "
        "or SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY on Railway.",
    )


def _postgres_ipv4_connect_args(database_url: str) -> dict:
    """Resolve DB hostname to IPv4 for libpq `hostaddr`.

    Many VPS / Docker hosts have no working IPv6 route. Supabase direct URLs
    often resolve to AAAA first, causing: "Network is unreachable".

    libpq uses `hostaddr` for the TCP target but still uses `host` for TLS
    verification and GSS, so this is safe for sslmode=require.

    Supabase expects SSL; pool/direct URLs sometimes omit sslmode in the URI.
    Passing port/sslmode/connect_timeout explicitly avoids ambiguous merges with SQLAlchemy's URL → psycopg2.
    """
    parsed = make_url(database_url)
    if not parsed.host:
        return {}
    port = parsed.port or 5432
    ipv4 = _first_ipv4(parsed.host, port)
    query = dict(parsed.query)
    sslmode = query.get("sslmode")
    if not sslmode and "supabase" in parsed.host.lower():
        sslmode = "require"
    if not sslmode:
        sslmode = "prefer"
    connect_timeout = int(os.getenv("PGCONNECT_TIMEOUT", "15"))
    return {
        "host": parsed.host,
        "hostaddr": ipv4,
        "port": port,
        "sslmode": sslmode,
        "connect_timeout": connect_timeout,
    }


def _build_engine():
    """Create SQLAlchemy engine. When PostgREST is the runtime, avoid opening direct db.* Postgres at import."""
    if "sqlite" in DATABASE_URL:
        return create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},
            echo=_sql_echo,
        )

    if "postgresql" not in DATABASE_URL:
        return create_engine(DATABASE_URL, echo=_sql_echo)

    # Direct db.*.supabase.co + PostgREST: app never uses this engine for requests (get_repo uses HTTP).
    if _use_ipv4_hostaddr_for_postgres() and use_supabase_runtime():
        logger.warning(
            "Supabase PostgREST is configured (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY): "
            "SQLAlchemy engine is bound to sqlite:///:memory: so DATABASE_URL is not opened at import "
            "(direct db.* often has no IPv4 from Railway). Auth and data use HTTPS. "
            "Use Transaction pooler DATABASE_URL for Alembic or Celery SQLAlchemy paths."
        )
        return create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            echo=_sql_echo,
        )

    engine_kwargs: dict = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_pre_ping": True,
        "echo": _sql_echo,
    }
    if _use_ipv4_hostaddr_for_postgres():
        try:
            engine_kwargs["connect_args"] = _postgres_ipv4_connect_args(DATABASE_URL)
            logger.info(
                "PostgreSQL: using IPv4 hostaddr for %s (set DATABASE_IPV4_ONLY=false to try default DNS)",
                make_url(DATABASE_URL).host,
            )
        except OSError as e:
            raise RuntimeError(
                "Cannot open Supabase direct Postgres URL from this host (IPv4 DNS/connection required). "
                f"Details: {e}\n"
                "Fix one of:\n"
                "  • Set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY (recommended on Railway).\n"
                "  • Supabase Dashboard → Connect → 'Transaction pooler' → DATABASE_URL (port 6543).\n"
                "  • DATABASE_IPV4_ONLY=false only if the host resolves to reachable IPv4."
            ) from e

    return create_engine(DATABASE_URL, **engine_kwargs)


engine = _build_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
