# Author: Sarala Biswal
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core.schemas import AgentOutput, EvidenceRef, SubmissionEvent, UnifiedContext


def submission(**overrides):
    data = {
        "submission_id": str(uuid4()),
        "domain": "insurance",
        "case_type": "commercial_property",
        "raw_payload": {"entity_id": "ins_cp_ca_001"},
        "source_channel": "api",
        "received_at": datetime.now(UTC),
        "jurisdiction": "US_CA",
    }
    data.update(overrides)
    return SubmissionEvent(**data)


def evidence(field: str = "case_value") -> EvidenceRef:
    return EvidenceRef(
        source="core", field=field, value=100, retrieved_at=datetime.now(UTC), confidence=0.9
    )


def test_submission_uuid_validation():
    assert submission().domain == "insurance"
    with pytest.raises(ValueError):
        submission(submission_id="bad")


def test_agent_output_validators_and_properties():
    out = AgentOutput(
        agent_id="a",
        agent_type="triage",
        decision="PASS",
        confidence=0.8,
        evidence=[evidence()],
        flags=[],
        explanation="This explanation is long enough for audit.",
        processing_ms=1,
    )
    assert out.is_confident
    assert not out.needs_escalation
    assert out.model_dump()
    with pytest.raises(ValueError):
        AgentOutput(
            agent_id="a",
            agent_type="triage",
            decision="PASS",
            confidence=1.2,
            evidence=[],
            flags=[],
            explanation="This explanation is long enough for audit.",
            processing_ms=1,
        )
    with pytest.raises(ValueError):
        AgentOutput(
            agent_id="a",
            agent_type="triage",
            decision="PASS",
            confidence=0.5,
            evidence=[],
            flags=[],
            explanation="short",
            processing_ms=1,
        )


def test_unified_context_from_results_full_partial_minimal():
    full = UnifiedContext.from_results(
        "s", "insurance", [{"a": 1}, {"b": 2}, {"c": 3}], ["core", "history", "external"]
    )
    assert full.context_confidence == "FULL"
    partial = UnifiedContext.from_results(
        "s", "insurance", [{"a": 1}, RuntimeError(), {"c": 3}], ["core", "history", "external"]
    )
    assert partial.context_confidence == "PARTIAL"
    assert partial.sources_missing == ["history"]
    minimal = UnifiedContext.from_results(
        "s",
        "insurance",
        [{"a": 1}, RuntimeError(), RuntimeError()],
        ["core", "history", "external"],
    )
    assert minimal.context_confidence == "MINIMAL"
