# Author: Sarala Biswal
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _training_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "local_training_script",
        Path("scripts/train_local_model.py"),
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_non_insurance_synthetic_profiles_are_domain_specific() -> None:
    synthetic_training_data = _training_module()._synthetic_training_data
    lending_x, lending_y = synthetic_training_data("lending", "credit")
    healthcare_x, healthcare_y = synthetic_training_data("healthcare", "criteria")
    wealth_x, wealth_y = synthetic_training_data("wealth", "suitability")

    assert lending_x.shape == healthcare_x.shape == wealth_x.shape == (8, 4)
    expected_labels = [0, 0, 0, 0, 1, 1, 1, 1]
    assert lending_y.tolist() == healthcare_y.tolist() == wealth_y.tolist() == expected_labels
    assert lending_x.tolist() != healthcare_x.tolist()
    assert healthcare_x.tolist() != wealth_x.tolist()


def test_makefile_trains_non_insurance_production_models() -> None:
    makefile = Path("Makefile").read_text()

    assert "train-domain-models:" in makefile
    assert "train-app-domain-models:" in makefile
    assert "train-app-lending-onnx:" in makefile
    assert "train-app-healthcare-torch:" in makefile
    assert "train-app-wealth-tensorflow:" in makefile
    assert "smoke-app-domain-models:" in makefile
    assert "smoke-app-lending-onnx:" in makefile
    assert "smoke-app-healthcare-torch:" in makefile
    assert "smoke-app-wealth-tensorflow:" in makefile
    assert "--domain lending --model-type credit" in makefile
    assert "--domain healthcare --model-type criteria" in makefile
    assert "--domain wealth --model-type suitability" in makefile
    assert "--stage Production" in makefile
    assert "--model-family onnx" in makefile
    assert "--model-family torch" in makefile
    assert "--model-family tensorflow" in makefile
    assert "scripts/smoke_app_domain_models.py" in makefile
    assert "--target lending-onnx" in makefile
    assert "--target healthcare-torch" in makefile
    assert "--target wealth-tensorflow" in makefile


def test_pyproject_declares_app_model_optional_runtimes() -> None:
    pyproject = Path("pyproject.toml").read_text()

    assert "app-models" in pyproject
    assert '"skl2onnx"' in pyproject
    assert '"onnxruntime"' in pyproject
    assert '"torch"' in pyproject
    assert '"tensorflow"' in pyproject
