"""Real-time event processing and dead-letter queue endpoints — /api/v1/events."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.events.contracts import DeadLetterRecord, DomainEvent, EventProcessingResult
from app.events.in_memory import InMemoryDeadLetterStore, InMemoryEventBus
from app.events.interfaces import DeadLetterStore, EventBus

router = APIRouter(prefix="/events", tags=["events"])

# Global event bus singleton for in-app event dispatching
_global_dead_letter = InMemoryDeadLetterStore()
_global_bus = InMemoryEventBus(dead_letter_store=_global_dead_letter)


def get_event_bus() -> EventBus:
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
    bus: EventBus = Depends(get_event_bus),
) -> EventProcessingResult:
    return await bus.publish(event)


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
