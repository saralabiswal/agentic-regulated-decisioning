# Author: Sarala Biswal
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from platform.data import postgres_store
from platform.observability.cost_tracker import CostTracker
from platform.registry.model_registry import ModelRegistry, ScoringModel
from tempfile import gettempdir
from uuid import uuid4

import pytest

from api.routers import health
from core.config import get_settings
from core.schemas import (
    AgentOutput,
    AuditRecord,
    EvidenceRef,
    SubmissionEvent,
    UnifiedContext,
    WorkbenchCase,
)


def _event() -> SubmissionEvent:
    return SubmissionEvent(
        submission_id=str(uuid4()),
        domain="insurance",
        case_type="commercial_property",
        raw_payload={"case_value": 1000},
        source_channel="test",
        received_at=datetime.now(UTC),
        jurisdiction="US_CA",
    )


def _agent() -> AgentOutput:
    return AgentOutput(
        agent_id="risk",
        agent_type="risk",
        decision="refer",
        confidence=0.7,
        evidence=[
            EvidenceRef(
                source="test",
                field="case_value",
                value=1000,
                retrieved_at=datetime.now(UTC),
                confidence=0.9,
            )
        ],
        flags=["review"],
        explanation="Risk signal requires manual review for this test.",
        processing_ms=1,
    )


def _case() -> WorkbenchCase:
    event = _event()
    context = UnifiedContext(
        submission_id=event.submission_id,
        domain=event.domain,
        sources_available=["test"],
        sources_missing=[],
        context_confidence="FULL",
        assembled_at=datetime.now(UTC),
        payload={"test": event.raw_payload},
    )
    return WorkbenchCase(
        case_id=str(uuid4()),
        submission=event,
        context=context,
        agent_outputs=[_agent()],
        agent_recommendation="refer",
        confidence=0.7,
        escalation_reason="test",
        created_at=datetime.now(UTC),
    )


class FakeConnection:
    def __init__(self, fetch_rows=None, fetchrow_value=None):
        self.fetch_rows = fetch_rows or []
        self.fetchrow_value = fetchrow_value
        self.executed = []
        self.closed = False

    async def execute(self, *args):
        self.executed.append(args)

    async def fetch(self, *args):
        self.executed.append(args)
        return self.fetch_rows

    async def fetchrow(self, *args):
        self.executed.append(args)
        return self.fetchrow_value

    async def fetchval(self, *args):
        self.executed.append(args)
        return 1

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_postgres_store_helpers(monkeypatch):
    case = _case()
    audit = AuditRecord(
        submission_id=case.submission.submission_id,
        domain=case.submission.domain,
        jurisdiction=case.submission.jurisdiction,
        decision_type="agent_auto",
        final_decision="refer",
        agent_outputs=[],
        governance_rules_applied=["rule-1"],
        governance_passed=True,
    )
    model_row = {
        "model_name": "insurance_risk_scorer",
        "domain": "insurance",
        "model_type": "risk",
        "version": "1",
        "stage": "Production",
        "mlflow_run_id": "run-1",
        "created_at": datetime.now(UTC),
    }
    connections = [
        FakeConnection(),
        FakeConnection(
            fetch_rows=[
                {
                    "audit_id": audit.audit_id,
                    "submission_id": audit.submission_id,
                    "domain": audit.domain,
                    "jurisdiction": audit.jurisdiction,
                    "decision_type": audit.decision_type,
                    "final_decision": audit.final_decision,
                    "agent_outputs": [],
                    "governance_rules_applied": ["rule-1"],
                    "governance_passed": True,
                    "human_reviewer": None,
                    "created_at": audit.created_at,
                }
            ]
        ),
        FakeConnection(),
        FakeConnection(fetch_rows=[{"case_json": case.model_dump(mode="json")}]),
        FakeConnection(fetchrow_value={"case_json": case.model_dump(mode="json")}),
        FakeConnection(),
        FakeConnection(fetch_rows=[{"dlq_id": str(uuid4()), "domain": "insurance"}]),
        FakeConnection(),
        FakeConnection(fetch_rows=[{"cost": 0.01}]),
        FakeConnection(fetch_rows=[model_row]),
        FakeConnection(fetchrow_value=model_row),
        FakeConnection(fetchrow_value=model_row),
        FakeConnection(),
        FakeConnection(),
    ]

    async def fake_connect():
        return connections.pop(0)

    monkeypatch.setattr(postgres_store, "connect", fake_connect)

    assert postgres_store.is_postgres_url("postgresql+asyncpg://db")
    assert postgres_store.normalize_url("postgresql+asyncpg://db") == "postgresql://db"
    await postgres_store.write_audit_record(audit)
    audit_records = await postgres_store.get_audit_records(audit.submission_id)
    assert audit_records[0].audit_id == audit.audit_id
    await postgres_store.write_workbench_case(case)
    workbench_cases = await postgres_store.get_workbench_cases("insurance", "pending")
    assert workbench_cases[0].case_id == case.case_id
    assert (await postgres_store.get_workbench_case(case.case_id)).case_id == case.case_id
    await postgres_store.write_dlq_record(
        {
            "dlq_id": str(uuid4()),
            "submission_id": case.submission.submission_id,
            "domain": "insurance",
            "event_json": case.submission.model_dump(mode="json"),
            "error_message": "boom",
            "attempt_count": 3,
            "created_at": datetime.now(UTC),
        }
    )
    assert (await postgres_store.get_dlq_records())[0]["domain"] == "insurance"
    await postgres_store.write_llm_cost("insurance", "risk", "mock", "mock", 1, 1, 0.0)
    assert (await postgres_store.get_llm_costs("insurance"))[0]["cost"] == 0.01
    assert (await postgres_store.list_model_versions())[0]["version"] == "1"
    assert (
        await postgres_store.upsert_model_version("insurance", "risk", "1", "Production", "run-1")
    )["mlflow_run_id"] == "run-1"
    assert (await postgres_store.get_model_version("insurance", "risk", "Production")) is not None
    await postgres_store.archive_model_stage("insurance", "risk", "Production")
    await postgres_store.set_model_stage("insurance", "risk", "1", "Archived")


@pytest.mark.asyncio
async def test_health_local_checks(monkeypatch):
    monkeypatch.setenv("APP_MODE", "mock")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/test.db")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "file:///tmp/mlruns")
    get_settings.cache_clear()
    try:
        assert await health._redis_check() == "mock"
        assert await health._db_check() == "local"
        assert await health._mlflow_check() == "local"
        response = await health.health()
        assert response["status"] == "healthy"
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_cost_tracker_async_sqlite(monkeypatch):
    db_path = Path(gettempdir()) / f"live_services_cost_test_{uuid4()}.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    try:
        cost = await CostTracker().record_llm_call_async(
            "insurance", "risk", "openai", "openai/gpt-4o-mini", 100, 50
        )
        assert cost > 0
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_model_registry_async_postgres_branch(monkeypatch):
    async def fake_list():
        return [{"domain": "insurance", "model_type": "risk", "version": "1"}]

    async def fake_upsert(domain, model_type, version, stage, mlflow_run_id):
        return {
            "model_name": f"{domain}_{model_type}_scorer",
            "domain": domain,
            "model_type": model_type,
            "version": version,
            "stage": stage,
            "mlflow_run_id": mlflow_run_id,
        }

    async def fake_get(domain, model_type, stage):
        if stage == "Staging":
            return None
        return {
            "domain": domain,
            "model_type": model_type,
            "version": "1",
            "mlflow_run_id": "local",
        }

    async def fake_none(*_args):
        return None

    monkeypatch.setattr("platform.registry.model_registry.is_postgres_url", lambda: True)
    monkeypatch.setattr("platform.registry.model_registry.list_model_versions", fake_list)
    monkeypatch.setattr("platform.registry.model_registry.upsert_model_version", fake_upsert)
    monkeypatch.setattr("platform.registry.model_registry.get_model_version", fake_get)
    monkeypatch.setattr("platform.registry.model_registry.archive_model_stage", fake_none)
    monkeypatch.setattr("platform.registry.model_registry.set_model_stage", fake_none)

    registry = ModelRegistry()
    assert (await registry.alist_models())[0]["version"] == "1"
    assert (await registry.aregister("insurance", "risk", "1", "Production"))["stage"]
    assert isinstance(await registry.aget_production_model("insurance", "risk"), ScoringModel)
    production, shadow = await registry.arun_with_shadow("insurance", "risk", {"case_value": 1000})
    assert production.model_version == "1"
    assert shadow is None
    assert (await registry.apromote("insurance", "risk", "2", "Production"))["version"] == "2"
    assert (await registry.arollback("insurance", "risk"))["rolled_back"]
