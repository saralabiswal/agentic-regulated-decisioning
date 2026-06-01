# Author: Sarala Biswal
from __future__ import annotations

from datetime import UTC, datetime
from platform.governance.audit_trail import AuditTrailWriter
from platform.governance.engine import GovernanceEngine, evaluate_condition
from platform.governance.explainability import ExplainabilityGenerator
from uuid import uuid4

from core.schemas import AgentOutput, EvidenceRef, OrchestratorState, SubmissionEvent


def state_with_factor(field: str = "credit_score") -> OrchestratorState:
    submission = SubmissionEvent(
        submission_id=str(uuid4()),
        domain="insurance",
        case_type="commercial_property",
        raw_payload={"case_value": 2_000_000},
        source_channel="test",
        received_at=datetime.now(UTC),
        jurisdiction="US_CA",
    )
    output = AgentOutput(
        agent_id="a",
        agent_type="scoring",
        decision="STANDARD",
        confidence=0.8,
        evidence=[
            EvidenceRef(
                source="core",
                field=field,
                value=700,
                retrieved_at=datetime.now(UTC),
                confidence=0.9,
            )
        ],
        flags=[],
        explanation="This explanation is detailed enough to support an audit decision.",
        processing_ms=1,
    )
    return OrchestratorState(submission=submission, agent_outputs=[output], final_decision="ACCEPT")


def test_governance_detects_prohibited_factor_and_override():
    result = GovernanceEngine().evaluate(state_with_factor())
    assert not result.passed
    assert result.escalation_triggered
    assert result.violations


def test_notice_fills_template():
    state = state_with_factor("protection_class")
    rules = GovernanceEngine.load_rules("insurance", "US_CA")
    notice = ExplainabilityGenerator().generate_adverse_action_notice(state, rules)
    assert "{factors}" not in notice
    assert "protection_class" in notice


def test_governance_condition_rejects_unsafe_expression_nodes():
    try:
        evaluate_condition("__import__('os').system('echo unsafe')", {})
    except ValueError as exc:
        assert "Unsupported condition node" in str(exc)
    else:
        raise AssertionError("unsafe condition expression should be rejected")


def test_governance_condition_treats_missing_numeric_values_as_not_triggered():
    assert evaluate_condition("missing_case_value > 1000000", {}) is False


async def test_audit_writer_round_trip():
    state = state_with_factor("protection_class")
    result = GovernanceEngine().evaluate(state)
    record = await AuditTrailWriter().write(state, result)
    records = await AuditTrailWriter().get(state.submission.submission_id)
    assert record in records
