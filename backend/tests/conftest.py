"""Pytest configuration and fixtures for Keylia API tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_async_session, Base
from app.config import settings


# Test database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session_maker = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def async_client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing API endpoints."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield async_session

    app.dependency_overrides[get_async_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """Create synchronous test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User",
    }


@pytest.fixture
def mock_listing_data() -> dict[str, Any]:
    """Sample listing data for testing."""
    return {
        "address_line1": "123 Test Street",
        "city": "Los Angeles",
        "state": "CA",
        "zip_code": "90210",
        "listing_price": 1500000,
        "bedrooms": 4,
        "bathrooms": 3,
        "square_feet": 2500,
        "property_type": "single_family",
        "listing_status": "for_sale",
        "features": ["Pool", "Garage", "Smart Home"],
    }


@pytest.fixture
def mock_project_data() -> dict[str, Any]:
    """Sample project data for testing."""
    return {
        "title": "Test Tour Video",
        "type": "listing_tour",
        "style_settings": {
            "tone": "luxury",
            "duration_seconds": 30,
            "video_model": "kling",
        },
        "voice_settings": {
            "enabled": True,
            "language": "en-US",
            "gender": "female",
        },
    }


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Mock authentication headers for testing protected endpoints."""
    return {
        "Authorization": "Bearer test-token-for-testing",
    }
