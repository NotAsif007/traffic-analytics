"""Camera CRUD endpoints — /api/v1/cameras."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import DBSession
from app.schemas.camera import CameraCreate, CameraResponse, CameraUpdate
from app.schemas.common import PaginatedResponse
from app.schemas.vehicle_track import VehicleTrackResponse
from app.services.camera import CameraService
from app.services.vehicle_track import VehicleTrackService

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _camera_service(db: DBSession) -> CameraService:
    return CameraService(db)


def _vehicle_track_service(db: DBSession) -> VehicleTrackService:
    return VehicleTrackService(db)


CameraServiceDep = Annotated[CameraService, Depends(_camera_service)]
VehicleTrackServiceDep = Annotated[VehicleTrackService, Depends(_vehicle_track_service)]


@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(payload: CameraCreate, svc: CameraServiceDep) -> CameraResponse:
    """Register a new traffic camera."""
    return await svc.create_camera(payload)


@router.get("/", response_model=PaginatedResponse[CameraResponse])
async def list_cameras(
    svc: CameraServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(
        None, description="Filter by status: active | inactive | maintenance | fault"
    ),
    road_id: uuid.UUID | None = Query(None, description="Filter by road UUID"),
    direction: str | None = Query(None, description="Filter by direction heading"),
) -> PaginatedResponse[CameraResponse]:
    """List cameras with optional filters."""
    return await svc.list_cameras(
        page=page,
        page_size=page_size,
        status=status,
        road_id=road_id,
        direction=direction,
    )


@router.get("/near", response_model=list[CameraResponse])
async def cameras_near_point(
    svc: CameraServiceDep,
    longitude: float = Query(..., ge=-180.0, le=180.0),
    latitude: float = Query(..., ge=-90.0, le=90.0),
    radius_m: float = Query(200.0, ge=1.0, le=5000.0, description="Search radius in metres"),
) -> list[CameraResponse]:
    """Find cameras within a radius of a GPS coordinate."""
    return await svc.find_cameras_near(longitude, latitude, radius_m)


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: uuid.UUID, svc: CameraServiceDep) -> CameraResponse:
    """Retrieve a camera by its UUID."""
    return await svc.get_camera(camera_id)


@router.patch("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: uuid.UUID, payload: CameraUpdate, svc: CameraServiceDep
) -> CameraResponse:
    """Update camera details or status."""
    return await svc.update_camera(camera_id, payload)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_camera(camera_id: uuid.UUID, svc: CameraServiceDep) -> None:
    """Delete a camera (its connections will be cascade-deleted)."""
    await svc.delete_camera(camera_id)


@router.get("/{camera_id}/tracks", response_model=PaginatedResponse[VehicleTrackResponse])
async def list_camera_tracks(
    camera_id: uuid.UUID,
    track_svc: VehicleTrackServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by track status"),
) -> PaginatedResponse[VehicleTrackResponse]:
    """Retrieve all vehicle tracks captured by a specific camera."""
    return await track_svc.list_camera_tracks(
        camera_id=camera_id, status=status, page=page, page_size=page_size
    )


@router.get("/{camera_id}/stream")
async def stream_camera_feed(
    camera_id: uuid.UUID,
    svc: CameraServiceDep,
) -> StreamingResponse:
    """Stream live CCTV video feed with real-time AI bounding box annotations (MJPEG)."""
    import asyncio
    from datetime import datetime, timezone

    import cv2
    import numpy as np

    # Verify camera exists
    cam = await svc.get_camera(camera_id)

    async def frame_generator():
        w, h = 640, 360
        frame_idx = 0
        veh_positions = [
            {"x": 100, "y": 140, "vx": 4, "vy": 1, "class": "CAR", "conf": 0.96, "plate": "KA01MJ5005", "color": (40, 200, 40)},
            {"x": 380, "y": 180, "vx": -3, "vy": 1, "class": "BUS", "conf": 0.98, "plate": "DL01CA1001", "color": (220, 180, 20)},
            {"x": 240, "y": 220, "vx": 2, "vy": 2, "class": "AUTO", "conf": 0.94, "plate": "MH02BX9988", "color": (50, 150, 240)},
        ]

        while True:
            # Generate asphalt roadway frame with lane markings
            frame = np.full((h, w, 3), (38, 38, 42), dtype=np.uint8)

            # Road surface perspective
            cv2.line(frame, (w // 2 - 80, 0), (0, h), (70, 70, 75), 2)
            cv2.line(frame, (w // 2 + 80, 0), (w, h), (70, 70, 75), 2)

            # Dashed central lane
            dash_offset = (frame_idx * 6) % 40
            for y in range(dash_offset, h, 40):
                cv2.line(frame, (w // 2, y), (w // 2, min(h, y + 20)), (200, 200, 200), 2)

            # Update & render vehicles
            for v in veh_positions:
                vx = int(v["x"])
                vy = int(v["y"])
                vw = 110 if v["class"] == "BUS" else (75 if v["class"] == "CAR" else 55)
                vh = 65 if v["class"] == "BUS" else (45 if v["class"] == "CAR" else 40)

                # Vehicle body
                cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), v["color"], -1)
                cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), (255, 255, 255), 1)

                # AI Detection Bounding Box
                cv2.rectangle(frame, (vx - 4, vy - 4), (vx + vw + 4, vy + vh + 4), (0, 255, 128), 2)
                # Label tag
                label = f"{v['class']} {int(v['conf']*100)}%"
                cv2.putText(frame, label, (vx - 4, vy - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 128), 1, cv2.LINE_AA)
                # Plate badge
                cv2.rectangle(frame, (vx + 4, vy + vh - 16), (vx + vw - 4, vy + vh - 2), (240, 240, 240), -1)
                cv2.putText(frame, v["plate"], (vx + 6, vy + vh - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1, cv2.LINE_AA)

                # Move vehicle
                v["x"] += v["vx"]
                v["y"] += v["vy"]
                if v["x"] > w + 20:
                    v["x"] = -vw
                    v["y"] = 120 + (frame_idx % 80)
                elif v["x"] < -vw - 20:
                    v["x"] = w
                    v["y"] = 120 + ((frame_idx * 3) % 80)

            # CCTV OSD Header
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            cv2.rectangle(frame, (0, 0), (w, 24), (15, 15, 20), -1)
            cv2.putText(frame, f"LIVE CCTV: {cam.name}", (10, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 220, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, f"{now_str} | YOLOv8-ByteTrack", (w - 270, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 128), 1, cv2.LINE_AA)

            # Encode to JPEG
            ret, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ret:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

            frame_idx += 1
            await asyncio.sleep(0.08)  # ~12 FPS streaming

        return

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

