# Author: Sarala Biswal
"""Insurance specialist agents."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.llm.client import generate_agent_explanation
from platform.observability.metrics import agent_duration_seconds, llm_tokens_total
from time import perf_counter

from core.schemas import AgentOutput, EvidenceRef, UnifiedContext
from domains.insurance.adapter import InsuranceAdapter


def _evidence(source: str, field: str, value: object, confidence: float = 0.9) -> EvidenceRef:
    return EvidenceRef(
        source=source,
        field=field,
        value=value,
        retrieved_at=datetime.now(UTC),
        confidence=confidence,
    )


def _core(context: UnifiedContext) -> dict:
    return context.payload.get("core", {})


def _history(context: UnifiedContext) -> dict:
    return context.payload.get("history", {})


def _external(context: UnifiedContext) -> dict:
    return context.payload.get("external", {})


class InsuranceTriageAgent:
    """Classifies insurance submissions before scoring and appetite checks."""
    agent_id = "insurance_triage"
    agent_type = "triage"

    async def run(
        self, context: UnifiedContext, prior_outputs: list[AgentOutput] | None = None
    ) -> AgentOutput:
        """Run this insurance specialist and return an auditable agent output."""
        started = perf_counter()
        core = _core(context)
        case_type = core.get("case_type", "commercial_property")
        tiv = float(core.get("tiv") or core.get("case_value") or 0)
        flags: list[str] = []
        if context.sources_missing:
            flags.append("INCOMPLETE_DATA")
        if case_type == "surplus_lines" or tiv > 7_500_000:
            decision = "SURPLUS_LINES_REFERRAL"
            flags.append("SURPLUS_LINES")
            confidence = 0.86
        elif tiv > 1_000_000 or core.get("protection_class", 0) >= 6:
            decision = "COMPLEX_REVIEW"
            confidence = 0.82 if context.context_confidence == "FULL" else 0.68
        else:
            decision = "STANDARD_PROCESSING"
            confidence = 0.9 if context.context_confidence == "FULL" else 0.7
        explanation = (
            f"Triage classified the {case_type} submission as {decision} using TIV "
            f"{tiv:,.0f}, occupancy {core.get('occupancy', 'not provided')}, protection class "
            f"{core.get('protection_class', 'not provided')}, and source completeness "
            f"{context.context_confidence}. The classification identifies whether standard "
            "underwriting can continue or whether specialist review is required before pricing."
        )
        explanation = await generate_agent_explanation(
            domain="insurance",
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            evidence={
                "case_type": case_type,
                "tiv": tiv,
                "occupancy": core.get("occupancy"),
                "protection_class": core.get("protection_class"),
                "context_confidence": context.context_confidence,
            },
            fallback=explanation,
        )
        output = AgentOutput(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            evidence=[
                _evidence("core", "case_value", tiv),
                _evidence("core", "case_type", case_type),
            ],
            flags=flags,
            explanation=explanation,
            processing_ms=int((perf_counter() - started) * 1000),
        )
        agent_duration_seconds.labels(domain="insurance", agent_type=self.agent_type).observe(
            perf_counter() - started
        )
        llm_tokens_total.labels(
            domain="insurance", agent_type=self.agent_type, provider="mock"
        ).inc(180)
        return output


class InsuranceRiskScoringAgent:
    """Scores insurance risk while excluding prohibited jurisdictional factors."""
    agent_id = "insurance_risk_scoring"
    agent_type = "scoring"

    async def run(
        self, context: UnifiedContext, prior_outputs: list[AgentOutput] | None = None
    ) -> AgentOutput:
        """Run this insurance specialist and return an auditable agent output."""
        started = perf_counter()
        core = _core(context)
        history = _history(context)
        external = _external(context)
        jurisdiction = str(core.get("jurisdiction") or "US_CA")
        prohibited = set(InsuranceAdapter().get_governance_rules(jurisdiction).prohibited_factors)
        flags = [factor for factor in prohibited if factor in core]
        loss_frequency = int(history.get("frequency_5y", 0))
        protection_class = int(core.get("protection_class", 1))
        tiv = float(core.get("tiv") or core.get("case_value") or 0)
        if tiv > 7_500_000 or loss_frequency >= 2 or protection_class >= 7:
            decision, confidence = "SUBSTANDARD", 0.77
        elif protection_class <= 3 and loss_frequency <= 1:
            decision, confidence = "STANDARD", 0.81
        else:
            decision, confidence = "PREFERRED", 0.86
        if core.get("violations", 0) == 0 and core.get("vehicle_year", 0) >= 2020:
            decision, confidence = "PREFERRED", 0.88
        explanation = (
            f"Risk scoring assigned {decision} after reviewing construction type "
            f"{core.get('construction_type', 'not provided')}, year built "
            f"{core.get('year_built', 'not provided')}, protection class {protection_class}, "
            f"TIV {tiv:,.0f}, loss frequency {loss_frequency}, and external rating "
            f"{external.get('bureau_rating', 'not provided')}. The score uses underwriting "
            "risk characteristics and excludes any prohibited jurisdictional factors when "
            "those appear in the payload."
        )
        explanation = await generate_agent_explanation(
            domain="insurance",
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            evidence={
                "construction_type": core.get("construction_type"),
                "year_built": core.get("year_built"),
                "protection_class": protection_class,
                "tiv": tiv,
                "loss_frequency": loss_frequency,
                "bureau_rating": external.get("bureau_rating"),
                "excluded_prohibited_factors": sorted(prohibited),
            },
            fallback=explanation,
        )
        output = AgentOutput(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            evidence=[
                _evidence("core", "protection_class", protection_class),
                _evidence("history", "frequency_5y", loss_frequency),
                _evidence("external", "bureau_rating", external.get("bureau_rating")),
            ],
            flags=flags,
            explanation=explanation,
            processing_ms=int((perf_counter() - started) * 1000),
        )
        agent_duration_seconds.labels(domain="insurance", agent_type=self.agent_type).observe(
            perf_counter() - started
        )
        llm_tokens_total.labels(
            domain="insurance", agent_type=self.agent_type, provider="mock"
        ).inc(240)
        return output


class InsuranceAppetiteAgent:
    """Converts scored insurance risk into an appetite recommendation."""
    agent_id = "insurance_appetite"
    agent_type = "decision"

    async def run(
        self, context: UnifiedContext, prior_outputs: list[AgentOutput] | None = None
    ) -> AgentOutput:
        """Run this insurance specialist and return an auditable agent output."""
        started = perf_counter()
        prior_outputs = prior_outputs or []
        core = _core(context)
        external = _external(context)
        risk = prior_outputs[-1].decision if prior_outputs else "STANDARD"
        tiv = float(core.get("tiv") or core.get("case_value") or 0)
        appetite = external.get(
            "appetite", {"PREFERRED": 5_000_000, "STANDARD": 2_000_000, "SUBSTANDARD": 1_000_000}
        )
        flags: list[str] = []
        if risk == "DECLINE":
            decision, confidence = "DECLINE", 0.9
        elif risk == "SUBSTANDARD" or tiv > appetite.get(risk, 0):
            decision, confidence = "REFER", 0.82
            flags.append("TREATY_LIMIT_REVIEW")
        elif risk == "STANDARD" and tiv > 1_000_000:
            decision, confidence = "ACCEPT_WITH_CONDITIONS", 0.84
        else:
            decision, confidence = "ACCEPT", 0.9
        explanation = (
            f"Appetite review recommends {decision} for a {risk} risk with TIV {tiv:,.0f}. "
            f"The rule set accepts preferred risks up to {appetite.get('PREFERRED', 0):,.0f}, "
            f"standard risks up to {appetite.get('STANDARD', 0):,.0f}, and refers substandard or "
            "capacity-constrained submissions to underwriting leadership or facultative "
            "reinsurance. "
            "The recommendation preserves the agent evidence trail for human review and audit."
        )
        explanation = await generate_agent_explanation(
            domain="insurance",
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            evidence={
                "risk": risk,
                "tiv": tiv,
                "appetite_limit": appetite.get(risk),
                "flags": flags,
            },
            fallback=explanation,
        )
        output = AgentOutput(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            evidence=[
                _evidence("external", "appetite_limit", appetite.get(risk)),
                _evidence("core", "tiv", tiv),
            ],
            flags=flags,
            explanation=explanation,
            processing_ms=int((perf_counter() - started) * 1000),
        )
        agent_duration_seconds.labels(domain="insurance", agent_type=self.agent_type).observe(
            perf_counter() - started
        )
        llm_tokens_total.labels(
            domain="insurance", agent_type=self.agent_type, provider="mock"
        ).inc(260)
        return output


AGENTS = {
    "triage": InsuranceTriageAgent(),
    "risk_scoring": InsuranceRiskScoringAgent(),
    "appetite_check": InsuranceAppetiteAgent(),
}
