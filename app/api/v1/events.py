"""Real-time event processing and dead-letter queue endpoints — /api/v1/events."""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.events.contracts import DeadLetterRecord, DomainEvent, EventProcessingResult
from app.events.coordinator import EventCoordinator
from app.events.in_memory import InMemoryDeadLetterStore, InMemoryEventBus
from app.events.interfaces import DeadLetterStore
from app.models.camera import Camera
from app.schemas.vehicle_observation import VehicleObservationCreate

router = APIRouter(prefix="/events", tags=["events"])

# Global event bus singleton for in-app event dispatching
_global_dead_letter = InMemoryDeadLetterStore()
_global_bus = InMemoryEventBus(dead_letter_store=_global_dead_letter)


def get_event_bus() -> InMemoryEventBus:
    return _global_bus


def get_dead_letter_store() -> DeadLetterStore:
    return _global_dead_letter


@router.post(
    "/publish",
    response_model=EventProcessingResult,
    status_code=status.HTTP_200_OK,
    summary="Publish a domain event to the real-time event bus",
)
async def publish_event(
    event: DomainEvent,
    bus: InMemoryEventBus = Depends(get_event_bus),
) -> EventProcessingResult:
    return await bus.publish(event)


@router.get(
    "/recent",
    response_model=list[DomainEvent],
    summary="Get recent real-time domain events from memory buffer",
)
async def get_recent_events(
    bus: InMemoryEventBus = Depends(get_event_bus),
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None, description="Optional event type filter"),
) -> list[DomainEvent]:
    return bus.get_recent(limit=limit, event_type=event_type)


@router.get(
    "/stream",
    summary="Live Server-Sent Events (SSE) stream of real-time traffic events",
    response_class=StreamingResponse,
)
async def stream_realtime_events(
    request: Request,
    bus: InMemoryEventBus = Depends(get_event_bus),
) -> StreamingResponse:
    """
    Continuous real-time SSE stream of domain events (VEHICLE_OBSERVED, PLATE_RECOGNIZED, ALERT_CREATED, etc.).
    """
    queue: asyncio.Queue[DomainEvent] = asyncio.Queue(maxsize=100)
    bus.add_listener(queue)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send initial connected event
            connected_data = {
                "event_id": f"SYS-{uuid.uuid4()}",
                "event_type": "CONNECTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "server-stream",
                "payload": {"message": "Connected to CityTrack AI Real-Time Telemetry Stream"},
            }
            yield f"data: {json.dumps(connected_data)}\n\n"

            # Flush recent events so the client has immediate context
            recent = bus.get_recent(limit=5)
            for ev in recent:
                yield f"data: {json.dumps(ev.model_dump(mode='json'))}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield ": heartbeat\n\n"
        finally:
            bus.remove_listener(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


INDIAN_STATE_PLATES = [
    ("KA", "01", ["MJ4040", "AB1234", "HG7788", "EF5678", "CD9012", "XY3322"]),
    ("DL", "03", ["CA1234", "CC4567", "DD8899", "EE1122", "FF3344", "ZZ9900"]),
    ("MH", "02", ["CB9876", "AY1122", "BZ3344", "CX5566", "DF7788", "EG9900"]),
    ("TS", "09", ["UA5555", "UB6677", "UC7788", "UD8899", "UE1122", "UF3344"]),
    ("TN", "07", ["JK7890", "JL8901", "JM9012", "JN0123", "JP1234", "JQ2345"]),
    ("WB", "04", ["LM2345", "LN3456", "LP4567", "LQ5678", "LR6789", "LS7890"]),
]

VEHICLE_CLASSES = [
    ("car", 0.45),
    ("auto_rickshaw", 0.20),
    ("motorcycle", 0.20),
    ("bus", 0.10),
    ("truck", 0.05),
]

COLORS = ["White", "Silver", "Black", "Red", "Blue", "Yellow", "Grey"]


@router.post(
    "/simulate-tick",
    summary="Trigger a simulated real-time CCTV detection across Indian metropolitan network",
)
async def simulate_live_tick(
    db: AsyncSession = Depends(get_db),
    bus: InMemoryEventBus = Depends(get_event_bus),
    count: int = Query(1, ge=1, le=10, description="Number of observations to generate"),
) -> dict:
    """
    Simulate live edge CCTV cameras capturing traffic in Bengaluru, Delhi NCR, Mumbai, Hyderabad, Chennai, or Kolkata.
    """
    cameras = (await db.execute(select(Camera).where(Camera.status == "active"))).scalars().all()
    if not cameras:
        cameras = (await db.execute(select(Camera))).scalars().all()

    if not cameras:
        return {"status": "error", "message": "No cameras found. Please seed the database first."}

    results = []
    coordinator = EventCoordinator(session=db, event_bus=bus)

    for _ in range(count):
        cam = random.choice(cameras)
        state_code, rto, suffixes = random.choice(INDIAN_STATE_PLATES)
        plate_str = f"{state_code}{rto}{random.choice(suffixes)}"
        classes, weights = zip(*VEHICLE_CLASSES, strict=False)
        v_class = random.choices(classes, weights=weights)[0]
        color = random.choice(COLORS)
        speed = round(random.uniform(25.0, 95.0), 1)
        conf = round(random.uniform(0.88, 0.99), 3)

        payload = VehicleObservationCreate(
            source=f"edge-node-{cam.camera_id.lower()}",
            source_observation_id=f"sim-{uuid.uuid4().hex[:10]}",
            camera_id=cam.id,
            observed_at=datetime.now(timezone.utc),
            vehicle_class=v_class,
            vehicle_color=color,
            detection_confidence=conf,
            plate_text=plate_str,
            plate_confidence=round(conf - random.uniform(0.01, 0.05), 3),
            plate_region=state_code,
            estimated_speed_kmh=speed,
            direction=cam.direction or "forward",
        )

        pipeline_res = await coordinator.handle_vehicle_observed(payload)
        results.append(
            {
                "camera": cam.name,
                "plate": plate_str,
                "vehicle_class": v_class,
                "speed_kmh": speed,
                "confidence": conf,
                "trajectory_id": pipeline_res.get("trajectory_id"),
                "alert": pipeline_res.get("alert"),
            }
        )

    return {"status": "success", "generated_count": len(results), "events": results}


@router.get(
    "/dead-letter",
    response_model=list[DeadLetterRecord],
    summary="List failed event records from the dead-letter queue for diagnostics",
)
async def list_dead_letters(
    dl_store: DeadLetterStore = Depends(get_dead_letter_store),
    status_filter: str | None = Query(None, description="FAILED | RETRIED | RESOLVED"),
    limit: int = Query(50, ge=1, le=200),
) -> list[DeadLetterRecord]:
    return await dl_store.list_dead_letters(status=status_filter, limit=limit)


@router.post(
    "/dead-letter/{record_id}/resolve",
    summary="Mark a dead-letter event as resolved",
)
async def resolve_dead_letter(
    record_id: uuid.UUID,
    dl_store: DeadLetterStore = Depends(get_dead_letter_store),
) -> dict[str, str]:
    await dl_store.mark_resolved(record_id)
    return {"status": "RESOLVED", "record_id": str(record_id)}
