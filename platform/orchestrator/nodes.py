# Author: Sarala Biswal
"""Orchestrator node functions."""

from __future__ import annotations

from importlib import import_module
from platform.governance.audit_trail import AuditTrailWriter
from platform.governance.engine import GovernanceEngine
from platform.mcp.assembler import assemble
from platform.observability.tracing import trace_span
from platform.workbench.queue import WorkbenchQueue

from core.schemas import OrchestratorState
from domains.registry import DomainRegistry


async def load_domain_adapter(state: OrchestratorState) -> OrchestratorState:
    """Resolve the domain plugin selected by the submission event."""
    adapter = DomainRegistry.get(state.submission.domain)
    state.adapter_id = adapter.domain_id
    return state


async def assemble_context(state: OrchestratorState) -> OrchestratorState:
    """Build unified evidence context before specialist agents run."""
    adapter = DomainRegistry.get(state.submission.domain)
    state.context = await assemble(state.submission, adapter.get_mcp_config())
    if state.context.context_confidence == "MINIMAL":
        state.escalation_required = True
        state.escalation_reason = "Insufficient data sources available"
    return state


async def run_named_agent(state: OrchestratorState, agent_name: str) -> OrchestratorState:
    """Execute one domain-owned specialist agent and update recommendation state."""
    if state.context is None:
        raise ValueError("context is required before running agents")
    with trace_span(
        "agent.run",
        {
            "domain": state.submission.domain,
            "case_type": state.submission.case_type,
            "agent.name": agent_name,
        },
    ):
        agent_module = import_module(f"domains.{state.submission.domain}.agents")
        if hasattr(agent_module, "AGENTS"):
            output = await agent_module.AGENTS[agent_name].run(state.context, state.agent_outputs)
        else:
            output = await agent_module.run_agent(agent_name, state.context, state.agent_outputs)
    state.agent_outputs.append(output)
    state.overall_confidence = sum(item.confidence for item in state.agent_outputs) / len(
        state.agent_outputs
    )
    if output.needs_escalation:
        state.escalation_required = True
        state.escalation_reason = state.escalation_reason or f"{output.agent_type} requires review"
    if output.agent_type in {"decision", "policy_check", "coverage_rules", "product_eligibility"}:
        state.final_decision = output.decision
    return state


async def apply_governance(state: OrchestratorState) -> OrchestratorState:
    """Evaluate domain and Playbook governance after an agent produces output."""
    with trace_span(
        "governance.evaluate",
        {"domain": state.submission.domain, "jurisdiction": state.submission.jurisdiction},
    ):
        result = GovernanceEngine().evaluate(state)
    state.governance_passed = result.passed
    if not result.passed or result.escalation_triggered:
        state.escalation_required = True
        state.escalation_reason = result.escalation_reason or "; ".join(result.violations)
    state.audit_trail_id = result.evaluated_at.isoformat()
    return state


async def route_to_human(state: OrchestratorState) -> OrchestratorState:
    """Create a reviewer workbench case when automation must pause."""
    case = await WorkbenchQueue().enqueue(
        state, state.escalation_reason or "Confidence or governance threshold triggered"
    )
    state.audit_trail_id = case.case_id
    return state


async def write_audit_trail(state: OrchestratorState) -> OrchestratorState:
    """Append the final audit record for reconstruction and reporting."""
    result = GovernanceEngine().evaluate(state) if state.agent_outputs else None
    with trace_span(
        "audit.write",
        {"domain": state.submission.domain, "submission_id": state.submission.submission_id},
    ):
        record = await AuditTrailWriter().write(state, result)
    state.audit_trail_id = record.audit_id
    return state
