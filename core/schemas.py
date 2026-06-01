# Author: Sarala Biswal
"""Canonical schemas crossing platform layer boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

DomainId = Literal["insurance", "lending", "healthcare", "wealth"]
ContextConfidence = Literal["FULL", "PARTIAL", "MINIMAL"]


class SubmissionEvent(BaseModel):
    """Immutable intake event that starts a regulated decision run."""

    model_config = ConfigDict(frozen=True)

    submission_id: str
    domain: DomainId
    case_type: str
    raw_payload: dict[str, Any]
    source_channel: str
    received_at: datetime
    jurisdiction: str
    priority: Literal["standard", "high", "urgent"] = "standard"

    @field_validator("submission_id")
    @classmethod
    def validate_uuid4(cls, value: str) -> str:
        """Enforce UUID4 submission ids before events cross service boundaries."""
        parsed = UUID(value, version=4)
        if str(parsed) != value:
            raise ValueError("submission_id must be a valid uuid4 string")
        return value


class StreamMessageView(BaseModel):
    """Serializable stream message view used by runtime diagnostics."""
    model_config = ConfigDict(frozen=True)

    message_id: str
    submission_id: str
    domain: str
    case_type: str
    source_channel: str
    received_at: datetime
    event: SubmissionEvent | None = None
    parse_error: str | None = None


class StreamInspection(BaseModel):
    """Operational view of the configured submission stream and dead-letter state."""

    model_config = ConfigDict(frozen=True)

    backend: Literal["memory", "redis", "local_sync"]
    mode: str
    stream_name: str
    consumer_group: str
    status: str
    input_count: int = Field(ge=0)
    pending_count: int = Field(ge=0)
    dlq_count: int = Field(ge=0)
    recent_inputs: list[StreamMessageView] = Field(default_factory=list)
    output_note: str


class EvidenceRef(BaseModel):
    """Traceable piece of evidence used by an agent recommendation."""

    model_config = ConfigDict(frozen=True)

    source: str
    field: str
    value: Any
    retrieved_at: datetime
    confidence: float = Field(ge=0.0, le=1.0)


class AgentOutput(BaseModel):
    """Required agent result crossing the agent, governance, audit, and UI boundary."""

    model_config = ConfigDict(frozen=True)

    agent_id: str
    agent_type: str
    decision: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceRef]
    flags: list[str]
    explanation: str = Field(min_length=20)
    processing_ms: int = Field(ge=0)

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        """Reject empty agent explanations before audit persistence."""
        if not value.strip():
            raise ValueError("explanation must be non-empty")
        return value

    @property
    def is_confident(self) -> bool:
        """Return whether an agent output meets the platform confidence bar."""
        return self.confidence >= 0.75

    @property
    def needs_escalation(self) -> bool:
        """Return whether low confidence or flags require human review."""
        return self.confidence < 0.75 or bool(self.flags)


class UnifiedContext(BaseModel):
    """Merged context packet built from MCP sources for downstream specialist agents."""

    model_config = ConfigDict(frozen=True)

    submission_id: str
    domain: str
    sources_available: list[str]
    sources_missing: list[str]
    context_confidence: ContextConfidence
    assembled_at: datetime
    payload: dict[str, Any]

    @classmethod
    def from_results(
        cls,
        submission_id: str,
        domain: str,
        results: list[Any],
        names: list[str],
    ) -> UnifiedContext:
        """Normalize successful and failed MCP calls into one confidence-scored context."""
        available: list[str] = []
        missing: list[str] = []
        payload: dict[str, Any] = {}
        for name, result in zip(names, results, strict=True):
            if isinstance(result, Exception):
                missing.append(name)
            else:
                available.append(name)
                payload[name] = result
        confidence: ContextConfidence = (
            "FULL" if not missing else "PARTIAL" if len(available) >= 2 else "MINIMAL"
        )
        return cls(
            submission_id=submission_id,
            domain=domain,
            sources_available=available,
            sources_missing=missing,
            context_confidence=confidence,
            assembled_at=datetime.now(UTC),
            payload=payload,
        )


class OrchestratorState(BaseModel):
    """Mutable state envelope that flows through the decision graph."""
    submission: SubmissionEvent
    adapter_id: str | None = None
    context: UnifiedContext | None = None
    playbook_override: PlaybookOverride | None = None
    agent_outputs: list[AgentOutput] = Field(default_factory=list)
    overall_confidence: float = 0.0
    escalation_required: bool = False
    escalation_reason: str = ""
    final_decision: str = ""
    governance_passed: bool = False
    audit_trail_id: str = ""


class WorkbenchCase(BaseModel):
    """Human review queue case with context, recommendation, and reviewer result."""
    case_id: str
    submission: SubmissionEvent
    context: UnifiedContext
    agent_outputs: list[AgentOutput]
    agent_recommendation: str
    confidence: float
    escalation_reason: str
    assigned_to: str | None = None
    status: Literal["pending", "in_review", "decided"] = "pending"
    human_decision: str | None = None
    human_notes: str | None = None
    created_at: datetime
    decided_at: datetime | None = None


class AuditRecord(BaseModel):
    """Durable audit event for agent, governance, human, and registry decisions."""
    model_config = ConfigDict(frozen=True)

    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    submission_id: str
    domain: str
    jurisdiction: str
    decision_type: Literal["agent_auto", "human_override", "human_confirm", "model_event"]
    final_decision: str
    agent_outputs: list[AgentOutput]
    governance_rules_applied: list[str]
    governance_passed: bool
    human_reviewer: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GovernanceEvaluationResult(BaseModel):
    """Structured governance outcome used for routing and audit writing."""
    model_config = ConfigDict(frozen=True)

    passed: bool
    violations: list[str]
    rules_applied: list[str]
    escalation_triggered: bool
    escalation_reason: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlaybookEscalationOverride(BaseModel):
    """Playbook-provided escalation settings after conservative merging."""
    model_config = ConfigDict(frozen=True)

    confidence_threshold: float = Field(ge=0.0, le=1.0)
    value_threshold: float = Field(ge=0.0)
    mandatory_review_cases: list[str]


class PlaybookGovernanceOverride(BaseModel):
    """Playbook-provided governance rules layered onto domain policy."""
    model_config = ConfigDict(frozen=True)

    jurisdiction: str
    regulatory_framework: str
    prohibited_factors: list[str]
    required_disclosures: list[str] | dict[str, str]
    audit_retention_days: int
    effective_date: str | None = None
    escalation_overrides: list[dict[str, Any]] = Field(default_factory=list)


class PlaybookOverride(BaseModel):
    """Runtime override object attached to orchestrator state for one Playbook."""
    model_config = ConfigDict(frozen=True)

    playbook_name: str
    escalation_config: PlaybookEscalationOverride
    governance_config: PlaybookGovernanceOverride


class PlaybookRuleAppliedEvent(BaseModel):
    """Event describing one Playbook, jurisdiction, or platform rule result."""
    model_config = ConfigDict(frozen=True)

    submission_id: str
    layer: int
    rule_source: Literal["playbook", "jurisdiction", "platform"]
    rule_field: str
    rule_value: str
    result: str
    display: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlaybookLayerEvent(BaseModel):
    """Event describing progress through a Playbook execution layer."""
    model_config = ConfigDict(frozen=True)

    submission_id: str
    layer: str
    name: str
    status: Literal["pending", "running", "complete", "skipped", "review"]
    duration_ms: int = Field(ge=0)
    detail: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlaybookRunRecord(BaseModel):
    """Persisted summary of a completed Playbook run."""
    model_config = ConfigDict(frozen=True)

    playbook_run_id: str = Field(default_factory=lambda: str(uuid4()))
    submission_id: str
    playbook_name: str
    domain: DomainId
    case_type: str
    jurisdiction: str
    final_decision: str | None = None
    total_latency_ms: int | None = None
    total_llm_cost: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
