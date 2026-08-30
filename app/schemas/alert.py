"""Alert and BlacklistEntry Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from app.schemas.common import AppBaseModel

VALID_ALERT_TYPES = {
    "BLACKLIST_MATCH",
    "ROUTE_ANOMALY",
    "TRAVEL_TIME_ANOMALY",
    "CAMERA_OFFLINE",
    "UNUSUAL_VEHICLE_PATTERN",
}

VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_ALERT_STATUSES = {"NEW", "ACKNOWLEDGED", "RESOLVED", "DISMISSED"}


# ---------------------------------------------------------------------------
# Blacklist Schemas
# ---------------------------------------------------------------------------


class BlacklistEntryBase(AppBaseModel):
    plate_text: str = Field(..., max_length=20, examples=["KA01AB1234"])
    reason: str = Field(
        ..., max_length=255, examples=["Stolen vehicle report", "Wanted suspect vehicle"]
    )
    priority: str = Field(default="medium", examples=["low", "medium", "high", "critical"])
    is_active: bool = Field(default=True)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_SEVERITIES:
            raise ValueError(f"priority must be one of: {', '.join(sorted(VALID_SEVERITIES))}")
        return v


class BlacklistEntryCreate(BlacklistEntryBase):
    pass


class BlacklistEntryUpdate(AppBaseModel):
    reason: str | None = None
    priority: str | None = None
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    notes: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class BlacklistEntryResponse(BlacklistEntryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BlacklistFilters(AppBaseModel):
    plate_text: str | None = None
    priority: str | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Alert Schemas
# ---------------------------------------------------------------------------


class AlertBase(AppBaseModel):
    alert_code: str = Field(..., examples=["ALT-20260830-0001"])
    alert_type: str = Field(..., examples=["BLACKLIST_MATCH", "ROUTE_ANOMALY"])
    severity: str = Field(default="medium", examples=["low", "medium", "high", "critical"])
    status: str = Field(default="NEW", examples=["NEW", "ACKNOWLEDGED", "RESOLVED", "DISMISSED"])
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    title: str = Field(..., max_length=255)
    description: str = Field(..., description="Explainable description of the anomaly or detection")
    camera_id: uuid.UUID | None = None
    vehicle_identity_id: uuid.UUID | None = None
    trajectory_id: uuid.UUID | None = None
    observation_id: uuid.UUID | None = None
    blacklist_entry_id: uuid.UUID | None = None
    evidence: dict[str, Any] = Field(
        default_factory=dict, description="Structured explainability evidence"
    )
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("alert_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_ALERT_TYPES:
            raise ValueError(f"alert_type must be one of: {', '.join(sorted(VALID_ALERT_TYPES))}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in VALID_SEVERITIES:
            raise ValueError(f"severity must be one of: {', '.join(sorted(VALID_SEVERITIES))}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_ALERT_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(VALID_ALERT_STATUSES))}")
        return v


class AlertCreate(AlertBase):
    pass


class AlertResponse(AlertBase):
    id: uuid.UUID
    camera_name: str | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    dismissed_at: datetime | None = None
    dismissed_by: str | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AlertDetailResponse(AlertResponse):
    pass


class AlertActionRequest(AppBaseModel):
    action_by: str = Field(default="operator", description="Identifier of operator or system user")
    notes: str | None = Field(default=None, description="Action explanation or resolution summary")


class AlertFilters(AppBaseModel):
    alert_type: str | None = None
    severity: str | None = None
    status: str | None = None
    camera_id: uuid.UUID | None = None
    vehicle_identity_id: uuid.UUID | None = None
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    created_after: datetime | None = None
    created_before: datetime | None = None
