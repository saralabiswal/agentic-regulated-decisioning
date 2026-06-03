.PHONY: install docker-up docker-down migrate seed train-model train-domain-models train-app-domain-models train-app-lending-onnx train-app-healthcare-torch train-app-wealth-tensorflow smoke-app-domain-models smoke-app-lending-onnx smoke-app-healthcare-torch smoke-app-wealth-tensorflow live-smoke demo dev test lint typecheck format

# Install Python and frontend dependencies.
install:
	uv sync --all-extras
	cd ui && npm install

# Start local services for the full platform.
docker-up:
	docker compose up -d

# Stop local services.
docker-down:
	docker compose down

# Run database migrations. The demo uses auto-create helpers in mock mode.
migrate:
	uv run python -m platform.data.migrations

# Seed all four domains and mock models.
seed:
	uv run python -m seed.seed_all

# Train and register a local MLflow model. Override DOMAIN, MODEL_TYPE, VERSION, STAGE, FAMILY.
train-model:
	uv run python scripts/train_local_model.py --domain $${DOMAIN:-insurance} --model-type $${MODEL_TYPE:-risk} --version $${VERSION:-local-1} --stage $${STAGE:-Staging} --model-family $${FAMILY:-sklearn}

# Train and register local synthetic Production models for the non-insurance domains.
train-domain-models:
	uv run python scripts/train_local_model.py --domain lending --model-type credit --version $${VERSION:-local-1} --stage Production --model-family $${FAMILY:-sklearn}
	uv run python scripts/train_local_model.py --domain healthcare --model-type criteria --version $${VERSION:-local-1} --stage Production --model-family $${FAMILY:-sklearn}
	uv run python scripts/train_local_model.py --domain wealth --model-type suitability --version $${VERSION:-local-1} --stage Production --model-family $${FAMILY:-sklearn}

# Train and register app-oriented open-source runtime models for the non-insurance domains.
train-app-domain-models:
	uv run python scripts/train_local_model.py --domain lending --model-type credit --version $${LENDING_VERSION:-onnx-1} --stage Production --model-family onnx
	uv run python scripts/train_local_model.py --domain healthcare --model-type criteria --version $${HEALTHCARE_VERSION:-torch-1} --stage Production --model-family torch
	uv run python scripts/train_local_model.py --domain wealth --model-type suitability --version $${WEALTH_VERSION:-tensorflow-1} --stage Production --model-family tensorflow

train-app-lending-onnx:
	uv run python scripts/train_local_model.py --domain lending --model-type credit --version $${LENDING_VERSION:-onnx-1} --stage Production --model-family onnx

train-app-healthcare-torch:
	uv run python scripts/train_local_model.py --domain healthcare --model-type criteria --version $${HEALTHCARE_VERSION:-torch-1} --stage Production --model-family torch

train-app-wealth-tensorflow:
	uv run python scripts/train_local_model.py --domain wealth --model-type suitability --version $${WEALTH_VERSION:-tensorflow-1} --stage Production --model-family tensorflow

# Train and score the app-oriented runtime models end to end.
smoke-app-domain-models:
	uv run python scripts/smoke_app_domain_models.py

smoke-app-lending-onnx:
	uv run python scripts/smoke_app_domain_models.py --target lending-onnx

smoke-app-healthcare-torch:
	uv run python scripts/smoke_app_domain_models.py --target healthcare-torch

smoke-app-wealth-tensorflow:
	uv run python scripts/smoke_app_domain_models.py --target wealth-tensorflow

# Exercise PostgreSQL, Redis, and MLflow live service paths.
live-smoke:
	uv run python scripts/live_backend_smoke.py

# Run a single demo. Override DOMAIN, CASE, and JURISDICTION.
demo:
	uv run python demo.py --domain $${DOMAIN:-insurance} --case $${CASE:-commercial_property} --jurisdiction $${JURISDICTION:-US_CA}

# Start API and UI for development.
dev:
	uv run python -m uvicorn api.main:app --reload --port 8000

# Run tests with coverage.
test:
	uv run pytest

# Run Ruff linting.
lint:
	uv run ruff check .

# Run mypy type checking.
typecheck:
	uv run mypy .

# Format Python code.
format:
	uv run ruff format .
