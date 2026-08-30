"""Alert and BlacklistEntry Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

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
    reason: str = Field(..., max_length=255, examples=["Stolen vehicle report", "Wanted suspect vehicle"])
    priority: str = Field(default="medium", examples=["low", "medium", "high", "critical"])
    is_active: bool = Field(default=True)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_SEVERITIES:
            raise ValueError(f"priority must be one of: {', '.join(sorted(VALID_SEVERITIES))}")
        return v


class BlacklistEntryCreate(BlacklistEntryBase):
    pass


class BlacklistEntryUpdate(AppBaseModel):
    reason: Optional[str] = None
    priority: Optional[str] = None
    is_active: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")


class BlacklistEntryResponse(BlacklistEntryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BlacklistFilters(AppBaseModel):
    plate_text: Optional[str] = None
    priority: Optional[str] = None
    is_active: Optional[bool] = None


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
    camera_id: Optional[uuid.UUID] = None
    vehicle_identity_id: Optional[uuid.UUID] = None
    trajectory_id: Optional[uuid.UUID] = None
    observation_id: Optional[uuid.UUID] = None
    blacklist_entry_id: Optional[uuid.UUID] = None
    evidence: dict[str, Any] = Field(default_factory=dict, description="Structured explainability evidence")
    metadata_: Optional[dict[str, Any]] = Field(default=None, alias="metadata")

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
    camera_name: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    dismissed_at: Optional[datetime] = None
    dismissed_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AlertDetailResponse(AlertResponse):
    pass


class AlertActionRequest(AppBaseModel):
    action_by: str = Field(default="operator", description="Identifier of operator or system user")
    notes: Optional[str] = Field(default=None, description="Action explanation or resolution summary")


class AlertFilters(AppBaseModel):
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    camera_id: Optional[uuid.UUID] = None
    vehicle_identity_id: Optional[uuid.UUID] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
