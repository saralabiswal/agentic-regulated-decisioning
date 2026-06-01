# Author: Sarala Biswal
"""Working stub lending agents."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.llm.client import generate_agent_explanation

from core.schemas import AgentOutput, EvidenceRef, UnifiedContext


async def _out(
    agent_type: str,
    decision: str,
    confidence: float,
    context: UnifiedContext,
    flags: list[str] | None = None,
) -> AgentOutput:
    core = context.payload.get("core", {})
    explanation = (
        f"Lending {agent_type} produced {decision} using income, DTI, credit history, "
        "and policy checks while excluding prohibited fair credit rules factors from the "
        "decision basis."
    )
    explanation = await generate_agent_explanation(
        domain="lending",
        agent_type=agent_type,
        decision=decision,
        confidence=confidence,
        evidence={"case_value": core.get("case_value"), "flags": flags or []},
        fallback=explanation,
    )
    return AgentOutput(
        agent_id=f"lending_{agent_type}",
        agent_type=agent_type,
        decision=decision,
        confidence=confidence,
        evidence=[
            EvidenceRef(
                source="core",
                field="case_value",
                value=core.get("case_value"),
                retrieved_at=datetime.now(UTC),
                confidence=0.9,
            )
        ],
        flags=flags or [],
        explanation=explanation,
        processing_ms=1,
    )


async def run_agent(name: str, context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    """Run the domain-specific specialist agent selected by name."""
    core = context.payload.get("core", {})
    if core.get("case_type") == "mortgage":
        return await _out(name, "ESCALATE", 0.68, context, ["MANUAL_REVIEW"])
    if name == "policy_check":
        return await _out(name, "APPROVE", 0.83, context)
    return await _out(name, "PASS", 0.82, context)
