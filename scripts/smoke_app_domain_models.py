# Author: Sarala Biswal
"""Train and score app-oriented non-insurance model runtimes."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import sitecustomize  # noqa: F401, E402

APP_MODEL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "domain": "lending",
        "model_type": "credit",
        "version": "onnx-smoke",
        "model_family": "onnx",
        "features": {
            "case_value": 42_000,
            "confidence_hint": 0.82,
            "history_risk": 0.2,
            "external_risk": 0.22,
        },
    },
    {
        "domain": "healthcare",
        "model_type": "criteria",
        "version": "torch-smoke",
        "model_family": "torch",
        "features": {
            "case_value": 2_800,
            "confidence_hint": 0.88,
            "history_risk": 0.25,
            "external_risk": 0.12,
        },
    },
    {
        "domain": "wealth",
        "model_type": "suitability",
        "version": "tensorflow-smoke",
        "model_family": "tensorflow",
        "features": {
            "case_value": 500_000,
            "confidence_hint": 0.84,
            "history_risk": 0.3,
            "external_risk": 0.3,
        },
    },
)

_TARGETS = {
    f"{spec['domain']}-{spec['model_family']}": spec for spec in APP_MODEL_SPECS
}

_REQUIRED_PACKAGES = {
    "onnx": ["skl2onnx", "onnxruntime"],
    "torch": ["torch"],
    "tensorflow": ["tensorflow"],
}


def _selected_specs(target: str) -> tuple[dict[str, Any], ...]:
    if target == "all":
        return APP_MODEL_SPECS
    return (_TARGETS[target],)


def _missing_runtime_packages(specs: tuple[dict[str, Any], ...]) -> list[str]:
    packages: list[str] = []
    for spec in specs:
        for package in _REQUIRED_PACKAGES[str(spec["model_family"])]:
            if importlib.util.find_spec(package) is None:
                packages.append(package)
    return sorted(set(packages))


def _training_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "local_training_script",
        ROOT / "scripts" / "train_local_model.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load scripts/train_local_model.py.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    """Train each app runtime model and verify registry scoring."""
    parser = argparse.ArgumentParser(description="Smoke test app-oriented model runtimes.")
    parser.add_argument(
        "--target",
        choices=["all", *_TARGETS.keys()],
        default="all",
        help="Runtime target to smoke test.",
    )
    args = parser.parse_args()
    specs = _selected_specs(args.target)
    missing = _missing_runtime_packages(specs)
    if missing:
        raise RuntimeError(
            "Install app model optional runtimes before smoke testing: "
            f"{', '.join(missing)}. Run `uv sync --extra app-models`."
        )
    from platform.registry.model_registry import ModelRegistry

    train_and_register = _training_module().train_and_register

    results: list[dict[str, Any]] = []
    registry = ModelRegistry()
    for spec in specs:
        registered = train_and_register(
            domain=spec["domain"],
            model_type=spec["model_type"],
            version=spec["version"],
            stage="Production",
            model_family=spec["model_family"],
        )
        scoring = registry.get_production_model(
            spec["domain"],
            spec["model_type"],
        ).score(spec["features"])
        if scoring.model_version == "rules-fallback":
            raise RuntimeError(
                f"{spec['domain']} {spec['model_type']} fell back to rules after training."
            )
        results.append(
            {
                "domain": spec["domain"],
                "model_type": spec["model_type"],
                "model_family": spec["model_family"],
                "version": scoring.model_version,
                "score": scoring.score,
                "confidence": scoring.confidence,
                "mlflow_run_id": registered["mlflow_run_id"],
            }
        )
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
