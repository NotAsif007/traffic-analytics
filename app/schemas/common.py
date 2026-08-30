"""
Common Pydantic schemas shared across all API resources.

Includes:
- Standard error response envelope
- Paginated response wrapper
- Base config for all response schemas
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Base schema config
# ---------------------------------------------------------------------------


class AppBaseModel(BaseModel):
    """
    Base model with shared configuration.

    - from_attributes: enables creating schemas directly from SQLAlchemy ORM objects
    - populate_by_name: allows using field names even when aliases are defined
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )


# ---------------------------------------------------------------------------
# Error response
# ---------------------------------------------------------------------------


class ErrorDetail(AppBaseModel):
    """Inner detail object within an error response."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(AppBaseModel):
    """
    Standard error envelope.

    All API errors return this shape:
        {"error": {"code": "...", "message": "...", "details": {...}}}
    """

    error: ErrorDetail


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

T = TypeVar("T")


class PaginatedResponse(AppBaseModel, Generic[T]):
    """Generic paginated list response."""

    items: list[T]
    total: int = Field(..., description="Total number of matching records")
    page: int = Field(..., description="Current page (1-indexed)")
    page_size: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")

    @classmethod
    def build(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        pages = max(1, -(-total // page_size))  # ceiling division
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ---------------------------------------------------------------------------
# Common query parameters
# ---------------------------------------------------------------------------


class PaginationParams(AppBaseModel):
    """Reusable pagination query parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=200, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
