"""
Circuit breaker implementation for external API calls.

The circuit breaker pattern prevents cascading failures when external services
are unavailable or experiencing issues. It monitors failures and opens the
circuit to prevent further calls when a threshold is exceeded.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures exceeded threshold, requests fail fast
- HALF_OPEN: Testing if service recovered, limited requests allowed

Usage:
    breaker = CircuitBreaker("openai", failure_threshold=5, recovery_timeout=60)
    
    try:
        result = await breaker.call(async_api_function, *args, **kwargs)
    except CircuitBreakerOpen:
        # Handle circuit open state (service unavailable)
        pass
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, ParamSpec
import structlog

logger = structlog.get_logger()

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    
    def __init__(self, service_name: str, retry_after: float):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {service_name}. Retry after {retry_after:.1f}s"
        )


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Args:
        service_name: Name of the service (for logging)
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before testing recovery
        success_threshold: Successes needed in half-open to close circuit
        expected_exceptions: Exception types to count as failures
    """
    service_name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 2
    expected_exceptions: tuple = field(default_factory=lambda: (Exception,))
    
    # State
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    success_count: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    last_state_change: float = field(default_factory=time.time, init=False)
    
    def __post_init__(self):
        self._lock = asyncio.Lock()
    
    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN
    
    @property
    def time_since_last_failure(self) -> float:
        return time.time() - self.last_failure_time
    
    @property
    def retry_after(self) -> float:
        """Seconds until circuit will transition to half-open."""
        if not self.is_open:
            return 0.0
        remaining = self.recovery_timeout - self.time_since_last_failure
        return max(0.0, remaining)
    
    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state
        self.last_state_change = time.time()
        
        if new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
        elif new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
        
        logger.info(
            "Circuit breaker state transition",
            service=self.service_name,
            old_state=old_state.value,
            new_state=new_state.value,
        )
    
    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            if self.is_half_open:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)
    
    async def _record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.warning(
                "Circuit breaker recorded failure",
                service=self.service_name,
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
                error=str(error)[:100],
            )
            
            if self.is_half_open:
                # Any failure in half-open immediately opens circuit
                await self._transition_to(CircuitState.OPEN)
            elif self.failure_count >= self.failure_threshold:
                await self._transition_to(CircuitState.OPEN)
    
    async def _check_state(self) -> None:
        """Check and potentially update circuit state."""
        async with self._lock:
            if self.is_open and self.time_since_last_failure >= self.recovery_timeout:
                await self._transition_to(CircuitState.HALF_OPEN)
    
    async def call(
        self,
        func: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Async or sync function to call
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function
            
        Returns:
            Result of the function call
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception from the wrapped function
        """
        await self._check_state()
        
        if self.is_open:
            raise CircuitBreakerOpen(self.service_name, self.retry_after)
        
        try:
            # Handle both async and sync functions
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await self._record_success()
            return result
            
        except self.expected_exceptions as e:
            await self._record_failure(e)
            raise
    
    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "success_count": self.success_count,
            "retry_after": self.retry_after,
            "time_since_last_failure": self.time_since_last_failure if self.last_failure_time else None,
        }
    
    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()
        
        logger.info("Circuit breaker manually reset", service=self.service_name)


# Global circuit breakers for external services
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker for a service.
    
    Uses a singleton pattern to ensure one breaker per service.
    """
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(
            service_name=service_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _circuit_breakers[service_name]


def with_circuit_breaker(
    service_name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
):
    """
    Decorator to wrap a function with circuit breaker protection.
    
    Usage:
        @with_circuit_breaker("openai")
        async def call_openai_api(...):
            ...
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        breaker = get_circuit_breaker(service_name, failure_threshold, recovery_timeout)
        
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


def get_all_circuit_breaker_statuses() -> list[dict]:
    """Get status of all circuit breakers for monitoring."""
    return [breaker.get_status() for breaker in _circuit_breakers.values()]
