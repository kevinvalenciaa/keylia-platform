"""Rate limiting middleware for FastAPI."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using a sliding window algorithm.

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
            default_limit: Default requests per window
            default_window: Default window in seconds
            ai_limit: Requests per window for AI endpoints
            ai_window: Window in seconds for AI endpoints
        """
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.ai_limit = ai_limit
        self.ai_window = ai_window

        # Store request counts: {client_ip: [(timestamp, endpoint_type), ...]}
        self.request_log: dict[str, list[tuple[float, str]]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type for rate limiting."""
        ai_patterns = [
            "/api/v1/ai/",
            "/api/v1/tour-videos/",
            "/api/v1/projects/",
        ]

        for pattern in ai_patterns:
            if pattern in path:
                return "ai"

        return "default"

    def _clean_old_requests(
        self, requests: list[tuple[float, str]], window: int
    ) -> list[tuple[float, str]]:
        """Remove requests outside the current window."""
        cutoff = time.time() - window
        return [(ts, et) for ts, et in requests if ts > cutoff]

    def _count_requests(
        self, requests: list[tuple[float, str]], endpoint_type: str, window: int
    ) -> int:
        """Count requests of a specific type within the window."""
        cutoff = time.time() - window
        return sum(1 for ts, et in requests if ts > cutoff and et == endpoint_type)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/openapi.json"]:
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

        # Clean old requests and count current
        self.request_log[client_ip] = self._clean_old_requests(
            self.request_log[client_ip], max(self.default_window, self.ai_window)
        )

        request_count = self._count_requests(
            self.request_log[client_ip], endpoint_type, window
        )

        # Check if rate limit exceeded
        if request_count >= limit:
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                endpoint_type=endpoint_type,
                request_count=request_count,
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
                    "X-RateLimit-Reset": str(int(time.time() + window)),
                },
            )

        # Log request
        self.request_log[client_ip].append((time.time(), endpoint_type))

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, limit - request_count - 1)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + window))

        return response


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
