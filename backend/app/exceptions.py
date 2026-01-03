"""Standardized API exceptions for consistent error handling.

This module provides a production-ready exception system that:
- Ensures consistent error response structure across all endpoints
- Provides typed error codes for frontend handling
- Includes request context for debugging
- Supports structured logging of errors
- Integrates with FastAPI's exception handling

Usage:
    from app.exceptions import (
        APIError,
        NotFoundError,
        ValidationError,
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        ExternalServiceError,
    )

    # In route handlers:
    raise NotFoundError(
        message="Listing not found",
        details={"listing_id": listing_id}
    )
"""

from enum import Enum
from typing import Any, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog
import traceback

logger = structlog.get_logger()


class ErrorCode(str, Enum):
    """Standardized error codes for API responses.

    These codes allow frontend applications to programmatically
    handle specific error conditions.
    """

    # Authentication & Authorization (1xxx)
    AUTHENTICATION_REQUIRED = "AUTH_001"
    INVALID_CREDENTIALS = "AUTH_002"
    TOKEN_EXPIRED = "AUTH_003"
    TOKEN_INVALID = "AUTH_004"
    INSUFFICIENT_PERMISSIONS = "AUTH_005"
    ACCOUNT_DISABLED = "AUTH_006"
    EMAIL_NOT_VERIFIED = "AUTH_007"

    # Validation Errors (2xxx)
    VALIDATION_ERROR = "VAL_001"
    INVALID_INPUT = "VAL_002"
    MISSING_REQUIRED_FIELD = "VAL_003"
    INVALID_FORMAT = "VAL_004"
    VALUE_OUT_OF_RANGE = "VAL_005"

    # Resource Errors (3xxx)
    NOT_FOUND = "RES_001"
    ALREADY_EXISTS = "RES_002"
    CONFLICT = "RES_003"
    GONE = "RES_004"

    # Rate Limiting (4xxx)
    RATE_LIMIT_EXCEEDED = "RATE_001"
    QUOTA_EXCEEDED = "RATE_002"
    TRIAL_EXPIRED = "RATE_003"
    SUBSCRIPTION_REQUIRED = "RATE_004"

    # External Service Errors (5xxx)
    EXTERNAL_SERVICE_ERROR = "EXT_001"
    AI_SERVICE_ERROR = "EXT_002"
    PAYMENT_ERROR = "EXT_003"
    STORAGE_ERROR = "EXT_004"
    EMAIL_SERVICE_ERROR = "EXT_005"

    # Server Errors (9xxx)
    INTERNAL_ERROR = "SRV_001"
    SERVICE_UNAVAILABLE = "SRV_002"
    DATABASE_ERROR = "SRV_003"
    CONFIGURATION_ERROR = "SRV_004"


class ErrorResponse(BaseModel):
    """Standardized error response model.

    All API errors return this structure for consistency.
    """

    error: bool = True
    code: str
    message: str
    details: Optional[dict[str, Any]] = None
    request_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "code": "RES_001",
                "message": "Listing not found",
                "details": {"listing_id": "123e4567-e89b-12d3-a456-426614174000"},
                "request_id": "req_abc123",
            }
        }


class APIError(HTTPException):
    """Base exception for all API errors.

    Provides consistent error structure and automatic logging.
    Subclass this for specific error types.

    Args:
        status_code: HTTP status code
        code: ErrorCode enum value
        message: Human-readable error message
        details: Additional context (must be JSON-serializable)
        log_error: Whether to log this error (default True)
        include_traceback: Include traceback in logs (default False)
    """

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: Optional[dict[str, Any]] = None,
        log_error: bool = True,
        include_traceback: bool = False,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.log_error = log_error
        self.include_traceback = include_traceback

        # Build the detail dict for HTTPException
        detail = {
            "error": True,
            "code": code.value,
            "message": message,
            "details": self.details,
        }

        super().__init__(status_code=status_code, detail=detail)

    def log(self, request_id: Optional[str] = None) -> None:
        """Log the error with structured context."""
        if not self.log_error:
            return

        log_data = {
            "error_code": self.code.value,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }

        if request_id:
            log_data["request_id"] = request_id

        if self.include_traceback:
            log_data["traceback"] = traceback.format_exc()

        if self.status_code >= 500:
            logger.error("API Error", **log_data)
        else:
            logger.warning("API Error", **log_data)


# Specific Error Types


class NotFoundError(APIError):
    """Resource not found (404)."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message=message,
            details=details,
        )


class ValidationError(APIError):
    """Request validation failed (400)."""

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[dict[str, Any]] = None,
        field: Optional[str] = None,
    ):
        if field and details is None:
            details = {"field": field}
        elif field and details is not None:
            details["field"] = field

        super().__init__(
            status_code=400,
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
        )


class AuthenticationError(APIError):
    """Authentication required or failed (401)."""

    def __init__(
        self,
        message: str = "Authentication required",
        code: ErrorCode = ErrorCode.AUTHENTICATION_REQUIRED,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=401,
            code=code,
            message=message,
            details=details,
        )


class AuthorizationError(APIError):
    """User lacks required permissions (403)."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=403,
            code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            message=message,
            details=details,
        )


class ConflictError(APIError):
    """Resource conflict (409)."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message=message,
            details=details,
        )


class AlreadyExistsError(APIError):
    """Resource already exists (409)."""

    def __init__(
        self,
        message: str = "Resource already exists",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=409,
            code=ErrorCode.ALREADY_EXISTS,
            message=message,
            details=details,
        )


class RateLimitError(APIError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if retry_after:
            details = details or {}
            details["retry_after_seconds"] = retry_after

        super().__init__(
            status_code=429,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details,
        )


class QuotaExceededError(APIError):
    """Usage quota exceeded (429)."""

    def __init__(
        self,
        message: str = "Usage quota exceeded",
        quota_type: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        if quota_type:
            details["quota_type"] = quota_type

        super().__init__(
            status_code=429,
            code=ErrorCode.QUOTA_EXCEEDED,
            message=message,
            details=details,
        )


class SubscriptionRequiredError(APIError):
    """Active subscription required (402)."""

    def __init__(
        self,
        message: str = "Active subscription required",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=402,
            code=ErrorCode.SUBSCRIPTION_REQUIRED,
            message=message,
            details=details,
        )


class ExternalServiceError(APIError):
    """External service failure (502)."""

    def __init__(
        self,
        message: str = "External service error",
        service: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        if service:
            details["service"] = service

        super().__init__(
            status_code=502,
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=message,
            details=details,
            include_traceback=True,
        )


class AIServiceError(APIError):
    """AI service failure (502)."""

    def __init__(
        self,
        message: str = "AI service error",
        service: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        details = details or {}
        if service:
            details["service"] = service

        super().__init__(
            status_code=502,
            code=ErrorCode.AI_SERVICE_ERROR,
            message=message,
            details=details,
            include_traceback=True,
        )


class PaymentError(APIError):
    """Payment processing failure (402)."""

    def __init__(
        self,
        message: str = "Payment processing failed",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=402,
            code=ErrorCode.PAYMENT_ERROR,
            message=message,
            details=details,
        )


class DatabaseError(APIError):
    """Database operation failed (500)."""

    def __init__(
        self,
        message: str = "Database error",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=500,
            code=ErrorCode.DATABASE_ERROR,
            message=message,
            details=details,
            include_traceback=True,
        )


class InternalError(APIError):
    """Unexpected internal error (500)."""

    def __init__(
        self,
        message: str = "Internal server error",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message=message,
            details=details,
            include_traceback=True,
        )


class ServiceUnavailableError(APIError):
    """Service temporarily unavailable (503)."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=503,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            details=details,
        )


# Exception Handlers for FastAPI


def get_request_id(request: Request) -> Optional[str]:
    """Extract request ID from headers or state."""
    # Check common request ID headers
    for header in ["X-Request-ID", "X-Correlation-ID", "Request-ID"]:
        if header in request.headers:
            return request.headers[header]

    # Check request state
    if hasattr(request.state, "request_id"):
        return request.state.request_id

    return None


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions with consistent response format."""
    request_id = get_request_id(request)

    # Log the error
    exc.log(request_id)

    # Build response
    content = {
        "error": True,
        "code": exc.code.value,
        "message": exc.message,
        "details": exc.details,
    }

    if request_id:
        content["request_id"] = request_id

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle standard HTTPException with consistent response format."""
    request_id = get_request_id(request)

    # If detail is already structured, use it
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail
    else:
        # Wrap unstructured detail
        content = {
            "error": True,
            "code": ErrorCode.INTERNAL_ERROR.value,
            "message": str(exc.detail) if exc.detail else "An error occurred",
            "details": {},
        }

    if request_id:
        content["request_id"] = request_id

    logger.warning(
        "HTTP Exception",
        status_code=exc.status_code,
        message=content.get("message"),
        request_id=request_id,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with logging and safe response."""
    request_id = get_request_id(request)

    # Log the full exception
    logger.exception(
        "Unhandled exception",
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    content = {
        "error": True,
        "code": ErrorCode.INTERNAL_ERROR.value,
        "message": "An unexpected error occurred",
        "details": {},
    }

    if request_id:
        content["request_id"] = request_id

    return JSONResponse(
        status_code=500,
        content=content,
    )


def register_exception_handlers(app) -> None:
    """Register all exception handlers with a FastAPI app.

    Usage:
        from app.exceptions import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
