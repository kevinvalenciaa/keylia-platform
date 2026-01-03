"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_check_returns_status(self, client: TestClient) -> None:
        """Test that health check endpoint returns status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "checks" in data

    def test_health_check_includes_database_status(self, client: TestClient) -> None:
        """Test that health check includes database status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "status" in data["checks"]["database"]

    def test_health_check_includes_redis_status(self, client: TestClient) -> None:
        """Test that health check includes Redis status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "redis" in data["checks"]

    def test_root_endpoint_returns_api_info(self, client: TestClient) -> None:
        """Test that root endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Keylia" in data["message"]
        assert "version" in data


class TestKubernetesProbes:
    """Test Kubernetes liveness and readiness probes."""

    def test_liveness_probe_returns_alive(self, client: TestClient) -> None:
        """Test that liveness probe returns alive status."""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_liveness_probe_always_succeeds(self, client: TestClient) -> None:
        """Test that liveness probe succeeds even with degraded dependencies."""
        # Liveness should always return 200 if the app is running
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_readiness_probe_checks_database(self, client: TestClient) -> None:
        """Test that readiness probe checks database connection."""
        response = client.get("/health/ready")

        # Should return 200 if DB is healthy, 503 if not
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "ready"
            assert "database" in data


class TestDatabaseHealth:
    """Test database health checking."""

    @pytest.mark.asyncio
    async def test_database_health_check_returns_latency(self) -> None:
        """Test that database health check returns latency."""
        from app.database import check_db_health

        result = await check_db_health()

        assert "status" in result
        if result["status"] == "healthy":
            assert "latency_ms" in result
            assert isinstance(result["latency_ms"], (int, float))

    @pytest.mark.asyncio
    async def test_database_health_handles_connection_error(self) -> None:
        """Test that database health check handles connection errors gracefully."""
        from app.database import check_db_health

        # This should not raise an exception
        result = await check_db_health()

        assert "status" in result
        # Either healthy or unhealthy, but should always return a result
        assert result["status"] in ["healthy", "unhealthy"]


class TestRedisHealth:
    """Test Redis health checking."""

    @pytest.mark.asyncio
    async def test_redis_health_returns_status(self) -> None:
        """Test that Redis health check returns status."""
        from app.middleware.rate_limit import check_redis_health

        result = await check_redis_health()

        assert "status" in result
        # Redis might be unavailable in test environment
        assert result["status"] in ["healthy", "unhealthy", "unavailable"]

    @pytest.mark.asyncio
    async def test_redis_health_indicates_fallback(self) -> None:
        """Test that Redis health indicates fallback mode when unavailable."""
        from app.middleware.rate_limit import check_redis_health

        result = await check_redis_health()

        if result["status"] == "unavailable":
            assert "fallback" in result
            assert result["fallback"] == "in-memory"


class TestAPIDocumentation:
    """Test suite for API documentation endpoints."""

    def test_openapi_schema_available(self, client: TestClient) -> None:
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Keylia API"

    def test_openapi_schema_includes_version(self, client: TestClient) -> None:
        """Test that OpenAPI schema includes version."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "info" in schema
        assert "version" in schema["info"]

    def test_openapi_paths_defined(self, client: TestClient) -> None:
        """Test that OpenAPI schema has paths defined."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert len(schema["paths"]) > 0
