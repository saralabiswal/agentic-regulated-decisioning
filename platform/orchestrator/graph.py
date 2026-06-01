# Author: Sarala Biswal
"""LangGraph domain orchestrator."""

from __future__ import annotations

from platform.orchestrator.nodes import (
    apply_governance,
    assemble_context,
    load_domain_adapter,
    route_to_human,
    run_named_agent,
    write_audit_trail,
)

from langgraph.graph import END, START, StateGraph

from core.schemas import OrchestratorState
from domains.registry import DomainRegistry


def _thresholds(state: OrchestratorState):
    if state.playbook_override:
        return state.playbook_override.escalation_config
    return DomainRegistry.get(state.submission.domain).get_escalation_thresholds()


async def _route_minimal_context(state: OrchestratorState) -> str:
    if (
        state.escalation_required
        and state.context
        and state.context.context_confidence == "MINIMAL"
    ):
        return "route_to_human"
    return "run_agent_0"


async def _run_agent_by_index(state: OrchestratorState, index: int) -> OrchestratorState:
    adapter = DomainRegistry.get(state.submission.domain)
    sequence = adapter.get_agent_sequence(state.submission.case_type)
    if index >= len(sequence):
        return state
    return await run_named_agent(state, sequence[index])


async def _run_agent_0(state: OrchestratorState) -> OrchestratorState:
    return await _run_agent_by_index(state, 0)


async def _run_agent_1(state: OrchestratorState) -> OrchestratorState:
    return await _run_agent_by_index(state, 1)


async def _run_agent_2(state: OrchestratorState) -> OrchestratorState:
    return await _run_agent_by_index(state, 2)


async def _route_after_first_governance(state: OrchestratorState) -> str:
    thresholds = _thresholds(state)
    if state.escalation_required:
        return "route_to_human"
    if state.agent_outputs and state.agent_outputs[-1].confidence < thresholds.confidence_threshold:
        return "route_to_human"
    if float(state.submission.raw_payload.get("case_value", 0)) > thresholds.value_threshold:
        return "route_to_human"
    if state.submission.case_type in thresholds.mandatory_review_cases:
        return "route_to_human"
    return "run_agent_1"


async def _route_after_intermediate_governance(state: OrchestratorState) -> str:
    return "route_to_human" if state.escalation_required else "run_agent_2"


async def _route_after_governance(state: OrchestratorState) -> str:
    return "route_to_human" if state.escalation_required else "write_audit_trail"


class DecisionGraph:
    """Executable decision graph that keeps routing logic outside domain adapters."""

    def __init__(self) -> None:
        """Compile the state graph with governance checks between each specialist agent."""
        builder = StateGraph(OrchestratorState)
        builder.add_node("load_domain_adapter", load_domain_adapter)
        builder.add_node("assemble_context", assemble_context)
        builder.add_node("run_agent_0", _run_agent_0)
        builder.add_node("run_agent_1", _run_agent_1)
        builder.add_node("run_agent_2", _run_agent_2)
        builder.add_node("apply_governance_0", apply_governance)
        builder.add_node("apply_governance_1", apply_governance)
        builder.add_node("apply_governance_2", apply_governance)
        builder.add_node("route_to_human", route_to_human)
        builder.add_node("write_audit_trail", write_audit_trail)
        builder.add_edge(START, "load_domain_adapter")
        builder.add_edge("load_domain_adapter", "assemble_context")
        builder.add_conditional_edges(
            "assemble_context",
            _route_minimal_context,
            {"route_to_human": "route_to_human", "run_agent_0": "run_agent_0"},
        )
        builder.add_edge("run_agent_0", "apply_governance_0")
        builder.add_conditional_edges(
            "apply_governance_0",
            _route_after_first_governance,
            {"route_to_human": "route_to_human", "run_agent_1": "run_agent_1"},
        )
        builder.add_edge("run_agent_1", "apply_governance_1")
        builder.add_conditional_edges(
            "apply_governance_1",
            _route_after_intermediate_governance,
            {"route_to_human": "route_to_human", "run_agent_2": "run_agent_2"},
        )
        builder.add_edge("run_agent_2", "apply_governance_2")
        builder.add_conditional_edges(
            "apply_governance_2",
            _route_after_governance,
            {"route_to_human": "route_to_human", "write_audit_trail": "write_audit_trail"},
        )
        builder.add_edge("route_to_human", "write_audit_trail")
        builder.add_edge("write_audit_trail", END)
        self._compiled = builder.compile()

    async def ainvoke(self, initial_state: OrchestratorState) -> OrchestratorState:
        """Run the graph and coerce the LangGraph result back to the canonical state model."""
        result = await self._compiled.ainvoke(initial_state)
        return OrchestratorState.model_validate(result)


def build_graph() -> DecisionGraph:
    """Create a fresh graph instance for API and Playbook execution paths."""
    return DecisionGraph()
