"""Domain event schemas, event types, and dead-letter models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import ConfigDict, Field

from app.schemas.common import AppBaseModel


class EventType(str, Enum):
    VEHICLE_OBSERVED = "VEHICLE_OBSERVED"
    PLATE_RECOGNIZED = "PLATE_RECOGNIZED"
    TRACK_UPDATED = "TRACK_UPDATED"
    VEHICLE_MATCHED = "VEHICLE_MATCHED"
    TRAJECTORY_UPDATED = "TRAJECTORY_UPDATED"
    ALERT_CREATED = "ALERT_CREATED"
    OBSERVATION_FAILED = "OBSERVATION_FAILED"


class DomainEvent(AppBaseModel):
    """
    Standardized, versioned event contract for real-time traffic processing.
    """
    event_id: str = Field(
        default_factory=lambda: f"EVT-{uuid.uuid4()}",
        description="Globally unique identifier for the event",
    )
    event_type: str = Field(..., description="VEHICLE_OBSERVED | PLATE_RECOGNIZED | ...")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event creation timestamp",
    )
    source: str = Field(..., description="Originating subsystem (e.g. anpr-pipeline, tracker)")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event data payload")
    schema_version: str = Field(default="1.0", description="Semantic schema version")
    idempotency_key: Optional[str] = Field(
        default=None, description="Optional key to enforce idempotent deduplication"
    )

    model_config = ConfigDict(populate_by_name=True)


class DeadLetterRecord(AppBaseModel):
    """
    Diagnostic record of an event that failed processing after all retries.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_id: str
    event_type: str
    source: str
    payload: dict[str, Any]
    error_message: str
    error_traceback: Optional[str] = None
    retry_count: int = Field(default=1)
    first_failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_failed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="FAILED", description="FAILED | RETRIED | RESOLVED")


class EventProcessingResult(AppBaseModel):
    success: bool
    event_id: str
    event_type: str
    handler_count: int
    errors: list[str] = Field(default_factory=list)
