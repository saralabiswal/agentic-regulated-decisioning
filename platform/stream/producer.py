# Author: Sarala Biswal
"""Submission event producer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import isawaitable
from platform.observability.metrics import submissions_published_total
from platform.stream import memory_stream
from platform.stream.redis_stream import publish as redis_publish

from core.config import get_settings
from core.schemas import SubmissionEvent


class SubmissionProducer:
    """Publishes typed submission events to Redis in real mode or memory otherwise."""

    def __init__(
        self, handler: Callable[[SubmissionEvent], object | Awaitable[object]] | None = None
    ) -> None:
        """Capture the target domain and derive the stream name used by publishers."""
        self.handler = handler

    async def publish(self, event: SubmissionEvent) -> str:
        """Write one submission event and return the backend message identifier."""
        settings = get_settings()
        submissions_published_total.labels(domain=event.domain, channel=event.source_channel).inc()
        if settings.app_mode == "local_sync" or not settings.redis_url:
            message_id = memory_stream.publish(f"submissions:{event.domain}", event)
            if self.handler:
                result = self.handler(event)
                if isawaitable(result):
                    await result
            return message_id if settings.app_mode != "local_sync" else "local-sync"
        if settings.app_mode == "real":
            return await redis_publish(settings.redis_url, f"submissions:{event.domain}", event)
        return memory_stream.publish(f"submissions:{event.domain}", event)
