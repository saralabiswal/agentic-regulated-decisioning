# Author: Sarala Biswal
"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from platform.observability.tracing import configure_tracing, instrument_fastapi
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

import structlog
from api.routers import (
    analytics,
    audit,
    config,
    health,
    intake,
    playbook,
    registry,
    streams,
    workbench,
)
from core.config import get_settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log process lifecycle events without mutating runtime state."""
    logger.info("startup", app_mode=get_settings().app_mode)
    yield
    logger.info("shutdown")


app = FastAPI(
    title="agentic-regulated-decisioning",
    description="Domain-plugin agentic decisioning platform for regulated industries",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
origins = [origin for origin in settings.cors_origins.split(",") if origin] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
configure_tracing()
instrument_fastapi(app)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Capture request timing for every API call before returning the response."""
    started = perf_counter()
    response = await call_next(request)
    logger.info(
        "request",
        path=request.url.path,
        status=response.status_code,
        duration_ms=int((perf_counter() - started) * 1000),
    )
    return response


app.include_router(intake.router, prefix="/api/v1")
app.include_router(workbench.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(registry.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")
app.include_router(playbook.router, prefix="/api/v1")
app.include_router(streams.router, prefix="/api/v1")
app.include_router(health.router)
