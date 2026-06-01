# Author: Sarala Biswal
"""Seed mock MLflow models."""

from __future__ import annotations

from pathlib import Path
from platform.registry.model_registry import ModelRegistry
from tempfile import TemporaryDirectory

from core.config import get_settings


def _seed_mlflow_model(domain: str, model_type: str) -> str:
    import mlflow
    import mlflow.sklearn
    import numpy as np
    from sklearn.linear_model import LogisticRegression

    tracking_uri = get_settings().mlflow_tracking_uri
    if tracking_uri.startswith("http"):
        mlflow.set_tracking_uri(tracking_uri)
    else:
        tracking_dir = Path(".local/mlruns").resolve()
        tracking_dir.mkdir(parents=True, exist_ok=True)
        mlflow.set_tracking_uri(tracking_dir.as_uri())
    mlflow.set_experiment("regulated-decisioning-seed-models")
    model_name = f"{domain}_{model_type}_scorer"
    x = np.array(
        [
            [0.1, 0.2, 0.2, 0.1],
            [0.3, 0.4, 0.4, 0.3],
            [0.6, 0.5, 0.7, 0.6],
            [0.8, 0.9, 0.8, 0.9],
        ]
    )
    y = np.array([0, 0, 1, 1])
    model = LogisticRegression().fit(x, y)
    with mlflow.start_run(run_name=model_name) as run:
        mlflow.log_param("domain", domain)
        mlflow.log_param("model_type", model_type)
        with TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "model"
            mlflow.sklearn.save_model(model, path=model_path)
            mlflow.log_artifacts(str(model_path), artifact_path="model")
        return run.info.run_id


def main() -> None:
    """Run this module as a command-line entry point."""
    registry = ModelRegistry()
    for domain, model_type in [
        ("insurance", "risk"),
        ("lending", "credit"),
        ("healthcare", "criteria"),
        ("wealth", "suitability"),
    ]:
        run_id = _seed_mlflow_model(domain, model_type)
        registry.register(domain, model_type, "1", "Production", run_id)
        registry.register(domain, model_type, "2", "Staging", f"seed-{domain}-{model_type}-shadow")
    print("Seeded local model registry metadata.")


if __name__ == "__main__":
    main()
