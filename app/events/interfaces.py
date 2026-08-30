"""Abstract interfaces for EventBus and DeadLetterStore."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.events.contracts import DeadLetterRecord, DomainEvent, EventProcessingResult

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(ABC):
    """
    Abstract publish-subscribe event bus interface.
    Decouples domain event publishing from underlying message brokers (Redis / In-Memory).
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> EventProcessingResult:
        """Publish a domain event to all registered subscribers."""
        ...

    @abstractmethod
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register an async handler function for a specific event type."""
        ...

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        ...


class DeadLetterStore(ABC):
    """
    Storage and retrieval interface for failed event processing diagnostics.
    """

    @abstractmethod
    async def record_failure(
        self,
        event: DomainEvent,
        error: Exception,
        traceback_str: str | None = None,
    ) -> DeadLetterRecord: ...

    @abstractmethod
    async def list_dead_letters(
        self, status: str | None = None, limit: int = 50
    ) -> list[DeadLetterRecord]: ...

    @abstractmethod
    async def get_by_id(self, record_id: uuid.UUID) -> DeadLetterRecord | None: ...

    @abstractmethod
    async def mark_resolved(self, record_id: uuid.UUID) -> None: ...
