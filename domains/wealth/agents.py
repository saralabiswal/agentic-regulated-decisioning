# Author: Sarala Biswal
"""Wealth suitability specialist agents."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.llm.client import generate_agent_explanation
from platform.registry.model_registry import ModelRegistry
from typing import Any

from core.schemas import AgentOutput, EvidenceRef, UnifiedContext

_RISK_ORDER = {
    "low": 1,
    "conservative": 1,
    "moderate": 2,
    "balanced": 2,
    "high": 3,
    "aggressive": 3,
}


def _core(context: UnifiedContext) -> dict[str, Any]:
    return context.payload.get("core", {})


def _history(context: UnifiedContext) -> dict[str, Any]:
    return context.payload.get("history", {})


def _external(context: UnifiedContext) -> dict[str, Any]:
    return context.payload.get("external", {})


def _num(value: Any, default: float = 0.0) -> float:
    return float(value) if isinstance(value, int | float) else default


def _risk_level(value: Any) -> int:
    return _RISK_ORDER.get(str(value or "moderate").lower(), 2)


def _client_risk(core: dict[str, Any]) -> str:
    return str(core.get("risk_tolerance") or core.get("risk_profile") or "moderate").lower()


def _product_risk(external: dict[str, Any], core: dict[str, Any]) -> str:
    product_type = str(core.get("proposed_product_type") or "").lower()
    if "option" in product_type:
        return "high"
    if "annuity" in product_type:
        return str(external.get("product_risk") or "low").lower()
    return str(external.get("product_risk") or "moderate").lower()


def _horizon(core: dict[str, Any]) -> float:
    return _num(core.get("investment_horizon_years") or core.get("horizon_years"), 5.0)


def _evidence(source: str, field: str, value: object, confidence: float = 0.9) -> EvidenceRef:
    return EvidenceRef(
        source=source,
        field=field,
        value=value,
        retrieved_at=datetime.now(UTC),
        confidence=confidence,
    )


async def _suitability_model_score(core: dict[str, Any], external: dict[str, Any]):
    client_risk = _risk_level(_client_risk(core))
    product_risk = _risk_level(_product_risk(external, core))
    features = {
        "case_value": _num(core.get("case_value") or core.get("investment_amount")),
        "confidence_hint": 0.85 if product_risk <= client_risk else 0.35,
        "history_risk": 0.35,
        "external_risk": product_risk / 3,
    }
    model = await ModelRegistry().aget_production_model("wealth", "suitability")
    return model.score(features)


async def _out(
    agent_type: str,
    decision: str,
    confidence: float,
    context: UnifiedContext,
    evidence: list[EvidenceRef],
    *,
    flags: list[str] | None = None,
    model_version: str | None = None,
) -> AgentOutput:
    core = _core(context)
    external = _external(context)
    explanation = (
        f"Wealth {agent_type} produced {decision} using investment objective, time horizon, "
        "liquidity needs, risk tolerance, product risk, and account restrictions."
    )
    explanation = await generate_agent_explanation(
        domain="wealth",
        agent_type=agent_type,
        decision=decision,
        confidence=confidence,
        evidence={
            "case_type": core.get("case_type"),
            "client_risk": _client_risk(core),
            "product_risk": _product_risk(external, core),
            "horizon_years": _horizon(core),
            "model_version": model_version,
            "flags": flags or [],
        },
        fallback=explanation,
    )
    return AgentOutput(
        agent_id=f"wealth_{agent_type}",
        agent_type=agent_type,
        decision=decision,
        confidence=confidence,
        evidence=evidence,
        flags=flags or [],
        explanation=explanation,
        processing_ms=1,
    )


async def _suitability(context: UnifiedContext) -> AgentOutput:
    core = _core(context)
    external = _external(context)
    history = _history(context)
    horizon = _horizon(core)
    product_risk = _product_risk(external, core)
    model_score = await _suitability_model_score(core, external)
    evidence = [
        _evidence(
            "core",
            "investment_objective",
            core.get("investment_objective") or core.get("objective"),
        ),
        _evidence("core", "investment_horizon_years", horizon),
        _evidence("history", "transactions", history.get("transactions")),
        _evidence("external", "product_risk", product_risk),
        _evidence("model_registry", "model_version", model_score.model_version, 0.8),
    ]
    if horizon < 3 and product_risk in {"moderate", "high"}:
        return await _out(
            "suitability",
            "SUITABILITY_REVIEW",
            0.72,
            context,
            evidence,
            flags=["short_horizon_product_review"],
            model_version=model_score.model_version,
        )
    return await _out(
        "suitability",
        "SUITABILITY_ALIGNED",
        0.86,
        context,
        evidence,
        model_version=model_score.model_version,
    )


async def _risk_tolerance(context: UnifiedContext) -> AgentOutput:
    core = _core(context)
    external = _external(context)
    client_risk = _client_risk(core)
    product_risk = _product_risk(external, core)
    evidence = [
        _evidence("core", "risk_tolerance", client_risk),
        _evidence("external", "product_risk", product_risk),
        _evidence("core", "account_type", core.get("account_type")),
    ]
    if _risk_level(product_risk) > _risk_level(client_risk):
        return await _out(
            "risk_tolerance",
            "RISK_PROFILE_MISMATCH",
            0.66,
            context,
            evidence,
            flags=["risk_profile_mismatch"],
        )
    return await _out("risk_tolerance", "RISK_ALIGNED", 0.87, context, evidence)


async def _product_eligibility(context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    core = _core(context)
    external = _external(context)
    evidence = [
        _evidence("core", "account_type", core.get("account_type")),
        _evidence("core", "client_age", core.get("client_age") or core.get("age")),
        _evidence("external", "product_risk", _product_risk(external, core)),
    ]
    prior_flags = [flag for output in prior for flag in output.flags]
    case_type = str(core.get("case_type", "suitability_check"))
    if prior_flags:
        return await _out(
            "product_eligibility",
            "ESCALATE",
            0.66,
            context,
            evidence,
            flags=prior_flags,
        )
    if case_type == "options_authorization":
        return await _out(
            "product_eligibility",
            "ESCALATE",
            0.7,
            context,
            evidence,
            flags=["options_authorization_review"],
        )
    if case_type == "annuity_recommendation":
        return await _out(
            "product_eligibility",
            "SUITABLE_WITH_DOCUMENTATION",
            0.84,
            context,
            evidence,
        )
    return await _out("product_eligibility", "SUITABLE", 0.88, context, evidence)


async def run_agent(name: str, context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    """Run the domain-specific specialist agent selected by name."""
    if name == "suitability":
        return await _suitability(context)
    if name == "risk_tolerance":
        return await _risk_tolerance(context)
    return await _product_eligibility(context, prior)
