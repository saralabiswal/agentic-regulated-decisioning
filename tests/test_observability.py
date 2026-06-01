# Author: Sarala Biswal
from __future__ import annotations

from platform.data.store import connect, migrate
from platform.observability.cost_tracker import CostTracker
from platform.observability.tracing import configure_tracing, trace_span
from platform.registry.model_registry import ModelRegistry
from platform.registry.model_runtime import coerce_probability

import pytest


@pytest.mark.asyncio
async def test_cost_tracker_and_registry():
    cost = CostTracker().record_llm_call(
        "insurance", "triage", "openai", "openai/gpt-4o-mini", 1000, 1000
    )
    assert cost == pytest.approx(0.00075)
    summary = await CostTracker().get_cost_summary("insurance")
    assert summary["total_cost"] >= cost
    result, shadow = ModelRegistry().run_with_shadow("unseeded", "risk", {"case_value": 1000})
    assert result.model_version == "rules-fallback"
    assert shadow is None
    ModelRegistry().register("insurance", "risk", "1", "Production")
    ModelRegistry().register("insurance", "risk", "2", "Staging")
    production, shadow = ModelRegistry().run_with_shadow(
        "insurance", "risk", {"case_value": 1000}
    )
    assert production.model_version == "1"
    assert shadow and shadow.model_version == "2"
    assert ModelRegistry().promote("insurance", "risk", "2", "Production")["version"] == "2"
    assert ModelRegistry().rollback("insurance", "risk")["rolled_back"]
    migrate()
    with connect() as db:
        model_events = db.execute(
            """
            SELECT audit_id FROM audit_records
            WHERE domain = ? AND decision_type = ?
            """,
            ("insurance", "model_event"),
        ).fetchall()
    assert model_events
    assert configure_tracing()["configured"]
    with trace_span("test.span", {"domain": "insurance", "sample.count": 1}) as span:
        assert span is not None


def test_model_runtime_probability_parsing():
    assert coerce_probability([{"score": 0.67}]) == pytest.approx(0.67)
    assert coerce_probability([[0.2, 0.8]]) == pytest.approx(0.8)
    assert coerce_probability(2.0) == pytest.approx(1.0)


def test_registry_uses_loaded_mlflow_prediction(monkeypatch: pytest.MonkeyPatch):
    from platform.registry import model_registry
    from platform.registry.model_runtime import ModelRuntimePrediction

    def fake_score_mlflow_run(**kwargs):
        return ModelRuntimePrediction(
            score=0.73,
            confidence=0.91,
            feature_importance={"case_value": 1.0},
            runtime_flavor="pyfunc",
        )

    monkeypatch.setattr(model_registry, "score_mlflow_run", fake_score_mlflow_run)
    ModelRegistry().register("runtime", "risk", "loaded", "Production", "real-run-id")
    result, shadow = ModelRegistry().run_with_shadow(
        "runtime", "risk", {"case_value": 250_000}
    )
    assert shadow is None
    assert result.score == pytest.approx(0.73)
    assert result.confidence == pytest.approx(0.91)
    assert result.model_version == "loaded"
