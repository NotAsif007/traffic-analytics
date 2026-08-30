"""Real-time event processing package."""

from app.events.contracts import (
    DeadLetterRecord,
    DomainEvent,
    EventProcessingResult,
    EventType,
)
from app.events.coordinator import EventCoordinator
from app.events.in_memory import InMemoryDeadLetterStore, InMemoryEventBus
from app.events.interfaces import DeadLetterStore, EventBus, EventHandler
from app.events.redis_bus import ResilientEventBus

__all__ = [
    "EventType",
    "DomainEvent",
    "DeadLetterRecord",
    "EventProcessingResult",
    "EventBus",
    "DeadLetterStore",
    "EventHandler",
    "InMemoryEventBus",
    "InMemoryDeadLetterStore",
    "ResilientEventBus",
    "EventCoordinator",
]
