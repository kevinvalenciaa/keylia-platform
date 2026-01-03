"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_check_returns_healthy(self, client: TestClient) -> None:
        """Test that health check endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_root_endpoint_returns_api_info(self, client: TestClient) -> None:
        """Test that root endpoint returns API information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Keylia" in data["message"]
        assert "version" in data


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
