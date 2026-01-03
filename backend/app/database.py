"""Database configuration and session management."""

import time
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
import structlog

from app.config import settings

logger = structlog.get_logger()

# Create async engine
# statement_cache_size=0 is required for Supabase transaction pooler (pgbouncer)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"statement_cache_size": 0},
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


# Alias for backwards compatibility with tests
get_async_session = async_session_maker


async def init_db() -> None:
    """
    Initialize and validate database connection.

    This function verifies database connectivity at startup.
    In production, schema is managed via Alembic migrations.

    Raises:
        RuntimeError: If database connection fails
    """
    try:
        async with engine.begin() as conn:
            # Verify database connection with a simple query
            result = await conn.execute(text("SELECT 1"))
            result.scalar()

            # Log successful connection (mask credentials)
            db_host = settings.DATABASE_URL.split("@")[-1].split("/")[0] if "@" in settings.DATABASE_URL else "configured"
            logger.info(
                "Database connection verified",
                database_host=db_host,
            )
    except Exception as e:
        logger.critical(
            "Failed to connect to database - application cannot start",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Re-raise to prevent application from starting without database
        raise RuntimeError(f"Database connection failed: {e}") from e


async def check_db_health() -> dict:
    """
    Check database health for monitoring endpoints.

    Returns:
        dict with status and latency information
    """
    try:
        start = time.monotonic()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = (time.monotonic() - start) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
