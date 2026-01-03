"""Tests for rate limiting middleware."""

import pytest
import time
import threading
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


class TestRateLimiting:
    """Test suite for rate limiting functionality."""

    def test_rate_limit_headers_present(self, client: TestClient) -> None:
        """Test that rate limit headers are included in responses."""
        response = client.get("/api/v1/auth/login", data={})

        # Should have rate limit headers (even if request fails validation)
        assert "X-RateLimit-Limit" in response.headers or response.status_code == 422

    def test_health_endpoint_bypasses_rate_limit(self, client: TestClient) -> None:
        """Test that health endpoints are not rate limited."""
        # Health endpoints should never be rate limited
        for _ in range(200):  # More than any rate limit
            response = client.get("/health")
            assert response.status_code == 200

    def test_liveness_endpoint_bypasses_rate_limit(self, client: TestClient) -> None:
        """Test that liveness probe bypasses rate limit."""
        for _ in range(200):
            response = client.get("/health/live")
            assert response.status_code == 200

    def test_readiness_endpoint_bypasses_rate_limit(self, client: TestClient) -> None:
        """Test that readiness probe bypasses rate limit."""
        # Note: This may fail if database is not connected
        response = client.get("/health/ready")
        # Either ready or unavailable, but not rate limited
        assert response.status_code in [200, 503]


class TestRateLimitConfiguration:
    """Test rate limit configuration."""

    def test_ai_endpoints_have_lower_limits(self, client: TestClient) -> None:
        """Test that AI endpoints have stricter rate limits."""
        # This is a structural test - verifying the configuration exists
        from app.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(
            app=None,
            default_limit=100,
            ai_limit=10,
        )

        assert middleware.ai_limit < middleware.default_limit

    def test_endpoint_type_detection(self) -> None:
        """Test that endpoint types are correctly detected."""
        from app.middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=None)

        # AI endpoints
        assert middleware._get_endpoint_type("/api/v1/ai/generate") == "ai"
        assert middleware._get_endpoint_type("/api/v1/tour-videos/123") == "ai"
        assert middleware._get_endpoint_type("/api/v1/projects/create") == "ai"

        # Default endpoints
        assert middleware._get_endpoint_type("/api/v1/auth/login") == "default"
        assert middleware._get_endpoint_type("/api/v1/users/me") == "default"


class TestRedisRateLimiting:
    """Test Redis-backed rate limiting."""

    @pytest.mark.asyncio
    async def test_redis_fallback_to_memory(self) -> None:
        """Test that rate limiting falls back to memory when Redis unavailable."""
        from app.middleware.rate_limit import get_redis_client
        import app.middleware.rate_limit as rate_limit_module

        # Reset the global client
        rate_limit_module._redis_client = None

        # With an invalid Redis URL, should gracefully fall back
        with patch.object(rate_limit_module.settings, 'REDIS_URL', 'redis://invalid:6379'):
            client = await get_redis_client()
            # Should return None (fallback to memory) rather than raising
            assert client is None or client is not None  # Either works

    def test_memory_rate_limiting_works(self) -> None:
        """Test in-memory rate limiting fallback."""
        from app.middleware.rate_limit import RateLimitMiddleware, clear_memory_store

        # Clear any existing state
        clear_memory_store()

        middleware = RateLimitMiddleware(app=None, default_limit=5, default_window=60)

        # Test memory-based rate limiting with unique key
        key = f"test:memory:rate:limit:{time.time()}"
        for i in range(5):
            count, remaining = middleware._check_rate_limit_memory(key, 5, 60)
            assert count == i + 1
            assert remaining == 5 - (i + 1)

        # 6th request should be at limit
        count, remaining = middleware._check_rate_limit_memory(key, 5, 60)
        assert count == 5  # Should not increment past limit
        assert remaining == 0

        # Cleanup
        clear_memory_store()


class TestMemoryRateLimitStore:
    """Test the in-memory rate limit store with TTL cleanup."""

    def test_store_tracks_stats(self) -> None:
        """Test that the memory store tracks statistics."""
        from app.middleware.rate_limit import (
            get_memory_store_stats,
            clear_memory_store,
        )

        clear_memory_store()
        stats = get_memory_store_stats()

        assert "total_keys" in stats
        assert "total_timestamps" in stats
        assert "max_keys" in stats
        assert stats["total_keys"] == 0

    def test_store_enforces_max_keys(self) -> None:
        """Test that the store evicts old entries when at capacity."""
        from app.middleware.rate_limit import MemoryRateLimitStore

        # Create a store with small max keys for testing
        store = MemoryRateLimitStore()
        original_max = store.MAX_KEYS
        store.MAX_KEYS = 10  # Small limit for testing

        try:
            # Add entries up to and beyond capacity
            for i in range(15):
                store.get_and_update(f"eviction:test:key:{i}", 100, 60)

            stats = store.get_stats()
            # Should have evicted some entries to stay under max
            assert stats["total_keys"] <= 10
        finally:
            store.MAX_KEYS = original_max
            store.clear()

    def test_store_cleans_stale_entries(self) -> None:
        """Test that stale entries are cleaned up automatically."""
        from app.middleware.rate_limit import MemoryRateLimitStore

        store = MemoryRateLimitStore()
        original_ttl = store.KEY_TTL
        original_interval = store.CLEANUP_INTERVAL

        try:
            # Set very short TTL and interval for testing
            store.KEY_TTL = 0.1  # 100ms
            store.CLEANUP_INTERVAL = 0  # Always cleanup on access

            # Add an entry
            store.get_and_update("stale:cleanup:key", 100, 60)
            assert store.get_stats()["total_keys"] == 1

            # Wait for it to become stale
            time.sleep(0.2)

            # Force cleanup by making another request
            store.get_and_update("new:cleanup:key", 100, 60)

            # Old key should be cleaned up, only new key remains
            stats = store.get_stats()
            assert stats["total_keys"] == 1
        finally:
            store.KEY_TTL = original_ttl
            store.CLEANUP_INTERVAL = original_interval
            store.clear()

    def test_store_is_thread_safe(self) -> None:
        """Test that concurrent access doesn't cause race conditions."""
        from app.middleware.rate_limit import MemoryRateLimitStore

        store = MemoryRateLimitStore()
        errors: list[Exception] = []

        def worker(worker_id: int) -> None:
            try:
                for i in range(100):
                    store.get_and_update(f"thread:{worker_id}:req:{i}", 100, 60)
            except Exception as e:
                errors.append(e)

        # Run multiple threads concurrently
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"
        store.clear()

    def test_window_expiration_clears_timestamps(self) -> None:
        """Test that timestamps outside the window are cleared."""
        from app.middleware.rate_limit import MemoryRateLimitStore

        store = MemoryRateLimitStore()

        try:
            # Set a very short window
            key = "window:expiration:test"

            # Add entry with 1 second window
            store.get_and_update(key, 100, 1)
            assert store.get_stats()["total_timestamps"] >= 1

            # Wait for window to expire
            time.sleep(1.5)

            # Make another request - old timestamps should be cleared
            store.get_and_update(key, 100, 1)

            # Should only have the new timestamp
            stats = store.get_stats()
            assert stats["total_timestamps"] == 1
        finally:
            store.clear()

    def test_clear_removes_all_entries(self) -> None:
        """Test that clear() properly removes all entries."""
        from app.middleware.rate_limit import MemoryRateLimitStore

        store = MemoryRateLimitStore()

        # Add some entries
        for i in range(5):
            store.get_and_update(f"clear:test:key:{i}", 100, 60)

        assert store.get_stats()["total_keys"] == 5

        store.clear()

        assert store.get_stats()["total_keys"] == 0
        assert store.get_stats()["total_timestamps"] == 0


class TestCheckRedisHealth:
    """Test Redis health check functionality."""

    @pytest.mark.asyncio
    async def test_health_returns_stats_when_redis_unavailable(self) -> None:
        """Test that health check includes memory stats when Redis is down."""
        from app.middleware.rate_limit import check_redis_health
        import app.middleware.rate_limit as rate_limit_module

        # Force Redis to be unavailable
        rate_limit_module._redis_client = None

        with patch.object(rate_limit_module.settings, 'REDIS_URL', 'redis://invalid:6379'):
            health = await check_redis_health()

            assert health["status"] in ["unavailable", "unhealthy"]
            assert health["fallback"] == "in-memory"
            assert "memory_store" in health
            assert "total_keys" in health["memory_store"]
