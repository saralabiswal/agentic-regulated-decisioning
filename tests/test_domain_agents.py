# Author: Sarala Biswal
from __future__ import annotations

from datetime import UTC, datetime
from platform.mcp.assembler import assemble
from uuid import uuid4

import pytest

from core.schemas import SubmissionEvent
from domains.healthcare import agents as healthcare_agents
from domains.lending import agents as lending_agents
from domains.registry import DomainRegistry
from domains.wealth import agents as wealth_agents


def _event(domain: str, case_type: str, entity_id: str, jurisdiction: str) -> SubmissionEvent:
    return SubmissionEvent(
        submission_id=str(uuid4()),
        domain=domain,
        case_type=case_type,
        raw_payload={"entity_id": entity_id, "case_type": case_type},
        source_channel="test",
        received_at=datetime.now(UTC),
        jurisdiction=jurisdiction,
    )


@pytest.mark.asyncio
async def test_lending_agents_use_credit_evidence_and_policy_conditions():
    adapter = DomainRegistry.get("lending")
    context = await assemble(
        _event("lending", "personal_loan", "lend_pl_fl_003", "US_FL"),
        adapter.get_mcp_config(),
    )

    eligibility = await lending_agents.run_agent("eligibility", context, [])
    scoring = await lending_agents.run_agent("credit_scoring", context, [eligibility])
    policy = await lending_agents.run_agent("policy_check", context, [eligibility, scoring])

    assert eligibility.decision == "ELIGIBLE"
    assert scoring.decision == "CONDITIONAL_CREDIT"
    assert policy.decision == "APPROVE_WITH_CONDITIONS"
    assert any(item.source == "model_registry" for item in scoring.evidence)


@pytest.mark.asyncio
async def test_healthcare_agents_escalate_incomplete_clinical_notes():
    adapter = DomainRegistry.get("healthcare")
    context = await assemble(
        _event("healthcare", "specialty_referral", "hc_ref_tx_002", "US_TX"),
        adapter.get_mcp_config(),
    )

    triage = await healthcare_agents.run_agent("clinical_triage", context, [])
    criteria = await healthcare_agents.run_agent("criteria_check", context, [triage])

    assert triage.decision == "CLINICAL_DOCUMENTATION_REVIEW"
    assert "incomplete_clinical_notes" in triage.flags
    assert criteria.decision == "CRITERIA_NOT_MET"
    assert any(item.source == "model_registry" for item in criteria.evidence)


@pytest.mark.asyncio
async def test_wealth_agents_detect_risk_profile_mismatch():
    adapter = DomainRegistry.get("wealth")
    context = await assemble(
        _event("wealth", "options_authorization", "wealth_opt_fl_002", "US_FL"),
        adapter.get_mcp_config(),
    )

    suitability = await wealth_agents.run_agent("suitability", context, [])
    risk = await wealth_agents.run_agent("risk_tolerance", context, [suitability])
    product = await wealth_agents.run_agent(
        "product_eligibility",
        context,
        [suitability, risk],
    )

    assert suitability.decision == "SUITABILITY_ALIGNED"
    assert risk.decision == "RISK_PROFILE_MISMATCH"
    assert "risk_profile_mismatch" in risk.flags
    assert product.decision == "ESCALATE"
