# Author: Sarala Biswal
"""Orchestrator routing decisions."""

from __future__ import annotations

from core.schemas import OrchestratorState, PlaybookEscalationOverride
from domains.base import EscalationConfig
from domains.registry import DomainRegistry


def should_escalate_after_triage(state: OrchestratorState) -> str:
    """Choose the next graph route after triage confidence is known."""
    thresholds: EscalationConfig | PlaybookEscalationOverride
    if state.playbook_override:
        thresholds = state.playbook_override.escalation_config
    else:
        thresholds = DomainRegistry.get(state.submission.domain).get_escalation_thresholds()
    if state.escalation_required:
        return "route_to_human"
    if state.agent_outputs and state.agent_outputs[-1].confidence < thresholds.confidence_threshold:
        return "route_to_human"
    if float(state.submission.raw_payload.get("case_value", 0)) > thresholds.value_threshold:
        return "route_to_human"
    if state.submission.case_type in thresholds.mandatory_review_cases:
        return "route_to_human"
    return "run_scoring_agent"
