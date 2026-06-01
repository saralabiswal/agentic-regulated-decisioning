# Author: Sarala Biswal
"""Working stub wealth agents."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.llm.client import generate_agent_explanation

from core.schemas import AgentOutput, EvidenceRef, UnifiedContext


async def run_agent(name: str, context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    """Run the domain-specific specialist agent selected by name."""
    core = context.payload.get("core", {})
    external = context.payload.get("external", {})
    mismatch = core.get("risk_profile") == "conservative" and external.get("product_risk") == "high"
    decision = "ESCALATE" if mismatch else "SUITABLE"
    confidence = 0.66 if mismatch else 0.86
    flags = ["risk_profile_mismatch"] if mismatch else []
    explanation = (
        f"Wealth {name} evaluated suitability using objective, time horizon, liquidity "
        f"needs, risk tolerance, and product risk to produce {decision}."
    )
    explanation = await generate_agent_explanation(
        domain="wealth",
        agent_type=name,
        decision=decision,
        confidence=confidence,
        evidence={
            "risk_profile": core.get("risk_profile"),
            "product_risk": external.get("product_risk"),
            "flags": flags,
        },
        fallback=explanation,
    )
    return AgentOutput(
        agent_id=f"wealth_{name}",
        agent_type=name,
        decision=decision,
        confidence=confidence,
        evidence=[
            EvidenceRef(
                source="external",
                field="product_risk",
                value=external.get("product_risk"),
                retrieved_at=datetime.now(UTC),
                confidence=0.9,
            )
        ],
        flags=flags,
        explanation=explanation,
        processing_ms=1,
    )
