# Author: Sarala Biswal
"""In-process Redis Streams compatible fallback."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from core.schemas import SubmissionEvent


@dataclass(frozen=True)
class StreamMessage:
    """In-memory stream message with a Redis-like id and submission event."""
    message_id: str
    event: SubmissionEvent


_STREAMS: dict[str, list[StreamMessage]] = defaultdict(list)
_OFFSETS: dict[str, int] = defaultdict(int)


def publish(stream_name: str, event: SubmissionEvent) -> str:
    """Append an event to the in-memory stream and return its id."""
    index = len(_STREAMS[stream_name]) + 1
    message_id = f"{index}-0"
    _STREAMS[stream_name].append(StreamMessage(message_id=message_id, event=event))
    return message_id


def read(stream_name: str, consumer_group: str, count: int = 10) -> list[StreamMessage]:
    """Read pending stream messages from the selected backend."""
    key = f"{stream_name}:{consumer_group}"
    offset = _OFFSETS[key]
    messages = _STREAMS[stream_name][offset : offset + count]
    _OFFSETS[key] = offset + len(messages)
    return messages


def inspect(
    stream_name: str, consumer_group: str, count: int = 10
) -> tuple[list[StreamMessage], int]:
    """Return stream diagnostics and recent messages."""
    messages = _STREAMS[stream_name][-count:]
    pending = max(len(_STREAMS[stream_name]) - _OFFSETS[f"{stream_name}:{consumer_group}"], 0)
    return messages, pending


def reset() -> None:
    """Clear in-process event or stream state for tests and demos."""
    _STREAMS.clear()
    _OFFSETS.clear()
