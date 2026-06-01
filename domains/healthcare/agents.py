# Author: Sarala Biswal
"""Working stub healthcare agents."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.llm.client import generate_agent_explanation

from core.schemas import AgentOutput, EvidenceRef, UnifiedContext


async def run_agent(name: str, context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    """Run the domain-specific specialist agent selected by name."""
    core = context.payload.get("core", {})
    external = context.payload.get("external", {})
    flags = [] if core.get("notes_complete", True) else ["incomplete_clinical_notes"]
    decision = "APPROVE" if external.get("criteria_met", True) and not flags else "ESCALATE"
    confidence = 0.84 if decision == "APPROVE" else 0.64
    explanation = (
        f"Healthcare {name} reviewed medical necessity criteria, benefit coverage, "
        f"and clinical note completeness to produce {decision} with an auditable rationale."
    )
    explanation = await generate_agent_explanation(
        domain="healthcare",
        agent_type=name,
        decision=decision,
        confidence=confidence,
        evidence={
            "criteria_met": external.get("criteria_met"),
            "notes_complete": core.get("notes_complete", True),
            "flags": flags,
        },
        fallback=explanation,
    )
    return AgentOutput(
        agent_id=f"healthcare_{name}",
        agent_type=name,
        decision=decision,
        confidence=confidence,
        evidence=[
            EvidenceRef(
                source="external",
                field="criteria_met",
                value=external.get("criteria_met"),
                retrieved_at=datetime.now(UTC),
                confidence=0.9,
            )
        ],
        flags=flags,
        explanation=explanation,
        processing_ms=1,
    )
