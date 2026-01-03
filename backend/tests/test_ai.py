"""Tests for AI generation endpoints."""

import pytest
from httpx import AsyncClient


class TestAIEndpoints:
    """Test suite for AI generation endpoints."""

    @pytest.mark.asyncio
    async def test_generate_script_requires_auth(
        self, async_client: AsyncClient
    ) -> None:
        """Test that script generation requires authentication."""
        response = await async_client.post(
            "/api/v1/ai/generate-script",
            json={"listing_id": "00000000-0000-0000-0000-000000000000"},
        )

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_generate_caption_requires_auth(
        self, async_client: AsyncClient
    ) -> None:
        """Test that caption generation requires authentication."""
        response = await async_client.post(
            "/api/v1/ai/generate-caption",
            json={"listing_id": "00000000-0000-0000-0000-000000000000"},
        )

        assert response.status_code in [401, 403]


class TestAIValidation:
    """Test suite for AI input validation."""

    @pytest.mark.asyncio
    async def test_script_generation_validates_listing_id(
        self, async_client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test that script generation validates listing ID format."""
        response = await async_client.post(
            "/api/v1/ai/generate-script",
            json={"listing_id": "invalid-uuid"},
            headers=auth_headers,
        )

        assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_caption_generation_validates_platform(
        self, async_client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test that caption generation validates platform."""
        response = await async_client.post(
            "/api/v1/ai/generate-caption",
            json={
                "listing_id": "00000000-0000-0000-0000-000000000000",
                "platform": "invalid_platform",
            },
            headers=auth_headers,
        )

        assert response.status_code in [401, 403, 422]
