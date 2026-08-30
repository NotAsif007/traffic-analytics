"""
Domain exceptions.

All exceptions in this module are pure Python — no FastAPI or HTTP coupling.
The API error-handling layer in app/core/errors.py translates these into
HTTP responses.
"""

from __future__ import annotations

from typing import Any


class TrafficAnalyticsError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# Not Found
# ---------------------------------------------------------------------------


class NotFoundError(TrafficAnalyticsError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} not found",
            details={"resource": resource, "identifier": str(identifier)},
        )
        self.resource = resource
        self.identifier = identifier


# ---------------------------------------------------------------------------
# Validation / Business Rule Errors
# ---------------------------------------------------------------------------


class ValidationError(TrafficAnalyticsError):
    """Raised when input data violates a domain business rule."""


class ConflictError(TrafficAnalyticsError):
    """Raised when an operation conflicts with existing state."""

    def __init__(self, resource: str, reason: str) -> None:
        super().__init__(
            message=f"Conflict on {resource}: {reason}",
            details={"resource": resource, "reason": reason},
        )


# ---------------------------------------------------------------------------
# Infrastructure Errors
# ---------------------------------------------------------------------------


class DatabaseError(TrafficAnalyticsError):
    """Raised when a database operation fails unexpectedly."""


class ServiceUnavailableError(TrafficAnalyticsError):
    """Raised when an external service dependency is unavailable."""
