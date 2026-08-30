"""
Health check schemas.

These are the request/response models for GET /api/v1/health
and GET /api/v1/health/ready.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import AppBaseModel


class ComponentStatus(AppBaseModel):
    """Status of a single infrastructure component."""

    status: Literal["ok", "degraded", "unavailable"]
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip latency in milliseconds (if measurable)",
    )
    detail: str | None = Field(
        default=None,
        description="Additional context, e.g. version or error message",
    )


class HealthResponse(AppBaseModel):
    """
    Response from GET /api/v1/health.

    Reports the overall API status and the status of each component
    the API depends on.
    """

    status: Literal["ok", "degraded", "unavailable"]
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    components: dict[str, ComponentStatus] = Field(
        default_factory=dict,
        description="Status of each infrastructure component",
    )
