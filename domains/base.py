# Author: Sarala Biswal
"""Domain plugin protocol and shared config models."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from core.playbook_schema import PlaybookSubmissionValidationRequest, ValidationMessage


class EscalationConfig(BaseModel):
    """Domain-owned thresholds that decide whether automation must stop for review."""

    confidence_threshold: float = Field(ge=0.0, le=1.0)
    value_threshold: float
    mandatory_review_cases: list[str]


class GovernanceConfig(BaseModel):
    """Normalized governance rules loaded from domain YAML policy files."""

    jurisdiction: str
    regulatory_framework: str
    prohibited_factors: list[str]
    required_disclosures: list[str] | dict[str, str]
    audit_retention_days: int
    effective_date: str | None = None
    escalation_overrides: list[dict[str, Any]] = []


class MCPConfig(BaseModel):
    """Connector configuration for assembling context across internal and external sources."""

    core_system: dict[str, Any]
    history_system: dict[str, Any]
    external_data: dict[str, Any]


@runtime_checkable
class DomainAdapter(Protocol):
    """Contract every regulated domain must implement to plug into the platform."""

    domain_id: str
    display_name: str
    supported_case_types: list[str]

    def get_agent_sequence(self, case_type: str) -> list[str]:
        """Return the ordered specialist agents for the case type."""
        ...

    def get_escalation_thresholds(self) -> EscalationConfig:
        """Return default human-review thresholds for the domain."""
        ...

    def get_governance_rules(self, jurisdiction: str) -> GovernanceConfig:
        """Load governance rules for the requested jurisdiction."""
        ...

    def get_mcp_config(self) -> MCPConfig:
        """Return the context sources required by the domain."""
        ...

    def get_demo_cases(self) -> list[dict[str, Any]]:
        """Return seeded demo submissions for local walkthroughs."""
        ...

    def validate_submission(
        self, request: PlaybookSubmissionValidationRequest
    ) -> list[ValidationMessage]:
        """Validate Playbook submission data against domain rules."""
        ...


def validate_adapter(adapter: DomainAdapter) -> bool:
    """Exercise the adapter contract with a demo case so registry tests can fail fast."""
    case_type = adapter.supported_case_types[0]
    sequence = adapter.get_agent_sequence(case_type)
    escalation = adapter.get_escalation_thresholds()
    governance = adapter.get_governance_rules("federal")
    mcp = adapter.get_mcp_config()
    demo_cases = adapter.get_demo_cases()
    validation = adapter.validate_submission(
        PlaybookSubmissionValidationRequest(
            domain=adapter.domain_id,
            case_type=case_type,
            jurisdiction="federal",
            submission=demo_cases[0]["payload"],
        )
    )
    return (
        isinstance(sequence, list)
        and all(isinstance(item, str) for item in sequence)
        and isinstance(escalation, EscalationConfig)
        and isinstance(governance, GovernanceConfig)
        and isinstance(mcp, MCPConfig)
        and isinstance(demo_cases, list)
        and isinstance(validation, list)
    )
