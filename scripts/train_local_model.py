# Author: Sarala Biswal
"""Train and register a local MLflow model for a domain scorer."""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sitecustomize  # noqa: F401, E402

from mlflow.pyfunc import PythonModel

from core.config import get_settings
from platform.registry.model_registry import ModelRegistry
from platform.registry.model_runtime import FEATURE_COLUMNS


def _configure_mlflow() -> Any:
    import mlflow

    tracking_uri = get_settings().mlflow_tracking_uri
    if tracking_uri.startswith("http"):
        mlflow.set_tracking_uri(tracking_uri)
    else:
        tracking_dir = Path(".local/mlruns").resolve()
        tracking_dir.mkdir(parents=True, exist_ok=True)
        mlflow.set_tracking_uri(tracking_dir.as_uri())
    mlflow.set_experiment("regulated-decisioning-local-models")
    return mlflow


def _synthetic_training_data() -> tuple[Any, Any]:
    import numpy as np

    x = np.array(
        [
            [0.05, 0.15, 0.10, 0.10],
            [0.12, 0.25, 0.20, 0.15],
            [0.20, 0.35, 0.30, 0.25],
            [0.35, 0.45, 0.45, 0.40],
            [0.55, 0.65, 0.70, 0.60],
            [0.75, 0.80, 0.85, 0.90],
            [0.90, 0.90, 0.95, 0.95],
            [0.65, 0.75, 0.80, 0.70],
        ]
    )
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    return x, y


def _save_sklearn_compatible_model(mlflow: Any, model: Any) -> None:
    import mlflow.sklearn

    with TemporaryDirectory() as tmp_dir:
        model_path = Path(tmp_dir) / "model"
        mlflow.sklearn.save_model(model, path=model_path)
        mlflow.log_artifacts(str(model_path), artifact_path="model")


def _train_sklearn(logistic: bool = True) -> Any:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression

    x, y = _synthetic_training_data()
    model = LogisticRegression() if logistic else GradientBoostingClassifier(random_state=7)
    return model.fit(x, y)


def _train_xgboost() -> Any:
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("Install xgboost locally to train model_family=xgboost.") from exc

    x, y = _synthetic_training_data()
    model = XGBClassifier(
        n_estimators=20,
        max_depth=2,
        learning_rate=0.2,
        eval_metric="logloss",
        random_state=7,
    )
    return model.fit(x, y)


def _train_lightgbm() -> Any:
    try:
        from lightgbm import LGBMClassifier
    except ImportError as exc:
        raise RuntimeError("Install lightgbm locally to train model_family=lightgbm.") from exc

    x, y = _synthetic_training_data()
    model = LGBMClassifier(n_estimators=20, max_depth=2, learning_rate=0.2, random_state=7)
    return model.fit(x, y)


class WeightedRiskPyFunc(PythonModel):
    """Simple MLflow pyfunc model used for deterministic local risk scoring."""
    def predict(self, context, model_input, params=None):
        """Return deterministic risk probabilities for MLflow pyfunc scoring."""
        rows = model_input[list(FEATURE_COLUMNS)].to_numpy()
        results: list[dict[str, float]] = []
        for row in rows:
            score = 0.40 * row[0] + 0.20 * row[1] + 0.25 * row[2] + 0.15 * row[3]
            results.append({"score": max(0.0, min(1.0, float(score)))})
        return results


def _save_pyfunc_model(
    mlflow: Any,
    python_model: Any,
    artifacts: dict[str, str] | None = None,
) -> None:
    import mlflow.pyfunc

    with TemporaryDirectory() as tmp_dir:
        model_path = Path(tmp_dir) / "model"
        mlflow.pyfunc.save_model(
            path=str(model_path),
            python_model=python_model,
            artifacts=artifacts,
        )
        mlflow.log_artifacts(str(model_path), artifact_path="model")


class OnnxRiskPyFunc(PythonModel):
    """MLflow pyfunc wrapper that loads and scores an ONNX risk model."""
    def load_context(self, context: Any) -> None:
        """Load model artifacts from the MLflow pyfunc context."""
        import onnxruntime as runtime

        self.session = runtime.InferenceSession(context.artifacts["onnx_model"])

    def predict(self, context, model_input, params=None):
        """Return deterministic risk probabilities for MLflow pyfunc scoring."""
        rows = model_input[list(FEATURE_COLUMNS)].to_numpy().astype("float32")
        input_name = self.session.get_inputs()[0].name
        probabilities = self.session.run(None, {input_name: rows})[-1]
        results: list[dict[str, float]] = []
        for probability in probabilities:
            if isinstance(probability, dict):
                score = probability.get(1, probability.get("1", 0.5))
            else:
                score = probability[1] if len(probability) > 1 else probability[0]
            results.append({"score": float(score if score is not None else 0.5)})
        return results


def _save_onnx_model(mlflow: Any) -> None:
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
    except ImportError as exc:
        raise RuntimeError(
            "Install skl2onnx and onnxruntime locally to train model_family=onnx."
        ) from exc

    model = _train_sklearn()
    onnx_model = convert_sklearn(
        model,
        initial_types=[("features", FloatTensorType([None, len(FEATURE_COLUMNS)]))],
    )
    with TemporaryDirectory() as tmp_dir:
        artifact_path = Path(tmp_dir) / "risk_model.onnx"
        artifact_path.write_bytes(onnx_model.SerializeToString())
        _save_pyfunc_model(mlflow, OnnxRiskPyFunc(), {"onnx_model": str(artifact_path)})


class TorchRiskPyFunc(PythonModel):
    """MLflow pyfunc wrapper that loads and scores a Torch risk model."""
    def load_context(self, context: Any) -> None:
        """Load model artifacts from the MLflow pyfunc context."""
        import torch

        self.torch = torch
        self.model = torch.nn.Sequential(
            torch.nn.Linear(len(FEATURE_COLUMNS), 1),
            torch.nn.Sigmoid(),
        )
        self.model.load_state_dict(torch.load(context.artifacts["state"], map_location="cpu"))
        self.model.eval()

    def predict(self, context, model_input, params=None):
        """Return deterministic risk probabilities for MLflow pyfunc scoring."""
        rows = model_input[list(FEATURE_COLUMNS)].to_numpy().astype("float32")
        with self.torch.no_grad():
            tensor = self.torch.tensor(rows)
            scores = self.model(tensor).numpy().ravel()
        return [{"score": float(score)} for score in scores]


def _save_torch_model(mlflow: Any) -> None:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Install torch locally to train model_family=torch.") from exc

    x, y = _synthetic_training_data()
    tensor_x = torch.tensor(x, dtype=torch.float32)
    tensor_y = torch.tensor(y.reshape(-1, 1), dtype=torch.float32)
    model = torch.nn.Sequential(torch.nn.Linear(len(FEATURE_COLUMNS), 1), torch.nn.Sigmoid())
    optimizer = torch.optim.Adam(model.parameters(), lr=0.05)
    loss_fn = torch.nn.BCELoss()
    for _ in range(200):
        optimizer.zero_grad()
        loss = loss_fn(model(tensor_x), tensor_y)
        loss.backward()
        optimizer.step()
    with TemporaryDirectory() as tmp_dir:
        state_path = Path(tmp_dir) / "state.pt"
        torch.save(model.state_dict(), state_path)
        _save_pyfunc_model(mlflow, TorchRiskPyFunc(), {"state": str(state_path)})


class TensorFlowRiskPyFunc(PythonModel):
    """MLflow pyfunc wrapper that loads and scores a TensorFlow risk model."""
    def load_context(self, context: Any) -> None:
        """Load model artifacts from the MLflow pyfunc context."""
        import tensorflow as tensor_flow

        self.model = tensor_flow.keras.models.load_model(context.artifacts["model"])

    def predict(self, context, model_input, params=None):
        """Return deterministic risk probabilities for MLflow pyfunc scoring."""
        rows = model_input[list(FEATURE_COLUMNS)].to_numpy().astype("float32")
        scores = self.model.predict(rows, verbose=0).ravel()
        return [{"score": float(score)} for score in scores]


def _save_tensorflow_model(mlflow: Any) -> None:
    try:
        import tensorflow as tensor_flow
    except ImportError as exc:
        raise RuntimeError("Install tensorflow locally to train model_family=tensorflow.") from exc

    x, y = _synthetic_training_data()
    model = tensor_flow.keras.Sequential(
        [
            tensor_flow.keras.layers.Input(shape=(len(FEATURE_COLUMNS),)),
            tensor_flow.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="binary_crossentropy")
    model.fit(x, y, epochs=50, verbose=0)
    with TemporaryDirectory() as tmp_dir:
        model_path = Path(tmp_dir) / "model.keras"
        model.save(model_path)
        _save_pyfunc_model(mlflow, TensorFlowRiskPyFunc(), {"model": str(model_path)})


def train_and_register(
    *,
    domain: str,
    model_type: str,
    version: str,
    stage: str,
    model_family: str,
) -> dict[str, Any]:
    """Train the requested local model family and register it with MLflow."""
    mlflow = _configure_mlflow()
    model_name = f"{domain}_{model_type}_scorer"
    with mlflow.start_run(run_name=f"{model_name}_{model_family}") as run:
        mlflow.log_param("domain", domain)
        mlflow.log_param("model_type", model_type)
        mlflow.log_param("model_family", model_family)
        mlflow.log_param("feature_columns", ",".join(FEATURE_COLUMNS))
        if model_family == "sklearn":
            _save_sklearn_compatible_model(mlflow, _train_sklearn())
        elif model_family == "gradient_boosting":
            _save_sklearn_compatible_model(mlflow, _train_sklearn(logistic=False))
        elif model_family == "xgboost":
            _save_sklearn_compatible_model(mlflow, _train_xgboost())
        elif model_family == "lightgbm":
            _save_sklearn_compatible_model(mlflow, _train_lightgbm())
        elif model_family == "pyfunc":
            _save_pyfunc_model(mlflow, WeightedRiskPyFunc())
        elif model_family == "onnx":
            _save_onnx_model(mlflow)
        elif model_family == "torch":
            _save_torch_model(mlflow)
        elif model_family == "tensorflow":
            _save_tensorflow_model(mlflow)
        else:
            raise ValueError(f"Unsupported model_family: {model_family}")
        run_id = run.info.run_id
    registry_result = ModelRegistry().register(domain, model_type, version, stage, run_id)
    return {
        **registry_result,
        "model_family": model_family,
        "mlflow_run_id": run_id,
    }


def main() -> None:
    """Run this module as a command-line entry point."""
    parser = argparse.ArgumentParser(description="Train and register a local model.")
    parser.add_argument("--domain", default="insurance")
    parser.add_argument("--model-type", default="risk")
    parser.add_argument("--version", default="local-1")
    parser.add_argument("--stage", default="Staging")
    parser.add_argument(
        "--model-family",
        choices=[
            "sklearn",
            "gradient_boosting",
            "xgboost",
            "lightgbm",
            "pyfunc",
            "onnx",
            "torch",
            "tensorflow",
        ],
        default="sklearn",
    )
    args = parser.parse_args()
    result = train_and_register(
        domain=args.domain,
        model_type=args.model_type,
        version=args.version,
        stage=args.stage,
        model_family=args.model_family,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
