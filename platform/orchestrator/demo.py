# Author: Sarala Biswal
"""Demo runner for the orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.orchestrator.graph import build_graph
from uuid import uuid4

from core.schemas import OrchestratorState, SubmissionEvent
from domains.registry import DomainRegistry


async def run_demo(
    domain: str, case_type: str, jurisdiction: str, print_output: bool = True
) -> OrchestratorState:
    """Execute a single seeded orchestrator demo scenario."""
    adapter = DomainRegistry.get(domain)
    demo_cases = adapter.get_demo_cases()
    case = next(item for item in demo_cases if item["case_type"] == case_type)
    submission = SubmissionEvent(
        submission_id=str(uuid4()),
        domain=domain,
        case_type=case_type,
        raw_payload={**case["payload"], "case_type": case_type},
        source_channel="demo_cli",
        received_at=datetime.now(UTC),
        jurisdiction=jurisdiction,
    )
    final_state = await build_graph().ainvoke(OrchestratorState(submission=submission))
    if print_output:
        print_demo_output(final_state)
    return final_state


def print_demo_output(state: OrchestratorState) -> None:
    """Print the important decision, context, and audit fields for a demo run."""
    print(f"Domain: {state.submission.domain} | Case: {state.submission.case_type}")
    if state.context:
        print(f"Context confidence: {state.context.context_confidence}")
    for output in state.agent_outputs:
        print(f"{output.agent_type}: {output.decision} ({output.confidence:.2f})")
    route = "human" if state.escalation_required else "auto"
    print(f"Final decision: {state.final_decision or 'ESCALATED'} | Route: {route}")
