"""In-memory EventBus and DeadLetterStore implementations."""

from __future__ import annotations

import asyncio
import traceback
import uuid
from collections import defaultdict

from app.core.logging import get_logger
from app.events.contracts import DeadLetterRecord, DomainEvent, EventProcessingResult
from app.events.interfaces import DeadLetterStore, EventBus, EventHandler

logger = get_logger(__name__)


class InMemoryDeadLetterStore(DeadLetterStore):
    def __init__(self, max_records: int = 1000) -> None:
        self._records: dict[uuid.UUID, DeadLetterRecord] = {}
        self._max_records = max_records

    async def record_failure(
        self,
        event: DomainEvent,
        error: Exception,
        traceback_str: str | None = None,
    ) -> DeadLetterRecord:
        tb = traceback_str or traceback.format_exc()
        record = DeadLetterRecord(
            id=uuid.uuid4(),
            event_id=event.event_id,
            event_type=event.event_type,
            source=event.source,
            payload=event.payload,
            error_message=str(error),
            error_traceback=tb,
        )
        if len(self._records) >= self._max_records:
            # Drop oldest
            oldest_key = next(iter(self._records))
            del self._records[oldest_key]

        self._records[record.id] = record
        logger.error(
            "event.dead_letter_recorded",
            event_id=event.event_id,
            event_type=event.event_type,
            error=str(error),
        )
        return record

    async def list_dead_letters(
        self, status: str | None = None, limit: int = 50
    ) -> list[DeadLetterRecord]:
        records = list(self._records.values())
        if status:
            records = [r for r in records if r.status == status]
        records.sort(key=lambda x: x.last_failed_at, reverse=True)
        return records[:limit]

    async def get_by_id(self, record_id: uuid.UUID) -> DeadLetterRecord | None:
        return self._records.get(record_id)

    async def mark_resolved(self, record_id: uuid.UUID) -> None:
        if record_id in self._records:
            self._records[record_id].status = "RESOLVED"


class InMemoryEventBus(EventBus):
    """
    In-memory asynchronous event bus with idempotent deduplication and dead-letter protection.
    """

    def __init__(
        self,
        dead_letter_store: DeadLetterStore | None = None,
        max_processed_keys: int = 10000,
    ) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._processed_keys: set[str] = set()
        self._processed_keys_order: list[str] = []
        self._max_keys = max_processed_keys
        self._dead_letter = dead_letter_store or InMemoryDeadLetterStore()
        self._recent_events: list[DomainEvent] = []
        self._listeners: set[asyncio.Queue[DomainEvent]] = set()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug("event_bus.subscribed", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def add_listener(self, queue: asyncio.Queue[DomainEvent]) -> None:
        """Register an active async queue for live SSE / WebSocket event streaming."""
        self._listeners.add(queue)

    def remove_listener(self, queue: asyncio.Queue[DomainEvent]) -> None:
        """Unregister an async queue when a stream client disconnects."""
        self._listeners.discard(queue)

    def get_recent(
        self, limit: int = 50, event_type: str | None = None
    ) -> list[DomainEvent]:
        """Return the most recent domain events buffered in memory."""
        events = self._recent_events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return list(reversed(events[-limit:]))

    async def publish(self, event: DomainEvent) -> EventProcessingResult:
        """
        Publish an event to all subscribers with idempotency checking and dead-letter safety.
        """
        # Record into rolling recent events buffer
        self._recent_events.append(event)
        if len(self._recent_events) > 500:
            self._recent_events.pop(0)

        # Notify active streaming listeners (e.g. SSE / Terminal / UI monitors)
        for listener_q in list(self._listeners):
            try:
                listener_q.put_nowait(event)
            except asyncio.QueueFull:
                pass
            except Exception:
                self._listeners.discard(listener_q)

        p = event.payload if isinstance(event.payload, dict) else {}
        logger.info(
            "telemetry.live_event",
            event_type=event.event_type,
            source=event.source,
            plate=p.get("plate_text"),
            camera=p.get("camera_name") or p.get("camera_id"),
            vehicle_class=p.get("vehicle_class"),
            speed=p.get("estimated_speed_kmh"),
        )

        # Idempotency check
        dedup_key = event.idempotency_key or event.event_id
        if dedup_key in self._processed_keys:
            logger.info("event_bus.duplicate_skipped", event_id=event.event_id, key=dedup_key)
            return EventProcessingResult(
                success=True,
                event_id=event.event_id,
                event_type=event.event_type,
                handler_count=0,
            )

        # Mark processed
        self._processed_keys.add(dedup_key)
        self._processed_keys_order.append(dedup_key)
        if len(self._processed_keys_order) > self._max_keys:
            oldest = self._processed_keys_order.pop(0)
            self._processed_keys.discard(oldest)

        handlers = list(self._handlers.get(event.event_type, []))
        # Also notify wildcard "*" subscribers
        handlers.extend(self._handlers.get("*", []))

        errors: list[str] = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                err_msg = f"Handler {handler.__name__} failed: {e}"
                errors.append(err_msg)
                await self._dead_letter.record_failure(event, e)

        success = len(errors) == 0
        return EventProcessingResult(
            success=success,
            event_id=event.event_id,
            event_type=event.event_type,
            handler_count=len(handlers),
            errors=errors,
        )
