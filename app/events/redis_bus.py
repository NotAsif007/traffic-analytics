"""Redis-backed EventBus with graceful in-memory fallback."""

from __future__ import annotations

import json
from typing import Optional

from app.core.logging import get_logger
from app.events.contracts import DomainEvent, EventProcessingResult
from app.events.in_memory import InMemoryDeadLetterStore, InMemoryEventBus
from app.events.interfaces import DeadLetterStore, EventBus, EventHandler

logger = get_logger(__name__)


class ResilientEventBus(EventBus):
    """
    Production-grade event bus that leverages Redis when available,
    while guaranteeing seamless in-memory fallback if Redis is unreachable.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        dead_letter_store: Optional[DeadLetterStore] = None,
    ) -> None:
        self._dead_letter = dead_letter_store or InMemoryDeadLetterStore()
        self._memory_bus = InMemoryEventBus(dead_letter_store=self._dead_letter)
        self._redis_url = redis_url
        self._redis_client = None
        self._is_redis_available = False

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._memory_bus.subscribe(event_type, handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        self._memory_bus.unsubscribe(event_type, handler)

    async def _get_redis_client(self):
        if not self._redis_url:
            return None
        if self._redis_client is None:
            try:
                import redis.asyncio as aioredis
                self._redis_client = aioredis.from_url(
                    self._redis_url, socket_timeout=1.0, socket_connect_timeout=1.0
                )
                await self._redis_client.ping()
                self._is_redis_available = True
                logger.info("event_bus.redis_connected", url=self._redis_url)
            except Exception as e:
                self._is_redis_available = False
                logger.warning("event_bus.redis_unavailable_fallback_to_memory", error=str(e))
                self._redis_client = None
        return self._redis_client

    async def publish(self, event: DomainEvent) -> EventProcessingResult:
        # Try publishing to Redis for external consumers / workers
        try:
            client = await self._get_redis_client()
            if client and self._is_redis_available:
                channel = f"traffic:events:{event.event_type}"
                event_data = event.model_dump_json()
                await client.publish(channel, event_data)
        except Exception as e:
            self._is_redis_available = False
            self._redis_client = None
            logger.warning("event_bus.redis_publish_failed_using_memory", error=str(e))

        # Always process synchronously / in-memory for local subscribers
        return await self._memory_bus.publish(event)
