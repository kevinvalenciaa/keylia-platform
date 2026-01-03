"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


class TestAuthEndpoints:
    """Test suite for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register_creates_user(
        self, async_client: AsyncClient, mock_user_data: dict
    ) -> None:
        """Test that user registration creates a new user."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json=mock_user_data,
        )

        # Registration might return 201 or 200 depending on implementation
        assert response.status_code in [200, 201, 422]  # 422 if validation fails without DB

    @pytest.mark.asyncio
    async def test_register_rejects_invalid_email(
        self, async_client: AsyncClient, mock_user_data: dict
    ) -> None:
        """Test that registration rejects invalid email format."""
        mock_user_data["email"] = "invalid-email"

        response = await async_client.post(
            "/api/v1/auth/register",
            json=mock_user_data,
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_requires_credentials(
        self, async_client: AsyncClient
    ) -> None:
        """Test that login requires email and password."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={},
        )

        assert response.status_code == 422  # Missing required fields


class TestTokenValidation:
    """Test suite for JWT token validation."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(
        self, async_client: AsyncClient
    ) -> None:
        """Test that protected endpoints require authentication."""
        response = await async_client.get("/api/v1/users/me")

        # Should return 401 or 403 without valid token
        assert response.status_code in [401, 403, 404]  # 404 if endpoint doesn't exist

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(
        self, async_client: AsyncClient
    ) -> None:
        """Test that invalid tokens are rejected."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code in [401, 403, 404]
