.PHONY: install docker-up docker-down migrate seed train-model live-smoke demo dev test lint typecheck format

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
