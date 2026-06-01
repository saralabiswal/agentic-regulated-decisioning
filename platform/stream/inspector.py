# Author: Sarala Biswal
"""Stream inspection facade for runtime and UI diagnostics."""

from __future__ import annotations

from platform.stream.dlq_handler import DeadLetterHandler
from platform.stream.memory_stream import inspect as inspect_memory
from platform.stream.redis_stream import inspect as inspect_redis

from core.config import get_settings
from core.schemas import DomainId, StreamInspection, StreamMessageView


def _stream_name(domain: str) -> str:
    return f"submissions:{domain}"


def _consumer_group(domain: str) -> str:
    return f"orchestrator-{domain}"


async def inspect_submission_stream(domain: DomainId, limit: int = 10) -> StreamInspection:
    """Return stream health and recent input messages for the Operations UI."""
    settings = get_settings()
    stream_name = _stream_name(domain)
    consumer_group = _consumer_group(domain)
    dlq_records = [
        record
        for record in await DeadLetterHandler().get_dlq_events(limit=50)
        if record.get("domain") == domain
    ]

    if settings.app_mode == "real" and settings.redis_url:
        recent_inputs, pending_count, status = await inspect_redis(
            settings.redis_url, stream_name, consumer_group, limit
        )
        return StreamInspection(
            backend="redis",
            mode=settings.app_mode,
            stream_name=stream_name,
            consumer_group=consumer_group,
            status=status,
            input_count=len(recent_inputs),
            pending_count=pending_count,
            dlq_count=len(dlq_records),
            recent_inputs=recent_inputs,
            output_note=(
                "Redis Streams captures intake inputs. Successful outputs are persisted as "
                "workbench cases, audit records, analytics rows, and reports; failed outputs "
                "are visible in the DLQ count."
            ),
        )

    messages, pending_count = inspect_memory(stream_name, consumer_group, limit)
    recent_inputs = [
        StreamMessageView(
            message_id=message.message_id,
            submission_id=message.event.submission_id,
            domain=message.event.domain,
            case_type=message.event.case_type,
            source_channel=message.event.source_channel,
            received_at=message.event.received_at,
            event=message.event,
        )
        for message in messages
    ]
    backend = "local_sync" if settings.app_mode == "local_sync" else "memory"
    status = (
        "local-sync bypasses queued stream storage"
        if backend == "local_sync"
        else f"{len(recent_inputs)} in-process input events recorded"
    )
    return StreamInspection(
        backend=backend,
        mode=settings.app_mode,
        stream_name=stream_name,
        consumer_group=consumer_group,
        status=status,
        input_count=len(recent_inputs),
        pending_count=pending_count,
        dlq_count=len(dlq_records),
        recent_inputs=recent_inputs,
        output_note=(
            "Mock mode uses an in-process Redis Streams-compatible buffer. Local-sync mode "
            "executes directly and does not enqueue Redis inputs. Successful outputs are stored "
            "in workbench, audit, analytics, and report paths."
        ),
    )
