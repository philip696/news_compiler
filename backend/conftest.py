"""
Pytest configuration and fixtures for test suite.
Sets up environment variables, database fixtures, and shared test utilities.
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from cryptography.fernet import Fernet

# Generate and set TEST encryption key BEFORE any models import
if not os.environ.get("TOKEN_ENCRYPTION_KEY"):
    os.environ["TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from app.db.database import Base
from app.models import (
    WeChatAuth, WeChatAccount, WeChatSubscription, 
    WeChatArticle, WeChatSyncLog
)


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine (SQLite in-memory)"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # Enable foreign key constraints in SQLite
    def configure_sqlite(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    from sqlalchemy import event
    event.listen(engine, "connect", configure_sqlite)
    
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a test database session"""
    connection = db_engine.connect()
    
    # Ensure foreign keys are enabled for this connection
    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    
    transaction = connection.begin()
    session = sessionmaker(bind=connection)(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def encryption_key():
    """Provide encryption key for test fixtures"""
    return os.environ.get("TOKEN_ENCRYPTION_KEY")
