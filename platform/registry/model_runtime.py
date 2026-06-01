# Author: Sarala Biswal
"""Local MLflow model scoring helpers.

The registry stores model metadata. This module owns runtime loading so the
registry can support multiple open-source model families behind one scoring
contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FEATURE_COLUMNS = ("case_value", "confidence_hint", "history_risk", "external_risk")


@dataclass(frozen=True)
class ModelRuntimePrediction:
    """Normalized model runtime prediction with score, confidence, and importance."""
    score: float
    confidence: float
    feature_importance: dict[str, float]
    runtime_flavor: str


def build_feature_values(features: dict[str, Any]) -> list[float]:
    """Project feature dictionaries into the model runtime feature order."""
    return [
        float(features.get("case_value") or features.get("tiv") or 0) / 10_000_000,
        float(features.get("confidence_hint", 0.5)),
        float(features.get("history_risk", 0.5)),
        float(features.get("external_risk", 0.5)),
    ]


def build_feature_importance(features: dict[str, Any]) -> dict[str, float]:
    """Build deterministic feature-importance weights for fallback scoring."""
    if not features:
        return {column: 1 / len(FEATURE_COLUMNS) for column in FEATURE_COLUMNS}
    return {key: 1 / len(features) for key in features}


def _clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, value))


def _records_from_prediction(prediction: Any) -> Any:
    if hasattr(prediction, "to_dict"):
        try:
            return prediction.to_dict(orient="records")
        except TypeError:
            return prediction.to_dict()
    if hasattr(prediction, "tolist"):
        return prediction.tolist()
    return prediction


def coerce_probability(prediction: Any) -> float:
    """Normalize common model output shapes into a 0..1 probability."""
    value = _records_from_prediction(prediction)
    if isinstance(value, dict):
        for key in ("score", "probability", "risk_score", "positive_probability", "1"):
            if key in value:
                return _clamp_probability(float(value[key]))
        if value:
            return coerce_probability(next(iter(value.values())))
    if isinstance(value, list | tuple):
        if not value:
            return 0.5
        first = value[0]
        if isinstance(first, dict):
            return coerce_probability(first)
        if isinstance(first, list | tuple):
            if len(first) > 1:
                return _clamp_probability(float(first[1]))
            return coerce_probability(first[0])
        return _clamp_probability(float(first))
    return _clamp_probability(float(value))


def _feature_frame(features: dict[str, Any]) -> Any:
    import pandas as pd

    values = build_feature_values(features)
    return pd.DataFrame([values], columns=FEATURE_COLUMNS)


def _score_native_probability_model(
    *,
    model_uri: str,
    tracking_uri: str,
    features: dict[str, Any],
) -> ModelRuntimePrediction | None:
    try:
        import mlflow
        import mlflow.sklearn
        import numpy as np

        mlflow.set_tracking_uri(tracking_uri)
        model = mlflow.sklearn.load_model(model_uri)
        if not hasattr(model, "predict_proba"):
            return None
        vector = np.array([build_feature_values(features)])
        probability = float(model.predict_proba(vector)[0][1])
        return ModelRuntimePrediction(
            score=_clamp_probability(probability),
            confidence=0.82,
            feature_importance={
                "case_value": 0.4,
                "confidence_hint": 0.2,
                "history_risk": 0.2,
                "external_risk": 0.2,
            },
            runtime_flavor="native_probability",
        )
    except Exception:
        return None


def _score_pyfunc_model(
    *,
    model_uri: str,
    tracking_uri: str,
    features: dict[str, Any],
) -> ModelRuntimePrediction | None:
    try:
        import mlflow
        import mlflow.pyfunc

        mlflow.set_tracking_uri(tracking_uri)
        model = mlflow.pyfunc.load_model(model_uri)
        probability = coerce_probability(model.predict(_feature_frame(features)))
        return ModelRuntimePrediction(
            score=probability,
            confidence=0.8,
            feature_importance=build_feature_importance(features),
            runtime_flavor="pyfunc",
        )
    except Exception:
        return None


def score_mlflow_run(
    *,
    mlflow_run_id: str,
    tracking_uri: str,
    features: dict[str, Any],
) -> ModelRuntimePrediction | None:
    """Load a model from MLflow and score it with native or pyfunc fallback."""
    if mlflow_run_id in {"local", ""} or mlflow_run_id.startswith("seed-"):
        return None
    model_uri = f"runs:/{mlflow_run_id}/model"
    return _score_native_probability_model(
        model_uri=model_uri,
        tracking_uri=tracking_uri,
        features=features,
    ) or _score_pyfunc_model(
        model_uri=model_uri,
        tracking_uri=tracking_uri,
        features=features,
    )
