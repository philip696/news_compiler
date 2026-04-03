import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

# Create data directory if it doesn't exist
db_dir = Path(__file__).parent.parent.parent / "data"
db_dir.mkdir(exist_ok=True)

# Database URL - supports both SQLite (local) and PostgreSQL (production)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_dir}/geb.db")

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

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
