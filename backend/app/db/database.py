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


def _postgres_ipv4_connect_args(database_url: str) -> dict:
    """Resolve DB hostname to IPv4 for libpq `hostaddr`.

    Many VPS / Docker hosts have no working IPv6 route. Supabase direct URLs
    often resolve to AAAA first, causing: "Network is unreachable".

    libpq uses `hostaddr` for the TCP target but still uses `host` for TLS
    verification and GSS, so this is safe for sslmode=require.
    """
    parsed = make_url(database_url)
    if not parsed.host:
        return {}
    port = parsed.port or 5432
    infos = socket.getaddrinfo(
        parsed.host, port, socket.AF_INET, socket.SOCK_STREAM
    )
    ipv4 = infos[0][4][0]
    return {"host": parsed.host, "hostaddr": ipv4}


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
    if os.getenv("DATABASE_IPV4_ONLY", "").lower() in ("1", "true", "yes"):
        try:
            engine_kwargs["connect_args"] = _postgres_ipv4_connect_args(DATABASE_URL)
            logger.info(
                "DATABASE_IPV4_ONLY: connecting via IPv4 hostaddr for %s",
                make_url(DATABASE_URL).host,
            )
        except OSError as e:
            logger.warning(
                "DATABASE_IPV4_ONLY set but IPv4 resolve failed (%s); "
                "using default DNS (set DATABASE_IPV4_ONLY=0 or fix DNS).",
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
