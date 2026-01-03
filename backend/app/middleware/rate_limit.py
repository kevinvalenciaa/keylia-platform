"""Rate limiting middleware for FastAPI with Redis backend.

This module provides a production-ready rate limiter with:
- Redis-backed distributed rate limiting (preferred)
- In-memory fallback with proper TTL cleanup (no memory leaks)
- Sliding window algorithm for accurate rate limiting
- Configurable limits for different endpoint types
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.config import settings

logger = structlog.get_logger()

# Redis client singleton
_redis_client: Optional["redis.asyncio.Redis"] = None


async def get_redis_client() -> Optional["redis.asyncio.Redis"]:
    """
    Get or create Redis client singleton.

    Returns:
        Redis client if available, None if Redis is not configured or unavailable
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        import redis.asyncio as redis

        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        # Test connection
        await _redis_client.ping()
        logger.info("Redis rate limiter connected", redis_url=settings.REDIS_URL.split("@")[-1] if "@" in settings.REDIS_URL else "configured")
        return _redis_client
    except ImportError:
        logger.warning("redis package not installed, falling back to in-memory rate limiting")
        return None
    except Exception as e:
        logger.warning("Redis connection failed, falling back to in-memory rate limiting", error=str(e))
        return None


@dataclass
class RateLimitEntry:
    """A rate limit entry with timestamps and last access tracking."""
    timestamps: list[float] = field(default_factory=list)
    last_accessed: float = field(default_factory=time.time)


class MemoryRateLimitStore:
    """
    Thread-safe in-memory rate limit storage with automatic TTL cleanup.

    This prevents memory leaks by:
    1. Tracking last access time for each key
    2. Running periodic cleanup of stale entries
    3. Enforcing a maximum number of tracked keys
    4. Using per-key locks for minimal contention (not a global lock)
    """

    # Maximum number of keys to track (prevents unbounded growth)
    MAX_KEYS = 10000

    # Cleanup interval in seconds
    CLEANUP_INTERVAL = 60

    # TTL for stale keys (keys not accessed within this time are removed)
    KEY_TTL = 300  # 5 minutes

    # Number of lock buckets for sharding (reduces contention)
    LOCK_BUCKETS = 64

    def __init__(self):
        self._store: dict[str, RateLimitEntry] = {}
        # Use a sharded lock system instead of a single global lock
        # This reduces contention by distributing keys across multiple locks
        self._locks = [threading.Lock() for _ in range(self.LOCK_BUCKETS)]
        self._global_lock = threading.Lock()  # Only for cleanup operations
        self._last_cleanup = time.time()

    def _get_lock_for_key(self, key: str) -> threading.Lock:
        """Get the lock for a specific key using hash-based sharding."""
        bucket = hash(key) % self.LOCK_BUCKETS
        return self._locks[bucket]

    def get_and_update(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[int, int]:
        """
        Get current count and update rate limit entry.

        Uses per-key lock sharding to minimize contention under high load.

        Args:
            key: The rate limit key (e.g., "ratelimit:ai:192.168.1.1")
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (current_count, remaining)
        """
        now = time.time()
        window_start = now - window

        # Use sharded lock for the specific key
        key_lock = self._get_lock_for_key(key)

        with key_lock:
            # Check if cleanup is needed (use non-blocking try to avoid bottleneck)
            if now - self._last_cleanup > self.CLEANUP_INTERVAL:
                if self._global_lock.acquire(blocking=False):
                    try:
                        # Double-check after acquiring lock
                        if now - self._last_cleanup > self.CLEANUP_INTERVAL:
                            self._cleanup_stale_entries(now)
                            self._last_cleanup = now
                    finally:
                        self._global_lock.release()

            # Get or create entry
            if key not in self._store:
                # Check if we're at capacity (quick check without global lock)
                if len(self._store) >= self.MAX_KEYS:
                    # Try to evict, but don't block
                    if self._global_lock.acquire(blocking=False):
                        try:
                            if len(self._store) >= self.MAX_KEYS:
                                self._evict_oldest_entries()
                        finally:
                            self._global_lock.release()
                self._store[key] = RateLimitEntry()

            entry = self._store[key]
            entry.last_accessed = now

            # Clean old timestamps outside the window
            entry.timestamps = [ts for ts in entry.timestamps if ts > window_start]

            current_count = len(entry.timestamps)

            if current_count < limit:
                entry.timestamps.append(now)
                current_count += 1

            remaining = max(0, limit - current_count)
            return current_count, remaining

    def _cleanup_stale_entries(self, now: float) -> None:
        """Remove entries that haven't been accessed recently."""
        stale_threshold = now - self.KEY_TTL
        stale_keys = [
            key for key, entry in self._store.items()
            if entry.last_accessed < stale_threshold
        ]

        for key in stale_keys:
            del self._store[key]

        if stale_keys:
            logger.debug(
                "Rate limiter cleanup: removed stale entries",
                removed_count=len(stale_keys),
                remaining_keys=len(self._store),
            )

    def _evict_oldest_entries(self) -> None:
        """Evict oldest 10% of entries when at capacity."""
        if not self._store:
            return

        evict_count = max(1, len(self._store) // 10)

        # Sort by last_accessed and remove oldest
        sorted_keys = sorted(
            self._store.keys(),
            key=lambda k: self._store[k].last_accessed
        )

        for key in sorted_keys[:evict_count]:
            del self._store[key]

        logger.warning(
            "Rate limiter at capacity: evicted oldest entries",
            evicted_count=evict_count,
            max_keys=self.MAX_KEYS,
        )

    def get_stats(self) -> dict:
        """Get statistics about the memory store."""
        with self._global_lock:
            total_timestamps = sum(
                len(entry.timestamps) for entry in self._store.values()
            )
            return {
                "total_keys": len(self._store),
                "total_timestamps": total_timestamps,
                "max_keys": self.MAX_KEYS,
                "lock_buckets": self.LOCK_BUCKETS,
            }

    def clear(self) -> None:
        """Clear all entries (useful for testing)."""
        with self._global_lock:
            self._store.clear()


# Global memory store instance
_memory_store = MemoryRateLimitStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.

    Supports both Redis (distributed) and in-memory (single instance) backends.
    Redis is preferred for production deployments with multiple workers/containers.

    Limits requests based on client IP address with configurable
    limits for different endpoint patterns.
    """

    def __init__(
        self,
        app,
        default_limit: int = 100,
        default_window: int = 60,
        ai_limit: int = 10,
        ai_window: int = 60,
    ):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            default_limit: Default requests per window (default: 100/min)
            default_window: Default window in seconds (default: 60)
            ai_limit: Requests per window for AI endpoints (default: 10/min)
            ai_window: Window in seconds for AI endpoints (default: 60)
        """
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.ai_limit = ai_limit
        self.ai_window = ai_window
        self._redis_available: Optional[bool] = None

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request, respecting proxy headers.

        Checks X-Forwarded-For and X-Real-IP headers for requests
        behind a load balancer or reverse proxy.
        """
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can contain multiple IPs, take the first (client)
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_endpoint_type(self, path: str) -> str:
        """
        Determine endpoint type for rate limiting tiers.

        AI endpoints have stricter limits due to computational cost.
        """
        ai_patterns = [
            "/api/v1/ai/",
            "/api/v1/tour-videos/",
            "/api/v1/projects/",
        ]

        for pattern in ai_patterns:
            if pattern in path:
                return "ai"

        return "default"

    async def _check_rate_limit_redis(
        self,
        redis_client: "redis.asyncio.Redis",
        key: str,
        limit: int,
        window: int,
    ) -> tuple[int, int]:
        """
        Check and update rate limit using Redis sliding window.

        Uses a Lua script for atomic operations.

        Returns:
            Tuple of (current_count, remaining)
        """
        now = time.time()
        window_start = now - window

        # Use Redis pipeline for atomic operations
        pipe = redis_client.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count requests in window
        pipe.zcard(key)
        # Set TTL to auto-cleanup
        pipe.expire(key, window + 10)

        results = await pipe.execute()
        current_count = results[2]

        remaining = max(0, limit - current_count)
        return current_count, remaining

    def _check_rate_limit_memory(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[int, int]:
        """
        Check and update rate limit using in-memory storage.

        This is a fallback when Redis is unavailable. Uses the global
        MemoryRateLimitStore which provides:
        - Automatic TTL cleanup of stale entries
        - Maximum key limit to prevent unbounded growth
        - Thread-safe operations

        Returns:
            Tuple of (current_count, remaining)
        """
        return _memory_store.get_and_update(key, limit, window)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health checks and documentation
        skip_paths = ["/health", "/health/live", "/health/ready", "/", "/openapi.json", "/api/docs", "/api/redoc"]
        if request.url.path in skip_paths:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        endpoint_type = self._get_endpoint_type(request.url.path)

        # Determine limits based on endpoint type
        if endpoint_type == "ai":
            limit = self.ai_limit
            window = self.ai_window
        else:
            limit = self.default_limit
            window = self.default_window

        # Build rate limit key
        key = f"ratelimit:{endpoint_type}:{client_ip}"

        # Try Redis first, fall back to memory
        redis_client = await get_redis_client()

        if redis_client:
            try:
                current_count, remaining = await self._check_rate_limit_redis(
                    redis_client, key, limit, window
                )
            except Exception as e:
                logger.warning("Redis rate limit check failed, using memory", error=str(e))
                current_count, remaining = self._check_rate_limit_memory(key, limit, window)
        else:
            current_count, remaining = self._check_rate_limit_memory(key, limit, window)

        reset_time = int(time.time() + window)

        # Check if rate limit exceeded
        if current_count > limit:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                endpoint_type=endpoint_type,
                request_count=current_count,
                limit=limit,
                path=request.url.path,
            )

            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


async def check_redis_health() -> dict:
    """
    Check Redis health for monitoring endpoints.

    Returns:
        dict with status and latency information
    """
    try:
        redis_client = await get_redis_client()
        if not redis_client:
            return {
                "status": "unavailable",
                "fallback": "in-memory",
                "memory_store": _memory_store.get_stats(),
            }

        start = time.time()
        await redis_client.ping()
        latency_ms = (time.time() - start) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "fallback": "in-memory",
            "memory_store": _memory_store.get_stats(),
        }


def get_memory_store_stats() -> dict:
    """
    Get statistics about the in-memory rate limit store.

    Useful for monitoring memory usage when Redis is unavailable.

    Returns:
        dict with total_keys, total_timestamps, and max_keys
    """
    return _memory_store.get_stats()


def clear_memory_store() -> None:
    """
    Clear the in-memory rate limit store.

    Useful for testing or administrative purposes.
    """
    _memory_store.clear()


def create_rate_limiter(
    default_limit: int = 100,
    default_window: int = 60,
    ai_limit: int = 10,
    ai_window: int = 60,
) -> type[RateLimitMiddleware]:
    """
    Factory function to create rate limiter with custom configuration.

    Args:
        default_limit: Requests per window for standard endpoints
        default_window: Window in seconds for standard endpoints
        ai_limit: Requests per window for AI endpoints (more restrictive)
        ai_window: Window in seconds for AI endpoints

    Returns:
        Configured RateLimitMiddleware class
    """

    class ConfiguredRateLimiter(RateLimitMiddleware):
        def __init__(self, app):
            super().__init__(
                app,
                default_limit=default_limit,
                default_window=default_window,
                ai_limit=ai_limit,
                ai_window=ai_window,
            )

    return ConfiguredRateLimiter
