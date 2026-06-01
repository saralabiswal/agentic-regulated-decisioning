# Author: Sarala Biswal
"""Exercise live PostgreSQL, Redis, and MLflow service paths."""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sitecustomize  # noqa: F401, E402

os.environ.setdefault("APP_MODE", "real")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:15432/regulated_decisioning",
)
os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5001")

from platform.data.postgres_schema import migrate_postgres
from platform.governance.audit_trail import AuditTrailWriter
from platform.observability.cost_tracker import CostTracker
from platform.registry.model_registry import ModelRegistry
from platform.stream.consumer import SubmissionConsumer
from platform.stream.dlq_handler import DeadLetterHandler
from platform.stream.producer import SubmissionProducer
from platform.workbench.queue import WorkbenchQueue

from core.config import get_settings
from core.schemas import (
    AgentOutput,
    EvidenceRef,
    OrchestratorState,
    SubmissionEvent,
    UnifiedContext,
)
from seed.seed_models import main as seed_models


def _submission() -> SubmissionEvent:
    return SubmissionEvent(
        submission_id=str(uuid4()),
        domain="insurance",
        case_type="commercial_property",
        raw_payload={
            "entity_id": "live-smoke-001",
            "case_value": 1_250_000,
            "confidence_hint": 0.7,
        },
        source_channel="live-smoke",
        received_at=datetime.now(UTC),
        jurisdiction="US_CA",
        priority="standard",
    )


def _state(event: SubmissionEvent) -> OrchestratorState:
    evidence = EvidenceRef(
        source="live-smoke",
        field="case_value",
        value=event.raw_payload["case_value"],
        retrieved_at=datetime.now(UTC),
        confidence=0.96,
    )
    output = AgentOutput(
        agent_id="live-smoke-risk",
        agent_type="risk",
        decision="refer",
        confidence=0.72,
        evidence=[evidence],
        flags=["manual_review"],
        explanation="Live smoke test generated a manual review recommendation.",
        processing_ms=12,
    )
    context = UnifiedContext(
        submission_id=event.submission_id,
        domain=event.domain,
        sources_available=["live-smoke"],
        sources_missing=[],
        context_confidence="FULL",
        assembled_at=datetime.now(UTC),
        payload={"live-smoke": event.raw_payload},
    )
    return OrchestratorState(
        submission=event,
        adapter_id="insurance",
        context=context,
        agent_outputs=[output],
        overall_confidence=output.confidence,
        escalation_required=True,
        escalation_reason="live smoke manual review",
        final_decision=output.decision,
        governance_passed=True,
    )


async def _clear_stream() -> None:
    from redis import asyncio as redis_async

    redis_url = get_settings().redis_url
    if redis_url is None:
        raise RuntimeError("REDIS_URL is required for the live backend smoke test")
    client = redis_async.from_url(redis_url, decode_responses=True)
    try:
        await client.delete("submissions:insurance")
    finally:
        await client.aclose()


async def main() -> None:
    """Run this module as a command-line entry point."""
    await migrate_postgres(get_settings().database_url)
    await _clear_stream()

    event = _submission()
    consumed: list[str] = []

    async def handler(message: SubmissionEvent) -> None:
        """Record that the live consumer received the published smoke event."""
        consumed.append(message.submission_id)

    published_id = await SubmissionProducer().publish(event)
    consumer = SubmissionConsumer()
    await consumer.start("insurance", handler)
    consumed_count = await consumer.poll_once()

    state = _state(event)
    audit = await AuditTrailWriter().write(state)
    audit_records = await AuditTrailWriter().get(event.submission_id)

    queue = WorkbenchQueue()
    case = await queue.enqueue(state, "live smoke manual review")
    decided, human_audit_id = await queue.record_decision(
        case.case_id,
        "human_approve",
        "live-smoke-reviewer",
        "Validated live backend persistence.",
    )

    await DeadLetterHandler().send_to_dlq(event, "live smoke synthetic failure", 3)
    dlq_count = len(await DeadLetterHandler().get_dlq_events(limit=10))

    cost = await CostTracker().record_llm_call_async(
        "insurance",
        "risk",
        "openai",
        "openai/gpt-4o-mini",
        800,
        250,
    )
    cost_summary = await CostTracker().get_cost_summary("insurance")

    registry = ModelRegistry()
    await asyncio.to_thread(seed_models)
    models = await registry.alist_models()
    production, shadow = await registry.arun_with_shadow(
        "insurance",
        "risk",
        {"case_value": 1_250_000, "confidence_hint": 0.7},
    )

    summary = {
        "redis": {
            "published_id": published_id,
            "consumed_count": consumed_count,
            "consumed_submission_ids": consumed,
        },
        "postgres": {
            "audit_id": audit.audit_id,
            "audit_records_for_submission": len(audit_records),
            "workbench_case_id": decided.case_id,
            "human_audit_id": human_audit_id,
            "dlq_events_sampled": dlq_count,
            "llm_cost": cost,
            "llm_total_cost": cost_summary["total_cost"],
        },
        "mlflow": {
            "tracking_uri": get_settings().mlflow_tracking_uri,
            "registered_models": len(models),
            "insurance_risk_version": production.model_version,
            "insurance_shadow_version": shadow.model_version if shadow else None,
        },
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
