"""Database utilities for Celery workers.

This module provides synchronous database access for Celery tasks,
with proper connection pooling and engine caching to avoid creating
new engines on every task invocation.
"""

from contextlib import contextmanager
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
import structlog

from app.config import settings

logger = structlog.get_logger()


@lru_cache(maxsize=1)
def get_sync_engine() -> Engine:
    """
    Get cached synchronous database engine.
    
    Uses lru_cache to ensure only one engine is created across
    all Celery workers in the same process. The engine maintains
    its own connection pool.
    
    Returns:
        SQLAlchemy Engine instance with connection pooling
    """
    # Convert async URL to sync (remove +asyncpg driver prefix)
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    
    engine = create_engine(
        sync_url,
        pool_size=5,           # Base pool size
        max_overflow=10,       # Additional connections when pool is exhausted
        pool_timeout=30,       # Seconds to wait for available connection
        pool_recycle=1800,     # Recycle connections after 30 minutes
        pool_pre_ping=True,    # Verify connections before using
        echo=settings.DEBUG,
    )
    
    logger.info(
        "Created synchronous database engine for Celery",
        pool_size=5,
        max_overflow=10,
    )
    
    return engine


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker:
    """
    Get cached session factory.
    
    Returns:
        SQLAlchemy sessionmaker bound to the sync engine
    """
    engine = get_sync_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_sync_db() -> Session:
    """
    Get a new synchronous database session for Celery tasks.
    
    This creates a new session from the cached session factory.
    The caller is responsible for closing the session.
    
    Returns:
        SQLAlchemy Session instance
    
    Usage:
        db = get_sync_db()
        try:
            # do work
            db.commit()
        finally:
            db.close()
    """
    SessionLocal = get_session_factory()
    return SessionLocal()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Automatically handles session lifecycle including commit/rollback.
    
    Usage:
        with get_db_session() as db:
            user = db.query(User).first()
            user.name = "new name"
            # Commits automatically on success
    
    Yields:
        SQLAlchemy Session instance
    """
    session = get_sync_db()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine() -> None:
    """
    Dispose of the database engine and clear caches.
    
    Call this during graceful shutdown or when recycling workers.
    """
    engine = get_sync_engine()
    engine.dispose()
    
    # Clear caches to allow recreation
    get_sync_engine.cache_clear()
    get_session_factory.cache_clear()
    
    logger.info("Disposed synchronous database engine")
