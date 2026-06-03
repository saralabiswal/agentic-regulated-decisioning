# Author: Sarala Biswal
"""Consumer lending specialist agents."""

from __future__ import annotations

from datetime import UTC, datetime
from platform.llm.client import generate_agent_explanation
from platform.registry.model_registry import ModelRegistry
from typing import Any

from core.schemas import AgentOutput, EvidenceRef, UnifiedContext


def _core(context: UnifiedContext) -> dict[str, Any]:
    return context.payload.get("core", {})


def _history(context: UnifiedContext) -> dict[str, Any]:
    return context.payload.get("history", {})


def _external(context: UnifiedContext) -> dict[str, Any]:
    return context.payload.get("external", {})


def _num(value: Any, default: float = 0.0) -> float:
    return float(value) if isinstance(value, int | float) else default


def _debt_ratio(core: dict[str, Any]) -> float:
    if isinstance(core.get("dti"), int | float):
        return float(core["dti"])
    income = _num(core.get("annual_income") or core.get("income"))
    monthly_debt = _num(core.get("monthly_debt_obligations"))
    return monthly_debt / (income / 12) if income > 0 and monthly_debt > 0 else 0.0


def _thin_file(core: dict[str, Any], history: dict[str, Any]) -> bool:
    credit_months = core.get("months_credit_history")
    return bool(
        core.get("thin_file")
        or history.get("payments") == "thin_file"
        or (isinstance(credit_months, int | float) and credit_months < 12)
    )


def _evidence(source: str, field: str, value: object, confidence: float = 0.9) -> EvidenceRef:
    return EvidenceRef(
        source=source,
        field=field,
        value=value,
        retrieved_at=datetime.now(UTC),
        confidence=confidence,
    )


async def _model_score(core: dict[str, Any], history: dict[str, Any], external: dict[str, Any]):
    features = {
        "case_value": _num(core.get("case_value") or core.get("requested_loan_amount")),
        "confidence_hint": min(max((_num(external.get("bureau_score"), 700) - 500) / 350, 0), 1),
        "history_risk": 0.35 if history.get("payments") in {"clean", "on_time"} else 0.72,
        "external_risk": 1 - min(max((_num(external.get("bureau_score"), 700) - 500) / 350, 0), 1),
    }
    model = await ModelRegistry().aget_production_model("lending", "credit")
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
        f"Lending {agent_type} produced {decision} using debt capacity, credit performance, "
        "payment history, collateral/request details, and fair-credit governance exclusions."
    )
    explanation = await generate_agent_explanation(
        domain="lending",
        agent_type=agent_type,
        decision=decision,
        confidence=confidence,
        evidence={
            "case_type": core.get("case_type"),
            "case_value": core.get("case_value") or core.get("requested_loan_amount"),
            "debt_ratio": _debt_ratio(core),
            "bureau_score": external.get("bureau_score"),
            "model_version": model_version,
            "flags": flags or [],
        },
        fallback=explanation,
    )
    return AgentOutput(
        agent_id=f"lending_{agent_type}",
        agent_type=agent_type,
        decision=decision,
        confidence=confidence,
        evidence=evidence,
        flags=flags or [],
        explanation=explanation,
        processing_ms=1,
    )


async def _eligibility(context: UnifiedContext) -> AgentOutput:
    core = _core(context)
    ratio = _debt_ratio(core)
    income = _num(core.get("annual_income") or core.get("income"))
    case_type = str(core.get("case_type", "auto_loan"))
    evidence = [
        _evidence("core", "income", income),
        _evidence("core", "debt_ratio", ratio),
        _evidence("core", "case_type", case_type),
    ]
    if income <= 0:
        return await _out(
            "eligibility",
            "ELIGIBILITY_REVIEW",
            0.58,
            context,
            evidence,
            flags=["missing_income"],
        )
    if ratio > 0.5:
        return await _out(
            "eligibility",
            "DEBT_CAPACITY_REVIEW",
            0.68,
            context,
            evidence,
            flags=["debt_ratio_review"],
        )
    if case_type == "mortgage" or ratio > 0.4:
        return await _out("eligibility", "ELIGIBLE_REVIEW", 0.78, context, evidence)
    return await _out("eligibility", "ELIGIBLE", 0.88, context, evidence)


async def _credit_scoring(context: UnifiedContext) -> AgentOutput:
    core = _core(context)
    history = _history(context)
    external = _external(context)
    bureau_score = _num(external.get("bureau_score"), 700)
    thin_file = _thin_file(core, history)
    model_score = await _model_score(core, history, external)
    evidence = [
        _evidence("external", "bureau_score", bureau_score),
        _evidence("history", "payments", history.get("payments")),
        _evidence("model_registry", "model_version", model_score.model_version, 0.8),
        _evidence("model_registry", "credit_score", round(model_score.score, 4), 0.8),
    ]
    if bureau_score < 620:
        return await _out(
            "credit_scoring",
            "CREDIT_POLICY_REVIEW",
            0.7,
            context,
            evidence,
            flags=["credit_policy_review"],
            model_version=model_score.model_version,
        )
    if thin_file:
        return await _out(
            "credit_scoring",
            "CONDITIONAL_CREDIT",
            0.78,
            context,
            evidence,
            model_version=model_score.model_version,
        )
    if bureau_score >= 700 and model_score.score >= 0.45:
        return await _out(
            "credit_scoring",
            "CREDIT_ACCEPTABLE",
            0.86,
            context,
            evidence,
            model_version=model_score.model_version,
        )
    return await _out(
        "credit_scoring",
        "CREDIT_REVIEW",
        0.77,
        context,
        evidence,
        model_version=model_score.model_version,
    )


async def _policy_check(context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    core = _core(context)
    history = _history(context)
    external = _external(context)
    ratio = _debt_ratio(core)
    bureau_score = _num(external.get("bureau_score"), 700)
    evidence = [
        _evidence(
            "core",
            "case_value",
            core.get("case_value") or core.get("requested_loan_amount"),
        ),
        _evidence("core", "debt_ratio", ratio),
        _evidence("external", "bureau_score", bureau_score),
    ]
    prior_flags = [flag for output in prior for flag in output.flags]
    if prior_flags or bureau_score < 620:
        return await _out(
            "policy_check",
            "ESCALATE",
            0.69,
            context,
            evidence,
            flags=prior_flags or ["credit_policy_review"],
        )
    if ratio > 0.4 or _thin_file(core, history):
        return await _out("policy_check", "APPROVE_WITH_CONDITIONS", 0.82, context, evidence)
    return await _out("policy_check", "APPROVE", 0.88, context, evidence)


async def run_agent(name: str, context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    """Run the domain-specific specialist agent selected by name."""
    if name == "eligibility":
        return await _eligibility(context)
    if name == "credit_scoring":
        return await _credit_scoring(context)
    return await _policy_check(context, prior)
