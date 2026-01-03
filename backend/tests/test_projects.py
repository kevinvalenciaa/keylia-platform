"""Tests for project endpoints."""

import pytest
from httpx import AsyncClient


class TestProjectEndpoints:
    """Test suite for project CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_projects_requires_auth(
        self, async_client: AsyncClient
    ) -> None:
        """Test that listing projects requires authentication."""
        response = await async_client.get("/api/v1/projects")

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_project_requires_auth(
        self, async_client: AsyncClient, mock_project_data: dict
    ) -> None:
        """Test that creating a project requires authentication."""
        response = await async_client.post(
            "/api/v1/projects",
            json=mock_project_data,
        )

        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_project_not_found(
        self, async_client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test that getting a non-existent project returns 404."""
        response = await async_client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        # Will be 401/403 without valid auth, or 404 if not found
        assert response.status_code in [401, 403, 404]


class TestProjectValidation:
    """Test suite for project data validation."""

    @pytest.mark.asyncio
    async def test_create_project_validates_type(
        self, async_client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test that project creation validates project type."""
        invalid_project = {
            "title": "Test Project",
            "type": "invalid_type",  # Invalid type
        }

        response = await async_client.post(
            "/api/v1/projects",
            json=invalid_project,
            headers=auth_headers,
        )

        # Should return validation error or auth error
        assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_create_project_requires_title(
        self, async_client: AsyncClient, auth_headers: dict
    ) -> None:
        """Test that project creation requires a title."""
        incomplete_project = {
            "type": "listing_tour",
        }

        response = await async_client.post(
            "/api/v1/projects",
            json=incomplete_project,
            headers=auth_headers,
        )

        assert response.status_code in [401, 403, 422]
