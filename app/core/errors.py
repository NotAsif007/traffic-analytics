"""
HTTP error handling.

Translates domain exceptions → consistent JSON error responses.
Registers FastAPI exception handlers.

All error responses share the same envelope:
    {
        "error": {
            "code":    "NOT_FOUND",
            "message": "Camera not found",
            "details": {"resource": "Camera", "identifier": "abc-123"}
        }
    }
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    ConflictError,
    DatabaseError,
    NotFoundError,
    ServiceUnavailableError,
    TrafficAnalyticsError,
    ValidationError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI application."""

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(404, "NOT_FOUND", exc.message, exc.details)

    @app.exception_handler(ValidationError)
    async def handle_validation(_: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(422, "VALIDATION_ERROR", exc.message, exc.details)

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return _error_response(409, "CONFLICT", exc.message, exc.details)

    @app.exception_handler(DatabaseError)
    async def handle_database(_: Request, exc: DatabaseError) -> JSONResponse:
        logger.error("database.error", error=exc.message, details=exc.details)
        return _error_response(503, "DATABASE_ERROR", "A database error occurred.")

    @app.exception_handler(ServiceUnavailableError)
    async def handle_service_unavailable(_: Request, exc: ServiceUnavailableError) -> JSONResponse:
        logger.warning("service.unavailable", error=exc.message)
        return _error_response(503, "SERVICE_UNAVAILABLE", exc.message, exc.details)

    @app.exception_handler(TrafficAnalyticsError)
    async def handle_domain(_: Request, exc: TrafficAnalyticsError) -> JSONResponse:
        logger.warning("domain.error", error=exc.message)
        return _error_response(400, "DOMAIN_ERROR", exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Translate Pydantic v2 validation errors into our error envelope."""
        errors = []
        for e in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in e["loc"]),
                    "message": e["msg"],
                    "type": e["type"],
                }
            )
        return _error_response(
            422,
            "REQUEST_VALIDATION_ERROR",
            "Request validation failed.",
            {"errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(exc.status_code, "HTTP_ERROR", exc.detail)

    @app.exception_handler(Exception)
    async def handle_unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled.error", exc_info=exc)
        return _error_response(
            500,
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again later.",
        )
