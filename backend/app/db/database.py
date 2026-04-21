import logging
import os
import socket
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
db_dir = Path(__file__).parent.parent.parent / "data"
db_dir.mkdir(parents=True, exist_ok=True)

# Database URL - supports both SQLite (local) and PostgreSQL (production)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_dir}/geb.db")


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
    infos = socket.getaddrinfo(
        parsed.host, port, socket.AF_INET, socket.SOCK_STREAM
    )
    ipv4 = infos[0][4][0]
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


# Engine configuration based on database type
engine_kwargs = {}
if "sqlite" in DATABASE_URL:
    # SQLite specific settings
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["echo"] = os.getenv("SQL_ECHO", "false").lower() == "true"
elif "postgresql" in DATABASE_URL:
    # PostgreSQL specific settings - use connection pooling
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    engine_kwargs["pool_pre_ping"] = True  # Test connections before using
    engine_kwargs["echo"] = os.getenv("SQL_ECHO", "false").lower() == "true"
    if _use_ipv4_hostaddr_for_postgres():
        try:
            engine_kwargs["connect_args"] = _postgres_ipv4_connect_args(DATABASE_URL)
            logger.info(
                "PostgreSQL: using IPv4 hostaddr for %s (set DATABASE_IPV4_ONLY=false to disable)",
                make_url(DATABASE_URL).host,
            )
        except OSError as e:
            logger.warning(
                "IPv4 hostaddr resolve failed (%s); using default DNS. "
                "If deploy fails with IPv6 unreachable, set DATABASE_IPV4_ONLY=true after fixing DNS, "
                "or use Supabase pooler (port 6543) / SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.",
                e,
            )

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
