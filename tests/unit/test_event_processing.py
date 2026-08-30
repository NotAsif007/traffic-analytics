"""Unit tests for Real-Time Event Processing: idempotency, dead-letter capture, high throughput, and fallbacks."""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.events.contracts import DomainEvent, EventType
from app.events.in_memory import InMemoryDeadLetterStore, InMemoryEventBus
from app.events.redis_bus import ResilientEventBus


@pytest.fixture
def dead_letter_store() -> InMemoryDeadLetterStore:
    return InMemoryDeadLetterStore()


@pytest.fixture
def event_bus(dead_letter_store: InMemoryDeadLetterStore) -> InMemoryEventBus:
    return InMemoryEventBus(dead_letter_store=dead_letter_store)


@pytest.mark.unit
async def test_publish_and_subscribe_success(event_bus: InMemoryEventBus) -> None:
    received: list[DomainEvent] = []

    async def _handler(event: DomainEvent) -> None:
        received.append(event)

    event_bus.subscribe(EventType.VEHICLE_OBSERVED.value, _handler)

    event = DomainEvent(
        event_type=EventType.VEHICLE_OBSERVED.value,
        source="unit-test",
        payload={"plate": "KA01AB1234"},
    )
    result = await event_bus.publish(event)

    assert result.success is True
    assert result.handler_count == 1
    assert len(received) == 1
    assert received[0].payload["plate"] == "KA01AB1234"


@pytest.mark.unit
async def test_idempotent_event_deduplication(event_bus: InMemoryEventBus) -> None:
    """Duplicate events with identical idempotency_key are skipped safely."""
    call_count = 0

    async def _handler(event: DomainEvent) -> None:
        nonlocal call_count
        call_count += 1

    event_bus.subscribe(EventType.VEHICLE_OBSERVED.value, _handler)

    event1 = DomainEvent(
        event_type=EventType.VEHICLE_OBSERVED.value,
        source="unit-test",
        payload={"obs": 1},
        idempotency_key="same-key-12345",
    )
    event2 = DomainEvent(
        event_type=EventType.VEHICLE_OBSERVED.value,
        source="unit-test",
        payload={"obs": 1},
        idempotency_key="same-key-12345",
    )

    res1 = await event_bus.publish(event1)
    res2 = await event_bus.publish(event2)

    assert res1.success is True
    assert res1.handler_count == 1
    assert res2.success is True
    assert res2.handler_count == 0  # Deduplicated and skipped
    assert call_count == 1


@pytest.mark.unit
async def test_failed_processing_records_in_dead_letter(
    event_bus: InMemoryEventBus, dead_letter_store: InMemoryDeadLetterStore
) -> None:
    """Unhandled handler exceptions are caught and stored in DeadLetterStore."""

    async def _failing_handler(event: DomainEvent) -> None:
        raise ValueError("Simulated database connection failure")

    event_bus.subscribe(EventType.PLATE_RECOGNIZED.value, _failing_handler)

    event = DomainEvent(
        event_type=EventType.PLATE_RECOGNIZED.value,
        source="unit-test",
        payload={"plate": "DL01XY9999"},
    )
    result = await event_bus.publish(event)

    assert result.success is False
    assert len(result.errors) == 1

    dead_letters = await dead_letter_store.list_dead_letters()
    assert len(dead_letters) == 1
    dl = dead_letters[0]
    assert dl.event_id == event.event_id
    assert dl.event_type == EventType.PLATE_RECOGNIZED.value
    assert "Simulated database connection failure" in dl.error_message
    assert dl.status == "FAILED"

    # Mark resolved
    await dead_letter_store.mark_resolved(dl.id)
    updated = await dead_letter_store.get_by_id(dl.id)
    assert updated.status == "RESOLVED"


@pytest.mark.unit
async def test_high_throughput_burst(event_bus: InMemoryEventBus) -> None:
    """Simulate 200 concurrent events processed safely."""
    received_count = 0

    async def _handler(event: DomainEvent) -> None:
        nonlocal received_count
        received_count += 1

    event_bus.subscribe(EventType.TRACK_UPDATED.value, _handler)

    tasks = [
        event_bus.publish(
            DomainEvent(
                event_type=EventType.TRACK_UPDATED.value,
                source="burst-test",
                payload={"track_idx": i},
                idempotency_key=f"burst-{i}",
            )
        )
        for i in range(200)
    ]
    results = await asyncio.gather(*tasks)

    assert len(results) == 200
    assert all(r.success for r in results)
    assert received_count == 200


@pytest.mark.unit
async def test_resilient_bus_redis_fallback() -> None:
    """ResilientEventBus falls back seamlessly to in-memory bus when Redis is unreachable."""
    # Invalid unreachable redis URL
    bus = ResilientEventBus(redis_url="redis://localhost:9999/0")

    received = []

    async def _handler(event: DomainEvent) -> None:
        received.append(event)

    bus.subscribe(EventType.VEHICLE_MATCHED.value, _handler)

    event = DomainEvent(
        event_type=EventType.VEHICLE_MATCHED.value,
        source="fallback-test",
        payload={"match_id": str(uuid.uuid4())},
    )
    result = await bus.publish(event)

    assert result.success is True
    assert len(received) == 1
