# Author: Sarala Biswal
"""Submission event consumer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from platform.observability.metrics import submissions_consumed_total
from platform.stream.dlq_handler import DeadLetterHandler
from platform.stream.memory_stream import StreamMessage, read
from platform.stream.redis_stream import ack as redis_ack
from platform.stream.redis_stream import read as redis_read

from core.config import get_settings
from core.schemas import SubmissionEvent


class SubmissionConsumer:
    """Consumes submission events from memory/local or Redis streams with DLQ fallback."""

    async def start(
        self, domain: str, handler: Callable[[SubmissionEvent], Awaitable[object]]
    ) -> None:
        """Attach the domain and handler used by polling calls."""
        self.domain = domain
        self.handler = handler

    async def poll_once(self, count: int = 10) -> int:
        """Read a bounded batch from the configured stream backend."""
        settings = get_settings()
        if settings.app_mode == "real" and settings.redis_url:
            messages = await redis_read(
                settings.redis_url,
                f"submissions:{self.domain}",
                f"orchestrator-{self.domain}",
                "worker-1",
                count,
            )
            processed = 0
            for _stream_name, stream_messages in messages:
                for message_id, payload in stream_messages:
                    event = SubmissionEvent.model_validate_json(payload["event"])
                    await self.process_message(StreamMessage(message_id=message_id, event=event))
                    await redis_ack(
                        settings.redis_url,
                        f"submissions:{self.domain}",
                        f"orchestrator-{self.domain}",
                        message_id,
                    )
                    processed += 1
            return processed
        processed = 0
        for message in read(f"submissions:{self.domain}", f"orchestrator-{self.domain}", count):
            await self.process_message(message)
            processed += 1
        return processed

    async def process(self, event: SubmissionEvent) -> None:
        """Process one submission event through the configured handler."""
        await self.process_message(StreamMessage(message_id="direct", event=event))

    async def process_message(self, message: StreamMessage) -> None:
        """Run the handler with retries before moving failures to the dead-letter queue."""
        last_error = ""
        for attempt in range(1, 4):
            try:
                await self.handler(message.event)
                submissions_consumed_total.labels(domain=message.event.domain, status="ok").inc()
                return
            except Exception as exc:
                last_error = str(exc)
                if attempt == 3:
                    await DeadLetterHandler().send_to_dlq(message.event, last_error, attempt)
                    submissions_consumed_total.labels(
                        domain=message.event.domain, status="dlq"
                    ).inc()
