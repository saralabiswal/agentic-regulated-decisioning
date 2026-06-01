# Author: Sarala Biswal
from __future__ import annotations

from datetime import UTC, datetime
from platform.mcp.assembler import assemble
from platform.orchestrator.graph import build_graph
from uuid import uuid4

import pytest

from core.schemas import OrchestratorState, SubmissionEvent
from domains.registry import DomainRegistry


def event(entity_id: str = "ins_cp_ca_001") -> SubmissionEvent:
    return SubmissionEvent(
        submission_id=str(uuid4()),
        domain="insurance",
        case_type="commercial_property",
        raw_payload={
            "entity_id": entity_id,
            "case_value": 4_200_000,
            "case_type": "commercial_property",
        },
        source_channel="test",
        received_at=datetime.now(UTC),
        jurisdiction="US_CA",
    )


def event_for(
    domain: str, case_type: str, entity_id: str, jurisdiction: str, payload: dict
) -> SubmissionEvent:
    return SubmissionEvent(
        submission_id=str(uuid4()),
        domain=domain,
        case_type=case_type,
        raw_payload={**payload, "entity_id": entity_id, "case_type": case_type},
        source_channel="test",
        received_at=datetime.now(UTC),
        jurisdiction=jurisdiction,
    )


@pytest.mark.asyncio
async def test_full_context_assembly():
    adapter = DomainRegistry.get("insurance")
    context = await assemble(event(), adapter.get_mcp_config())
    assert context.context_confidence == "FULL"
    assert context.payload["core"]["entity_id"] == "ins_cp_ca_001"


@pytest.mark.asyncio
async def test_orchestrator_runs_and_escalates_high_value_governance():
    state = await build_graph().ainvoke(OrchestratorState(submission=event()))
    assert state.context is not None
    assert state.agent_outputs
    assert state.escalation_required
    assert state.audit_trail_id


@pytest.mark.asyncio
async def test_orchestrator_runs_all_domain_agent_paths():
    cases = [
        ("insurance", "personal_auto", "ins_pa_ca_003", "US_CA", {"case_value": 38_000}),
        ("lending", "auto_loan", "lend_auto_tx_001", "US_TX", {"case_value": 42_000}),
        ("healthcare", "prior_auth", "hc_mri_ca_001", "US_CA", {"case_value": 2800}),
        ("wealth", "suitability_check", "wealth_eq_ca_001", "US_CA", {"case_value": 500_000}),
    ]
    for domain, case_type, entity_id, jurisdiction, payload in cases:
        final = await build_graph().ainvoke(
            OrchestratorState(
                submission=event_for(domain, case_type, entity_id, jurisdiction, payload)
            )
        )
        assert final.agent_outputs
        assert final.audit_trail_id
