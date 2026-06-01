# Author: Sarala Biswal
"""Optional Redis Streams client path."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.schemas import StreamMessageView, SubmissionEvent


def _client(url: str) -> Any:
    try:
        from redis import asyncio as redis_async
    except ImportError as exc:
        raise RuntimeError("redis dependency is not installed") from exc
    return redis_async.from_url(url, decode_responses=True)


async def publish(url: str, stream_name: str, event: SubmissionEvent) -> str:
    """Append an event to Redis Streams and return its message id."""
    client = _client(url)
    try:
        return await client.xadd(stream_name, {"event": event.model_dump_json()})
    finally:
        await client.aclose()


async def read(url: str, stream_name: str, group: str, consumer: str, count: int = 10) -> list:
    """Read pending stream messages from the selected backend."""
    client = _client(url)
    try:
        try:
            await client.xgroup_create(stream_name, group, id="0", mkstream=True)
        except Exception:
            pass
        return await client.xreadgroup(group, consumer, {stream_name: ">"}, count=count, block=1000)
    finally:
        await client.aclose()


async def ack(url: str, stream_name: str, group: str, message_id: str) -> None:
    """Acknowledge a processed Redis stream message."""
    client = _client(url)
    try:
        await client.xack(stream_name, group, message_id)
    finally:
        await client.aclose()


def _view(message_id: str, payload: dict[str, str]) -> StreamMessageView:
    try:
        event = SubmissionEvent.model_validate_json(payload["event"])
        return StreamMessageView(
            message_id=message_id,
            submission_id=event.submission_id,
            domain=event.domain,
            case_type=event.case_type,
            source_channel=event.source_channel,
            received_at=event.received_at,
            event=event,
        )
    except Exception as exc:
        return StreamMessageView(
            message_id=message_id,
            submission_id="unknown",
            domain="unknown",
            case_type="unknown",
            source_channel="unknown",
            received_at=datetime.now(UTC),
            parse_error=str(exc),
        )


async def inspect(
    url: str, stream_name: str, group: str, count: int = 10
) -> tuple[list[StreamMessageView], int, str]:
    """Return stream diagnostics and recent messages."""
    client = _client(url)
    try:
        try:
            info = await client.xinfo_stream(stream_name)
            input_count = int(info.get("length", 0))
        except Exception as exc:
            return [], 0, f"stream unavailable: {type(exc).__name__}"

        pending_count = 0
        try:
            pending = await client.xpending(stream_name, group)
            if isinstance(pending, dict):
                pending_count = int(pending.get("pending", 0))
            elif isinstance(pending, (list, tuple)) and pending:
                pending_count = int(pending[0])
        except Exception:
            pending_count = 0

        rows = await client.xrevrange(stream_name, "+", "-", count=count)
        entries = [_view(message_id, payload) for message_id, payload in reversed(rows)]
        return entries, pending_count, f"{input_count} input events recorded"
    finally:
        await client.aclose()
