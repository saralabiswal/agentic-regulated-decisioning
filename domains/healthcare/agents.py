# Author: Sarala Biswal
"""Healthcare prior-authorization specialist agents."""

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


def _notes_complete(core: dict[str, Any]) -> bool:
    if "clinical_notes_complete" in core:
        return bool(core["clinical_notes_complete"])
    return bool(core.get("notes_complete", True))


def _conservative_duration(core: dict[str, Any]) -> float:
    return _num(core.get("conservative_treatment_duration_weeks"), 6.0)


def _evidence(source: str, field: str, value: object, confidence: float = 0.9) -> EvidenceRef:
    return EvidenceRef(
        source=source,
        field=field,
        value=value,
        retrieved_at=datetime.now(UTC),
        confidence=confidence,
    )


async def _criteria_model_score(core: dict[str, Any], external: dict[str, Any]):
    features = {
        "case_value": _num(core.get("case_value") or core.get("estimated_cost")),
        "confidence_hint": 0.9 if external.get("criteria_met", True) else 0.35,
        "history_risk": 0.4,
        "external_risk": 0.2 if external.get("criteria_met", True) else 0.8,
    }
    model = await ModelRegistry().aget_production_model("healthcare", "criteria")
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
        f"Healthcare {agent_type} produced {decision} using clinical completeness, "
        "medical-necessity criteria, prior authorization history, and coverage rules."
    )
    explanation = await generate_agent_explanation(
        domain="healthcare",
        agent_type=agent_type,
        decision=decision,
        confidence=confidence,
        evidence={
            "case_type": core.get("case_type"),
            "procedure": core.get("procedure") or core.get("procedure_description"),
            "criteria_met": external.get("criteria_met"),
            "notes_complete": _notes_complete(core),
            "model_version": model_version,
            "flags": flags or [],
        },
        fallback=explanation,
    )
    return AgentOutput(
        agent_id=f"healthcare_{agent_type}",
        agent_type=agent_type,
        decision=decision,
        confidence=confidence,
        evidence=evidence,
        flags=flags or [],
        explanation=explanation,
        processing_ms=1,
    )


async def _clinical_triage(context: UnifiedContext) -> AgentOutput:
    core = _core(context)
    history = _history(context)
    notes_complete = _notes_complete(core)
    case_value = _num(core.get("case_value") or core.get("estimated_cost"))
    complexity = core.get("complexity")
    evidence = [
        _evidence("core", "clinical_notes_complete", notes_complete),
        _evidence("core", "case_value", case_value),
        _evidence("history", "prior_auths", history.get("prior_auths", [])),
    ]
    if not notes_complete:
        return await _out(
            "clinical_triage",
            "CLINICAL_DOCUMENTATION_REVIEW",
            0.62,
            context,
            evidence,
            flags=["incomplete_clinical_notes"],
        )
    if complexity == "multi_system":
        return await _out("clinical_triage", "COMPLEX_CLINICAL_REVIEW", 0.78, context, evidence)
    return await _out("clinical_triage", "CLINICALLY_COMPLETE", 0.88, context, evidence)


async def _criteria_check(context: UnifiedContext) -> AgentOutput:
    core = _core(context)
    external = _external(context)
    criteria_met = bool(external.get("criteria_met", True))
    duration = _conservative_duration(core)
    model_score = await _criteria_model_score(core, external)
    evidence = [
        _evidence("external", "criteria_met", criteria_met),
        _evidence("core", "conservative_treatment_duration_weeks", duration),
        _evidence("model_registry", "model_version", model_score.model_version, 0.8),
        _evidence("model_registry", "criteria_score", round(model_score.score, 4), 0.8),
    ]
    if not criteria_met:
        return await _out(
            "criteria_check",
            "CRITERIA_NOT_MET",
            0.64,
            context,
            evidence,
            flags=["criteria_gap"],
            model_version=model_score.model_version,
        )
    if core.get("case_type") in {"prior_auth", "prior_auth_imaging"} and duration < 4:
        return await _out(
            "criteria_check",
            "CRITERIA_REVIEW",
            0.77,
            context,
            evidence,
            model_version=model_score.model_version,
        )
    return await _out(
        "criteria_check",
        "CRITERIA_MET",
        0.87,
        context,
        evidence,
        model_version=model_score.model_version,
    )


async def _coverage_rules(context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    core = _core(context)
    external = _external(context)
    evidence = [
        _evidence("core", "procedure_code", core.get("procedure_code") or core.get("cpt")),
        _evidence("external", "criteria", external.get("criteria")),
        _evidence("core", "site_of_service", core.get("site_of_service")),
    ]
    prior_flags = [flag for output in prior for flag in output.flags]
    if prior_flags:
        return await _out("coverage_rules", "ESCALATE", 0.66, context, evidence, flags=prior_flags)
    if core.get("cpt") or core.get("procedure_code"):
        return await _out("coverage_rules", "APPROVE_WITH_CODES", 0.88, context, evidence)
    return await _out("coverage_rules", "APPROVE", 0.86, context, evidence)


async def run_agent(name: str, context: UnifiedContext, prior: list[AgentOutput]) -> AgentOutput:
    """Run the domain-specific specialist agent selected by name."""
    if name == "clinical_triage":
        return await _clinical_triage(context)
    if name == "criteria_check":
        return await _criteria_check(context)
    return await _coverage_rules(context, prior)
