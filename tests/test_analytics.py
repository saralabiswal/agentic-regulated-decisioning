# Author: Sarala Biswal
from __future__ import annotations

from datetime import UTC, datetime
from platform.data.analytics import by_domain, by_jurisdiction, summary
from platform.governance.audit_trail import AuditTrailWriter
from uuid import uuid4

import pytest

from core.schemas import AgentOutput, EvidenceRef, OrchestratorState, SubmissionEvent


def _state(domain: str, jurisdiction: str, decision: str, confidence: float) -> OrchestratorState:
    submission = SubmissionEvent(
        submission_id=str(uuid4()),
        domain=domain,
        case_type="commercial_property" if domain == "insurance" else "auto_loan",
        raw_payload={"case_value": 1000},
        source_channel="test",
        received_at=datetime.now(UTC),
        jurisdiction=jurisdiction,
    )
    output = AgentOutput(
        agent_id="test_agent",
        agent_type="decision",
        decision=decision,
        confidence=confidence,
        evidence=[
            EvidenceRef(
                source="test",
                field="case_value",
                value=1000,
                retrieved_at=datetime.now(UTC),
                confidence=0.9,
            )
        ],
        flags=[],
        explanation="This test decision includes enough explanation for schema validation.",
        processing_ms=1,
    )
    return OrchestratorState(
        submission=submission,
        agent_outputs=[output],
        overall_confidence=confidence,
        final_decision=decision,
        governance_passed=True,
    )


@pytest.mark.asyncio
async def test_analytics_summary_groupings_include_real_audit_records() -> None:
    insurance = _state("insurance", "US_CA", "ACCEPT", 0.91)
    lending = _state("lending", "US_TX", "ESCALATED", 0.62)
    await AuditTrailWriter().write(insurance)
    await AuditTrailWriter().write(
        lending,
        decision_type="human_override",
    )

    total = await summary()
    domains = await by_domain()
    jurisdictions = await by_jurisdiction()

    assert total["total_submissions"] >= 2
    assert total["avg_confidence"] > 0
    assert any(row["domain"] == "insurance" for row in domains)
    assert any(row["jurisdiction"] == "US_TX" for row in jurisdictions)
