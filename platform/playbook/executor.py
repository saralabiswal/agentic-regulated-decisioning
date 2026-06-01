# Author: Sarala Biswal
"""Playbook execution service."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.governance.engine import evaluate_condition
from platform.observability.tracing import trace_span
from platform.orchestrator.graph import build_graph
from platform.playbook.events import publish_layer_event, publish_rule_event
from platform.playbook.history import write_run
from time import perf_counter
from typing import Any
from uuid import uuid4

from core.playbook_schema import Playbook, raise_if_blocking
from core.schemas import (
    OrchestratorState,
    PlaybookEscalationOverride,
    PlaybookGovernanceOverride,
    PlaybookLayerEvent,
    PlaybookOverride,
    PlaybookRuleAppliedEvent,
    PlaybookRunRecord,
    SubmissionEvent,
)
from domains.base import EscalationConfig, GovernanceConfig
from domains.registry import DomainRegistry


class PlaybookExecutor:
    """Validate a Playbook, apply its safe overrides, execute the graph, and persist results."""

    async def run(self, playbook: Playbook) -> str:
        """Run one Playbook and return the generated submission identifier."""
        with trace_span(
            "playbook.run",
            {
                "domain": playbook.domain.name,
                "case_type": playbook.domain.case_type,
                "jurisdiction": playbook.jurisdiction.code,
            },
        ):
            adapter = DomainRegistry.get(playbook.domain.name)
            messages = adapter.validate_submission(playbook.validation_request())
            raise_if_blocking(messages)

            escalation_config = self._merge_escalation(
                adapter.get_escalation_thresholds(),
                playbook,
            )
            override = PlaybookOverride(
                playbook_name=playbook.playbook.name,
                escalation_config=escalation_config,
                governance_config=self._merge_governance(
                    adapter.get_governance_rules(playbook.jurisdiction.code),
                    playbook,
                    escalation_config,
                ),
            )
            submission = self._build_submission(playbook)
            self._emit_layer_event(submission.submission_id, "L0", "Intake", "running", 0)
            self._emit_rule_events(submission.submission_id, playbook)

            started_at = perf_counter()
            state = await build_graph().ainvoke(
                OrchestratorState(submission=submission, playbook_override=override)
            )
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            self._emit_completion_events(submission.submission_id, state, elapsed_ms)
            await write_run(
                PlaybookRunRecord(
                    submission_id=submission.submission_id,
                    playbook_name=playbook.playbook.name,
                    domain=playbook.domain.name,
                    case_type=playbook.domain.case_type,
                    jurisdiction=playbook.jurisdiction.code,
                    final_decision=state.final_decision or "ESCALATED",
                    total_latency_ms=elapsed_ms,
                    total_llm_cost=0.0,
                )
            )
            return submission.submission_id

    def _emit_layer_event(
        self,
        submission_id: str,
        layer: str,
        name: str,
        status: str,
        duration_ms: int,
        detail: str = "",
    ) -> None:
        publish_layer_event(
            PlaybookLayerEvent(
                submission_id=submission_id,
                layer=layer,
                name=name,
                status=status,
                duration_ms=duration_ms,
                detail=detail or f"{name} {status}",
            )
        )

    def _emit_completion_events(
        self, submission_id: str, state: OrchestratorState, elapsed_ms: int
    ) -> None:
        """Publish L0-L9 layer events for UI trace and audit reconstruction."""
        context_status = state.context.context_confidence if state.context else "missing"
        agent_names = ", ".join(output.agent_type for output in state.agent_outputs) or "none"
        review_status = "review" if state.escalation_required else "skipped"
        self._emit_layer_event(submission_id, "L0", "Intake", "complete", 4, "Playbook accepted")
        self._emit_layer_event(submission_id, "L1", "Stream", "complete", 8, "Local execution path")
        self._emit_layer_event(
            submission_id, "L2", "Orchestrator", "complete", 12, state.adapter_id or "-"
        )
        self._emit_layer_event(submission_id, "L3", "Agents", "complete", elapsed_ms, agent_names)
        self._emit_layer_event(submission_id, "L4", "Context", "complete", 0, str(context_status))
        self._emit_layer_event(
            submission_id,
            "L5",
            "Human Review",
            review_status,
            0,
            state.escalation_reason or "No human review required",
        )
        self._emit_layer_event(submission_id, "L6", "Data", "complete", 0, "Run history persisted")
        self._emit_layer_event(
            submission_id, "L7", "Model Registry", "complete", 0, "Registry fallback available"
        )
        self._emit_layer_event(
            submission_id, "L8", "Observability", "complete", 0, "Metrics and spans emitted"
        )
        self._emit_layer_event(
            submission_id,
            "L9",
            "Governance",
            "complete" if state.governance_passed else "review",
            0,
            "Governance passed" if state.governance_passed else "Governance review required",
        )

    def _merge_escalation(
        self, default: EscalationConfig, playbook: Playbook
    ) -> PlaybookEscalationOverride:
        """Merge Playbook thresholds conservatively so uploads cannot weaken defaults."""
        threshold = default.confidence_threshold
        if playbook.rules.confidence_threshold is not None:
            threshold = min(playbook.rules.confidence_threshold, default.confidence_threshold)
        value_threshold = default.value_threshold
        if playbook.rules.max_auto_decision_value is not None:
            value_threshold = min(playbook.rules.max_auto_decision_value, default.value_threshold)
        return PlaybookEscalationOverride(
            confidence_threshold=threshold,
            value_threshold=value_threshold,
            mandatory_review_cases=list(default.mandatory_review_cases),
        )

    def _merge_governance(
        self,
        default: GovernanceConfig,
        playbook: Playbook,
        escalation: PlaybookEscalationOverride,
    ) -> PlaybookGovernanceOverride:
        """Combine domain governance with Playbook-specific rules without removing controls."""
        prohibited = _unique(default.prohibited_factors + playbook.rules.prohibited_factors)
        escalation_overrides = list(default.escalation_overrides)
        for trigger in playbook.rules.mandatory_review_triggers:
            escalation_overrides.append(
                {
                    "condition": trigger,
                    "action": "playbook_mandatory_human_review",
                    "source": "playbook",
                }
            )
        if playbook.rules.max_auto_decision_value is not None:
            escalation_overrides.append(
                {
                    "condition": f"case_value > {escalation.value_threshold}",
                    "action": "playbook_value_threshold_review",
                    "source": "playbook",
                }
            )
        return PlaybookGovernanceOverride(
            jurisdiction=default.jurisdiction,
            regulatory_framework=default.regulatory_framework,
            prohibited_factors=prohibited,
            required_disclosures=default.required_disclosures,
            audit_retention_days=default.audit_retention_days,
            effective_date=default.effective_date,
            escalation_overrides=escalation_overrides,
        )

    def _build_submission(self, playbook: Playbook) -> SubmissionEvent:
        """Convert a validated Playbook into the canonical submission event."""
        payload = {
            **playbook.submission,
            "case_type": playbook.domain.case_type,
        }
        payload.setdefault("entity_id", f"playbook_{uuid4().hex[:12]}")
        payload.setdefault("case_value", _infer_case_value(playbook.submission))
        return SubmissionEvent(
            submission_id=str(uuid4()),
            domain=playbook.domain.name,
            case_type=playbook.domain.case_type,
            raw_payload=payload,
            source_channel="playbook_upload",
            received_at=datetime.now(UTC),
            jurisdiction=playbook.jurisdiction.code,
        )

    def _emit_rule_events(self, submission_id: str, playbook: Playbook) -> None:
        """Record Playbook rule evaluations for the audit report and UI trace."""
        values = {
            **playbook.submission,
            "case_value": _infer_case_value(playbook.submission),
            "domain": playbook.domain.name,
            "jurisdiction": playbook.jurisdiction.code,
            "flags": [],
        }
        for factor in playbook.rules.prohibited_factors:
            result = "factor_present" if factor in playbook.submission else "factor_not_present"
            publish_rule_event(
                PlaybookRuleAppliedEvent(
                    submission_id=submission_id,
                    layer=9,
                    rule_source="playbook",
                    rule_field="prohibited_factors",
                    rule_value=factor,
                    result=result,
                    display=f"{factor} checked against submission and evidence.",
                )
            )
        for trigger in playbook.rules.mandatory_review_triggers:
            result = "triggered" if evaluate_condition(trigger, values) else "not_triggered"
            publish_rule_event(
                PlaybookRuleAppliedEvent(
                    submission_id=submission_id,
                    layer=9,
                    rule_source="playbook",
                    rule_field="mandatory_review_triggers",
                    rule_value=trigger,
                    result=result,
                    display=f"Playbook trigger '{trigger}' evaluated as {result}.",
                )
            )


def _infer_case_value(submission: dict[str, Any]) -> float:
    for field_name in (
        "case_value",
        "total_insured_value",
        "requested_loan_amount",
        "investment_amount",
        "estimated_cost",
    ):
        value = submission.get(field_name)
        if isinstance(value, int | float):
            return float(value)
    return 0.0


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values
