"""
Development seed script — Synthetic City Network (Phase 2)

Creates a plausible road graph for a fictional Indian city district with:
  - 5 roads (arterial + collector + local)
  - 8 cameras at key junctions
  - 14 directed camera-to-camera connections

Usage:
    python tools/seed_city.py

Requires DATABASE_URL and ALEMBIC_DATABASE_URL in .env (or environment).
Idempotent: skips objects that already exist by camera_id / external_id.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Make the project root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

# ---------------------------------------------------------------------------
# Seed data — synthetic city district
# ---------------------------------------------------------------------------

ROADS = [
    {
        "external_id": "seed/road/mg-road",
        "name": "MG Road",
        "road_type": "arterial",
        "direction": "two_way",
        "speed_limit_kmh": 60,
        "lane_count": 6,
        "description": "Main arterial road running east-west through city centre",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.5800, 12.9750],
                [77.5900, 12.9748],
                [77.6000, 12.9745],
                [77.6100, 12.9742],
            ],
        },
    },
    {
        "external_id": "seed/road/ring-road-north",
        "name": "Ring Road North",
        "road_type": "arterial",
        "direction": "two_way",
        "speed_limit_kmh": 80,
        "lane_count": 4,
        "description": "Northern bypass arterial",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.5800, 12.9900],
                [77.5900, 12.9900],
                [77.6000, 12.9900],
                [77.6100, 12.9900],
            ],
        },
    },
    {
        "external_id": "seed/road/residency-road",
        "name": "Residency Road",
        "road_type": "collector",
        "direction": "one_way_forward",
        "speed_limit_kmh": 40,
        "lane_count": 2,
        "description": "One-way collector road through residential zone",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.5900, 12.9748],
                [77.5900, 12.9800],
                [77.5900, 12.9850],
            ],
        },
    },
    {
        "external_id": "seed/road/brigade-road",
        "name": "Brigade Road",
        "road_type": "collector",
        "direction": "two_way",
        "speed_limit_kmh": 40,
        "lane_count": 4,
        "description": "Commercial collector road",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.6000, 12.9745],
                [77.6000, 12.9800],
                [77.6000, 12.9850],
                [77.6000, 12.9900],
            ],
        },
    },
    {
        "external_id": "seed/road/industrial-link",
        "name": "Industrial Area Link Road",
        "road_type": "local",
        "direction": "two_way",
        "speed_limit_kmh": 30,
        "lane_count": 2,
        "description": "Local road connecting industrial area",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [77.6100, 12.9742],
                [77.6100, 12.9800],
                [77.6100, 12.9900],
            ],
        },
    },
]

# 8 cameras — at key junctions of the above road network
CAMERAS = [
    {
        "camera_id": "CAM-MG-W",
        "name": "MG Road West Entry",
        "road_key": "seed/road/mg-road",
        "direction": "E",
        "fov_degrees": 110,
        "lane_count": 6,
        "status": "active",
        "location": {"type": "Point", "coordinates": [77.5800, 12.9750]},
        "height_m": 8,
        "metadata": {
            "stream_url": "rtsp://10.0.1.1:554/cam-mg-w",
            "model": "Hikvision DS-2CD2085G1",
        },
    },
    {
        "camera_id": "CAM-MG-C1",
        "name": "MG Road Central 1 (Residency Junction)",
        "road_key": "seed/road/mg-road",
        "direction": "E",
        "fov_degrees": 120,
        "lane_count": 6,
        "status": "active",
        "location": {"type": "Point", "coordinates": [77.5900, 12.9748]},
        "height_m": 8,
        "metadata": {"stream_url": "rtsp://10.0.1.2:554/cam-mg-c1"},
    },
    {
        "camera_id": "CAM-MG-C2",
        "name": "MG Road Central 2 (Brigade Junction)",
        "road_key": "seed/road/mg-road",
        "direction": "E",
        "fov_degrees": 120,
        "lane_count": 6,
        "status": "active",
        "location": {"type": "Point", "coordinates": [77.6000, 12.9745]},
        "height_m": 8,
        "metadata": {"stream_url": "rtsp://10.0.1.3:554/cam-mg-c2"},
    },
    {
        "camera_id": "CAM-MG-E",
        "name": "MG Road East Entry (Industrial Junction)",
        "road_key": "seed/road/mg-road",
        "direction": "E",
        "fov_degrees": 110,
        "lane_count": 6,
        "status": "active",
        "location": {"type": "Point", "coordinates": [77.6100, 12.9742]},
        "height_m": 8,
        "metadata": {"stream_url": "rtsp://10.0.1.4:554/cam-mg-e"},
    },
    {
        "camera_id": "CAM-RES-N",
        "name": "Residency Road North",
        "road_key": "seed/road/residency-road",
        "direction": "N",
        "fov_degrees": 100,
        "lane_count": 2,
        "status": "active",
        "location": {"type": "Point", "coordinates": [77.5900, 12.9850]},
        "height_m": 6,
        "metadata": {"stream_url": "rtsp://10.0.2.1:554/cam-res-n"},
    },
    {
        "camera_id": "CAM-BRG-N",
        "name": "Brigade Road North",
        "road_key": "seed/road/brigade-road",
        "direction": "N",
        "fov_degrees": 100,
        "lane_count": 4,
        "status": "active",
        "location": {"type": "Point", "coordinates": [77.6000, 12.9850]},
        "height_m": 6,
        "metadata": {"stream_url": "rtsp://10.0.2.2:554/cam-brg-n"},
    },
    {
        "camera_id": "CAM-RING-W",
        "name": "Ring Road North West Entry",
        "road_key": "seed/road/ring-road-north",
        "direction": "E",
        "fov_degrees": 115,
        "lane_count": 4,
        "status": "active",
        "location": {"type": "Point", "coordinates": [77.5800, 12.9900]},
        "height_m": 10,
        "metadata": {"stream_url": "rtsp://10.0.3.1:554/cam-ring-w"},
    },
    {
        "camera_id": "CAM-IND-N",
        "name": "Industrial Link Road North",
        "road_key": "seed/road/industrial-link",
        "direction": "N",
        "fov_degrees": 100,
        "lane_count": 2,
        "status": "maintenance",
        "location": {"type": "Point", "coordinates": [77.6100, 12.9900]},
        "height_m": 6,
        "metadata": {"stream_url": "rtsp://10.0.4.1:554/cam-ind-n"},
        "notes": "Scheduled maintenance 2026-09-01",
    },
]

# Directed camera connections — plausible vehicle movements
# Format: (source_camera_id, dest_camera_id, min_s, max_s, avg_s, dist_m, type)
CONNECTIONS = [
    # MG Road eastbound progression
    ("CAM-MG-W", "CAM-MG-C1", 60, 180, 90, 850.0, "direct"),
    ("CAM-MG-C1", "CAM-MG-C2", 60, 180, 90, 900.0, "direct"),
    ("CAM-MG-C2", "CAM-MG-E", 60, 180, 90, 950.0, "direct"),
    # MG Road westbound progression
    ("CAM-MG-E", "CAM-MG-C2", 60, 180, 90, 950.0, "direct"),
    ("CAM-MG-C2", "CAM-MG-C1", 60, 180, 90, 900.0, "direct"),
    ("CAM-MG-C1", "CAM-MG-W", 60, 180, 90, 850.0, "direct"),
    # MG Road → Residency Road (turning north at CAM-MG-C1)
    ("CAM-MG-C1", "CAM-RES-N", 90, 300, 150, 1200.0, "via_junction"),
    # MG Road → Brigade Road (turning north at CAM-MG-C2)
    ("CAM-MG-C2", "CAM-BRG-N", 90, 300, 150, 1100.0, "via_junction"),
    # Residency Road → Ring Road North
    ("CAM-RES-N", "CAM-RING-W", 120, 360, 180, 1500.0, "direct"),
    # Brigade Road → Ring Road North (Industrial junction)
    ("CAM-BRG-N", "CAM-IND-N", 90, 300, 150, 1300.0, "via_junction"),
    # Industrial Link → Ring Road
    ("CAM-IND-N", "CAM-RING-W", 90, 300, 150, 1800.0, "via_junction"),
    # Ring Road eastbound → Industrial area
    ("CAM-RING-W", "CAM-IND-N", 120, 360, 180, 2200.0, "direct"),
    # Cross connection: MG Road East to Industrial via link road
    ("CAM-MG-E", "CAM-IND-N", 60, 180, 90, 600.0, "direct"),
    # Return: Industrial back to MG Road East
    ("CAM-IND-N", "CAM-MG-E", 60, 180, 90, 600.0, "direct"),
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        # Import models
        from app.models.camera import Camera
        from app.models.camera_connection import CameraConnection
        from app.models.road import Road

        # ----------------------------------------------------------------
        # Roads
        # ----------------------------------------------------------------
        road_id_map: dict[str, object] = {}

        for rd in ROADS:
            existing = (
                await session.execute(sa.select(Road).where(Road.external_id == rd["external_id"]))
            ).scalar_one_or_none()

            if existing:
                print(f"  [SKIP] Road already exists: {rd['name']}")
                road_id_map[rd["external_id"]] = existing.id  # type: ignore[union-attr]
                continue

            geom_raw = rd.pop("geometry", None)
            road_key = rd.pop("road_key", None)

            geom_wkt = None
            if geom_raw:
                from shapely.geometry import shape

                geom_wkt = f"SRID=4326;{shape(geom_raw).wkt}"

            road = Road(**{k: v for k, v in rd.items() if k != "road_key"}, geometry=geom_wkt)
            session.add(road)
            await session.flush()
            await session.refresh(road)
            road_id_map[road.external_id] = road.id  # type: ignore[union-attr]
            print(f"  [CREATED] Road: {road.name} ({road.id})")  # type: ignore[union-attr]

        # ----------------------------------------------------------------
        # Cameras
        # ----------------------------------------------------------------
        camera_id_map: dict[str, object] = {}

        for cam in CAMERAS:
            existing = (
                await session.execute(sa.select(Camera).where(Camera.camera_id == cam["camera_id"]))
            ).scalar_one_or_none()

            if existing:
                print(f"  [SKIP] Camera already exists: {cam['camera_id']}")
                camera_id_map[cam["camera_id"]] = existing.id  # type: ignore[union-attr]
                continue

            road_key = cam.pop("road_key")
            location_raw = cam.pop("location", None)
            metadata = cam.pop("metadata", None)

            location_wkt = None
            if location_raw:
                from shapely.geometry import shape

                location_wkt = f"SRID=4326;{shape(location_raw).wkt}"

            road_id = road_id_map.get(road_key)
            camera = Camera(
                **dict(cam.items()),
                road_id=road_id,
                location=location_wkt,
                metadata_=metadata,
            )
            session.add(camera)
            await session.flush()
            await session.refresh(camera)
            camera_id_map[camera.camera_id] = camera.id  # type: ignore[union-attr]
            print(f"  [CREATED] Camera: {camera.camera_id} ({camera.id})")  # type: ignore[union-attr]

        # ----------------------------------------------------------------
        # Connections
        # ----------------------------------------------------------------
        for src_cid, dst_cid, min_s, max_s, avg_s, dist_m, conn_type in CONNECTIONS:
            src_id = camera_id_map.get(src_cid)
            dst_id = camera_id_map.get(dst_cid)

            if not src_id or not dst_id:
                print(f"  [WARN] Missing camera for connection {src_cid} → {dst_cid}")
                continue

            existing = (
                await session.execute(
                    sa.select(CameraConnection).where(
                        CameraConnection.source_camera_id == src_id,
                        CameraConnection.destination_camera_id == dst_id,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                print(f"  [SKIP] Connection already exists: {src_cid} → {dst_cid}")
                continue

            conn = CameraConnection(
                source_camera_id=src_id,
                destination_camera_id=dst_id,
                min_travel_time_s=min_s,
                max_travel_time_s=max_s,
                avg_travel_time_s=avg_s,
                distance_m=dist_m,
                connection_type=conn_type,
            )
            session.add(conn)
            await session.flush()
            print(f"  [CREATED] Connection: {src_cid} → {dst_cid} ({min_s}-{max_s}s, {dist_m}m)")

        await session.commit()
        print("\n✅ Seed complete.")

    await engine.dispose()


if __name__ == "__main__":
    print("🌱 Seeding city network...")
    asyncio.run(seed())
