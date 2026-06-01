# Author: Sarala Biswal
from __future__ import annotations

from datetime import UTC, datetime
from platform.stream.consumer import SubmissionConsumer
from platform.stream.dlq_handler import DeadLetterHandler
from platform.stream.inspector import inspect_submission_stream
from platform.stream.memory_stream import reset
from platform.stream.producer import SubmissionProducer
from uuid import uuid4

import pytest

from core.schemas import SubmissionEvent


def event() -> SubmissionEvent:
    return SubmissionEvent(
        submission_id=str(uuid4()),
        domain="insurance",
        case_type="commercial_property",
        raw_payload={"entity_id": "ins_cp_ca_001"},
        source_channel="test",
        received_at=datetime.now(UTC),
        jurisdiction="US_CA",
    )


@pytest.mark.asyncio
async def test_producer_and_dlq():
    seen = []
    assert await SubmissionProducer(handler=lambda e: seen.append(e)).publish(event())
    consumer = SubmissionConsumer()

    async def fail(_):
        raise RuntimeError("boom")

    await consumer.start("insurance", fail)
    await consumer.process(event())
    assert await DeadLetterHandler().get_dlq_events()


@pytest.mark.asyncio
async def test_memory_stream_poll_once_processes_published_event():
    reset()
    seen = []

    async def handler(item):
        seen.append(item.submission_id)

    item = event()
    await SubmissionProducer().publish(item)
    consumer = SubmissionConsumer()
    await consumer.start("insurance", handler)

    assert await consumer.poll_once() == 1
    assert seen == [item.submission_id]


@pytest.mark.asyncio
async def test_stream_inspector_shows_memory_inputs():
    reset()
    item = event()
    await SubmissionProducer().publish(item)

    inspection = await inspect_submission_stream("insurance")

    assert inspection.backend == "local_sync"
    assert inspection.stream_name == "submissions:insurance"
    assert inspection.recent_inputs[0].submission_id == item.submission_id
