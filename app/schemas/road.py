"""Road Pydantic schemas."""

from __future__ import annotations

import uuid

from pydantic import ConfigDict, Field

from app.schemas.common import AppBaseModel

# ---------------------------------------------------------------------------
# Shared geometry helpers
# ---------------------------------------------------------------------------


class GeoJSONGeometry(AppBaseModel):
    """GeoJSON geometry object (for API input/output)."""

    type: str = Field(..., examples=["LineString"])
    coordinates: list = Field(..., description="GeoJSON coordinate array")


# ---------------------------------------------------------------------------
# Road schemas
# ---------------------------------------------------------------------------


class RoadBase(AppBaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["MG Road"])
    external_id: str | None = Field(None, max_length=128, examples=["way/123456"])
    road_type: str | None = Field(None, max_length=64, examples=["arterial"])
    direction: str | None = Field(
        None,
        max_length=32,
        examples=["one_way_forward", "two_way"],
        description="one_way_forward | one_way_reverse | two_way",
    )
    speed_limit_kmh: int | None = Field(None, ge=0, le=300, examples=[60])
    lane_count: int | None = Field(None, ge=1, le=20, examples=[4])
    description: str | None = None
    geometry: GeoJSONGeometry | None = Field(
        None, description="GeoJSON LineString of the road centreline"
    )


class RoadCreate(RoadBase):
    """Request body for creating a road."""

    pass


class RoadUpdate(AppBaseModel):
    """Request body for updating a road (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    external_id: str | None = Field(None, max_length=128)
    road_type: str | None = Field(None, max_length=64)
    direction: str | None = Field(None, max_length=32)
    speed_limit_kmh: int | None = Field(None, ge=0, le=300)
    lane_count: int | None = Field(None, ge=1, le=20)
    description: str | None = None
    geometry: GeoJSONGeometry | None = None


class RoadResponse(RoadBase):
    """Full road response including server-generated fields."""

    id: uuid.UUID
    camera_count: int = Field(default=0, description="Number of cameras on this road")

    model_config = ConfigDict(from_attributes=True)
