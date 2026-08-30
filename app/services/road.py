"""Road service — business logic for road management."""

from __future__ import annotations

import uuid
from typing import Any

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping, shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.road import Road
from app.repositories.road import RoadRepository
from app.schemas.common import PaginatedResponse
from app.schemas.road import GeoJSONGeometry, RoadCreate, RoadResponse, RoadUpdate

logger = get_logger(__name__)


def _geometry_to_geojson(geom: Any) -> GeoJSONGeometry | None:
    """Convert a GeoAlchemy2 geometry value to a GeoJSON dict."""
    if geom is None:
        return None
    try:
        shapely_geom = to_shape(geom)
        geojson = mapping(shapely_geom)
        return GeoJSONGeometry(type=geojson["type"], coordinates=list(geojson["coordinates"]))
    except Exception:
        return None


def _geojson_to_wkt(geojson: GeoJSONGeometry | None) -> str | None:
    """Convert a GeoJSONGeometry schema to a WKT string with SRID."""
    if geojson is None:
        return None
    try:
        geom = shape({"type": geojson.type, "coordinates": geojson.coordinates})
        return f"SRID=4326;{geom.wkt}"
    except Exception as e:
        raise ValueError(f"Invalid geometry: {e}") from e


def _road_to_response(road: Road) -> RoadResponse:
    camera_count = len(road.cameras) if road.cameras else 0
    return RoadResponse(
        id=road.id,
        name=road.name,
        external_id=road.external_id,
        road_type=road.road_type,
        direction=road.direction,
        speed_limit_kmh=road.speed_limit_kmh,
        lane_count=road.lane_count,
        description=road.description,
        geometry=_geometry_to_geojson(road.geometry),
        camera_count=camera_count,
    )


class RoadService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = RoadRepository(session)

    async def create_road(self, payload: RoadCreate) -> RoadResponse:
        # Check external_id uniqueness if provided
        if payload.external_id:
            existing = await self._repo.get_by_external_id(payload.external_id)
            if existing:
                raise ConflictError("Road", f"external_id '{payload.external_id}' already exists")

        road = Road(
            name=payload.name,
            external_id=payload.external_id,
            road_type=payload.road_type,
            direction=payload.direction,
            speed_limit_kmh=payload.speed_limit_kmh,
            lane_count=payload.lane_count,
            description=payload.description,
            geometry=_geojson_to_wkt(payload.geometry),
        )
        road = await self._repo.create(road)
        logger.info("road.created", road_id=str(road.id), name=road.name)
        return _road_to_response(road)

    async def get_road(self, road_id: uuid.UUID) -> RoadResponse:
        road = await self._repo.get_by_id(road_id)
        if not road:
            raise NotFoundError("Road", road_id)
        return _road_to_response(road)

    async def list_roads(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        road_type: str | None = None,
        direction: str | None = None,
    ) -> PaginatedResponse[RoadResponse]:
        offset = (page - 1) * page_size
        roads, total = await self._repo.list_roads(
            offset=offset, limit=page_size, road_type=road_type, direction=direction
        )
        items = [_road_to_response(r) for r in roads]
        return PaginatedResponse.build(items=items, total=total, page=page, page_size=page_size)

    async def update_road(self, road_id: uuid.UUID, payload: RoadUpdate) -> RoadResponse:
        road = await self._repo.get_by_id(road_id)
        if not road:
            raise NotFoundError("Road", road_id)

        updates: dict[str, Any] = {}
        for field in (
            "name",
            "external_id",
            "road_type",
            "direction",
            "speed_limit_kmh",
            "lane_count",
            "description",
        ):
            val = getattr(payload, field, None)
            if val is not None:
                updates[field] = val
        if payload.geometry is not None:
            updates["geometry"] = _geojson_to_wkt(payload.geometry)

        road = await self._repo.update(road, updates)
        return _road_to_response(road)

    async def delete_road(self, road_id: uuid.UUID) -> None:
        road = await self._repo.get_by_id(road_id)
        if not road:
            raise NotFoundError("Road", road_id)
        await self._repo.delete(road)
        logger.info("road.deleted", road_id=str(road_id))

    async def find_roads_near(
        self,
        longitude: float,
        latitude: float,
        radius_m: float = 500.0,
    ) -> list[RoadResponse]:
        roads = await self._repo.find_near_point(longitude, latitude, radius_m)
        return [_road_to_response(r) for r in roads]
