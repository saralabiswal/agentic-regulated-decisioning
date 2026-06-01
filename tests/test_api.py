# Author: Sarala Biswal
from __future__ import annotations

from platform.orchestrator.graph import build_graph

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from core.config import reset_runtime_config
from core.schemas import OrchestratorState
from tests.test_mcp_assembler import event


@pytest.mark.asyncio
async def test_api_basic_paths():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/submissions",
            json={
                "domain": "insurance",
                "case_type": "commercial_property",
                "jurisdiction": "US_CA",
                "raw_payload": {"entity_id": "ins_cp_ca_001"},
            },
        )
        assert response.status_code == 202
        assert response.json()["status"] == "accepted"
        assert (await client.get("/api/v1/workbench/cases")).json() == []
        health = await client.get("/health")
        assert health.json()["status"] == "healthy"
        assert (await client.get("/metrics")).status_code == 200
        assert (await client.get("/api/v1/analytics/summary")).status_code == 200
        assert isinstance((await client.get("/api/v1/analytics/by-domain")).json(), list)
        assert isinstance((await client.get("/api/v1/analytics/by-jurisdiction")).json(), list)
        assert (await client.get("/api/v1/audit/nope")).json() == []
        assert (await client.get("/api/v1/audit/nope/notice")).json() == {
            "adverse_action_notice": ""
        }
        assert (await client.get("/api/v1/registry/models")).json() == []
        stream_inspection = await client.get("/api/v1/streams/inspection?domain=insurance")
        assert stream_inspection.status_code == 200
        assert stream_inspection.json()["stream_name"] == "submissions:insurance"
        promoted = await client.post(
            "/api/v1/registry/models/insurance_risk/promote",
            json={"version": "1", "target_stage": "Production"},
        )
        assert promoted.json()["stage"] == "Production"
        try:
            assert (
                await client.post(
                    "/api/v1/config/runtime",
                    json={"llm_provider": "mock", "app_mode": "mock"},
                )
            ).status_code == 200
            config = (await client.get("/api/v1/config")).json()
            assert "openai_api_key" not in config
            assert "anthropic_api_key" not in config
            assert config["app_mode"] == "mock"
            assert config["effective_llm_provider"]["provider"] == "mock"
            assert config["runtime_overrides"]["llm_provider"] == "mock"
        finally:
            reset_runtime_config()


@pytest.mark.asyncio
async def test_workbench_decision_appends_human_audit_record():
    final = await build_graph().ainvoke(OrchestratorState(submission=event()))
    assert final.escalation_required

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cases = (await client.get("/api/v1/workbench/cases")).json()
        case_id = cases[0]["case_id"]
        response = await client.post(
            f"/api/v1/workbench/cases/{case_id}/decide",
            json={"decision": "human_approve", "notes": "reviewed", "reviewer_id": "underwriter-1"},
        )
        assert response.status_code == 200
        audit_id = response.json()["audit_trail_id"]
        records = (await client.get(f"/api/v1/audit/{final.submission.submission_id}")).json()
        assert any(record["audit_id"] == audit_id for record in records)
        notice = (await client.get(f"/api/v1/audit/{final.submission.submission_id}/notice")).json()
        assert "adverse_action_notice" in notice


@pytest.mark.asyncio
async def test_workbench_decision_is_append_only_and_cannot_be_redecided():
    final = await build_graph().ainvoke(OrchestratorState(submission=event()))
    assert final.escalation_required

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cases = (await client.get("/api/v1/workbench/cases")).json()
        case_id = next(
            item["case_id"]
            for item in cases
            if item["submission"]["submission_id"] == final.submission.submission_id
        )
        first = await client.post(
            f"/api/v1/workbench/cases/{case_id}/decide",
            json={"decision": "human_approve", "notes": "reviewed", "reviewer_id": "underwriter-1"},
        )
        records_after_first = (
            await client.get(f"/api/v1/audit/{final.submission.submission_id}")
        ).json()
        second = await client.post(
            f"/api/v1/workbench/cases/{case_id}/decide",
            json={"decision": "human_decline", "notes": "changed", "reviewer_id": "underwriter-2"},
        )
        records_after_second = (
            await client.get(f"/api/v1/audit/{final.submission.submission_id}")
        ).json()

    assert first.status_code == 200
    assert second.status_code == 409
    assert len(records_after_second) == len(records_after_first)
